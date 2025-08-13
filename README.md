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

### Build a base Docker image in AMD64

When building the base ubuntu-server image, you must specify the platform:

```bash
docker buildx build --platform linux/amd64 -t ubuntu-server ubuntu-server
```

This command explicitly specifies the Linux AMD64 platform for better compatibility when running on Mac with Docker Desktop or OrbStack.

### Nginx and Socat to solve port forwarding between portal and server

I don't know what is the solution to configure portal, somehow it always keep redirect me to portal.local on window chrome browser.
The reason why I use nginx is because on window wsl2, if let say my host machine don't have adminstrative right to apply `/etc/hosts`:
```
    127.0.0.1 portal portal.local
    127.0.0.1 server server.local
    127.0.0.1 datastore datastore.local
```
I can only do this on wsl2 machine. Then use nginx to port forwarding localhost:7443 to portal:7443. 

For Socat, I use it to trick server local network stack to redirect localhost:6443 from server:6443 so it can talk to portal service, in order to complete the federation.

### Setup postgresql connection

To setup connection between pgadmin and postgresql, go to [http://localhost:8080/browser/](http://localhost:8080/browser/), in pgadmin use these settings:
```
Host name/address: docker-arcgis-enterprise_postgres_1
Port: 5432
Username: {follow your env}
Password: {follow your env}
```

Go to the postgresql database interactive mode:
```
podman exec -it docker-arcgis-enterprise_postgres_1 psql -U postgres
CREATE DATABASE arcgis_enterprise;
\l # list databases
\q # exit view list
```

Finally go to your ArcGIS Pro, create a sde file using following:
```
Platform: PostgreSQL
Instance: 172.23.254.226,5432 # You need to know your wsl2 or ip address exposed from container
Username: {follow your env}
Password: {follow your env}
Database: arcgis_enterprise
```

## One time authorisation

Please refer to this [website](https://enterprise.arcgis.com/en/server/10.9.1/install/linux/silently-install-arcgis-server.htm) to do one time authorisation for your .prvc provisioning file, if you want to generate .ecp file for arcgis server.

## Original Repository

For the original project and full documentation, please visit:
https://github.com/Wildsong/docker-arcgis-enterprise