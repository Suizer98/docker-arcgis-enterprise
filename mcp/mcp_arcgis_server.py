#!/usr/bin/env python3

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArcGISMCPServer:
    def __init__(self):
        self.server = Server("arcgis-enterprise")
        
        # ArcGIS configuration - all values must be provided via environment variables
        self.server_url = os.getenv("ARCGIS_SERVER_URL")
        self.portal_url = os.getenv("ARCGIS_PORTAL_URL")
        self.username = os.getenv("AGS_USERNAME")
        self.password = os.getenv("AGS_PASSWORD")
        self.portal_token = None
        
        # Validate required environment variables
        required_vars = {
            "ARCGIS_SERVER_URL": self.server_url,
            "ARCGIS_PORTAL_URL": self.portal_url,
            "AGS_USERNAME": self.username,
            "AGS_PASSWORD": self.password
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        logger.info(f"ArcGIS configuration loaded - Server: {self.server_url}, Portal: {self.portal_url}")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP server handlers for tools and resources"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available ArcGIS tools"""
            return [
                Tool(
                    name="list_arcgis_services",
                    description="Get all available ArcGIS services from the server",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_folders": {
                                "type": "boolean",
                                "description": "Whether to include services from subfolders",
                                "default": True
                            }
                        }
                    }
                ),
                Tool(
                    name="get_service_details",
                    description="Get detailed information about a specific ArcGIS service",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "service_name": {
                                "type": "string",
                                "description": "Name of the service to get details for"
                            },
                            "folder": {
                                "type": "string",
                                "description": "Folder containing the service (optional)",
                                "default": ""
                            }
                        },
                        "required": ["service_name"]
                    }
                ),
                Tool(
                    name="get_portal_token",
                    description="Get authentication token for ArcGIS Portal",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "expiration": {
                                "type": "integer",
                                "description": "Token expiration in minutes",
                                "default": 60
                            }
                        }
                    }
                ),
                Tool(
                    name="test_arcgis_connection",
                    description="Test connection to ArcGIS Server and Portal",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            try:
                if name == "list_arcgis_services":
                    include_folders = arguments.get("include_folders", True)
                    services = await self.list_services(include_folders)
                    return [TextContent(
                        type="text",
                        text=json.dumps(services, indent=2)
                    )]
                
                elif name == "get_service_details":
                    service_name = arguments["service_name"]
                    folder = arguments.get("folder", "")
                    details = await self.get_service_details(service_name, folder)
                    return [TextContent(
                        type="text",
                        text=json.dumps(details, indent=2)
                    )]
                
                elif name == "get_portal_token":
                    expiration = arguments.get("expiration", 60)
                    token = await self.get_portal_token(expiration)
                    return [TextContent(
                        type="text",
                        text=json.dumps({"token": token, "expiration_minutes": expiration}, indent=2)
                    )]
                
                elif name == "test_arcgis_connection":
                    result = await self.test_connection()
                    return [TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
                    
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available ArcGIS resources"""
            return [
                Resource(
                    uri="arcgis://server/info",
                    name="ArcGIS Server Information",
                    description="Basic information about the ArcGIS Server",
                    mimeType="application/json"
                ),
                Resource(
                    uri="arcgis://portal/info",
                    name="ArcGIS Portal Information", 
                    description="Basic information about the ArcGIS Portal",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read ArcGIS resources"""
            if uri == "arcgis://server/info":
                info = await self.get_server_info()
                return json.dumps(info, indent=2)
            elif uri == "arcgis://portal/info":
                info = await self.get_portal_info()
                return json.dumps(info, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")
    
    async def get_portal_token(self, expiration: int = 60) -> Optional[str]:
        """Get authentication token from ArcGIS Portal"""
        if not self.username or not self.password:
            raise ValueError("AGS_USERNAME and AGS_PASSWORD environment variables are required")
        
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
                
                logger.info(f"Getting Portal token from: {token_url}")
                response = await client.post(token_url, data=data)
                
                if response.status_code == 200:
                    token_data = response.json()
                    if "token" in token_data:
                        self.portal_token = token_data["token"]
                        logger.info("Portal token obtained successfully")
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
            async with httpx.AsyncClient(verify=False, timeout=10.0, follow_redirects=True) as client:
                if endpoint:
                    url = f"{self.server_url}/{endpoint}?f=json"
                else:
                    url = f"{self.server_url}?f=json"
                
                logger.info(f"Calling ArcGIS API: {url}")
                
                if use_token and endpoint and "/" not in endpoint:
                    if not self.portal_token:
                        await self.get_portal_token()
                    
                    if self.portal_token:
                        url += f"&token={self.portal_token}"
                        logger.info(f"Using Portal token for folder: {endpoint}")
                
                response = await client.get(url)
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"API Error: {response.status_code}")
                    return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return {"error": str(e)}
    
    async def list_services(self, include_folders: bool = True) -> List[Dict[str, Any]]:
        """List all ArcGIS services"""
        try:
            all_services = []
            
            root_result = await self.call_arcgis_api("")
            if "services" in root_result:
                all_services.extend(root_result["services"])
            
            if include_folders and "folders" in root_result:
                for folder in root_result["folders"]:
                    logger.info(f"Checking folder: {folder}")
                    folder_result = await self.call_arcgis_api(folder, use_token=True)
                    if "services" in folder_result:
                        for service in folder_result["services"]:
                            service["folder"] = folder
                        all_services.extend(folder_result["services"])
            
            return all_services
        except Exception as e:
            logger.error(f"Error listing services: {e}")
            return []
    
    async def get_service_details(self, service_name: str, folder: str = "") -> Dict[str, Any]:
        """Get detailed information about a specific service"""
        try:
            if folder:
                endpoint = f"{folder}/{service_name}/MapServer"
            else:
                endpoint = f"{service_name}/MapServer"
            
            return await self.call_arcgis_api(endpoint)
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

async def main():
    """Main entry point for MCP server"""
    arcgis_server = ArcGISMCPServer()
    
    async with stdio_server() as (read_stream, write_stream):
        await arcgis_server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="arcgis-enterprise",
                server_version="1.0.0",
                capabilities=arcgis_server.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
