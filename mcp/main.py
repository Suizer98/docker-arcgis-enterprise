#!/usr/bin/env python3

import logging
import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from fastapi_mcp import FastApiMCP
from dotenv import load_dotenv

from arcgis_client import ArcGISClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic models for API
class ListServicesRequest(BaseModel):
    pass
    
    class Config:
        # Allow empty body for MCP compatibility
        extra = "forbid"


class GetServiceDetailsRequest(BaseModel):
    service_name: str
    folder: Optional[str] = ""


class GetPortalTokenRequest(BaseModel):
    expiration: int = 60


class QueryServiceLayerRequest(BaseModel):
    service_name: str
    folder: str = ""
    layer_id: Optional[int] = 0
    where: str = "1=1"
    object_ids: Optional[List[int]] = None
    geometry: Optional[Dict[str, Any]] = None
    geometry_type: Optional[str] = "esriGeometryEnvelope"
    spatial_rel: Optional[str] = "esriSpatialRelIntersects"
    out_fields: str = "*"
    return_geometry: bool = True
    return_ids_only: bool = False
    return_count_only: bool = False
    order_by_fields: Optional[str] = None
    group_by_fields_for_statistics: Optional[str] = None
    out_statistics: Optional[List[Dict[str, Any]]] = None
    result_offset: Optional[int] = None
    result_record_count: Optional[int] = None
    return_distinct_values: bool = False
    return_extent_only: bool = False
    max_record_count: Optional[int] = 1000


class GetLayerInfoRequest(BaseModel):
    service_name: str
    folder: str = ""
    layer_id: int = 0


class QueryArcGISRequest(BaseModel):
    url: str
    params: Optional[Dict[str, Any]] = {}


# FastAPI app setup
app = FastAPI(
    title="ArcGIS Enterprise MCP Server",
    description="MCP server for ArcGIS Enterprise functionality using FastAPI-MCP",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize server (lazy initialization to avoid blocking startup)
arcgis_server = None

def get_arcgis_server():
    """Get or initialize ArcGIS client (lazy initialization)"""
    global arcgis_server
    if arcgis_server is None:
        logger.info("Initializing ArcGIS client...")
        arcgis_server = ArcGISClient()
        logger.info("ArcGIS client initialized")
    return arcgis_server

# Note: FastApiMCP will be initialized AFTER all routes are defined
# This ensures all endpoints are discovered and registered as MCP tools


@app.get("/")
async def root():
    return {
        "message": "ArcGIS Enterprise MCP Server",
        "version": "1.0.0",
        "protocol": "MCP (Model Context Protocol) + HTTP REST API",
        "description": "This server works in dual mode: MCP protocol for Cursor, HTTP REST API for agent/frontend",
        "mcp_endpoint": "/v1/sse",
        "endpoints": {
            "list_services": "/list-services",
            "get_service_details": "/get-service-details",
            "query_service_layer": "/query-service-layer",
            "get_layer_info": "/get-layer-info",
            "get_portal_token": "/get-portal-token",
            "test_connection": "/test-connection",
            "server_info": "/server-info",
            "portal_info": "/portal-info",
            "health": "/health",
            "list_functions": "/list-functions",
            "mcp_sse": "/v1/sse",
        },
        "usage": {
            "cursor": "Connect via MCP at http://localhost:8001/v1/sse",
            "agent": "Use HTTP endpoints directly at http://mcp:8001 (from Docker) or http://localhost:8001 (from host)",
        },
    }


@app.get("/health")
async def health_check():
    try:
        # Test basic connectivity
        server = get_arcgis_server()
        server_info = await server.get_server_info()
        return {
            "status": "healthy",
            "arcgis_server": server.server_url,
            "arcgis_portal": server.portal_url,
            "credentials_configured": bool(
                server.username and server.password
            ),
            "version": "1.0.0",
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "version": "1.0.0"}


@app.post(
    "/list-services",
    summary="List all ArcGIS services",
    description="Get all available ArcGIS services from the server (includes all folders). This endpoint works for both MCP (Cursor) and HTTP (agent) clients.",
    tags=["services"],
    operation_id="list_services",
)
async def list_services(request: Optional[ListServicesRequest] = Body(None)):
    """List all ArcGIS services from all folders"""
    try:
        # Handle empty body for MCP compatibility
        if request is None:
            request = ListServicesRequest()
        services = await get_arcgis_server().list_services()
        return {"services": services, "count": len(services)}
    except Exception as e:
        logger.error(f"Error listing services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/get-service-details",
    summary="Get service details",
    description="Get detailed information about a specific ArcGIS service. This endpoint works for both MCP (Cursor) and HTTP (agent) clients.",
    tags=["services"],
    operation_id="get_service_details",
)
async def get_service_details(request: GetServiceDetailsRequest):
    """Get detailed information about a specific ArcGIS service"""
    try:
        details = await get_arcgis_server().get_service_details(
            request.service_name, request.folder
        )
        return {
            "service_name": request.service_name,
            "folder": request.folder,
            "details": details,
        }
    except Exception as e:
        logger.error(f"Error getting service details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get-portal-token")
async def get_portal_token(request: GetPortalTokenRequest):
    try:
        token = await get_arcgis_server().get_portal_token(request.expiration)
        return {
            "token": token,
            "expiration_minutes": request.expiration,
            "success": token is not None,
        }
    except Exception as e:
        logger.error(f"Error getting portal token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/test-connection",
    summary="Test connection",
    description="Test connection to ArcGIS Server and Portal. This endpoint works for both MCP (Cursor) and HTTP (agent) clients.",
    tags=["system"],
)
async def test_connection():
    """Test connection to ArcGIS Server and Portal"""
    try:
        result = await get_arcgis_server().test_connection()
        return result
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/server-info")
async def get_server_info():
    try:
        info = await get_arcgis_server().get_server_info()
        return info
    except Exception as e:
        logger.error(f"Error getting server info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/portal-info")
async def get_portal_info():
    try:
        info = await get_arcgis_server().get_portal_info()
        return info
    except Exception as e:
        logger.error(f"Error getting portal info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/token-status")
async def get_token_status():
    try:
        status = get_arcgis_server().get_token_status()
        return status
    except Exception as e:
        logger.error(f"Error getting token status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/query-service-layer",
    summary="Query service layer",
    description="Query ArcGIS REST API directly with a URL and parameters. This endpoint works for both MCP (Cursor) and HTTP (agent) clients.",
    tags=["query"],
    operation_id="query_service_layer",
)
async def query_service_layer(request: QueryArcGISRequest):
    """Query ArcGIS REST API directly with a URL and parameters (simplified approach)"""
    try:
        import httpx
        import json

        # Ensure we have a valid token
        server = get_arcgis_server()
        await server._ensure_valid_token()

        # Add token to params if available
        if server.portal_token:
            request.params["token"] = server.portal_token

        logger.info(f"Querying ArcGIS URL: {request.url}")
        logger.info(f"With parameters: {request.params}")

        async with httpx.AsyncClient(
            verify=False, timeout=30.0, follow_redirects=True
        ) as client:
            response = await client.get(request.url, params=request.params)

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "data": result,
                    "url": request.url,
                    "params": request.params,
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "url": request.url,
                    "params": request.params,
                }
    except Exception as e:
        logger.error(f"Error querying ArcGIS: {e}")
        return {
            "success": False,
            "error": str(e),
            "url": request.url,
            "params": request.params,
        }


