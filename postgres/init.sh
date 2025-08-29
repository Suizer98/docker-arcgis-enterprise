#!/bin/bash

# Create ArcGIS enterprise database with postgres user
psql -U postgres << EOF
-- Create ArcGIS enterprise database
CREATE DATABASE arcgis_enterprise;

-- Grant all privileges to postgres user
GRANT ALL PRIVILEGES ON DATABASE arcgis_enterprise TO postgres;

-- Set ownership to postgres
ALTER DATABASE arcgis_enterprise OWNER TO postgres;

-- Load ST_Geometry library once for the entire instance
LOAD 'st_geometry';
EOF

# Configure PostgreSQL to load ST_Geometry at startup (permanent)
echo "shared_preload_libraries = 'st_geometry'" >> /var/lib/postgresql/data/postgresql.conf

# Connect to arcgis_enterprise database and install extensions
psql -U postgres -d arcgis_enterprise << EOF
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;
EOF
