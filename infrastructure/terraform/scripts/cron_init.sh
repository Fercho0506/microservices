#!/bin/bash
set -e

# Logs para depuración
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Iniciando CRON Worker bootstrap..."

export DEBIAN_FRONTEND=noninteractive

# Actualizar e instalar dependencias
apt-get update -y
apt-get install -y curl git

# Instalar Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Verificar instalación
node -v
npm -v

# Directorio persistente
mkdir -p /opt/bite
cd /opt/bite

# Evitar error si el script corre otra vez
rm -rf microservices

# Clonar repositorio
git clone https://github.com/Fercho0506/microservices.git

# Entrar al servicio
cd /opt/bite/microservices/cron-worker-service-node

# Instalar solo dependencias de producción
npm install --omit=dev

# Variables de entorno persistentes
cat > /etc/bite-cron.env <<EOF
INTEGRATION_SERVICE_URL=http://${integration_ip}:8081
DB_HOST=${db_host}
DB_NAME=finops_db
DB_USER=postgres
DB_PASSWORD=${db_password}
PORT=8082
EOF

# Cargar variables
set -a
source /etc/bite-cron.env
set +a

# Ejecutar en segundo plano
nohup node src/index.js \
  > /var/log/cron-worker.log \
  2>&1 &

echo "CRON Worker started"

sleep 5
ps aux | grep node
