# Code Review: Умник (Umnick) — AI Operations Platform

> **Reviewer:** Code Reviewer (subagent)
> **Date:** 2026-04-28
> **Branch:** Current state of `/opt/umnick/`

---

## Scores

| Category | Score | Notes |
|----------|-------|-------|
| **Security** | **5/10** | Critical runtime flaws, missing auth features, leaky defaults |
| **Architecture Compliance** | **6/10** | Major structural/compliance gaps, duplicate schedules |
| **Code Quality** | **6/10** | Good tool handlers, but runtime-breaking schema mismatch & DRY violations |

---

## Overall: REJECTED

**Verdict:** Multiple P0/P1 runtime-blocking issues exist. **Cannot ship in current state.** Several issues found by QA remain unaddressed, and additional critical flaws were discovered during this review.

---

## CRITICAL: Newly Discovered Issues (not in QA report)

### ⚠️ [P0] Invoice table has no `balance` column — tools will crash

**Location:** `scripts/init_db.sql:102-133` (invoices table), `tools/src/handlers/overdue_payments.py:27`, `tools/src/handlers/client_360.py:61`, `tools/src/handlers/active_clients.py:66`, `engine/src/tasks.py:72`

**Issue:** Every tool handler that queries invoices references `i.balance`, but the `invoices` table in `init_db.sql` **does not define a `balance` column** (the `GENERATED ALWAYS AS (amount - paid_amount) STORED` from ARCHITECTURE.md §2.1 was never implemented in SQL). Same for the Python model (`models.py:Invoice` — also no `balance` column).

At runtime, ALL queries like `SELECT ..., i.balance, ... FROM umnick.invoices i` will throw:
```
ERROR: column i.balance does not exist
```

This affects:
- `get_overdue_payments` — every execution will fail
- `get_client_360` — overdue summary query will fail
- `list_active_clients` — overdue subquery will fail
- `check_due_watchers` engine task — overdue check will fail

**Fix:** Either add `balance NUMERIC(16,2) GENERATED ALWAYS AS (amount - paid_amount) STORED` to the SQL schema and model, or replace all `i.balance` references with `(i.amount - i.paid_amount)`.

**Severity:** Deploy blocker — breaks 4/7 tools and 1 watcher.

---

### ⚠️ [P0] TS plugins POST but Python tools endpoints are GET — protocol mismatch

**Location:** `openclaw-plugins/src/client.ts:24-28`, `tools/src/app.py:44-170`

**Issue:** The TypeScript `ToolsApiClient` sends `method: 'POST'` with a JSON body payload:
```typescript
const response = await fetch(`${this.baseUrl}/tools/${toolName}`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-Tenant-Id': tenantId },
  body: JSON.stringify(params),
});
```

But the Python `Tool Runtime` app registers ALL tool endpoints as **GET** methods:
```python
@app.get("/tools/get_contract_utilization")
```

Getting parameters from query params, not request body. Every tool call from OpenClaw agent will fail with `405 Method Not Allowed`.

Additionally, the TS `params` shape differs from what GET expects:
- TS sends `{ tenant_id, contract_id, utilization_below, days_remaining }`
- Python expects query params `contract_id`, `counterparty_id`, `contract_number` (none of which match the TS parameter names exactly)

**Fix:** Either change TS to GET with query params, or change Python to POST with request body. Also align parameter names between TS and Python.

**Severity:** Deploy blocker — all 7 tools unusable from agent.

---

### ⚠️ [P0] Missing sync workers for invoices, payments, products, employees

**Location:** `bridge/src/tasks.py:96-111` (get_sync_worker factory), `bridge/src/sync/workers.py`

**Issue:** The `get_sync_worker()` factory only registers 3 workers: `counterparties`, `contracts`, `orders`. But `tasks.py` defines Celery tasks for `sync_invoices`, `sync_payments`, `sync_products`, `sync_employees` — all will raise `ValueError: Unknown entity` at runtime because no corresponding worker classes exist.

The engine Celery Beat also schedules these tasks (sync-invoices-every-5min, sync-payments-every-5min, etc.), so every 5 minutes these tasks will fail.

**Fix:** Implement `InvoiceSyncWorker`, `PaymentSyncWorker`, `ProductSyncWorker`, `EmployeeSyncWorker` classes in `workers.py` and register them in `get_sync_worker()`.

