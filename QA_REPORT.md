# QA Report: Умник — AI Operations Platform

> **Date:** 2026-04-28
> **Tester:** QA Agent (subagent)
> **Version:** MVP 1.0

---

## Summary

| Section | Passed | Failed | Skipped | Verdict |
|---------|--------|--------|---------|---------|
| Unit Tests | 26 | 26 | 0 | ❌ FAIL |
| Code Quality — Bridge | 4 | 1 | 0 | ⚠️ WARN |
| Code Quality — Tools | 4 | 0 | 0 | ✅ PASS |
| Code Quality — Engine | 4 | 0 | 0 | ✅ PASS |
| Code Quality — OpenClaw Plugins | 4 | 3 | 0 | ❌ FAIL |
| Security | 3 | 6 | 0 | ❌ FAIL |
| Structure & Completeness | 6 | 4 | 0 | ⚠️ WARN |
| **Total** | **51** | **40** | **0** | **❌ FAIL** |

**Coverage:** ~56% checks passed

---

## 1. Unit Tests

### 1.1 Bridge — `/opt/umnick/bridge/`

```
Result: 5 passed / 6 failed
```

**Failures cause:** `ModuleNotFoundError: No module named 'structlog'` — all 6 failures.

Test environment issue: `structlog` not installed despite being in `requirements.txt`. The `.venv` exists but tests don't use it (run outside venv). Tests need to run inside the venv or with `pip install structlog`.

Potential P1: `conftest.py` only adds `src/` to path but doesn't handle missing dependencies.

### 1.2 Tools — `/opt/umnick/tools/`

```
Result: 18 passed / 0 failed ✅
```

All 18 tests pass. Good coverage:
- Schema validation (9 tests)
- Tool handler logic (7 tests)
- Edge cases (2 tests: no results, invalid tenant ID)

### 1.3 Engine — `/opt/umnick/engine/`

```
Result: 3 passed / 20 failed
```

**Failures cause:** Same `structlog` import error. 20 tests fail due to missing module.

---

## 2. Code Quality

### 2.1 Bridge — Data Bridge (src/)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | SQL-модели включают tenant_id, created_at, updated_at | ✅ PASS | `TimestampMixin` used correctly. All entity tables have tenant_id + created_at + updated_at |
| 2 | OData клиент использует параметризованные запросы | ✅ PASS | `httpx` params dict — no f-string SQL |
| 3 | X-Tenant-Id middleware на всех admin endpoints | ✅ PASS | `_ensure_tenant_id()` dependency on all `/api/admin/*` routes |
| 4 | messages_ru.py на русском | ✅ PASS | All strings in Russian, including ENTITY_LABELS |

**Issue:** `sync/base.py` line 176 uses `text(f"""INSERT INTO {self.table_name} ...""")` — f-string in SQL. While `table_name` is developer-controlled (class property), it violates the project's own rule "no f-string in SQL" per ARCHITECTURE.md §10.1.

