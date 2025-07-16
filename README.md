# docker-arcgis-enterprise

> **Fork Notice**: This is a fork of the original [docker-arcgis-enterprise](https://github.com/Wildsong/docker-arcgis-enterprise) repository by Wildsong.

Tech stacks:

![Tech stacks](https://skillicons.dev/icons?i=docker,ubuntu,bash)

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

## One time authorisation

Please refer to this [website](https://enterprise.arcgis.com/en/server/10.9.1/install/linux/silently-install-arcgis-server.htm) to do one time authorisation for your .prvc provisioning file, if you want to generate .ecp file for arcgis server.

## Original Repository

For the original project and full documentation, please visit:
https://github.com/Wildsong/docker-arcgis-enterprise
