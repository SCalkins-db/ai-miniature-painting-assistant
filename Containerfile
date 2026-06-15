FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]

#### WHY Containerfile is used #####
    Podman ecosystem
    Red Hat/OpenShift
    Rootless containers
    Linux enterprise environments
####################################