from uuid import uuid4

import pytest
from sqlalchemy import Uuid, select, text

from models.dictionaries import Language
from repositories.dictionaries import apply_snapshot
from utils.database import SessionFactory

pytestmark = pytest.mark.infrastructure


@pytest.mark.asyncio
async def test_upsert_update_deactivate_reactivate_and_rollback():
    prefix = f"test-{uuid4()}"
    async with SessionFactory() as session:
        async with session.begin():
            await apply_snapshot(
                session, Language, [{"hh_id": prefix + "-1", "name": "One"}, {"hh_id": prefix + "-2", "name": "Two"}]
            )
            await session.flush()
            await apply_snapshot(session, Language, [{"hh_id": prefix + "-1", "name": "Changed"}])
            await session.flush()
            one = await session.scalar(select(Language).where(Language.hh_id == prefix + "-1"))
            two = await session.scalar(select(Language).where(Language.hh_id == prefix + "-2"))
            assert one and one.name == "Changed" and one.active
            original_id = one.id
            await apply_snapshot(session, Language, [{"hh_id": prefix + "-1", "name": "Changed"}])
            await session.flush()
            assert one.id == original_id
            assert two and not two.active
            await apply_snapshot(session, Language, [{"hh_id": prefix + "-2", "name": "Back"}])
            assert two.active and two.name == "Back"
            with pytest.raises(ValueError):
                await apply_snapshot(session, Language, [])
            assert two.active
            await session.rollback()


@pytest.mark.asyncio
async def test_migration_created_foreign_keys_unique_constraints_and_ci_indexes():
    async with SessionFactory() as session:
        constraints = (
            await session.execute(
                text(
                    "select 1 from pg_constraint where conname in "
                    "('professional_roles_category_hh_id_fkey','uq_professional_roles_category_hh_id_hh_id')"
                )
            )
        ).all()
        assert len(constraints) == 2
        assert isinstance(Language.__table__.c.id.type, Uuid)
        sync_state = (
            await session.execute(
                text(
                    "select data_type from information_schema.columns "
                    "where table_name='dictionary_sync_states' and column_name='id'"
                )
            )
        ).scalar_one()
        unique_name = await session.scalar(
            text(
                "select count(*) from pg_constraint where conrelid='dictionary_sync_states'::regclass and contype='u'"
            )
        )
        assert sync_state == "uuid"
        assert unique_name == 1
