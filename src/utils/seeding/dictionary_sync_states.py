from types import MappingProxyType
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from models.dictionaries import SyncState
from utils.database import SessionFactory

DICTIONARY_SYNC_STATE_SEEDS = MappingProxyType(
    {
        "dictionaries": UUID("19c15c4f-8a68-4d82-9b2f-d778a4aa8f91"),
        "areas": UUID("294acc73-77ff-46ab-86db-154f343c0351"),
        "countries": UUID("38ca1487-6299-43c4-bcbf-bc59881cc76a"),
        "professional_roles": UUID("4ea231dd-8c39-498b-a2c4-b8bd00294bea"),
        "industries": UUID("5da9db33-eb9c-4a98-b56c-d983e4f5abc2"),
        "metro": UUID("6bff0cb2-3bfc-4784-8302-bd615e4ea48a"),
        "languages": UUID("730f0616-2510-4224-84fa-5c35b37140e9"),
    }
)


class DictionarySyncStateSeedConflict(RuntimeError):
    """The persisted UUID/name mapping differs from the canonical seed definition."""


async def seed_dictionary_sync_states() -> None:
    """Create and validate the seven local sync-state rows in one transaction."""
    async with SessionFactory.begin() as session:
        rows = [
            {"id": state_id, "name": name, "status": "never"} for name, state_id in DICTIONARY_SYNC_STATE_SEEDS.items()
        ]
        statement = insert(SyncState).values(rows)
        # Both the logical name and the fixed UUID are unique. Ignoring either
        # conflict makes concurrent replicas safe; the exact post-check below
        # distinguishes an idempotent race from an incompatible collision.
        await session.execute(statement.on_conflict_do_nothing())

        states = (
            await session.execute(
                select(SyncState.id, SyncState.name).where(SyncState.name.in_(DICTIONARY_SYNC_STATE_SEEDS))
            )
        ).all()
        actual = {name: state_id for state_id, name in states}
        if actual != dict(DICTIONARY_SYNC_STATE_SEEDS):
            raise DictionarySyncStateSeedConflict("dictionary_sync_state_seed_conflict")
