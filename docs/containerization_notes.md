# Containerization Notes

## Overview

This project includes containerization support for Docker and Podman.

Containerization allows the application to run in a consistent Python environment without relying directly on the local system setup.

## Current Status

Completed:

- Docker installed
- Podman installed
- Dockerfile created
- Containerfile created
- requirements.txt created
- Application successfully built and run in a container

## Dockerfile

Current Dockerfile:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]