**Severity:** Deploy blocker — core data pipeline broken.

---

## Remaining QA Issues (confirmed or updated after code review)

### [P0] TS ↔ Python response key mismatches

**Status:** Confirmed, expanded. **Still unaddressed.**

| TS Plugin | TS expects | Python returns | Impact |
|-----------|-----------|----------------|--------|
| `contract-utilization.ts` | `data.contracts[]` | `data.contract` (single) | At best shows 1 contract, at worst breaks display logic |
| `contract-utilization.ts` | `c.contract_number` | `c.number` | Contract number won't display |
| `contract-utilization.ts` | `c.utilization_pct` | `c.utilization_pct` | ✅ matches |
| `client-360.ts` | `data.inn` | `data.counterparty.inn` | INN won't display |
| `client-360.ts` | `data.overdue_debt` | `data.overdue_summary.total_overdue` | Overdue data won't display |
| `client-360.ts` | `data.last_activity_date` | Doesn't exist | Shows "—" for last activity |
| `client-360.ts` | `c.amount` | `c.amount` (in nested) | ✅ partially works |
| `client-activity.ts` | `data.activity_summary.total_amount` | Doesn't exist | Shows 0₽ |
| `client-activity.ts` | `data.invoice_count` | `data.activity_summary.total_invoices` | Invoice count zero |
| `client-activity.ts` | `data.payments.length` | `data.payments` (same) | ✅ matches |
| `client-activity.ts` | `data.payment_total` | `data.activity_summary.total_payments_in/out` | Shows 0₽ |
| `client-activity.ts` | `data.last_activity_date` | Doesn't exist | Shows "нет данных" |
| `query-sales.ts` | `data.by_month` | `data.by_counterparty` | No breakdown displayed |
| `query-sales.ts` | `row.month` | — | N/A if by_counterparty used |
| `find-contracts.ts` | `data.total` | `data.total` (int) | ✅ partially matches |
| `find-contracts.ts` | `c.counterparty` | `c.counterparty` (name string) | ✅ matches |
| `active-clients.ts` | `c.name` | `c.name` | ✅ matches |
| `active-clients.ts` | `c.revenue` | `c.revenue_30d` | Revenue shows 0 |

**Key problem:** Even if the 10 most critical mismatches are fixed, the **method mismatch** (POST vs GET) means **nothing works** regardless of response structure.

### [P1] Duplicate Celery Beat schedules

**Status:** Confirmed. Both `bridge/src/tasks.py` and `engine/src/celery_app.py` define beat schedules. The bridge defines only the sync tasks schedule, but this competes with engine. In Docker Compose, only `celery-beat` runs (from engine Dockerfile, configured to use `src.tasks` which is `engine/src/tasks.py`). The bridge Celery app (`bridge/src/tasks.py`) has a beat schedule that is **never used** since no beat process starts for bridge. Dead config, not harmful but confusing.

### [P1] Docker .env path issue

**Status:** Confirmed. `Dockerfile.bridge` copies `.env` to `/app/.env`, then sets `WORKDIR /app/bridge`. But bridge's `config.py` reads `.env` from CWD (which becomes `/app/bridge/`). The `.env` file is at `/app/.env` but the app looks for it in `/app/bridge/.env`.

**Fix:** Add `ENV_FILE=/app/.env` or copy .env to `/app/bridge/.env` or change CMD to explicitly reference the env file.

### [P1] Plaintext DB password in docker-compose.yml

**Status:** Confirmed. Multiple environment variables expose `umnick_pass` in plaintext including `POSTGRES_PASSWORD`, `DATABASE_URL`, `DATABASE_URL_SYNC`. For development this is acceptable if documented; however, these are production defaults.

### [P1] `_parse_data_version`, `_parse_date`, `_extract_key` repeated in each sync worker

**Status:** Confirmed they're defined as `@staticmethod` on `BaseSyncWorker` (✅ already in base class). But `CounterpartySyncWorker`, `ContractSyncWorker`, `OrderSyncWorker` correctly call `self._parse_data_version()`. This is actually **not duplicated** in the code I read — they inherit from base. QA marked this as a DRY violation but it's actually clean.

