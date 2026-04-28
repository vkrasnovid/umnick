# Умник — Deployment Guide

## Overview

Умник (AI Operations Platform) consists of 5 Docker services:

| Service | Tech | Role | Internal Port | Host Port |
|---------|------|------|---------------|-----------|
| `postgres` | PostgreSQL 15 | Primary database | 5432 | 5432 |
| `redis` | Redis 7-alpine | Cache & Celery broker | 6379 | 6379 |
| `bridge` | FastAPI (Python 3.12) | Admin API & data sync | 8000 | **8085** |
| `tools` | FastAPI (Python 3.12) | Business tool library | 8001 | **8086** |
| `celery-worker` | Celery (Python 3.12) | Async task worker | — | — |
| `celery-beat` | Celery Beat | Scheduled watchers | — | — |
| `umnick-plugins` | TypeScript (Node 22) | OpenClaw agent plugins | 3000 | — |

## Prerequisites

- Docker Engine 24+
- Docker Compose v2

## Deployment

### 1. Clone the repository

```bash
git clone git@github.com:vkrasnovid/umnick.git
cd umnick
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your production values
```

> **Never commit `.env` to git.** It's already in `.gitignore`.

### 3. Start the stack

```bash
cd docker
docker compose up -d --build
```

This builds and starts all services in dependency order:
1. PostgreSQL (with auto-initialization of schema and seed data)
2. Redis
3. Bridge (waits for Postgres + Redis)
4. Tools (waits for Postgres)
5. Celery Worker (waits for Postgres + Redis)
6. Celery Beat (waits for Postgres + Redis)

### 4. Verify

```bash
# Container status
docker compose ps

# Health checks
curl http://localhost:8085/health
# → {"status":"ok","service":"bridge"}

curl http://localhost:8086/health
# → {"status":"ok","service":"tool-runtime"}

# Readiness probe (bridge checks DB + Redis)
curl http://localhost:8085/ready
# → {"status":"ready","database":"ok","redis":"ok"}

# Database connectivity
docker exec umnick-postgres pg_isready -U umnick
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | Async Postgres DSN (`postgresql+asyncpg://...`) |
| `DATABASE_URL_SYNC` | Yes | — | Sync Postgres DSN (`postgresql://...`) |
| `REDIS_URL` | Yes | — | Redis connection string |
| `CELERY_BROKER_URL` | Yes | — | Celery broker (use Redis) |
| `CELERY_RESULT_BACKEND` | Yes | — | Celery results backend (use Redis) |
| `SECRET_KEY` | **Yes** | — | App encryption key (no default, app fails to start without it) |
| `ENCRYPTION_KEY` | No | — | Base64 encryption key for OData credentials |
| `LOG_LEVEL` | No | `INFO` | Python logging level |
| `DEBUG` | No | `false` | Debug mode |
| `CORS_ORIGINS` | No | `http://localhost:5173,http://localhost:3000` | Comma-separated CORS origins |
| `OPENCLAW_API_URL` | No | `http://openclaw:8080` | OpenClaw API base URL |
| `OPENCLAW_API_KEY` | No | — | OpenClaw API key |
| `OTEL_SERVICE_NAME` | No | `umnick` | OpenTelemetry service name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | `http://otel-collector:4318` | OpenTelemetry collector endpoint |

## Port Allocations (Host)

| Port | Service | Purpose |
|------|---------|---------|
| 5432 | PostgreSQL | Database access (internal only) |
| 6379 | Redis | Cache access (internal only) |
| 8085 | Bridge API | Admin API, data sync, health checks |
| 8086 | Tools API | Tool runtime for business queries |

> Production — bind database/Redis ports to `127.0.0.1` only.

## Health Check URLs

- `GET /health` — Liveness probe (Bridge + Tools)
- `GET /ready` — Readiness probe (Bridge: checks DB + Redis)

## Celery Workers

Two Celery processes run alongside the API services:

- **celery-worker**: Executes async tasks (OData sync, watchers)
- **celery-beat**: Schedules periodic watcher checks per cron expressions

Both connect to Redis for broker/result backend.

## Database

### Schema initialization

On first container startup, PostgreSQL automatically runs:
1. `scripts/init_db.sql` — creates `umnick` schema with all tables, indexes, RLS
2. `scripts/seed_data.sql` — inserts demo data (tenant, counterparties, contracts, etc.)

### Manual seed

```bash
docker exec -i umnick-postgres psql -U umnick -d umnick < scripts/seed_data.sql
```

### Backup

```bash
docker exec umnick-postgres pg_dump -U umnick -d umnick > backup_$(date +%Y%m%d).sql
```

## Troubleshooting

### Container keeps restarting

Check logs:
```bash
docker logs umnick-bridge
docker logs umnick-tools
```

### ModuleNotFoundError: No module named 'config'

Python imports resolve via `PYTHONPATH=/app/{bridge,tools,engine}/src`. If you see this error:
- Ensure `PYTHONPATH` is set in the Dockerfile
- Try `docker compose build --no-cache <service>`

### PostgreSQL not accepting connections

```bash
docker logs umnick-postgres
docker exec umnick-postgres pg_isready -U umnick
```

### Celery beat not triggering watchers

```bash
docker logs umnick-celery-beat
# Check the beat schedule is loaded
docker exec umnick-celery-beat celery -A src.celery_app inspect scheduled
```

### No seed data

If seed data wasn't loaded (e.g., on re-deploy with persistent volume):
```bash
docker exec -i umnick-postgres psql -U umnick -d umnick < scripts/seed_data.sql
```

### Plugins container (separate)

The plugins module runs as a standalone container only when configured with OpenClaw:
```bash
docker compose -f openclaw-plugins/docker-compose.plugins.yml up
```

## Clean Shutdown

```bash
cd docker
docker compose down
# To also remove volumes (destroys data):
docker compose down -v
```