@app.post(
    "/get-layer-info",
    summary="Get layer information",
    description="Get information about a specific layer in a service. This endpoint works for both MCP (Cursor) and HTTP (agent) clients.",
    tags=["layers"],
    operation_id="get_layer_info",
)
async def get_layer_info(request: GetLayerInfoRequest):
    """Get information about a specific layer in a service"""
    try:
        result = await get_arcgis_server().get_layer_info(
            service_name=request.service_name,
            folder=request.folder,
            layer_id=request.layer_id,
        )
        return result
    except Exception as e:
        logger.error(f"Error getting layer info: {e}")
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
                "parameters": {},
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
                        "required": True,
                    },
                    "folder": {
                        "type": "string",
                        "description": "Folder containing the service (optional)",
                        "default": "",
                        "required": False,
                    },
                },
            },
            {
                "name": "query_service_layer",
                "description": "Query ArcGIS REST API directly with a URL and parameters (simplified approach)",
                "endpoint": "/query-service-layer",
                "method": "POST",
                "parameters": {
                    "url": {
                        "type": "string",
                        "description": "Full ArcGIS REST API URL to query",
                        "required": True,
                    },
                    "params": {
                        "type": "object",
                        "description": "Query parameters to send with the request",
                        "default": {},
                        "required": False,
                    },
                },
            },
            {
                "name": "get_layer_info",
                "description": "Get information about a specific layer in a service",
                "endpoint": "/get-layer-info",
                "method": "POST",
                "parameters": {
                    "service_name": {
                        "type": "string",
                        "description": "Name of the service",
                        "required": True,
                    },
                    "folder": {
                        "type": "string",
                        "description": "Folder containing the service",
                        "default": "",
                        "required": False,
                    },
                    "layer_id": {
                        "type": "integer",
                        "description": "Layer ID to get info for",
                        "default": 0,
                        "required": False,
                    },
                },
            },
            {
                "name": "test_connection",
                "description": "Test connection to ArcGIS Server and Portal",
                "endpoint": "/test-connection",
                "method": "GET",
                "parameters": {},
            },
        ]

        result = {
            "functions": functions,
            "count": len(functions),
            "server": "ArcGIS Enterprise MCP Server",
        }
        return result
    except Exception as e:
        logger.error(f"Error listing functions: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# Initialize FastAPI-MCP AFTER all routes are defined
# This ensures all endpoints are discovered and registered as MCP tools
mcp = FastApiMCP(app)

# Mount the MCP server to the FastAPI app
# FastApiMCP will expose the MCP server at /mcp by default
mcp.mount()

# Call setup_server() to ensure all tools are properly registered
# This is important if routes were added before mounting
try:
    if hasattr(mcp, 'setup_server'):
        mcp.setup_server()
        logger.info("MCP server setup completed, tools should be registered")
    else:
        logger.info("MCP server mounted (setup_server not available)")
except Exception as e:
    logger.warning(f"Could not call setup_server: {e}")

# Log registered tools for debugging
try:
    if hasattr(mcp, 'list_tools'):
        tools = mcp.list_tools()
        logger.info(f"MCP registered {len(tools)} tools: {[t.get('name', 'unknown') for t in tools]}")
    elif hasattr(mcp, '_tools'):
        logger.info(f"MCP registered {len(mcp._tools)} tools")
except Exception as e:
    logger.debug(f"Could not list tools: {e}")

if __name__ == "__main__":
    load_dotenv()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
