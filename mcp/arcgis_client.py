#!/usr/bin/env python3

import json
import logging
import os
from typing import Dict, Any, List, Optional
import httpx
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArcGISClient:
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
            
            # Simplify services to just essential information
            simplified_services = []
            for service in all_services:
                simplified_service = {
                    "name": service.get("name", ""),
                    "type": service.get("type", ""),
                    "folder": service.get("folder", "")
                }
                simplified_services.append(simplified_service)
            
            return {
                "services": simplified_services,
                "count": len(simplified_services)
            }
        except Exception as e:
            logger.error(f"Error listing services: {e}")
            return {"error": str(e)}
    
    
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
