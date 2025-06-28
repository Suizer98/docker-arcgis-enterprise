# docker-arcgis-enterprise

> **Fork Notice**: This is a fork of the original [docker-arcgis-enterprise](https://github.com/Wildsong/docker-arcgis-enterprise) repository by Wildsong.

## Changes in this fork

The main changes in this fork include:

- **Platform Compatibility**: Modified `compose.yaml` to specify Linux 64-bit platform for better compatibility across different systems
- **Dockerfile Updates**: Updated `ubuntu-server/Dockerfile` to align with latest syntax

## What is this?

ESRI ArcGIS Enterprise running in Docker containers on Linux. This fork focuses on improving platform compatibility and cross-system deployment, particularly for Docker/OrbStack on Mac systems.

## Quick Start

When building the base ubuntu-server image, you must specify the platform:

```bash
docker buildx build --platform linux/amd64 -t ubuntu-server ubuntu-server
```

This command explicitly specifies the Linux AMD64 platform for better compatibility when running on Mac with Docker Desktop or OrbStack.

## Original Repository

For the original project and full documentation, please visit:
https://github.com/Wildsong/docker-arcgis-enterprise
