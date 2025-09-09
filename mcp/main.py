#!/usr/bin/env python3

import logging
import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
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

# Initialize server
arcgis_server = ArcGISClient()

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
            "query_service_layer": "/query-service-layer",
            "get_layer_info": "/get-layer-info",
            "get_portal_token": "/get-portal-token",
            "test_connection": "/test-connection",
            "server_info": "/server-info",
            "portal_info": "/portal-info",
            "health": "/health",
            "mcp": "/mcp",
        },
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
            "credentials_configured": bool(
                arcgis_server.username and arcgis_server.password
            ),
            "version": "1.0.0",
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "version": "1.0.0"}


@app.post("/list-services")
async def list_services(request: ListServicesRequest):
    try:
        services = await arcgis_server.list_services()
        return {"services": services, "count": len(services)}
    except Exception as e:
        logger.error(f"Error listing services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get-service-details")
async def get_service_details(request: GetServiceDetailsRequest):
    try:
        details = await arcgis_server.get_service_details(
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
        token = await arcgis_server.get_portal_token(request.expiration)
        return {
            "token": token,
            "expiration_minutes": request.expiration,
            "success": token is not None,
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


@app.post("/query-service-layer")
async def query_service_layer(request: QueryArcGISRequest):
    """Query ArcGIS REST API directly with a URL and parameters (simplified approach)"""
    try:
        import httpx
        import json

        # Ensure we have a valid token
        await arcgis_server._ensure_valid_token()

        # Add token to params if available
        if arcgis_server.portal_token:
            request.params["token"] = arcgis_server.portal_token

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


@app.post("/get-layer-info")
async def get_layer_info(request: GetLayerInfoRequest):
    try:
        result = await arcgis_server.get_layer_info(
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

        return {
            "functions": functions,
            "count": len(functions),
            "server": "ArcGIS Enterprise MCP Server",
        }
    except Exception as e:
        logger.error(f"Error listing functions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Mount the MCP server to the FastAPI app
mcp.mount()

if __name__ == "__main__":
    load_dotenv()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
