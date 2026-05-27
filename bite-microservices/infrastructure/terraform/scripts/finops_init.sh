#!/bin/bash
set -e

apt-get update -y
apt-get install -y python3 python3-pip git

cd /labs
git clone https://github.com/YOUR_ORG/bite-microservices.git
cd bite-microservices/finops-service

pip3 install -r requirements.txt --break-system-packages 2>/dev/null || pip3 install -r requirements.txt

export DB_HOST="${db_host}"
export DB_NAME="finops_db"
export DB_USER="postgres"
export DB_PASSWORD="${db_password}"
export REDIS_HOST="${redis_host}"
export REDIS_PORT="6379"
export AUTH0_DOMAIN="${auth0_domain}"
export AUTH0_AUDIENCE="${auth0_audience}"
export DJANGO_SETTINGS_MODULE="finops.settings"

# Write env file for persistence
cat > /etc/bite-finops.env << EOF
DB_HOST=${db_host}
DB_NAME=finops_db
DB_USER=postgres
DB_PASSWORD=${db_password}
REDIS_HOST=${redis_host}
REDIS_PORT=6379
AUTH0_DOMAIN=${auth0_domain}
AUTH0_AUDIENCE=${auth0_audience}
EOF

python3 manage.py makemigrations expenses
python3 manage.py migrate
gunicorn finops.wsgi:application --bind 0.0.0.0:8080 --workers 4 --daemon --pid /tmp/finops.pid

echo "FinOps service started"
