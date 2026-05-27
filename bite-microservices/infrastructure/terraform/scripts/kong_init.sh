#!/bin/bash
set -e

# Install Docker
apt-get update -y
apt-get install -y docker.io git

# Clone repo
cd /labs
git clone https://github.com/YOUR_ORG/bite-microservices.git
cd bite-microservices

# Write dynamic kong.yaml with actual IPs
cat > /labs/bite-microservices/infrastructure/kong/kong.yaml << KONG_EOF
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

# Start Kong
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
  -v /labs/bite-microservices/infrastructure/kong/kong.yaml:/kong.yaml \
  kong:3.6

echo "Kong started successfully"
