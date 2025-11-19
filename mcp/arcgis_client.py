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
            "MCP_USERNAME": self.username,
            "MCP_PASSWORD": self.password,
        }

        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

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
                self.token_expires_at = datetime.datetime.now() + datetime.timedelta(
                    hours=1
                )
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
            "token_expires_at": (
                self.token_expires_at.isoformat() if self.token_expires_at else None
            ),
            "is_expired": self._is_token_expired(),
            "current_time": now.isoformat(),
        }

        if self.token_expires_at:
            time_until_expiry = self.token_expires_at - now
            status["minutes_until_expiry"] = int(time_until_expiry.total_seconds() / 60)

        return status

    async def get_portal_token(self, expiration: int = 60) -> Optional[str]:
        """Get authentication token from ArcGIS Portal"""
        if not self.username or not self.password:
            raise ValueError(
                "MCP_USERNAME and MCP_PASSWORD environment variables are required"
            )

        try:
            async with httpx.AsyncClient(
                verify=False, timeout=10.0, follow_redirects=True
            ) as client:
                token_url = f"{self.portal_url}/arcgis/sharing/rest/generateToken"
                data = {
                    "username": self.username,
                    "password": self.password,
                    "client": "referer",
                    "referer": "http://localhost:8000",
                    "expiration": str(expiration),
                    "f": "json",
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

    async def call_arcgis_api(
        self, endpoint: str = "", use_token: bool = False
    ) -> Dict[str, Any]:
        """Call ArcGIS REST API"""
        try:
            # Ensure we have a valid token if needed
            if use_token:
                await self._ensure_valid_token()

            async with httpx.AsyncClient(
                verify=False, timeout=10.0, follow_redirects=True
            ) as client:
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
                    return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
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
                    "folder": service.get("folder", ""),
                }
                simplified_services.append(simplified_service)

            return {"services": simplified_services, "count": len(simplified_services)}
        except Exception as e:
            return {"error": str(e)}

    async def get_service_details(
        self, service_name: str, folder: Optional[str] = ""
    ) -> Dict[str, Any]:
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
                        if (
                            service_name_from_list
                            == f"{input_folder}/{input_service_name}"
                            and service_folder_from_list == input_folder
                        ):
                            matching_service = service
                            folder = input_folder
                            service_name = input_service_name
                            break

                # Handle both formats: "ServiceName" with folder="Folder" and "Folder/ServiceName" with folder="Folder"
                if (
                    service_name_from_list == service_name
                    and service_folder_from_list == folder
                ):
                    matching_service = service
                    break
                elif (
                    service_name_from_list == f"{folder}/{service_name}"
                    and service_folder_from_list == folder
                ):
                    matching_service = service
                    break
                elif (
                    service_name_from_list == service_name
                    and not folder
                    and not service_folder_from_list
                ):
                    matching_service = service
                    break
                # Handle case where service_name_from_list is "Folder/ServiceName" and we're looking for just "ServiceName"
                elif (
                    service_name_from_list.endswith(f"/{service_name}")
                    and service_folder_from_list == folder
                ):
                    matching_service = service
                    service_name = service_name_from_list.split("/")[
                        -1
                    ]  # Extract just the service name
                    break

            if not matching_service:
                return {
                    "error": f"Service '{service_name}' not found in folder '{folder}'"
                }

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
                    "full_path": f"{folder}/{service_name}" if folder else service_name,
                }

            return result
        except Exception as e:
            return {"error": str(e)}

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to ArcGIS Server and Portal"""
        results = {
            "server": {"status": "unknown", "url": self.server_url},
            "portal": {"status": "unknown", "url": self.portal_url},
            "credentials": {"configured": bool(self.username and self.password)},
        }

        # Test server connection
        try:
            server_result = await self.call_arcgis_api("")
            if "error" not in server_result:
                results["server"]["status"] = "connected"
                results["server"]["services_count"] = len(
                    server_result.get("services", [])
                )
                results["server"]["folders_count"] = len(
                    server_result.get("folders", [])
                )
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
                "server_version": result.get("currentVersion", "unknown"),
            }
        except Exception as e:
            return {"error": str(e)}

    async def get_portal_info(self) -> Dict[str, Any]:
        """Get basic portal information"""
        return {
            "portal_url": self.portal_url,
            "credentials_configured": bool(self.username and self.password),
            "token_available": bool(self.portal_token),
        }

    async def query_service_layer(
        self,
        service_name: str,
        folder: str = "",
        layer_id: Optional[int] = 0,
        where: str = "1=1",
        object_ids: Optional[List[int]] = None,
        geometry: Optional[Dict[str, Any]] = None,
        geometry_type: Optional[str] = "esriGeometryEnvelope",
        spatial_rel: Optional[str] = "esriSpatialRelIntersects",
        out_fields: str = "*",
        return_geometry: bool = True,
        return_ids_only: bool = False,
        return_count_only: bool = False,
        order_by_fields: Optional[str] = None,
        group_by_fields_for_statistics: Optional[str] = None,
        out_statistics: Optional[List[Dict[str, Any]]] = None,
        result_offset: Optional[int] = None,
        result_record_count: Optional[int] = None,
        return_distinct_values: bool = False,
        return_extent_only: bool = False,
        max_record_count: Optional[int] = 1000,
    ) -> Dict[str, Any]:
        """
        Query a service layer with flexible parameters

        Args:
            service_name: Name of the service
            folder: Folder containing the service (empty string for root)
            layer_id: Layer ID to query (default: 0)
            where: SQL WHERE clause (default: "1=1" for all records)
            object_ids: List of specific object IDs to query
            geometry: Geometry for spatial query (dict with coordinates and spatial reference)
            geometry_type: Type of geometry (esriGeometryEnvelope, esriGeometryPoint, etc.)
            spatial_rel: Spatial relationship (esriSpatialRelIntersects, esriSpatialRelContains, etc.)
            out_fields: Comma-separated list of fields to return (default: "*")
            return_geometry: Whether to return geometry (default: True)
            return_ids_only: Return only object IDs (default: False)
            return_count_only: Return only count (default: False)
            order_by_fields: Fields to order by (e.g., "FIELD_NAME ASC")
            group_by_fields_for_statistics: Fields to group by for statistics
            out_statistics: List of statistics to calculate
            result_offset: Number of records to skip
            result_record_count: Maximum number of records to return
            return_distinct_values: Return only distinct values (default: False)
            return_extent_only: Return only extent (default: False)
            max_record_count: Maximum record count (default: 1000)
        """
        try:
            # Handle None values by providing defaults
            if layer_id is None:
                layer_id = 0
            if geometry_type is None:
                geometry_type = "esriGeometryEnvelope"
            if spatial_rel is None:
                spatial_rel = "esriSpatialRelIntersects"
            if max_record_count is None:
                max_record_count = 1000

            # First, get the service details to determine the correct service type
            service_details = await self.get_service_details(service_name, folder)
            if "error" in service_details:
                return service_details

            # Extract service metadata
            service_metadata = service_details.get("service_metadata", {})
            actual_service_name = service_metadata.get("name", service_name)
            actual_folder = service_metadata.get("folder", folder)
            service_type = service_metadata.get("type", "MapServer")

            # Construct the query endpoint
            if actual_folder:
                query_endpoint = f"{actual_folder}/{actual_service_name}/{service_type}/{layer_id}/query"
            else:
                query_endpoint = (
                    f"{actual_service_name}/{service_type}/{layer_id}/query"
                )

            # Build query parameters
            query_params = {
                "f": "json",
                "where": (
                    where if where else "1=1"
                ),  # Use "1=1" for all records if where is empty
                "outFields": out_fields,
                "returnGeometry": str(return_geometry).lower(),
                "returnIdsOnly": str(return_ids_only).lower(),
                "returnCountOnly": str(return_count_only).lower(),
                "returnDistinctValues": str(return_distinct_values).lower(),
                "returnExtentOnly": str(return_extent_only).lower(),
            }

            # Set record count limit - prefer result_record_count if provided
            if result_record_count is not None and result_record_count > 0:
                query_params["resultRecordCount"] = str(result_record_count)
            else:
                query_params["maxRecordCount"] = str(max_record_count)

            # Add object IDs if provided
            if object_ids:
                query_params["objectIds"] = ",".join(map(str, object_ids))

            # Add geometry for spatial query if provided
            if geometry:
                query_params["geometry"] = json.dumps(geometry)
                query_params["geometryType"] = geometry_type
                query_params["spatialRel"] = spatial_rel

            # Add ordering if provided
            if order_by_fields:
                query_params["orderByFields"] = order_by_fields

            # Add grouping for statistics if provided
            if group_by_fields_for_statistics:
                query_params["groupByFieldsForStatistics"] = (
                    group_by_fields_for_statistics
                )

            # Add statistics if provided
            if out_statistics:
                query_params["outStatistics"] = json.dumps(out_statistics)

            # Add result offset if provided
            if result_offset is not None and result_offset > 0:
                query_params["resultOffset"] = str(result_offset)

            # Make the query request
            async with httpx.AsyncClient(
                verify=False, timeout=30.0, follow_redirects=True
            ) as client:
                # Ensure we have a valid token
                await self._ensure_valid_token()

                url = f"{self.server_url}/{query_endpoint}"
                if self.portal_token:
                    query_params["token"] = self.portal_token

                logger.info(f"Querying service layer: {query_endpoint}")
                logger.info(f"Query parameters: {query_params}")

                response = await client.get(url, params=query_params)

                if response.status_code == 200:
                    result = response.json()

                    # Add query metadata to the result
                    result["query_metadata"] = {
                        "service_name": actual_service_name,
                        "folder": actual_folder,
                        "service_type": service_type,
                        "layer_id": layer_id,
                        "query_parameters": query_params,
                        "timestamp": datetime.datetime.now().isoformat(),
                    }

                    return result
                else:
                    return {
                        "error": f"Query failed with status {response.status_code}",
                        "details": response.text,
                    }

        except Exception as e:
            return {"error": str(e)}

    async def get_layer_info(
        self, service_name: str, folder: str = "", layer_id: int = 0
    ) -> Dict[str, Any]:
        """
        Get information about a specific layer in a service

        Args:
            service_name: Name of the service
            folder: Folder containing the service (empty string for root)
            layer_id: Layer ID to get info for (default: 0)
        """
        try:
            # First, get the service details to determine the correct service type
            service_details = await self.get_service_details(service_name, folder)
            if "error" in service_details:
                return service_details

            # Extract service metadata
            service_metadata = service_details.get("service_metadata", {})
            actual_service_name = service_metadata.get("name", service_name)
            actual_folder = service_metadata.get("folder", folder)
            service_type = service_metadata.get("type", "MapServer")

            # Construct the layer info endpoint
            if actual_folder:
                layer_endpoint = (
                    f"{actual_folder}/{actual_service_name}/{service_type}/{layer_id}"
                )
            else:
                layer_endpoint = f"{actual_service_name}/{service_type}/{layer_id}"

            # Make the request
            async with httpx.AsyncClient(
                verify=False, timeout=10.0, follow_redirects=True
            ) as client:
                # Ensure we have a valid token
                await self._ensure_valid_token()

                url = f"{self.server_url}/{layer_endpoint}?f=json"
                if self.portal_token:
                    url += f"&token={self.portal_token}"

                logger.info(f"Getting layer info: {layer_endpoint}")

                response = await client.get(url)

                if response.status_code == 200:
                    result = response.json()

                    # Add layer metadata
                    result["layer_metadata"] = {
                        "service_name": actual_service_name,
                        "folder": actual_folder,
                        "service_type": service_type,
                        "layer_id": layer_id,
                        "timestamp": datetime.datetime.now().isoformat(),
                    }

                    return result
                else:
                    return {
                        "error": f"Layer info request failed with status {response.status_code}",
                        "details": response.text,
                    }

        except Exception as e:
            return {"error": str(e)}
