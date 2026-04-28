"""
Tests for the Data Bridge.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport


class TestMessages:
    """Test Russian localization strings."""

    def test_messages_defined(self):
        from messages_ru import (
            TENANT_ID_REQUIRED, SYNC_TRIGGERED,
            SYNC_CONNECTION_OK, ENTITY_LABELS,
        )

        assert TENANT_ID_REQUIRED
        assert SYNC_TRIGGERED
        assert SYNC_CONNECTION_OK
        assert len(ENTITY_LABELS) >= 7
        assert ENTITY_LABELS["orders"] == "Заказы"


class TestCrypto:
    """Test credential encryption/decryption."""

    def test_encrypt_decrypt_roundtrip(self):
        from crypto import CredentialCrypto

        crypto = CredentialCrypto(key=b"testkey1234567890123456789012345")
        plaintext = "my_secret_password_123"

        encrypted = crypto.encrypt(plaintext)
        assert encrypted != plaintext
        assert isinstance(encrypted, str)

        decrypted = crypto.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_different_nonce(self):
        from crypto import CredentialCrypto

        crypto = CredentialCrypto(key=b"testkey1234567890123456789012345")
        plaintext = "same_text"

        encrypted1 = crypto.encrypt(plaintext)
        encrypted2 = crypto.encrypt(plaintext)
        assert encrypted1 != encrypted2  # Different nonce
        assert crypto.decrypt(encrypted1) == plaintext
        assert crypto.decrypt(encrypted2) == plaintext


class TestODataClient:
    """Test OData client."""

    def test_client_init(self):
        from odata import ODataClient, ODataConnectionParams

        params = ODataConnectionParams(
            base_url="https://test.server.com/odata",
            username="admin",
            password="secret",
        )
        client = ODataClient(params)
        assert client.base_url == "https://test.server.com/odata"

    def test_entity_configs_defined(self):
        from odata import ODATA_ENTITY_CONFIGS

        assert "counterparties" in ODATA_ENTITY_CONFIGS
        assert "contracts" in ODATA_ENTITY_CONFIGS
        assert "orders" in ODATA_ENTITY_CONFIGS
        assert "invoices" in ODATA_ENTITY_CONFIGS
        assert "payments" in ODATA_ENTITY_CONFIGS
        assert "products" in ODATA_ENTITY_CONFIGS
        assert "employees" in ODATA_ENTITY_CONFIGS
        assert len(ODATA_ENTITY_CONFIGS) >= 7


class TestConfig:
    """Test configuration loading."""

    def test_config_loads(self):
        from config import settings

        assert settings is not None
        assert settings.database_url is not None

    def test_config_has_defaults(self):
        from config import settings

        assert settings.log_level == "INFO"
        assert settings.redis_url == "redis://redis:6379/0"


class TestSyncWorkers:
    """Test sync worker factory."""

    def test_counterparty_mapping(self):
        from sync.workers import CounterpartySyncWorker
        import uuid

        record = {
            "Ref_Key": "test-ext-id",
            "Description": "ООО Тест",
            "INN": "7701123456",
            "IsBuyer": True,
            "Date_Time": "2026-04-28T21:00:00Z",
        }

        # Create worker and test mapping
        worker = CounterpartySyncWorker(
            tenant_id=uuid.uuid4(),
            tenant_settings={"odata_url": "http://test", "odata_username": "", "odata_password_enc": ""},
        )
        mapped = worker.map_record(record)

        assert mapped["external_id"] == "test-ext-id"
        assert mapped["name"] == "ООО Тест"
        assert mapped["inn"] == "7701123456"
        assert mapped["is_buyer"] is True
        assert mapped["is_client"] is True

    def test_contract_mapping(self):
        from sync.workers import ContractSyncWorker
        import uuid

        record = {
            "Ref_Key": "contract-ext-1",
            "Description": "Д-2025/001",
            "StartDate": "2025-01-01T00:00:00",
            "FinishDate": "2026-12-31T00:00:00",
            "Amount": 1500000.0,
            "Currency": "RUB",
            "Date_Time": "2026-04-28T21:00:00Z",
        }

        worker = ContractSyncWorker(
            tenant_id=uuid.uuid4(),
            tenant_settings={"odata_url": "http://test", "odata_username": "", "odata_password_enc": ""},
        )
        mapped = worker.map_record(record)

        assert mapped["external_id"] == "contract-ext-1"
        assert mapped["number"] == "Д-2025/001"
        assert mapped["date_start"] == "2025-01-01"
        assert mapped["amount"] == 1500000.0

    def test_order_mapping(self):
        from sync.workers import OrderSyncWorker
        import uuid

        record = {
            "Ref_Key": "order-ext-1",
            "Description": "ЗК-2026/001",
            "Date": "2026-04-15T00:00:00",
            "Amount": 340000.0,
            "Currency": "RUB",
            "Date_Time": "2026-04-28T21:00:00Z",
        }

        worker = OrderSyncWorker(
            tenant_id=uuid.uuid4(),
            tenant_settings={"odata_url": "http://test", "odata_username": "", "odata_password_enc": ""},
        )
        mapped = worker.map_record(record)

        assert mapped["external_id"] == "order-ext-1"
        assert mapped["number"] == "ЗК-2026/001"
        assert mapped["date"] == "2026-04-15"


class TestSyncBase:
    """Test abstract sync worker."""

    def test_sync_result_dataclass(self):
        from sync.base import SyncResult

        result = SyncResult()
        assert result.records_processed == 0
        assert result.records_created == 0
        assert result.records_updated == 0
        assert result.records_errors == 0
        assert result.error_message is None
        assert result.duration_ms == 0

        result.records_processed = 42
        result.error_message = "Test error"
        assert result.records_processed == 42
        assert result.error_message == "Test error"