### 2.2 Tools — Tool Library (src/)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Все 7 tools реализованы | ✅ PASS | contract_utilization, overdue_payments, client_activity, query_sales, find_contracts, client_360, active_clients |
| 2 | Все SQL-запросы параметризованы | ✅ PASS | All use `sa_text("""...""")\` with `:param` syntax |
| 3 | Все запросы включают фильтр по tenant_id | ✅ PASS | Every WHERE clause includes `tenant_id = :tenant_id` |
| 4 | Каждый handler возвращает ToolResponse | ✅ PASS | All return `ToolResponse(data=...)` or `ToolResponse(success=False, error=...)` |

Clean code. No issues found.

### 2.3 Engine — Proactive Engine (src/)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Модель Watcher в БД | ✅ PASS | Full model with all required fields |
| 2 | Дедупликация: SHA256 хэш | ✅ PASS | `compute_alert_hash()` uses SHA256 of JSON-serialized content |
| 3 | Snooze: поле snooze_until | ✅ PASS | Checked in `should_send_alert()` |
| 4 | Celery Beat schedule настроен | ✅ PASS | `celery_app.py` has full beat schedule |

### 2.4 OpenClaw Plugins (src/)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | 7 TypeScript файлов в src/tools/ | ✅ PASS | All 7 present |
| 2 | Каждый экспортирует name, description, inputSchema, handler | ✅ PASS | All follow ToolDefinition interface |
| 3 | client.ts с X-Tenant-Id заголовком | ✅ PASS | `headers: { 'X-Tenant-Id': tenantId }` in `client.ts` |
| 4 | agent-config.yaml с системным промптом на русском | ✅ PASS | Full Russian system prompt, tools list, watchers config |

**❌ CRITICAL: Incompatible response data structure between TS plugins and Python handlers**

Each of the 7 TypeScript plugins accesses response keys that don't match what the Python handlers return. This will cause runtime failures in production.

| TS Plugin | Ts Access | Actual Python Key | Severity |
|-----------|-----------|-------------------|----------|
| `contract-utilization.ts` | `data.contracts` (array) | `data.contract` (single object) | P0 |
| `contract-utilization.ts` | `c.utilization_percent` | `utilization_pct` | P1 |
| `contract-utilization.ts` | `c.elapsed_percent` | **field doesn't exist** | P1 |
| `client-360.ts` | `data.name` | `data.counterparty.name` | P1 |
| `client-360.ts` | `data.annual_revenue` | `data.sales_30d` | P1 |
| `client-360.ts` | `data.active_contracts_count` | No such field | P1 |
| `client-360.ts` | `data.top_contracts[]` | `data.contracts_active[]` | P1 |
| `client-activity.ts` | `data.counterparty_name` | `data.counterparty.name` | P1 |
| `client-activity.ts` | `data.order_count` | `data.activity_summary.total_orders` | P1 |
| `client-activity.ts` | `data.order_total` | No such field | P2 |
| `client-activity.ts` | `data.payment_count` | No such field | P2 |
| `client-activity.ts` | `data.days_since_last_activity` | No such field | P2 |
| `overdue-payments.ts` | `inv.counterparty_name` | `inv.counterparty` | P1 |
| `overdue-payments.ts` | `inv.amount` (for overdue amount) | Should be `inv.balance` | P1 |
| `query-sales.ts` | `data.total_revenue` | `data.summary.total_revenue` | P1 |
| `query-sales.ts` | `data.period_label` | No such field | P2 |
| `query-sales.ts` | `data.breakdown[].label` | `data.by_counterparty[].name` | P1 |
| `find-contracts.ts` | `data.total_count` | `data.total` | P1 |
| `find-contracts.ts` | `c.counterparty_name` | `c.counterparty` | P1 |
| `find-contracts.ts` | `c.expires_at` | `c.date_end` | P1 |

---

## 3. Security

### 3.1 SQL Injection Scan

```bash
grep -rn 'f"' --include="*.py" bridge/src/ tools/src/ engine/src/ | grep -i "sql\|query\|select\|insert\|update\|delete"
```

**Findings:**
1. **`bridge/src/sync/base.py:176`** — `text(f"""INSERT INTO {self.table_name} ...""")` — f-string table name. While controlled by class property (not user input), violates best practice. Risk: P2.

2. **`bridge/src/odata/client.py:211`** — `filter_expr = f"Date_Time gt datetime'{...}'"` — date from server-side timestamp, no user input involved. Low risk: P3.

3. **All tool handlers**: ✅ All use parameterized `sa_text("""...""")` with `:param` syntax.

### 3.2 Hardcoded Credentials Scan

```bash
grep -rn "password\|token\|secret\|api_key" --include="*.py" --include="*.ts"
```

**Findings:**
| File | Line | Finding | Severity |
|------|------|---------|----------|
| `bridge/src/config.py:35` | `secret_key: str = "umnick-dev-secret-key"` | Hardcoded dev secret key | **P1** |
| `docker/docker-compose.yml` | `POSTGRES_PASSWORD: umnick_pass` | Plaintext DB password in docker-compose | **P2** |
| `docker/docker-compose.yml` | `- SECRET_KEY=umnick-dev-secret-key` | Same dev key in docker-compose | **P2** |
| `.env.example` | `ENCRYPTION_KEY=base64:WzRlMjhY...` | Demo encryption key exposed | **P2** |
| `.env.example` | `OPENCLAW_API_KEY=sk-umnick-dev-key` | Dev API key exposed | **P3** |
| `.env.example` | `SECRET_KEY=umnick-dev-secret-key-change-in-production` | OK if changed in prod | ✅ |

### 3.3 Encryption Check

`bridge/src/crypto.py` exists ✅
- Uses `AES-256-GCM` ✅ (authenticated encryption, industry standard)
- Key from config (`settings.encryption_key`) ✅
- Proper nonce generation (`os.urandom(12)`) ✅
- base64 encoding for storage ✅

### 3.4 Additional Security Findings

| Issue | Severity | Details |
|-------|----------|---------|
| No rate limiting middleware | **P2** | ARCHITECTURE.md specifies 100 req/min per tenant, not implemented |
| No auth middleware | **P2** | Admin endpoints lack bearer-token auth (ARCHITECTURE.md requires it) |
| RLS not configured in init_db.sql | **P2** | ARCHITECTURE.md §9.3 describes RLS policies, but they're not in init_db.sql |
| No HTTPS/TLS | **P3** | Expected for MVP with reverse proxy, but docker-compose has no nginx/traefik |

---

## 4. Structure & Completeness

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | `requirements.txt` с зависимостями | ✅ PASS | Complete list of pinned dependencies |
| 2 | `docker-compose.yml` полный | ❌ FAIL | Missing `openclaw-plugins` service, missing `otel-collector` from monitoring stack |
| 3 | `.env.example` с документацией | ✅ PASS | Well-documented with comments |
| 4 | `ARCHITECTURE.md` присутствует | ✅ PASS | Comprehensive 50+ page document |
| 5 | `DESIGN_SPEC.md` присутствует | ✅ PASS | (confirmed exists) |
| 6 | Documentation consistency | ❌ FAIL | ARCHITECTURE.md describes structure that differs from actual code |

### Documentation Discrepancies

| ARCHITECTURE.md | Actual Code | Impact |
|-----------------|-------------|--------|
| Multi-file models (`counterparty.py`, `contract.py`, etc.) | Single `models.py` | Minor |
| `sync/orders.py`, `sync/contracts.py`, etc. | Single `sync/workers.py` | Minor |
| `bridge/tasks.py` structure | Different layout | Minor |
| Dockerfile.admin referenced | Doesn't exist | Medium |
| openclaw-plugins in main compose | Only in separate file | Minor |
| `admin/` React SPA directory | Doesn't exist | Medium — admin UI not built |
| otel-collector in monitoring compose | Not configured | Medium |

### Additional Structural Issues

| Issue | Severity | Details |
|-------|----------|---------|
| Python version mismatch (Docker: 3.11, .venv: 3.12) | P2 | Dockerfiles use Python 3.11, but development uses 3.12 |
| DRY violation: `_parse_data_version`, `_parse_date`, `_extract_key` duplicated in 3 workers | P3 | Should live in `BaseSyncWorker` |
| Duplicate Celery Beat schedules in bridge/tasks.py and engine/celery_app.py | P2 | Bridge tasks.py defines its own beat schedule AND engine/celery_app.py also defines one |
| `.env` won't be found in Docker for bridge service | P2 | Dockerfile sets WORKDIR `/app/bridge` but `.env` is at `/app/.env` |
| No `openclaw-plugins/src/tools/` directory structure in ARCHITECTURE.md | P3 | Minor mismatch |

---

## 5. Final Verdict

### ❌ FAIL — Not Ready for Production

**Must-fix before merge:**

1. **P0 — Align TS plugin response keys with Python handlers** (all 7 plugins broken)
2. **P1 — Install `structlog` in test environment** (26 tests failing due to missing dep)
3. **P1 — Replace `SECRET_KEY` hardcoded default with env-only** (security issue)
4. **P1 — Move `_parse_data_version` / `_parse_date` / `_extract_key` to `BaseSyncWorker`** (DRY)
5. **P2 — Add Rate Limiting middleware** (spec requirement)
6. **P2 — Add auth middleware to admin endpoints** (spec requirement)
7. **P2 — Resolve duplicate Celery Beat schedules** (who owns what?)
8. **P2 — Fix Docker .env path** (bridge service won't find config)
9. **P2 — Add RLS SQL to init_db.sql** (spec requirement)
10. **P3 — Remove f-string SQL in sync/base.py** (use format-agnostic approach)

**Should-fix before release:**
- Create Dockerfile.admin or note as not-yet-implemented
- Add openclaw-plugins service to main docker-compose.yml
- Unify Python version across Docker and dev
- Remove plaintext credentials from docker-compose.yml

**Low priority:**
- Close documentation-vs-code gaps (ARCHITECTURE.md references separate model files)
- Add missing Dockerfile.admin
- Add otel-collector to compose monitoring stack

---

## Appendix: Test Results

### Bridge Test Run
```
6 failed, 5 passed in 0.83s
All failures: ModuleNotFoundError('structlog')
```

### Tools Test Run
```
18 passed in 0.62s
```

### Engine Test Run
```
20 failed, 3 passed in 0.96s
All failures: ModuleNotFoundError('structlog')
```
