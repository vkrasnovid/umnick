from __future__ import annotations

"""
OData клиент для подключения к 1С через протокол OData.

Поддерживает Basic-аутентификацию, постраничную подкачку ($top/$skip),
инкрементальную синхронизацию по полю Date_Time (data_version).
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class ODataEntityConfig:
    """Конфигурация OData сущности."""
    entity_set: str
    select: str
    orderby: str = "Date_Time"
    top_default: int = 1000


# Маппинг КА2 → унифицированная модель
ODATA_ENTITY_CONFIGS: dict[str, ODataEntityConfig] = {
    "counterparties": ODataEntityConfig(
        entity_set="Catalog_Контрагенты",
        select="Ref_Key,Description,FullDescription,INN,KPP,OGRN,"
               "JuridicalAddress,ActualAddress,Phone,Email,"
               "InternetAddress_Presentation,IsBuyer,IsSupplier,Date_Time",
    ),
    "contracts": ODataEntityConfig(
        entity_set="Catalog_ДоговорыКонтрагентов",
        select="Ref_Key,Description,StartDate,FinishDate,Amount,"
               "Currency,ОрганизацияВзаиморасчетов_Key,Date_Time",
    ),
    "orders": ODataEntityConfig(
        entity_set="Document_ЗаказКлиента",
        select="Ref_Key,Description,Date,Amount,Currency,"
               "ОрганизацияВзаиморасчетов_Key,Date_Time",
    ),
    "invoices": ODataEntityConfig(
        entity_set="Document_СчетНаОплатуПокупателю",
        select="Ref_Key,Description,Date,Amount,Currency,"
               "ОрганизацияВзаиморасчетов_Key,Date_Time",
    ),
    "payments": ODataEntityConfig(
        entity_set="Document_ПоступлениеБезналичныхДенежныхСредств",
        select="Ref_Key,Description,Date,Amount,Currency,"
               "ОрганизацияВзаиморасчетов_Key,Date_Time",
    ),
    "products": ODataEntityConfig(
        entity_set="Catalog_Номенклатура",
        select="Ref_Key,Description,Артикул,Штрихкод,Date_Time",
    ),
    "employees": ODataEntityConfig(
        entity_set="Catalog_Сотрудники",
        select="Ref_Key,Description,Date_Time",
    ),
}


@dataclass
class ODataConnectionParams:
    """Параметры подключения к OData сервису 1С."""
    base_url: str
    username: str
    password: str


@dataclass
class ODataFetchResult:
    """Результат выборки из OData."""
    records: list[dict[str, Any]]
    total_count: int | None = None
    error: str | None = None


class ODataClient:
    """HTTP-клиент для OData сервиса 1С."""

    def __init__(self, conn_params: ODataConnectionParams):
        self.conn_params = conn_params
        self.base_url = conn_params.base_url.rstrip("/")

    async def _make_request(
        self,
        entity_set: str,
        select: str | None = None,
        filter_expr: str | None = None,
        orderby: str | None = None,
        top: int = 1000,
        skip: int = 0,
    ) -> ODataFetchResult:
        """Выполнить GET-запрос к OData endpoint."""
        url = f"{self.base_url}/{entity_set}"
        params: dict[str, Any] = {
            "$format": "json",
            "$top": top,
            "$skip": skip,
        }
        if select:
            params["$select"] = select
        if filter_expr:
            params["$filter"] = filter_expr
        if orderby:
            params["$orderby"] = orderby

        auth = httpx.BasicAuth(
            username=self.conn_params.username,
            password=self.conn_params.password,
        )

        try:
            async with httpx.AsyncClient(timeout=60.0, auth=auth) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            records = data.get("value", [])
            total_count = data.get("odata.count") or len(records)

            return ODataFetchResult(
                records=records,
                total_count=total_count,
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "OData HTTP error",
                status_code=e.response.status_code,
                url=str(e.request.url),
                entity_set=entity_set,
            )
            return ODataFetchResult(
                records=[],
                error=f"HTTP {e.response.status_code}: {e.response.text[:500]}",
            )
        except httpx.RequestError as e:
            logger.error(
                "OData request error",
                error=str(e),
                entity_set=entity_set,
            )
            return ODataFetchResult(
                records=[],
                error=f"Connection error: {e}",
            )

    async def fetch_all(
        self,
        entity_name: str,
        filter_expr: str | None = None,
    ) -> ODataFetchResult:
        """Выбрать все записи сущности с постраничной подкачкой."""
        config = ODATA_ENTITY_CONFIGS.get(entity_name)
        if not config:
            return ODataFetchResult(records=[], error=f"Unknown entity: {entity_name}")

        all_records: list[dict[str, Any]] = []
        skip = 0
        page_size = config.top_default
        last_error: str | None = None

        while True:
            result = await self._make_request(
                entity_set=config.entity_set,
                select=config.select,
                filter_expr=filter_expr,
                orderby=config.orderby,
                top=page_size,
                skip=skip,
            )

            if result.error:
                last_error = result.error
                break

            all_records.extend(result.records)

            if len(result.records) < page_size:
                break

            skip += page_size

        return ODataFetchResult(
            records=all_records,
            total_count=len(all_records),
            error=last_error,
        )

    async def fetch_incremental(
        self,
        entity_name: str,
        last_data_version: int = 0,
    ) -> ODataFetchResult:
        """Инкрементальная выборка записей, изменённых после last_data_version.

        Поле Date_Time в 1С содержит Unix timestamp изменений.
        """
        if last_data_version > 0:
            from_dt = datetime.fromtimestamp(last_data_version / 1000, tz=timezone.utc)
            filter_expr = f"Date_Time gt datetime'{from_dt.strftime('%Y-%m-%dT%H:%M:%S')}'"
        else:
            filter_expr = None

        return await self.fetch_all(entity_name, filter_expr=filter_expr)

    async def check_connection(self) -> dict[str, Any]:
        """Проверить соединение с OData сервисом."""
        try:
            # Попробуем получить список каталогов (servicemeta)
            url = f"{self.base_url}/$metadata"
            auth = httpx.BasicAuth(
                username=self.conn_params.username,
                password=self.conn_params.password,
            )
            async with httpx.AsyncClient(timeout=30.0, auth=auth) as client:
                response = await client.get(url)
                response.raise_for_status()

            return {"success": True, "message": "Connection established"}
        except Exception as e:
            return {"success": False, "error": str(e)}
