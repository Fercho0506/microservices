#!/bin/bash
set -e

# Logs
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Iniciando Cloud Integration bootstrap..."

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y python3 python3-pip python3-venv git

# En AWS Academy evita Mongo local:
# usa mongo_host apuntando a DocumentDB o Mongo externo

mkdir -p /opt/bite
cd /opt/bite

# Evita errores si corre dos veces
rm -rf microservices

git clone https://github.com/Fercho0506/microservices.git

cd /opt/bite/microservices/cloud-integration-service

# Entorno virtual
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# Asegurar gunicorn
pip install gunicorn

# Variables persistentes
cat > /etc/bite-cloud.env <<EOF
DB_HOST=${db_host}
DB_PASSWORD=${db_password}
MONGODB_HOST=${mongo_host}
ACTIVE_CLOUD_PROVIDER=aws
EOF

set -a
source /etc/bite-cloud.env
set +a

# Migraciones
python manage.py migrate || true

# Ejecutar servicio
nohup venv/bin/gunicorn \
 cloud_integration.wsgi:application \
 --bind 0.0.0.0:8081 \
 --workers 2 \
 > /var/log/cloud-integration.log 2>&1 &

echo "Integration service started"

sleep 5
ps aux | grep gunicorn
