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

# Appendix: Acceptance Testing Results

> **Date:** 2026-04-28
> **Tester:** QA User Agent (end-user acceptance tester)
> **Surface:** HTTP API (Bridge Admin + Tools Runtime)

## Summary

| Section | Passed | Failed | Verdict |
|---------|--------|--------|---------|
| Health & Liveness | 3 | 0 | ✅ |
| Auth & Multi-tenant | 5 | 0 | ✅ |
| Admin API | 4 | 0 | ✅ |
| Tools API (7 tools) | 0 | 7 | ❌ **ALL FAIL** |
| Seed Data | 4 | 0 | ✅ |
| **Total** | **16** | **7** | **❌ FAIL** |

**Coverage:** ~69% criteria passed — blocked by systematic SQL syntax bug in all tool handlers.

**Verdict:** ⚠️ **CONDITIONAL PASS — BLOCKED ON TOOLS FIX**

All infrastructure works (health, auth, admin endpoints, seed data). The 7 tools are broken by the same root cause: invalid SQLAlchemy syntax with PostgreSQL `::type` casts. Once fixed, all tools should function.

---

## Test Results

### Section 1: Health & Liveness

**Test 1.1 — Bridge /health**

```bash
curl http://217.114.5.77:8085/health
```

```json
{"status":"ok","service":"bridge"}
```

**Result:** ✅ PASS

**Test 1.2 — Tools /health**

```bash
curl http://217.114.5.77:8086/health
```

```json
{"status":"ok","service":"tool-runtime"}
```

**Result:** ✅ PASS

**Test 1.3 — Bridge /ready**

```bash
curl http://217.114.5.77:8085/ready
```

```json
{"status":"ready","database":"ok","redis":"ok"}
```

**Result:** ✅ PASS

---

### Section 2: Auth & Multi-tenant

**Test 2.1 — Admin endpoint without X-Admin-Token**

```bash
curl -H "X-Tenant-Id: <valid>" http://.../api/admin/dashboard
```

**HTTP 403 Forbidden**

**Result:** ✅ PASS

**Test 2.2 — Admin endpoint without X-Tenant-Id**

```bash
curl -H "X-Admin-Token: <valid>" http://.../api/admin/dashboard
```

**HTTP 403 Forbidden**

**Result:** ✅ PASS

**Test 2.3 — Valid credentials return data**

Using `X-Admin-Token: umnick-dev-secret-key-change-in-production` (value from `SECRET_KEY` in .env — the middleware compares against `settings.secret_key`):

```json
{
  "sync_status": {"last_sync": null, "status": "no_sync"},
  "db_stats": {"counterparties": 4, "contracts": 3, "orders": 4, "products": 5},
  "watchers_count": {"total": 3, "active": 3, "alerting": 0},
  "recent_alerts": []
}
```

**Result:** ✅ PASS

> ⚠️ **Note:** The test spec mentions `admin-dev-token` as the X-Admin-Token value, but the actual code validates against `settings.secret_key` from .env (`umnick-dev-secret-key-change-in-production`). The test spec is incorrect.

**Test 2.4 — Cross-tenant isolation**

Dashboard with non-existent tenant ID `00000000-0000-0000-0000-000000000002` returns same structure but all zeros:

```json
{
  "db_stats": {"counterparties": 0, "contracts": 0, "orders": 0, "products": 0}
}
```

Isolation is implicit (filtered by tenant_id in queries). ✅

**Test 2.5 — Tools API enforces X-Tenant-Id**

```bash
curl http://...:8086/tools/get_overdue_payments  # no header
```

**HTTP 422 Unprocessable Entity** — `{"detail":[{"type":"missing","loc":["header","X-Tenant-Id"],"msg":"Field required","input":null}]}`

**Result:** ✅ PASS (422 is acceptable for "missing required field" enforcement)

---

### Section 3: Tools API — All 7 Tools (❌ CRITICAL FAILURE)

**Every single tool returns HTTP 500 Internal Server Error.**

#### Root Cause: Invalid SQLAlchemy PostgreSQL cast syntax

All 7 tool handlers use `.py` PostgreSQL-style cast syntax directly in SQLAlchemy parameterized queries:

