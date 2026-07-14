from uuid import UUID

from sqlalchemy.dialects import postgresql

from models.dictionaries import SyncState
from utils.seeding.dictionary_sync_states import DICTIONARY_SYNC_STATE_SEEDS

EXPECTED = {
    "dictionaries": UUID("19c15c4f-8a68-4d82-9b2f-d778a4aa8f91"),
    "areas": UUID("294acc73-77ff-46ab-86db-154f343c0351"),
    "countries": UUID("38ca1487-6299-43c4-bcbf-bc59881cc76a"),
    "professional_roles": UUID("4ea231dd-8c39-498b-a2c4-b8bd00294bea"),
    "industries": UUID("5da9db33-eb9c-4a98-b56c-d983e4f5abc2"),
    "metro": UUID("6bff0cb2-3bfc-4784-8302-bd615e4ea48a"),
    "languages": UUID("730f0616-2510-4224-84fa-5c35b37140e9"),
}


def test_exact_literal_sync_state_seed_mapping() -> None:
    assert dict(DICTIONARY_SYNC_STATE_SEEDS) == EXPECTED
    assert len(set(DICTIONARY_SYNC_STATE_SEEDS.values())) == 7


def test_sync_state_insert_is_conflict_safe() -> None:
    statement = postgresql.insert(SyncState).values(id=EXPECTED["areas"], name="areas")
    compiled = str(
        statement.on_conflict_do_nothing().compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "ON CONFLICT DO NOTHING" in compiled
