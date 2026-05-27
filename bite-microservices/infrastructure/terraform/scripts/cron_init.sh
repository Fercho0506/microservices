#!/bin/bash
set -e

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs git

cd /labs
git clone https://github.com/YOUR_ORG/bite-microservices.git
cd bite-microservices/cron-worker-service-node

npm install --production

cat > /etc/bite-cron.env << ENVEOF
INTEGRATION_SERVICE_URL=http://${integration_ip}:8081
DB_HOST=${db_host}
DB_NAME=cron_db
DB_USER=postgres
DB_PASSWORD=${db_password}
PORT=8082
ENVEOF

# Run as background process
set -a && source /etc/bite-cron.env && set +a
nohup node src/index.js > /var/log/cron-worker.log 2>&1 &
echo "CRON Worker (Node.js) started"
