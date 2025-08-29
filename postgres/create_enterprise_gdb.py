#!/usr/bin/env python3
import arcpy

def create_enterprise_geodatabase():
    try:
        # Check license
        if arcpy.ProductInfo().upper() in ["ARCVIEW", "ENGINE"]:
            print("ERROR: Requires ArcGIS Pro Standard or Advanced license.")
            return False
        
        # Create enterprise geodatabase
        arcpy.management.CreateEnterpriseGeodatabase(
            database_platform="POSTGRESQL",
            instance_name="localhost",
            database_name="arcgis_enterprise_postgis",
            account_authentication="DATABASE_AUTH",
            database_admin="postgres",
            database_admin_password="samplepassword",
            sde_schema="SDE_SCHEMA",
            gdb_admin_name="sde",
            gdb_admin_password="samplepassword",
            tablespace_name="",
            authorization_file="C:/Users/sz.tey/Desktop/keycodes",
            # spatial_type="ST_GEOMETRY"
            # ERROR: Setup st_geometry library ArcGIS version does not match the expected version in use [Success] st_geometry library release expected: 1.30.4.10, found: 1.30.5.10
            # Connected RDBMS instance is not setup for Esri spatial type configuration.
            # ERROR 003425: Setup st_geometry library ArcGIS version does not match the expected version in use.
            # Failed to execute (CreateEnterpriseGeodatabase)
            spatial_type="POSTGIS"
        )
        
        print("SUCCESS: Enterprise geodatabase created!")
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    if not arcpy:
        print("ERROR: Must run in ArcGIS Pro!")
    else:
        create_enterprise_geodatabase()
