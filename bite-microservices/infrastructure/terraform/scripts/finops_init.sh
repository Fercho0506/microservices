#!/bin/bash
set -e

# Guardar logs
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Iniciando FinOps bootstrap..."

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y python3 python3-pip python3-venv git

# Carpeta de trabajo válida
mkdir -p /opt/bite
cd /opt/bite

# Evitar error si el script corre otra vez
rm -rf microservices

git clone https://github.com/Fercho0506/microservices.git

cd /opt/bite/microservices/finops-service

# Entorno virtual (muy recomendado en Ubuntu 22.04)
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# Si no viene en requirements
pip install gunicorn

cat > /etc/bite-finops.env <<EOF
DB_HOST=${db_host}
DB_NAME=finops_db
DB_USER=postgres
DB_PASSWORD=${db_password}
REDIS_HOST=${redis_host}
REDIS_PORT=6379
AUTH0_DOMAIN=${auth0_domain}
AUTH0_AUDIENCE=${auth0_audience}
DJANGO_SETTINGS_MODULE=finops.settings
EOF

set -a
source /etc/bite-finops.env
set +a

python manage.py migrate || true

nohup venv/bin/gunicorn \
    finops.wsgi:application \
    --bind 0.0.0.0:8080 \
    --workers 2 \
    > /var/log/finops.log 2>&1 &

echo "FinOps service started"