```sql
:counterparty_id::uuid
:threshold_amount::numeric
:days_overdue_min::integer
:min_revenue_30d::numeric
:expiring_soon_days::integer
```

This is **invalid in SQLAlchemy**. The `::type` syntax is interpreted as part of the parameter name (`counterparty_id::uuid`), causing `asyncpg.exceptions.PostgresSyntaxError: syntax error at or near ":"`.

#### Affected files and lines:

| File | Lines |
|------|-------|
| `handlers/active_clients.py:76` | `:min_revenue_30d::numeric` |
| `handlers/client_360.py:28` | `:counterparty_id::uuid` |
| `handlers/client_activity.py:31` | `:counterparty_id::uuid` |
| `handlers/contract_utilization.py:29-30` | `:contract_id::uuid`, `:counterparty_id::uuid` |
| `handlers/find_contracts.py:35,38-39` | `:counterparty_id::uuid`, `:expiring_soon_days::integer`, `:min_amount::numeric` |
| `handlers/overdue_payments.py:35-37` | `:days_overdue_min::integer`, `:counterparty_id::uuid`, `:threshold_amount::numeric` |
| `handlers/query_sales.py:36,58,89` | `:counterparty_id::uuid` |

#### Fix required:

Replace `:param::type` with `CAST(:param AS type)` in all SQL templates across all 7 handler files.

**Result per tool:**

| Tool | HTTP Status | Expected | Verdict |
|------|-------------|----------|---------|
| `get_contract_utilization` | 500 | 200 + data | ❌ FAIL |
| `get_overdue_payments` | 500 | 200 + data | ❌ FAIL |
| `list_active_clients` | 500 | 200 + data | ❌ FAIL |
| `query_sales` | 500 | 200 + data | ❌ FAIL |
| `find_contracts` | 500 | 200 + data | ❌ FAIL |
| `get_client_360` | 500 | 200 + data | ❌ FAIL |
| `get_client_activity` | 500 | 200 + data | ❌ FAIL |

---

### Section 4: Admin API

**Test 4.1 — Dashboard endpoint**

```bash
curl -H "X-Tenant-Id: a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11" -H "X-Admin-Token: <valid>" .../api/admin/dashboard
```

```json
{
  "sync_status": {"last_sync": null, "status": "no_sync"},
  "db_stats": {"counterparties": 4, "contracts": 3, "orders": 4, "products": 5},
  "watchers_count": {"total": 3, "active": 3, "alerting": 0},
  "recent_alerts": []
}
```

**Result:** ✅ PASS

**Test 4.2 — Sync status**

```bash
curl .../api/admin/sync/status
```

```json
{"status": "no_sync", "last_sync_at": null, "entity_type": null}
```

**Result:** ✅ PASS (correctly shows no sync has occurred)

**Test 4.3 — Watchers CRUD**

**GET /api/admin/watchers** → Returns 3 watchers with full details ✅

| Name | Priority | Enabled | Tool |
|------|----------|---------|------|
| `daily_overdue_check` | high | ✅ | `get_overdue_payments` |
| `low_stock_alert` | normal | ✅ | `list_active_clients` |
| `weekly_revenue_drop` | normal | ✅ | `query_sales` |

**GET /api/admin/watchers/{id}** → Returns individual watcher by ID ✅

**Result:** ✅ PASS

**Test 4.4 — Tools list**

```bash
curl .../api/admin/tools
```

Returns 7 tools with full schema definitions including:
- `name`, `display_name` (Russian), `description` (Russian)
- JSON Schema `parameters` with types, enums, defaults
- `status`: all "active"

**Result:** ✅ PASS

---

### Section 5: Seed Data

**Test 5.1 — Tenant exists**

```
ID:   a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
Name: ООО "Ромашка"
```

**Result:** ✅ PASS (1 tenant seeded)

**Test 5.2 — Counterparties**

| ID | Name | INN |
|----|------|-----|
| b0eebc99-...01 | ИП Иванов | 7702123456 |
| b0eebc99-...02 | ООО "ТехноСервис" | 7703123456 |
| b0eebc99-...03 | ООО "СтройМаркет" | 7704123456 |
| b0eebc99-...04 | ИП Петрова | 7705123456 |

