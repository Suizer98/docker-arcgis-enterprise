#!/usr/bin/env python3

import json
import logging
import os
from typing import Dict, Any, List, Optional
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from fastapi_mcp import FastApiMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API
class ListServicesRequest(BaseModel):
    pass  # No parameters needed - always return all services

class GetServiceDetailsRequest(BaseModel):
    service_name: str
    folder: Optional[str] = ""

class GetPortalTokenRequest(BaseModel):
    expiration: int = 60

class ArcGISFastAPIServer:
    def __init__(self):
        # ArcGIS configuration - all values must be provided via environment variables
        self.server_url = os.getenv("ARCGIS_SERVER_URL")
        self.portal_url = os.getenv("ARCGIS_PORTAL_URL")
        self.username = os.getenv("MCP_USERNAME")
        self.password = os.getenv("MCP_PASSWORD")
        self.portal_token = None
        self.token_expires_at = None
        
        # Validate required environment variables
        required_vars = {
            "ARCGIS_SERVER_URL": self.server_url,
            "ARCGIS_PORTAL_URL": self.portal_url,
            "ARCGIS_USERNAME": self.username,
            "ARCGIS_PASSWORD": self.password
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
    def _is_token_expired(self) -> bool:
        if not self.portal_token or not self.token_expires_at:
            return True
        
        import datetime
        now = datetime.datetime.now()
        # Consider token expired if it expires within 5 minutes
        buffer_time = datetime.timedelta(minutes=5)
        return now >= (self.token_expires_at - buffer_time)
    
    async def _ensure_valid_token(self) -> bool:
        if self._is_token_expired():
            logger.info("Token expired or missing, generating new token...")
            # Generate a new token for 1 hour (3600 seconds)
            token = await self.get_portal_token(expiration=3600)
            if token:
                import datetime
                self.token_expires_at = datetime.datetime.now() + datetime.timedelta(hours=1)
                logger.info(f"New token generated, expires at: {self.token_expires_at}")
                return True
            else:
                logger.error("Failed to generate new token")
                return False
        else:
            logger.info(f"Using existing token, expires at: {self.token_expires_at}")
            return True
    
    def get_token_status(self) -> Dict[str, Any]:
        import datetime
        now = datetime.datetime.now()
        
        status = {
            "has_token": bool(self.portal_token),
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "is_expired": self._is_token_expired(),
            "current_time": now.isoformat()
        }
        
        if self.token_expires_at:
            time_until_expiry = self.token_expires_at - now
            status["minutes_until_expiry"] = int(time_until_expiry.total_seconds() / 60)
        
        return status
    
    async def get_portal_token(self, expiration: int = 60) -> Optional[str]:
        """Get authentication token from ArcGIS Portal"""
        if not self.username or not self.password:
            raise ValueError("ARCGIS_USERNAME and ARCGIS_PASSWORD environment variables are required")
        
        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0, follow_redirects=True) as client:
                token_url = f"{self.portal_url}/arcgis/sharing/rest/generateToken"
                data = {
                    "username": self.username,
                    "password": self.password,
                    "client": "referer",
                    "referer": "http://localhost:8000",
                    "expiration": str(expiration),
                    "f": "json"
                }
                
                response = await client.post(token_url, data=data)
                
                if response.status_code == 200:
                    token_data = response.json()
                    if "token" in token_data:
                        self.portal_token = token_data["token"]
                        return self.portal_token
                    else:
                        logger.error(f"Token response error: {token_data}")
                        return None
                else:
                    logger.error(f"Token request failed: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error getting Portal token: {e}")
            return None
    
    async def call_arcgis_api(self, endpoint: str = "", use_token: bool = False) -> Dict[str, Any]:
        """Call ArcGIS REST API"""
        try:
            # Ensure we have a valid token if needed
            if use_token:
                await self._ensure_valid_token()
            
            async with httpx.AsyncClient(verify=False, timeout=10.0, follow_redirects=True) as client:
                if endpoint:
                    url = f"{self.server_url}/{endpoint}?f=json"
                else:
                    url = f"{self.server_url}?f=json"
                
                # Add token if available and needed
                if use_token and self.portal_token:
                    url += f"&token={self.portal_token}"
                    logger.info(f"Using token for API call: {endpoint}")
                else:
                    logger.info(f"Making API call without token: {endpoint}")
                
                response = await client.get(url)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"API Error: {response.status_code}")
                    return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return {"error": str(e)}
    
    async def list_services(self) -> List[Dict[str, Any]]:
        """List all ArcGIS services from all folders"""
        try:
            all_services = []
            
            # Get root services (with token)
            root_result = await self.call_arcgis_api("", use_token=True)
            if "services" in root_result:
                all_services.extend(root_result["services"])
            
            # Get services from folders (token needed)
            if "folders" in root_result:
                for folder in root_result["folders"]:
                    folder_result = await self.call_arcgis_api(folder, use_token=True)
                    if "services" in folder_result:
                        for service in folder_result["services"]:
                            service["folder"] = folder
                        all_services.extend(folder_result["services"])
            
            # Categorize services intelligently
            for service in all_services:
                folder = service.get("folder", "")
                service_name = service.get("name", "")
                service_type = service.get("type", "")
                
                # Smart categorization based on service characteristics
                if self._is_system_service(service_name, folder, service_type):
                    service["category"] = "system"
                    service["category_description"] = "System/Utility service"
                elif self._is_hosted_service(service_name, folder, service_type):
                    service["category"] = "hosted"
                    service["category_description"] = "Hosted service"
                else:
                    service["category"] = "custom"
                    service["category_description"] = "Custom service"
            
            # Group services by category for summary
            categorized = {
                "system": [s for s in all_services if s.get("category") == "system"],
                "hosted": [s for s in all_services if s.get("category") == "hosted"],
                "custom": [s for s in all_services if s.get("category") == "custom"]
            }
            
            return {
                "services": all_services,
                "count": len(all_services),
                "categorized": categorized,
                "summary": {
                    "system_services": len(categorized["system"]),
                    "hosted_services": len(categorized["hosted"]),
                    "custom_services": len(categorized["custom"])
                }
            }
        except Exception as e:
            logger.error(f"Error listing services: {e}")
            return {"error": str(e)}
    
    def _is_system_service(self, service_name: str, folder: str, service_type: str) -> bool:
        """Determine if a service is a system/utility service based on intelligent analysis"""
        # System folder indicators
        system_folders = ["System", "Utilities"]
        if folder in system_folders:
            return True
        
        # Service type indicators
        system_types = ["GPServer", "SymbolServer"]
        if service_type in system_types:
            return True
        
        # Service name patterns that indicate system services
        system_patterns = [
            "caching", "cache", "tools", "utilities", "utility", "system", "admin",
            "management", "controller", "service", "geocoding", "printing", "raster",
            "symbol", "offline", "packaging", "sync", "validation", "version",
            "topographic", "production", "network", "location", "referencing",
            "parcel", "fabric", "publishing", "reporting", "scene", "spatial",
            "analysis", "offline"
        ]
        
        service_lower = service_name.lower()
        for pattern in system_patterns:
            if pattern in service_lower:
                return True
        
        return False
    
    def _is_hosted_service(self, service_name: str, folder: str, service_type: str) -> bool:
        """Determine if a service is a hosted service based on intelligent analysis"""
        # Hosted folder indicator
        if folder == "Hosted":
            return True
        
        # Service type indicators for hosted services
        hosted_types = ["FeatureServer", "MapServer"]
        if service_type in hosted_types and folder == "Hosted":
            return True
        
        # Service name patterns that indicate hosted services
        hosted_patterns = [
            "hosted", "gdb", "database", "feature", "map", "layer", "data"
        ]
        
        service_lower = service_name.lower()
        for pattern in hosted_patterns:
            if pattern in service_lower and folder == "Hosted":
                return True
        
        return False
    
    async def get_service_details(self, service_name: str, folder: Optional[str] = "") -> Dict[str, Any]:
        """Get detailed information about a specific service - tries both MapServer and FeatureServer"""
        try:
            # First, get the service list to find the actual service type
            services_result = await self.list_services()
            
            # Extract the services array from the result
            if isinstance(services_result, dict) and "services" in services_result:
                services = services_result["services"]
            elif isinstance(services_result, list):
                services = services_result
            else:
                return {"error": "Failed to get services list"}
            
            # Normalize folder parameter
            folder = folder or ""
            
            # Find the matching service
            matching_service = None
            for service in services:
                service_name_from_list = service.get("name", "")
                service_folder_from_list = service.get("folder", "")
                
                # Handle case where service_name includes folder path (e.g., "Hosted/TouristAttractions")
                if "/" in service_name:
                    # Extract folder and service name from the full path
                    path_parts = service_name.split("/")
                    if len(path_parts) == 2:
                        input_folder, input_service_name = path_parts
                        if (service_name_from_list == f"{input_folder}/{input_service_name}" and 
                            service_folder_from_list == input_folder):
                            matching_service = service
                            folder = input_folder
                            service_name = input_service_name
                            break
                
                # Handle both formats: "ServiceName" with folder="Folder" and "Folder/ServiceName" with folder="Folder"
                if service_name_from_list == service_name and service_folder_from_list == folder:
                    matching_service = service
                    break
                elif service_name_from_list == f"{folder}/{service_name}" and service_folder_from_list == folder:
                    matching_service = service
                    break
                elif service_name_from_list == service_name and not folder and not service_folder_from_list:
                    matching_service = service
                    break
                # Handle case where service_name_from_list is "Folder/ServiceName" and we're looking for just "ServiceName"
                elif service_name_from_list.endswith(f"/{service_name}") and service_folder_from_list == folder:
                    matching_service = service
                    service_name = service_name_from_list.split("/")[-1]  # Extract just the service name
                    break
            
            if not matching_service:
                return {"error": f"Service '{service_name}' not found in folder '{folder}'"}
            
            # Determine the service type
            service_type = matching_service.get("type", "MapServer")
            
            # Construct endpoint based on actual service type
            if folder:
                endpoint = f"{folder}/{service_name}/{service_type}"
            else:
                endpoint = f"{service_name}/{service_type}"
            
            result = await self.call_arcgis_api(endpoint, use_token=True)
            
            # Add service metadata to the result
            if "error" not in result:
                result["service_metadata"] = {
                    "name": service_name,
                    "folder": folder,
                    "type": service_type,
                    "full_path": f"{folder}/{service_name}" if folder else service_name
                }
            
            return result
        except Exception as e:
            logger.error(f"Error getting service details: {e}")
            return {"error": str(e)}
    
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to ArcGIS Server and Portal"""
        results = {
            "server": {"status": "unknown", "url": self.server_url},
            "portal": {"status": "unknown", "url": self.portal_url},
            "credentials": {"configured": bool(self.username and self.password)}
        }
        
        # Test server connection
        try:
            server_result = await self.call_arcgis_api("")
            if "error" not in server_result:
                results["server"]["status"] = "connected"
                results["server"]["services_count"] = len(server_result.get("services", []))
                results["server"]["folders_count"] = len(server_result.get("folders", []))
            else:
                results["server"]["status"] = "error"
                results["server"]["error"] = server_result["error"]
        except Exception as e:
            results["server"]["status"] = "error"
            results["server"]["error"] = str(e)
        
        # Test portal connection
        try:
            if self.username and self.password:
                token = await self.get_portal_token()
                if token:
                    results["portal"]["status"] = "connected"
                    results["portal"]["token_obtained"] = True
                else:
                    results["portal"]["status"] = "error"
                    results["portal"]["error"] = "Failed to obtain token"
            else:
                results["portal"]["status"] = "error"
                results["portal"]["error"] = "No credentials configured"
        except Exception as e:
            results["portal"]["status"] = "error"
            results["portal"]["error"] = str(e)
        
        return results
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get basic server information"""
        try:
            result = await self.call_arcgis_api("")
            return {
                "server_url": self.server_url,
                "services_count": len(result.get("services", [])),
                "folders": result.get("folders", []),
                "server_version": result.get("currentVersion", "unknown")
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def get_portal_info(self) -> Dict[str, Any]:
        """Get basic portal information"""
        return {
            "portal_url": self.portal_url,
            "credentials_configured": bool(self.username and self.password),
            "token_available": bool(self.portal_token)
        }

# FastAPI app setup
app = FastAPI(
    title="ArcGIS Enterprise MCP Server",
    description="MCP server for ArcGIS Enterprise functionality using FastAPI-MCP",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize server
arcgis_server = ArcGISFastAPIServer()

# Initialize FastAPI-MCP
mcp = FastApiMCP(app)

@app.get("/")
async def root():
    return {
        "message": "ArcGIS Enterprise MCP Server",
        "version": "1.0.0",
        "protocol": "MCP (Model Context Protocol)",
        "endpoints": {
            "list_services": "/list-services",
            "get_service_details": "/get-service-details",
            "get_portal_token": "/get-portal-token",
            "test_connection": "/test-connection",
            "server_info": "/server-info",
            "portal_info": "/portal-info",
            "health": "/health",
            "mcp": "/mcp"
        }
    }

@app.get("/health")
async def health_check():
    try:
        # Test basic connectivity
        server_info = await arcgis_server.get_server_info()
        return {
            "status": "healthy",
            "arcgis_server": arcgis_server.server_url,
            "arcgis_portal": arcgis_server.portal_url,
            "credentials_configured": bool(arcgis_server.username and arcgis_server.password),
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "version": "1.0.0"
        }

@app.post("/list-services")
async def list_services(request: ListServicesRequest):
    try:
        services = await arcgis_server.list_services()
        return {
            "services": services,
            "count": len(services)
        }
    except Exception as e:
        logger.error(f"Error listing services: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-service-details")
async def get_service_details(request: GetServiceDetailsRequest):
    try:
        details = await arcgis_server.get_service_details(request.service_name, request.folder)
        return {
            "service_name": request.service_name,
            "folder": request.folder,
            "details": details
        }
    except Exception as e:
        logger.error(f"Error getting service details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get-portal-token")
async def get_portal_token(request: GetPortalTokenRequest):
    try:
        token = await arcgis_server.get_portal_token(request.expiration)
        return {
            "token": token,
            "expiration_minutes": request.expiration,
            "success": token is not None
        }
    except Exception as e:
        logger.error(f"Error getting portal token: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-connection")
async def test_connection():
    try:
        result = await arcgis_server.test_connection()
        return result
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/server-info")
async def get_server_info():
    try:
        info = await arcgis_server.get_server_info()
        return info
    except Exception as e:
        logger.error(f"Error getting server info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/portal-info")
async def get_portal_info():
    try:
        info = await arcgis_server.get_portal_info()
        return info
    except Exception as e:
        logger.error(f"Error getting portal info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/token-status")
async def get_token_status():
    try:
        status = arcgis_server.get_token_status()
        return status
    except Exception as e:
        logger.error(f"Error getting token status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list-functions")
async def list_functions():
    """List all available functions/tools that can be called"""
    try:
        functions = [
            {
                "name": "list_services",
                "description": "Get all available ArcGIS services from the server (includes all folders)",
                "endpoint": "/list-services",
                "method": "POST",
                "parameters": {}
            },
            {
                "name": "get_service_details",
                "description": "Get detailed information about a specific ArcGIS service",
                "endpoint": "/get-service-details",
                "method": "POST",
                "parameters": {
                    "service_name": {
                        "type": "string",
                        "description": "Name of the service to get details for",
                        "required": True
                    },
                    "folder": {
                        "type": "string",
                        "description": "Folder containing the service (optional)",
                        "default": "",
                        "required": False
                    }
                }
            },
            {
                "name": "test_connection",
                "description": "Test connection to ArcGIS Server and Portal",
                "endpoint": "/test-connection",
                "method": "GET",
                "parameters": {}
            }
        ]
        
        return {
            "functions": functions,
            "count": len(functions),
            "server": "ArcGIS Enterprise MCP Server"
        }
    except Exception as e:
        logger.error(f"Error listing functions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount the MCP server to the FastAPI app
mcp.mount()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    uvicorn.run(
        "arcgis_fastapi_server:app",
        host="0.0.0.0",
        port=8001,
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )
