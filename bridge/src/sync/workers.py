from __future__ import annotations

from typing import Any

from .base import BaseSyncWorker


class CounterpartySyncWorker(BaseSyncWorker):
    @property
    def entity_name(self) -> str:
        return "counterparties"

    @property
    def table_name(self) -> str:
        return "umnick.counterparties"

    def map_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "external_id": record.get("Ref_Key", ""),
            "data_version": self._parse_data_version(record.get("Date_Time")),
            "name": record.get("Description", "") or "",
            "full_name": record.get("FullDescription"),
            "inn": record.get("INN"),
            "kpp": record.get("KPP"),
            "ogrn": record.get("OGRN"),
            "legal_address": record.get("JuridicalAddress"),
            "actual_address": record.get("ActualAddress"),
            "phone": record.get("Phone"),
            "email": record.get("Email"),
            "website": record.get("InternetAddress_Presentation"),
            "is_buyer": bool(record.get("IsBuyer", False)),
            "is_supplier": bool(record.get("IsSupplier", False)),
            "is_client": bool(record.get("IsBuyer", False)),
            "raw_data": record,
        }


class ContractSyncWorker(BaseSyncWorker):
    @property
    def entity_name(self) -> str:
        return "contracts"

    @property
    def table_name(self) -> str:
        return "umnick.contracts"

    def map_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "external_id": record.get("Ref_Key", ""),
            "data_version": self._parse_data_version(record.get("Date_Time")),
            "number": record.get("Description"),
            "date_start": self._parse_date(record.get("StartDate")),
            "date_end": self._parse_date(record.get("FinishDate")),
            "amount": float(record.get("Amount", 0) or 0),
            "currency": record.get("Currency", "RUB"),
            "counterparty_external_id": self._extract_key(record.get("ОрганизацияВзаиморасчетов_Key")),
            "raw_data": record,
        }


class OrderSyncWorker(BaseSyncWorker):
    @property
    def entity_name(self) -> str:
        return "orders"

    @property
    def table_name(self) -> str:
        return "umnick.orders"

    def map_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "external_id": record.get("Ref_Key", ""),
            "data_version": self._parse_data_version(record.get("Date_Time")),
            "number": record.get("Description", "") or "",
            "date": self._parse_date(record.get("Date")),
            "amount": float(record.get("Amount", 0) or 0),
            "currency": record.get("Currency", "RUB"),
            "counterparty_external_id": self._extract_key(record.get("ОрганизацияВзаиморасчетов_Key")),
            "raw_data": record,
        }


class InvoiceSyncWorker(BaseSyncWorker):
    @property
    def entity_name(self) -> str:
        return "invoices"

    @property
    def table_name(self) -> str:
        return "umnick.invoices"

    def map_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "external_id": record.get("Ref_Key", ""),
            "data_version": self._parse_data_version(record.get("Date_Time")),
            "number": record.get("Description", "") or "",
            "date": self._parse_date(record.get("Date")),
            "due_date": self._parse_date(record.get("DueDate")),
            "amount": float(record.get("Amount", 0) or 0),
            "paid_amount": float(record.get("PaidAmount", 0) or 0),
            "status": "paid" if float(record.get("PaidAmount", 0) or 0) >= float(record.get("Amount", 0) or 0)
                       else ("partial" if float(record.get("PaidAmount", 0) or 0) > 0 else "unpaid"),
            "payment_date": self._parse_date(record.get("PaymentDate")),
            "invoice_type": self._extract_invoice_type(record),
            "counterparty_external_id": self._extract_key(record.get("ОрганизацияВзаиморасчетов_Key")),
            "order_external_id": self._extract_key(record.get("Order_Key")),
            "raw_data": record,
        }

    def _extract_invoice_type(self, record: dict[str, Any]) -> str:
        """Определить тип счета (outgoing/incoming) из данных 1С."""
        doc_type = record.get("ДокументОснование_Type", "")
        if "Поступление" in doc_type or "Входящий" in doc_type:
            return "incoming"
        return "outgoing"


class PaymentSyncWorker(BaseSyncWorker):
    @property
    def entity_name(self) -> str:
        return "payments"

    @property
    def table_name(self) -> str:
        return "umnick.payments"

    def map_record(self, record: dict[str, Any]) -> dict[str, Any]:
        direction = "incoming" if float(record.get("СуммаПлатежа", 0) or 0) > 0 else "outgoing"
        return {
            "external_id": record.get("Ref_Key", ""),
            "data_version": self._parse_data_version(record.get("Date_Time")),
            "number": record.get("Description", "") or "",
            "date": self._parse_date(record.get("Date")),
            "amount": abs(float(record.get("СуммаПлатежа", 0) or 0)),
            "paid_amount": abs(float(record.get("СуммаПлатежа", 0) or 0)),
            "currency": record.get("Currency", "RUB"),
            "payment_type": self._parse_payment_type(record),
            "direction": direction,
            "purpose": record.get("Purpose"),
            "payment_date": self._parse_date(record.get("Date")),
            "counterparty_external_id": self._extract_key(record.get("ОрганизацияВзаиморасчетов_Key")),
            "invoice_external_id": self._extract_key(record.get("Invoice_Key")),
            "order_external_id": self._extract_key(record.get("Order_Key")),
            "raw_data": record,
        }

    def _parse_payment_type(self, record: dict[str, Any]) -> str:
        payment_type = record.get("ВидБезналичныхРасчетов", "")
        if not payment_type:
            return "cashless"
        payment_type = payment_type.lower()
        if "налич" in payment_type:
            return "cash"
        if "карт" in payment_type:
            return "card"
        if "взаимозачет" in payment_type or "зачет" in payment_type:
            return "offset"
        return "cashless"


class ProductSyncWorker(BaseSyncWorker):
    @property
    def entity_name(self) -> str:
        return "products"

    @property
    def table_name(self) -> str:
        return "umnick.products"

    def map_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "external_id": record.get("Ref_Key", ""),
            "data_version": self._parse_data_version(record.get("Date_Time")),
            "name": record.get("Description", "") or "",
            "article": record.get("Article"),
            "barcode": record.get("BarCode"),
            "description": record.get("FullDescription"),
            "category": record.get("Parent_Key"),
            "unit": record.get("Unit", "шт"),
            "price": float(record.get("Price", 0) or 0),
            "cost_price": float(record.get("CostPrice", 0)) if record.get("CostPrice") else None,
            "currency": record.get("Currency", "RUB"),
            "stock_balance": float(record.get("StockBalance", 0) or 0),
            "stock_reserved": float(record.get("StockReserved", 0) or 0),
            "min_stock": float(record.get("MinStock", 0) or 0),
            "raw_data": record,
        }


class EmployeeSyncWorker(BaseSyncWorker):
    @property
    def entity_name(self) -> str:
        return "employees"

    @property
    def table_name(self) -> str:
        return "umnick.employees"

    def map_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "external_id": record.get("Ref_Key", ""),
            "data_version": self._parse_data_version(record.get("Date_Time")),
            "full_name": record.get("Description", "") or "",
            "position": record.get("Должность"),
            "email": record.get("Email"),
            "phone": record.get("Phone"),
            "department": record.get("Подразделение"),
            "is_active": not bool(record.get("ДатаУвольнения")),
            "raw_data": record,
        }
