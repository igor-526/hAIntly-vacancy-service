from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.dictionaries import SyncState


async def apply_snapshot(session: AsyncSession, model, records: list[dict]) -> dict[str, int]:
    if not records or any(not str(row.get("hh_id", "")) or not str(row.get("name", "")) for row in records):
        raise ValueError("Неполный или пустой снимок")
    composite_field = {
        "professional_roles": "category_hh_id",
        "dictionary_items": "dictionary_code",
    }.get(model.__tablename__)

    def item_key(row):
        return (getattr(row, composite_field), row.hh_id) if composite_field else row.hh_id

    existing_rows = (await session.scalars(select(model))).all()
    existing = {item_key(row): row for row in existing_rows}
    seen: set[object] = set()
    inserted = updated = 0
    for data in records:
        domain_key = (data[composite_field], str(data["hh_id"])) if composite_field is not None else str(data["hh_id"])
        seen.add(domain_key)
        item = existing.get(domain_key)
        if item is None:
            session.add(model(**data, active=True))
            inserted += 1
        else:
            changed = not item.active
            for field, value in data.items():
                if getattr(item, field) != value:
                    setattr(item, field, value)
                    changed = True
            item.active = True
            updated += int(changed)
    deactivated = 0
    for item in existing_rows:
        if item.active and item_key(item) not in seen:
            item.active = False
            deactivated += 1
    return {"inserted": inserted, "updated": updated, "deactivated": deactivated}


async def due_dictionaries(session: AsyncSession, *, max_age_hours: int, now: datetime | None = None) -> list[str]:
    from datetime import timedelta

    now = now or datetime.now(UTC)
    cutoff = now - timedelta(hours=max_age_hours)
    names = ("dictionaries", "areas", "countries", "professional_roles", "industries", "metro", "languages")
    states = {s.name: s for s in (await session.scalars(select(SyncState))).all()}
    return [
        name
        for name in names
        if name not in states or (last_success := states[name].last_success_at) is None or last_success <= cutoff
    ]
