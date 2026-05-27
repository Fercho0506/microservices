#!/bin/bash
set -e

apt-get update -y
apt-get install -y python3 python3-pip git

# Install MongoDB (for local dev; in prod use DocumentDB endpoint)
apt-get install -y mongodb

cd /labs
git clone https://github.com/YOUR_ORG/bite-microservices.git
cd bite-microservices/cloud-integration-service

pip3 install -r requirements.txt

export DB_HOST="${db_host}"
export DB_PASSWORD="${db_password}"
export MONGODB_HOST="${mongo_host}"
export ACTIVE_CLOUD_PROVIDER="aws"

python3 manage.py migrate
gunicorn cloud_integration.wsgi:application --bind 0.0.0.0:8081 --workers 2 --daemon

echo "Integration service started"
