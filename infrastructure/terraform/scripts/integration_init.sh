#!/bin/bash
set -e

# Logs
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Iniciando Cloud Integration bootstrap compatible con AWS Academy..."

export DEBIAN_FRONTEND=noninteractive

# Actualizar sistema e dependencias
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git gnupg curl

# ============================================================
# INSTALACIÓN DE MONGODB COMPATIBLE CON AWS ACADEMY (Ubuntu 22.04)
# ============================================================
echo "Instalando MongoDB compatible..."

# Usamos la versión 5.0/4.4 que no exige AVX avanzado y corre en t2/t3.micro
curl -fsSL https://www.mongodb.org/static/pgp/server-5.0.asc | \
   gpg --output /usr/share/keyrings/mongodb-server-5.0.gpg \
   --dearmor --yes

echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-5.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/5.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-5.0.list

apt-get update -y

# Forzar la instalación ignorando bloqueos de red comunes en laboratorios
apt-get install -y mongodb-org || apt-get install -y mongodb

# Arrancar el servicio
systemctl start mongod || systemctl start mongodb
systemctl enable mongod || systemctl enable mongodb

echo "MongoDB levantado con éxito en localhost"
# ============================================================

mkdir -p /opt/bite
cd /opt/bite

rm -rf microservices
git clone https://github.com/Fercho0506/microservices.git
cd /opt/bite/microservices/cloud-integration-service

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
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

python manage.py migrate || true

nohup venv/bin/gunicorn \
 cloud_integration.wsgi:application \
 --bind 0.0.0.0:8081 \
 --workers 2 \
 > /var/log/cloud-integration.log 2>&1 &

echo "Integration service started"
sleep 5
ps aux | grep gunicorn
