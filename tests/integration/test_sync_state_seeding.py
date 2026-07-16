import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, func, select, update

from models.dictionaries import SyncState
from utils.database import SessionFactory
from utils.seeding import DICTIONARY_SYNC_STATE_SEEDS, seed_dictionary_sync_states
from utils.seeding.dictionary_sync_states import DictionarySyncStateSeedConflict

pytestmark = pytest.mark.infrastructure


@pytest.mark.asyncio
async def test_seed_is_idempotent_and_preserves_metadata() -> None:
    await seed_dictionary_sync_states()
    marker = datetime(2026, 7, 14, tzinfo=UTC)
    async with SessionFactory.begin() as session:
        await session.execute(
            update(SyncState)
            .where(SyncState.name == "areas")
            .values(status="success", last_success_at=marker, last_error="preserve")
        )

    await seed_dictionary_sync_states()
    async with SessionFactory() as session:
        states = (await session.scalars(select(SyncState).order_by(SyncState.name))).all()
        canonical = [state for state in states if state.name in DICTIONARY_SYNC_STATE_SEEDS]
        assert len(canonical) == 7
        assert {state.name: state.id for state in canonical} == dict(DICTIONARY_SYNC_STATE_SEEDS)
        areas = next(state for state in canonical if state.name == "areas")
        assert (areas.status, areas.last_success_at, areas.last_error) == ("success", marker, "preserve")


@pytest.mark.asyncio
async def test_concurrent_seed_creates_one_row_per_name() -> None:
    async with SessionFactory.begin() as session:
        await session.execute(delete(SyncState).where(SyncState.name.in_(DICTIONARY_SYNC_STATE_SEEDS)))
    await asyncio.gather(*(seed_dictionary_sync_states() for _ in range(4)))
    async with SessionFactory() as session:
        count = await session.scalar(
            select(func.count()).select_from(SyncState).where(SyncState.name.in_(DICTIONARY_SYNC_STATE_SEEDS))
        )
        assert count == 7


@pytest.mark.asyncio
async def test_name_conflict_rolls_back_all_missing_inserts() -> None:
    await seed_dictionary_sync_states()
    async with SessionFactory.begin() as session:
        await session.execute(delete(SyncState).where(SyncState.name == "languages"))
        await session.execute(
            update(SyncState).where(SyncState.name == "areas").values(id="a1f5b615-5ee0-4ff1-8acb-9ca39932bd4e")
        )
    with pytest.raises(DictionarySyncStateSeedConflict):
        await seed_dictionary_sync_states()
    async with SessionFactory() as session:
        assert await session.scalar(select(SyncState).where(SyncState.name == "languages")) is None
    async with SessionFactory.begin() as session:
        await session.execute(delete(SyncState).where(SyncState.name == "areas"))
    await seed_dictionary_sync_states()


@pytest.mark.asyncio
async def test_uuid_collision_is_atomic() -> None:
    await seed_dictionary_sync_states()
    async with SessionFactory.begin() as session:
        await session.execute(delete(SyncState).where(SyncState.name == "languages"))
        session.add(SyncState(id=DICTIONARY_SYNC_STATE_SEEDS["languages"], name="foreign"))
    with pytest.raises(DictionarySyncStateSeedConflict):
        await seed_dictionary_sync_states()
    async with SessionFactory() as session:
        assert await session.scalar(select(SyncState).where(SyncState.name == "languages")) is None
    async with SessionFactory.begin() as session:
        await session.execute(delete(SyncState).where(SyncState.name == "foreign"))
    await seed_dictionary_sync_states()
