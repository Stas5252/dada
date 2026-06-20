import logging
from dataclasses import dataclass, field
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.contracts.billing import (
    BillingIdempotencyKey,
    BillingLedgerEntry,
    BillingOperation,
    BillingStatus,
    mark_duplicate_if_replayed,
)
from app.contracts.types import JsonValue
from app.db_models import BillingLedgerEntryModel

logger = logging.getLogger(__name__)


@dataclass
class InMemoryBillingLedger:
    entries: dict[str, BillingLedgerEntry] = field(default_factory=dict)

    async def find(self, *, key: BillingIdempotencyKey) -> BillingLedgerEntry | None:
        return self.entries.get(key.storage_key)

    async def save(self, *, entry: BillingLedgerEntry) -> BillingLedgerEntry:
        self.entries[entry.idempotency_key.storage_key] = entry
        return entry


class SqlAlchemyBillingLedger:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    async def find(self, *, key: BillingIdempotencyKey) -> BillingLedgerEntry | None:
        with self.session_factory() as session:
            model = session.scalar(
                select(BillingLedgerEntryModel).where(
                    BillingLedgerEntryModel.idempotency_key == key.storage_key
                )
            )
            if model:
                parts = model.idempotency_key.split(":")
                return BillingLedgerEntry(
                    tenant_id=model.tenant_id,
                    idempotency_key=BillingIdempotencyKey(
                        tenant_id=parts[0],
                        operation=BillingOperation(parts[1]),
                        subject_id=parts[2],
                        request_hash=parts[3],
                    ),
                    amount_minor=model.amount_minor,
                    currency=model.currency,
                    status=BillingStatus(model.status),
                )
            return None

    async def save(self, *, entry: BillingLedgerEntry) -> BillingLedgerEntry:
        with self.session_factory() as session:
            model = BillingLedgerEntryModel(
                id=str(uuid4()),
                tenant_id=entry.tenant_id,
                subject_id=entry.idempotency_key.subject_id,
                amount_minor=entry.amount_minor,
                currency=entry.currency,
                status=entry.status.value,
                idempotency_key=entry.idempotency_key.storage_key,
                payload={},
            )
            session.add(model)
            session.commit()
            return entry


@dataclass
class BillingService:
    ledger: InMemoryBillingLedger | SqlAlchemyBillingLedger = field(
        default_factory=InMemoryBillingLedger
    )

    async def apply_usage_charge(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        amount_minor: int,
        currency: str,
        payload: dict[str, JsonValue],
    ) -> BillingLedgerEntry:
        key = BillingIdempotencyKey.from_payload(
            tenant_id=tenant_id,
            operation=BillingOperation.APPLY_USAGE,
            subject_id=subject_id,
            payload=payload,
        )
        requested_entry = BillingLedgerEntry(
            tenant_id=tenant_id,
            idempotency_key=key,
            amount_minor=amount_minor,
            currency=currency,
            status=BillingStatus.APPLIED,
        )
        existing_entry = await self.ledger.find(key=key)
        entry = mark_duplicate_if_replayed(existing=existing_entry, requested=requested_entry)
        if entry.status != BillingStatus.DUPLICATE:
            await self.ledger.save(entry=entry)
        return entry
