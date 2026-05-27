# BITE.co — Microservicios FinOps

Sistema de gestión de costos cloud para el sprint 4 de ISIS2503 (Arquitectura de Software).

## Estructura del proyecto

```
bite-microservices/
├── finops-service/              # ASR 1 (Desempeño) + ASR 2 (Seguridad)
│   ├── finops/                  # Configuración Django
│   ├── expenses/                # App: modelos, vistas, middleware JWT
│   ├── Dockerfile
│   └── requirements.txt
│
├── cloud-integration-service/   # ASR 3 (Mantenibilidad)
│   ├── cloud_integration/       # Configuración Django
│   ├── integration/
│   │   └── providers/
│   │       ├── base.py          # Interfaz CloudProviderInterface
│   │       ├── aws_provider.py  # Implementación AWS
│   │       ├── gcp_provider.py  # Implementación GCP (experimento ASR 3)
│   │       └── factory.py       # ← ÚNICO archivo a modificar para agregar provider
│   └── requirements.txt
│
├── cron-worker-service/         # Sincronización periódica
│   └── worker/
│
├── infrastructure/
│   ├── kong/
│   │   ├── kong.yaml            # Config Kong para AWS
│   │   └── kong.local.yaml      # Config Kong para docker-compose
│   ├── terraform/
│   │   ├── main.tf              # Infraestructura AWS (AWS Academy compatible)
│   │   ├── variables.tf
│   │   └── scripts/             # user_data de cada EC2
│   └── scripts/
│       └── load_test.py         # Script de prueba de carga (ASR 1 y ASR 2)
│
└── docker-compose.yml           # Desarrollo local
```

## Microservicios

| Servicio | Puerto | ASR | Base de datos |
|---------|--------|-----|---------------|
| FinOps Service | 8080 | ASR 1, ASR 2 | PostgreSQL (RDS) |
| Cloud Integration | 8081 | ASR 3 | PostgreSQL + MongoDB |
| CRON Worker | 8082 | Orquestación | PostgreSQL |
| Kong Gateway | 8000 | Routing | DB-less |

## ASRs implementados

### ASR 1 — Desempeño
- Endpoint: `GET /finops/expenses/by-area/?company_id=X&start_date=Y&end_date=Z`
- Estrategia: índice compuesto PostgreSQL + cache Redis (p95 < 150ms)

### ASR 2 — Seguridad
- Middleware JWT en `expenses/middleware.py`
- Valida roles `finops`/`admin` desde Auth0 (RS256)
- Todo acceso bloqueado → 403 + registro en `audit_logs`

### ASR 3 — Mantenibilidad
- Patrón Strategy en `integration/providers/`
- Agregar un nuevo proveedor = 2 archivos máximo:
  1. `providers/<nuevo>_provider.py` (implementar `CloudProviderInterface`)
  2. `providers/factory.py` (registrar el nuevo proveedor)

## Inicio rápido (local)

```bash
# Copien sus credenciales Auth0
cp .env.example .env
# Editen .env con AUTH0_DOMAIN y AUTH0_AUDIENCE

docker-compose up --build

# Seed de datos
curl -X POST "http://localhost:8000/finops/expenses/seed/?company_id=1&records=500"

# Prueba de carga
python infrastructure/scripts/load_test.py --kong-ip localhost --token <JWT> --users 100 --asr both
```

## Despliegue en AWS Academy

```bash
cd infrastructure/terraform
# Creen terraform.tfvars (ver variables.tf)
terraform init
terraform apply -auto-approve
# Anotar kong_public_ip del output
```

**Nota AWS Academy:** No se crean roles IAM. Se usa `LabInstanceProfile` existente.
