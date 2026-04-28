from __future__ import annotations

"""
Базовый класс для синхронизации сущностей из 1С по OData.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from logging_setup import get_logger, correlation_id_ctx
from models import SyncLog
from odata import ODataClient, ODataConnectionParams

logger = get_logger(__name__)


@dataclass
class SyncResult:
    """Результат синхронизации одной сущности."""
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_errors: int = 0
    error_message: str | None = None
    duration_ms: int = 0


class BaseSyncWorker(ABC):
    """Абстрактный класс синхронизации сущности."""

    def __init__(self, tenant_id: uuid.UUID, tenant_settings: dict[str, Any]):
        self.tenant_id = tenant_id
        self.tenant_settings = tenant_settings
        self.odata_client = ODataClient(
            ODataConnectionParams(
                base_url=tenant_settings.get("odata_url", ""),
                username=tenant_settings.get("odata_username", ""),
                password=tenant_settings.get("odata_password_enc", ""),
            )
        )

    @property
    @abstractmethod
    def entity_name(self) -> str:
        """Имя сущности (соответствует sync_type)."""
        ...

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Имя таблицы в БД (схема.таблица)."""
        ...

    @abstractmethod
    def map_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Маппинг записи из 1С → унифицированная модель."""
        ...

    async def get_max_data_version(self, session: AsyncSession) -> int:
        """Получить максимальную версию данных для сущности."""
        result = await session.execute(
            text(f"""
                SELECT COALESCE(MAX(data_version), 0)
                FROM {self.table_name}
                WHERE tenant_id = :tenant_id
            """),
            {"tenant_id": self.tenant_id},
        )
        return result.scalar() or 0

    async def run(self, session: AsyncSession) -> SyncResult:
        """Выполнить синхронизацию."""
        start_ts = datetime.now(timezone.utc)
        result = SyncResult()

        try:
            max_version = await self.get_max_data_version(session)
            logger.info(
                "Starting sync",
                entity=self.entity_name,
                tenant_id=str(self.tenant_id),
                max_version=max_version,
            )

            fetch_result = await self.odata_client.fetch_incremental(
                self.entity_name,
                last_data_version=max_version,
            )

            if fetch_result.error:
                result.error_message = fetch_result.error
                logger.error(
                    "Sync fetch error",
                    entity=self.entity_name,
                    error=fetch_result.error,
                )
                return result

            records = fetch_result.records
            result.records_processed = len(records)

            for record in records:
                try:
                    mapped = self.map_record(record)
                    await self._upsert_record(session, mapped)
                    result.records_created += 1
                    result.records_updated += 1  # Combined for now
                except Exception as e:
                    result.records_errors += 1
                    logger.warning(
                        "Record sync error",
                        entity=self.entity_name,
                        error=str(e),
                        external_id=record.get("Ref_Key"),
                    )

            await session.commit()

        except Exception as e:
            result.error_message = str(e)
            logger.error(
                "Sync error",
                entity=self.entity_name,
                error=str(e),
            )
            await session.rollback()

        finally:
            end_ts = datetime.now(timezone.utc)
            result.duration_ms = int((end_ts - start_ts).total_seconds() * 1000)
            status = "error" if result.error_message else "success"

            # Сохраняем лог синхронизации
            sync_log = SyncLog(
                tenant_id=self.tenant_id,
                sync_type=self.entity_name,
                status=status,
                records_processed=result.records_processed,
                records_updated=result.records_updated,
                records_created=result.records_created,
                records_errors=result.records_errors,
                duration_ms=result.duration_ms,
                error_message=result.error_message,
                correlation_id=correlation_id_ctx.get(),
            )
            session.add(sync_log)
            await session.commit()

            logger.info(
                "Sync completed",
                entity=self.entity_name,
                status=status,
                processed=result.records_processed,
                duration_ms=result.duration_ms,
            )

        return result

    @staticmethod
    def _parse_data_version(date_time_val: Any) -> int:
        """Парсинг Date_Time из 1С в data_version (ms timestamp)."""
        if isinstance(date_time_val, (int, float)):
            return int(date_time_val)
        if isinstance(date_time_val, str):
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(date_time_val.replace("Z", "+00:00"))
                return int(dt.timestamp() * 1000)
            except ValueError:
                return 0
        return 0

    @staticmethod
    def _parse_date(date_val: Any) -> str | None:
        """Парсинг даты из 1С в YYYY-MM-DD."""
        if date_val is None:
            return None
        if isinstance(date_val, str):
            return date_val[:10]
        return str(date_val)

    @staticmethod
    def _extract_key(key_val: Any) -> str | None:
        """Извлечь GUID из ссылочного поля 1С."""
        if isinstance(key_val, str):
            return key_val
        if isinstance(key_val, dict):
            return key_val.get("Ref_Key") or str(key_val)
        if key_val is None:
            return None
        return str(key_val)

    async def _upsert_record(self, session: AsyncSession, mapped: dict[str, Any]) -> None:
        """UPSERT запись в БД."""
        columns = ", ".join(mapped.keys())
        placeholders = ", ".join(f":{k}" for k in mapped)
        updates = ", ".join(
            f"{k} = EXCLUDED.{k}"
            for k in mapped
            if k not in ("tenant_id", "external_id")
        )

        query = text(f"""
            INSERT INTO {self.table_name} (tenant_id, {columns})
            VALUES (:tenant_id, {placeholders})
            ON CONFLICT (tenant_id, external_id)
            DO UPDATE SET {updates}, updated_at = NOW()
        """)

        await session.execute(query, {"tenant_id": self.tenant_id, **mapped})