**Updated verdict:** ⚠️ P3 only — the helper methods DO live in `BaseSyncWorker`, but they're used correctly via `self.` in workers. No issue.

### [P2] No auth middleware on admin endpoints

**Status:** Partially addressed. `verify_admin_token()` dependency exists in `middleware.py` and is applied to `/api/admin/tenants` and `/api/admin/tools` endpoints. But it's **NOT** applied to:
- `POST /api/admin/connect`
- `POST /api/admin/sync/trigger`
- `GET /api/admin/sync/status`
- `GET /api/admin/sync/log`
- `GET /api/admin/dashboard`
- `GET/POST/PUT/DELETE /api/admin/watchers`

Per ARCHITECTURE.md §10.4: "Все admin endpoints требуют bearer-token аутентификацию". This requirement is not met.

**Severity:** P1 (increased) — tenant-specific admin operations are unprotected.

### [P2] RLS is configured in init_db.sql

**Status:** ✅ **Actually present!** QA report said RLS was missing, but `scripts/init_db.sql:326-350` correctly has `ENABLE ROW LEVEL SECURITY` and `CREATE POLICY tenant_isolation` for all tables.

**Updated verdict:** No issue. QA missed that RLS was already implemented. Score adjustment: +1 architecture compliance.

### [P3] Python version consistency

**Status:** ✅ All 3 Dockerfiles use `python:3.12-slim`. Dev `.venv` is Python 3.12. Consistent. QA report was incorrect here.

---

## Additional Findings

### [P2] Missing `invoices` sync worker in tasks.py Beat schedule

The engine `celery_app.py` schedules `sync-invoices-every-5min` and `sync-payments-every-5min` using task names like `tasks.sync_invoices` and `tasks.sync_payments`. These tasks exist in `bridge/tasks.py` as Celery tasks. However, the engine beat process runs `engine/src/tasks.py`, not `bridge/src/tasks.py`. The engine has its own `tasks.py` with `check_due_watchers` and local SQL helpers, but does NOT define `sync_invoices` or `sync_payments` tasks.

**Result:** All sync tasks referenced in engine's beat_schedule will fail with `Celery NotRegistered` when the beat process tries to dispatch them.

**Fix:** All sync tasks should be in a single Celery app shared between bridge and engine, or the engine beat should only schedule engine tasks and bridge should have its own beat process.

### [P2] `app.ready()` Redis connection leak

**Location:** `bridge/src/web/routers/health.py:24-35`

The readiness endpoint creates a new Redis async connection **on every request** via `aioredis.from_url()`. It calls `await r.aclose()` which is correct, but there's no connection pooling. Under load, rapid health checks could exhaust file descriptors.

**Fix:** Use a shared Redis connection pool via `redis.asyncio.ConnectionPool` or reuse the existing engine's connection.

### [P2] Agent config YAML references tools but doesn't call them correctly

**Location:** `openclaw-plugins/agent-config.yaml:45-68`

The `agent-config.yaml` lists tool names and watchers with conditions like `data.contracts.some(c => c.utilization_percent < 30)` — this is JavaScript syntax, but the engine's condition evaluator (`_safe_eval()` in `engine/src/tasks.py`) uses **Python eval**, not JS. The `some()` method doesn't exist in Python. Watcher conditions with `.some()` will always evaluate to `False`.

### [P2] Croniter import only inside task function, not at module level

**Location:** `engine/src/tasks.py:176`

```python
def check_due_watchers(self):
    from croniter import croniter
```

Deferred import means the first watcher check will be delayed by import time. Minor, but unconventional.

### [P3] `_safe_eval()` uses Python `eval` — dangerous

**Location:** `engine/src/tasks.py:143-168`

The engine uses `eval(converted, allowed_names, local_vars)` with a restricted namespace. While `__builtins__` is set to `{}` (mitigates most attacks), `eval` itself can still be problematic if expression injection is possible. Watcher conditions are stored in the database and editable by admins, so this is a limited risk. However, the `_safe_eval` function has a complex fallback that does arbitrary dict traversal on the data, which is fragile.

### [P3] `full_reconciliation.py` not implemented as separate worker