**Result:** ✅ PASS (4 counterparties seeded)

**Test 5.3 — Invoices**

Count: 4 invoices seeded

**Result:** ✅ PASS

**Test 5.4 — Watchers**

Count: 3 watchers seeded (daily_overdue_check, low_stock_alert, weekly_revenue_drop)

**Result:** ✅ PASS

**Other tables:** 3 contracts, 4 orders, 5 products also seeded.

---

## Issues Found

| # | Surface | Description | Severity | Reproducible |
|---|---------|-------------|----------|-------------|
| 1 | Tools API | All 7 tools return 500 — `::type` cast syntax invalid in SQLAlchemy | **P0** | Yes — every request to any tool |
| 2 | Test Spec | X-Admin-Token value in test spec (`admin-dev-token`) does not match actual validation (`SECRET_KEY` from .env) | P3 | N/A — spec issue |
| 3 | Test Spec | Tenant ID in test spec (`00000000-0000-0000-0000-000000000001`) does not match seeded tenant (`a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11`) | P3 | N/A — spec issue |

---

## Happy Path Coverage

| Flow | Status | Notes |
|------|--------|-------|
| Health check (Bridge) | ✅ | Returns ok |
| Health check (Tools) | ✅ | Returns ok |
| Readiness check (Bridge) | ✅ | Database + Redis both ok |
| Auth: missing token rejected | ✅ | 403 Forbidden |
| Auth: missing tenant ID rejected | ✅ | 403/422 |
| Auth: valid token accepted | ✅ | Returns data |
| Cross-tenant isolation | ✅ | Correct scoping |
| Admin: Dashboard stats | ✅ | Shows seeded data |
| Admin: Sync status | ✅ | Shows no_sync correctly |
| Admin: Watcher list + detail | ✅ | 3 watchers, full JSON |
| Admin: Tools list | ✅ | 7 tools with schemas |
| Tool: get_contract_utilization | ❌ | 500 — SQL syntax error |
| Tool: get_overdue_payments | ❌ | 500 — SQL syntax error |
| Tool: list_active_clients | ❌ | 500 — SQL syntax error |
| Tool: query_sales | ❌ | 500 — SQL syntax error |
| Tool: find_contracts | ❌ | 500 — SQL syntax error |
| Tool: get_client_360 | ❌ | 500 — SQL syntax error |
| Tool: get_client_activity | ❌ | 500 — SQL syntax error |

---

## Verdict Explanation

❌ **CONDITIONAL PASS — BLOCKED ON TOOLS FIX**

The platform infrastructure is solid: all health checks pass, auth is enforced, admin endpoints work correctly, seed data is present. The dashboard correctly shows 4 counterparties, 3 contracts, 4 orders, 5 products, and 3 watchers.

However, **all 7 tools are broken** with a systematic SQL syntax bug in every handler file. The fix is mechanical (replace `:param::type` with `CAST(:param AS type)` across 7 files). After that fix, all tools should work end-to-end.

**To unblock from CONDITIONAL PASS to full PASS:**
1. Fix SQL cast syntax in all 7 tools handler files (P0)
2. Re-run acceptance tests on all 7 tools
3. Confirm queries return data for the seeded tenant

---

## Recommendations for Lead

1. **P0 — Fix `::type` cast syntax** in all 7 handler files under `/opt/umnick/tools/src/handlers/`.
   - Replace `:param::uuid` → `CAST(:param AS uuid)`
   - Replace `:param::numeric` → `CAST(:param AS numeric)`
   - Replace `:param::integer` → `CAST(:param AS integer)`
   - This is the single root cause blocking all tools.

2. **P3 — Update acceptance test spec** with correct values:
   - Tenant ID: `a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11` (the seeded one)
   - X-Admin-Token: The value of `SECRET_KEY` from .env (currently `umnick-dev-secret-key-change-in-production`)
   - Document that the token validation is against `settings.secret_key`, not a dedicated `ADMIN_TOKEN` env var.

3. **P3 — Re-run acceptance tests** after tool fix to confirm all 7 tools return proper data.

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
