#!/bin/bash
set -e

# Logs
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Iniciando Kong bootstrap..."

export DEBIAN_FRONTEND=noninteractive

# Instalar dependencias
apt-get update -y
apt-get install -y docker.io git

# Iniciar Docker
systemctl enable docker
systemctl start docker

# Permitir uso de Docker
usermod -aG docker ubuntu

mkdir -p /opt/bite
cd /opt/bite

# Evitar error si vuelve a ejecutarse
rm -rf microservices

git clone https://github.com/Fercho0506/microservices.git

cd /opt/bite/microservices

mkdir -p infrastructure/kong

# Crear config dinámica
cat > /opt/bite/microservices/infrastructure/kong/kong.yaml <<KONG_EOF
_format_version: "3.0"
_transform: true

services:
  - name: finops-service
    protocol: http
    host: finops-upstream
    port: 8080
    path: /
    routes:
      - name: finops-routes
        paths: [/finops]
        strip_path: false

  - name: integration-service
    protocol: http
    host: integration-upstream
    port: 8081
    path: /
    routes:
      - name: integration-routes
        paths: [/integration]
        strip_path: false

  - name: cron-service
    protocol: http
    host: cron-upstream
    port: 8082
    path: /
    routes:
      - name: cron-routes
        paths: [/worker]
        strip_path: false

upstreams:
  - name: finops-upstream
    targets:
      - target: ${finops_ip}:8080
        weight: 100

  - name: integration-upstream
    targets:
      - target: ${integration_ip}:8081
        weight: 100

  - name: cron-upstream
    targets:
      - target: ${cron_ip}:8082
        weight: 100
KONG_EOF

# Limpiar si existe uno previo
docker rm -f kong || true

docker run -d \
  --name kong \
  --restart unless-stopped \
  -p 8000:8000 \
  -p 8443:8443 \
  -p 8001:8001 \
  -e KONG_DATABASE=off \
  -e KONG_DECLARATIVE_CONFIG=/kong.yaml \
  -e KONG_PROXY_ACCESS_LOG=/dev/stdout \
  -e KONG_ADMIN_ACCESS_LOG=/dev/stdout \
  -e KONG_PROXY_ERROR_LOG=/dev/stderr \
  -e KONG_ADMIN_ERROR_LOG=/dev/stderr \
  -v /opt/bite/microservices/infrastructure/kong/kong.yaml:/kong.yaml \
  kong:3.6

sleep 10

docker ps
docker logs kong

echo "Kong started successfully"