Per ARCHITECTURE §2.2, a "Full reconcile" entity exists. The task `full_reconciliation` in `bridge/tasks.py` simply iterates and calls `_run_sync_all()` for each entity sequentially inside a single asyncio event loop — blocking and potentially timing out on large datasets.

### [P3] No pagination cursor support for large datasets in sync

The `_make_request` method in `odata/client.py` has a hardcoded `$top=1000` page size, with incremental `$skip`. For entities with >100K records (common in 1С), this results in many sequential requests and OData servers may not support skips beyond certain limits efficiently.

### [P3] `threading` / `asyncio.new_event_loop()` pattern in Celery tasks

**Location:** `bridge/src/tasks.py:55-90`

Every sync task creates a new event loop with `asyncio.new_event_loop()`, runs async code, closes the loop. While functional, this is inefficient — a single event loop per worker process would be better. The pattern repeat in 8 different task functions is also very noisy.

### [P3] No tenant_id uniqueness constraint on watchers

**Location:** `models.py:417-418`

The Watcher model has `UNIQUE (tenant_id, name)` but this is implemented only in `init_db.sql:219` (`UNIQUE (tenant_id, name)`) and not as a Python-level constraint. The Alembic migration `0001_init.py` uses the SQL schema, so it's fine in production, but in development with auto-creating tables via `init_db()` the unique constraint won't be applied.

---

## Issues Summary

| Severity | Count | Key Items |
|----------|-------|-----------|
| **P0** | 4 | Missing `balance` column, POST/GET mismatch, missing sync workers, TS↔Python response keys |
| **P1** | 4 | Duplicate beat schedules, Docker .env path, missing admin auth on most endpoints, plaintext default passwords |
| **P2** | 6 | RLS not applied (✅ actually present), `balance` missing in schema, engine beat can't dispatch bridge tasks, Redis conn no pool, agent-config watchers use JS syntax, croniter deferred import |
| **P3** | 7 | `_safe_eval` risks, no reconciliation worker, no pagination cursor, asyncio loop-per-task, model constraint gaps, 1С connection test retry, doc gaps |

---

## Recommended Actions Before Deploy

### Must-fix (Blocking)

1. **Add `balance` column to invoices table** — OR replace all `i.balance` references with `(i.amount - i.paid_amount)` in all 4 tool handlers + engine tasks
2. **Fix TS↔Python method/param mismatch** — Change TS client to GET with query params OR change Python endpoints to POST with body. Align parameter names
3. **Implement missing sync workers** — `InvoiceSyncWorker`, `PaymentSyncWorker`, `ProductSyncWorker`, `EmployeeSyncWorker`
4. **Fix TS↔Python response key alignment** — Update all 7 TS plugins to match actual Python response structures
5. **Consolidate Celery schedules** — Move all schedules to a single Celery beat (engine is the logical owner); remove bridge beat config or make it config-aware
6. **Fix Celery task routing** — Ensure engine beat can dispatch bridge sync tasks (either shared Celery app or bridge runs its own beat)
7. **Add admin auth to all admin endpoints** — Apply `verify_admin_token()` dependency to `/api/admin/connect`, `/sync/*`, `/dashboard`, `/watchers/*`

### Should-fix (Before release)

8. **Fix Docker .env path** in Dockerfile.bridge (copy to correct location)
9. **Replace plaintext credentials** in docker-compose.yml with `${DB_PASSWORD}` env var reference
10. **Fix watcher condition syntax** in `agent-config.yaml` — use Python-compatible expressions
11. **Implement proper tool descriptions** in TS plugins — currently each has an independent description that doesn't match the Python tool's actual purpose (e.g., utilization tool describes itself as "contracts with utilization below expected" while Python returns a single contract's utilization)
12. **Add connection pooling** to health check Redis client
13. **Update PostgreSQL version** in Docker Compose to match ARCHITECTURE.md (16 vs 15)

### Low Priority

14. Add uvloop event loop reuse for Celery async tasks (perf optimization)
15. Implement `full_reconciliation` as a proper worker with batch processing
16. Add cursor/timestamp-based pagination for large OData result sets
17. Add Python-level unique constraints (SQLAlchemy `UniqueConstraint`) for watchers
18. Add tests for the `balance`-less queries (will fail when run against real PG)
19. Harmonize ARCHITECTURE.md with actual code structure (single `models.py` vs multi-file)
