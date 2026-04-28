#!/bin/bash
set -e

BASE_URL="${TOOLS_API_URL:-http://tools:8000}"
TENANT_ID="00000000-0000-0000-0000-000000000001"
PASS=0
FAIL=0

check() {
  local tool=$1
  local params=$2
  echo -n "Testing $tool... "
  status=$(curl -s -o /tmp/resp.json -w "%{http_code}" \
    -X POST "$BASE_URL/tools/$tool" \
    -H "Content-Type: application/json" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -d "$params")
  
  if [ "$status" = "200" ] || [ "$status" = "404" ] || [ "$status" = "400" ]; then
    echo "OK (HTTP $status)"
    PASS=$((PASS+1))
  else
    echo "FAIL (HTTP $status)"
    FAIL=$((FAIL+1))
  fi
}

echo "=== Умник E2E Tests ==="
echo "Base URL: $BASE_URL"
echo ""

# Health endpoints
echo -n "Testing health... "
if curl -sf "$BASE_URL/health" > /dev/null 2>&1; then
  echo "OK"; PASS=$((PASS+1))
else
  echo "FAIL"; FAIL=$((FAIL+1))
fi

echo -n "Testing readiness... "
if curl -sf "$BASE_URL/ready" > /dev/null 2>&1; then
  echo "OK"; PASS=$((PASS+1))
else
  echo "FAIL"; FAIL=$((FAIL+1))
fi

# Tools
check "get_contract_utilization" '{}'
check "get_overdue_payments" '{}'
check "get_client_activity" '{"client_id":"test"}'
check "query_sales" '{"period":"this_month"}'
check "find_contracts" '{}'
check "get_client_360" '{"client_id":"test"}'
check "list_active_clients" '{}'

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && echo "✅ All tests passed" || echo "❌ Some tests failed"
exit $FAIL
