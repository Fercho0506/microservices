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

echo "Validando conectividad con el RDS de AWS Academy en $DB_HOST..."

# En AWS Academy, el RDS puede tardar hasta 5-8 minutos en estar disponible.
# Ponemos un límite de 20 intentos para que el script no se quede en un bucle infinito
# si el laboratorio te bloqueó el puerto 5432 en el Security Group.
MAX_RETRIES=20
RETRY_COUNT=0

while ! nc -z -w3 "$DB_HOST" 5432; do
  RETRY_COUNT=$((RETRY_COUNT+1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "ALERTA: No se pudo conectar al RDS tras $MAX_RETRIES intentos."
    echo "Revisa el Security Group del RDS en tu consola de AWS Academy e intenta mitigar manualmente."
    break
  fi
  echo "RDS no disponible todavía (Intento $RETRY_COUNT/$MAX_RETRIES). Esperando 15 segundos..."
  sleep 15
done

# Generar migraciones para la app que maneja 'cloud_expenses'
echo "Preparando esquema para la app 'expenses'..."
python manage.py makemigrations expenses

# Ejecutar migración. En AWS Academy dejamos un '|| true' controlado SOLO si el nc falló,
# para que al menos la app web prenda y puedas debuguear por SSH el error de base de datos.
echo "Aplicando cambios estructurales a la base de datos..."
python manage.py migrate || echo "Aviso: Migración fallida. Posible bloqueo de red en el laboratorio."

nohup venv/bin/gunicorn \
    finops.wsgi:application \
    --bind 0.0.0.0:8080 \
    --workers 2 \
    > /var/log/finops.log 2>&1 &

echo "FinOps service started"
