"""
Tests for the Tool Library — schemas and handler logic.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSchemas:
    """Test Pydantic request/response models."""

    def test_contract_utilization_params(self):
        from schemas import ContractUtilizationParams

        params = ContractUtilizationParams(contract_id=str(uuid.uuid4()))
        assert params.contract_id is not None
        assert params.counterparty_id is None
        assert params.contract_number is None

    def test_overdue_payments_params_defaults(self):
        from schemas import OverduePaymentsParams

        params = OverduePaymentsParams()
        assert params.days_overdue_min == 1
        assert params.limit == 20
        assert params.counterparty_id is None
        assert params.threshold_amount is None

    def test_overdue_payments_params_custom(self):
        from schemas import OverduePaymentsParams

        params = OverduePaymentsParams(
            days_overdue_min=7,
            limit=10,
            threshold_amount=5000.0,
        )
        assert params.days_overdue_min == 7
        assert params.limit == 10
        assert params.threshold_amount == 5000.0

    def test_query_sales_params(self):
        from schemas import QuerySalesParams

        params = QuerySalesParams(period_days=90, granularity="week")
        assert params.period_days == 90
        assert params.granularity == "week"
        assert params.include_chart_data is False

    def test_client_activity_params_requires_one(self):
        from schemas import ClientActivityParams

        # All optional — validated at handler level
        params = ClientActivityParams(counterparty_id=str(uuid.uuid4()))
        assert params.counterparty_id is not None

    def test_find_contracts_params(self):
        from schemas import FindContractsParams

        params = FindContractsParams(
            query="Д-2025",
            status="active",
            limit=10,
        )
        assert params.query == "Д-2025"
        assert params.status == "active"
        assert params.limit == 10
        assert params.min_amount is None

    def test_client_360_params(self):
        from schemas import Client360Params

        params = Client360Params(inn="7701123456")
        assert params.inn == "7701123456"
        assert params.counterparty_id is None
        assert params.name_query is None

    def test_active_clients_params(self):
        from schemas import ActiveClientsParams

        params = ActiveClientsParams(
            segment="vip",
            sort_by="revenue",
            limit=10,
        )
        assert params.segment == "vip"
        assert params.sort_by == "revenue"
        assert params.limit == 10

    def test_tool_response(self):
        from schemas import ToolResponse

        resp = ToolResponse(success=True, data={"key": "value"})
        assert resp.success is True
        assert resp.data["key"] == "value"
        assert resp.error is None

        err_resp = ToolResponse(success=False, error="Something went wrong")
        assert err_resp.success is False
        assert err_resp.error == "Something went wrong"


class TestToolHandlers:
    """Test tool handler logic (mocked DB)."""

    @pytest.mark.asyncio
    async def test_contract_utilization_no_results(self):
        from handlers.contract_utilization import handle_contract_utilization
        from schemas import ContractUtilizationParams

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        params = ContractUtilizationParams(contract_id=str(uuid.uuid4()))
        result = await handle_contract_utilization(params, str(uuid.uuid4()), mock_session)

        assert result.success is False
        assert "Договор не найден" in (result.error or "")

    @pytest.mark.asyncio
    async def test_overdue_payments_no_results(self):
        from handlers.overdue_payments import handle_overdue_payments
        from schemas import OverduePaymentsParams

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        params = OverduePaymentsParams()
        result = await handle_overdue_payments(params, str(uuid.uuid4()), mock_session)

        assert result.success is True
        assert result.data["summary"]["total_overdue_count"] == 0
        assert result.data["summary"]["total_overdue_sum"] == 0

    @pytest.mark.asyncio
    async def test_overdue_payments_with_results(self):
        from handlers.overdue_payments import handle_overdue_payments
        from schemas import OverduePaymentsParams
        from datetime import date

        mock_session = AsyncMock()
        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda k: {
            "number": "СФ-001",
            "counterparty_name": "ООО Тест",
            "amount": 100000.0,
            "balance": 100000.0,
            "due_date": date(2026, 3, 15),
            "days_overdue": 44,
        }[k]

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        params = OverduePaymentsParams()
        result = await handle_overdue_payments(params, str(uuid.uuid4()), mock_session)

        assert result.success is True
        assert result.data["summary"]["total_overdue_count"] == 1
        assert result.data["summary"]["total_overdue_sum"] == 100000.0
        assert result.data["overdue_invoices"][0]["invoice_number"] == "СФ-001"

    @pytest.mark.asyncio
    async def test_query_sales(self):
        from handlers.query_sales import handle_query_sales
        from schemas import QuerySalesParams

        mock_session = AsyncMock()

        # Mock summary
        mock_summary = MagicMock()
        mock_summary.__getitem__.side_effect = lambda k: {
            "total_revenue": 1000000.0,
            "total_orders": 50,
            "avg_order_value": 20000.0,
        }[k]
        mock_summary_result = MagicMock()
        mock_summary_result.mappings.return_value.first.return_value = mock_summary

        # Mock by_counterparty
        mock_cp = MagicMock()
        mock_cp.__getitem__.side_effect = lambda k: {
            "name": "ООО Тест",
            "revenue": 500000.0,
            "orders_count": 25,
        }[k]
        mock_cp_result = MagicMock()
        mock_cp_result.mappings.return_value.all.return_value = [mock_cp]

        def mock_execute_side_effect(query, *args, **kwargs):
            query_str = str(query)
            if "SUM(amount)" in query_str and "GROUP BY" not in query_str:
                return mock_summary_result
            return mock_cp_result

        mock_session.execute = AsyncMock(side_effect=mock_execute_side_effect)

        params = QuerySalesParams()
        result = await handle_query_sales(params, str(uuid.uuid4()), mock_session)

        assert result.success is True
        assert result.data["summary"]["total_revenue"] == 1000000.0
        assert result.data["summary"]["total_orders"] == 50

    @pytest.mark.asyncio
    async def test_find_contracts(self):
        from handlers.find_contracts import handle_find_contracts
        from schemas import FindContractsParams

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        params = FindContractsParams()
        result = await handle_find_contracts(params, str(uuid.uuid4()), mock_session)

        assert result.success is True
        assert result.data["contracts"] == []
        assert result.data["total"] == 0

    @pytest.mark.asyncio
    async def test_client_360_no_result(self):
        from handlers.client_360 import handle_client_360
        from schemas import Client360Params

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        params = Client360Params(inn="7701123456")
        result = await handle_client_360(params, str(uuid.uuid4()), mock_session)

        assert result.success is False
        assert "Контрагент не найден" in (result.error or "")

    @pytest.mark.asyncio
    async def test_list_active_clients(self):
        from handlers.active_clients import handle_active_clients
        from schemas import ActiveClientsParams

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        params = ActiveClientsParams()
        result = await handle_active_clients(params, str(uuid.uuid4()), mock_session)

        assert result.success is True
        assert result.data["clients"] == []
        assert result.data["total"] == 0

    @pytest.mark.asyncio
    async def test_client_activity_no_cp(self):
        from handlers.client_activity import handle_client_activity
        from schemas import ClientActivityParams

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        params = ClientActivityParams(counterparty_id=str(uuid.uuid4()))
        result = await handle_client_activity(params, str(uuid.uuid4()), mock_session)

        assert result.success is False
        assert "Контрагент не найден" in (result.error or "")

    @pytest.mark.asyncio
    async def test_invalid_tenant_id(self):
        from handlers.contract_utilization import handle_contract_utilization
        from schemas import ContractUtilizationParams

        mock_session = AsyncMock()
        params = ContractUtilizationParams(contract_id=str(uuid.uuid4()))
        result = await handle_contract_utilization(params, "not-a-uuid", mock_session)

        assert result.success is False
        assert "Invalid tenant_id" in (result.error or "")
