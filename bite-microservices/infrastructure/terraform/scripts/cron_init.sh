#!/bin/bash
set -e

# Logs para depuración
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Iniciando bootstrap..."

# Instalar Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -

apt-get update
apt-get install -y nodejs git

# Crear directorio de trabajo
mkdir -p /opt/bite
cd /opt/bite

# Clonar repo real
git clone https://github.com/Fercho0506/microservices.git

# Entrar al servicio
cd /opt/bite/microservices/cron-worker-service-node

npm install --production

cat > /etc/bite-cron.env <<EOF
INTEGRATION_SERVICE_URL=http://${integration_ip}:8081
DB_HOST=${db_host}
DB_NAME=cron_db
DB_USER=postgres
DB_PASSWORD=${db_password}
PORT=8082
EOF

set -a
source /etc/bite-cron.env
set +a

nohup node src/index.js > /var/log/cron-worker.log 2>&1 &

echo "CRON Worker started"
