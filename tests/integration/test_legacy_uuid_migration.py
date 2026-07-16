import asyncio
import os
import subprocess
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg  # type: ignore[import-untyped]
import pytest

from settings import settings

SERVICE_ROOT = Path(__file__).resolve().parents[2]
BASE_REVISION = "20260714_0001"
HEAD_REVISION = "20260714_0002"
pytestmark = pytest.mark.infrastructure


async def _admin_execute(statement: str) -> None:
    connection = await asyncpg.connect(
        user=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database="postgres",
    )
    try:
        await connection.execute(statement)
    finally:
        await connection.close()


def _alembic(database: str, revision: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "alembic", "-c", "src/alembic.ini", "upgrade", revision],
        cwd=SERVICE_ROOT,
        env={**os.environ, "POSTGRES_DB": database},
        check=check,
        capture_output=True,
        text=True,
    )


def test_upgrade_legacy_rows_preserves_data_and_relations() -> None:
    database = f"vacancy_migration_{uuid4().hex}"
    language_id = uuid4()
    parent_id = uuid4()
    child_id = uuid4()

    async def seed_base_revision() -> None:
        connection = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=database,
        )
        try:
            await connection.execute(
                "INSERT INTO languages(id,hh_id,name,active) VALUES($1,'legacy-lang','Legacy',true)", language_id
            )
            await connection.execute(
                "INSERT INTO areas(id,hh_id,name,parent_hh_id,active) VALUES"
                "($1,'legacy-parent','Parent',NULL,true),($2,'legacy-child','Child','legacy-parent',true)",
                parent_id,
                child_id,
            )
        finally:
            await connection.close()

    async def verify() -> None:
        connection = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=database,
        )
        try:
            language = await connection.fetchrow("SELECT id,hh_id,name,active FROM languages WHERE id=$1", language_id)
            child = await connection.fetchrow("SELECT id,parent_hh_id FROM areas WHERE id=$1", child_id)
            revision = await connection.fetchval("SELECT version_num FROM alembic_version")
            filter_table = await connection.fetchval("SELECT to_regclass('public.filter_presets')")
            assert language and isinstance(language["id"], UUID)
            assert tuple(language.values())[1:] == ("legacy-lang", "Legacy", True)
            assert child and child["parent_hh_id"] == "legacy-parent"
            assert revision == HEAD_REVISION
            assert filter_table == "filter_presets"
        finally:
            await connection.close()

    asyncio.run(_admin_execute(f'CREATE DATABASE "{database}"'))
    try:
        _alembic(database, BASE_REVISION)
        asyncio.run(seed_base_revision())
        _alembic(database, "head")
        asyncio.run(verify())
    finally:
        asyncio.run(_admin_execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))


def test_fixed_uuid_collision_rolls_back_migration() -> None:
    database = f"vacancy_collision_{uuid4().hex}"

    async def create_collision() -> None:
        connection = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=database,
        )
        try:
            await connection.execute("CREATE TABLE filter_presets(marker text NOT NULL)")
            await connection.execute("INSERT INTO filter_presets(marker) VALUES('preserve')")
        finally:
            await connection.close()

    async def verify_rollback() -> None:
        connection = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=database,
        )
        try:
            revision = await connection.fetchval("SELECT version_num FROM alembic_version")
            marker = await connection.fetchval("SELECT marker FROM filter_presets")
            values_table = await connection.fetchval("SELECT to_regclass('public.filter_preset_values')")
            assert revision == BASE_REVISION
            assert marker == "preserve"
            assert values_table is None
        finally:
            await connection.close()

    asyncio.run(_admin_execute(f'CREATE DATABASE "{database}"'))
    try:
        _alembic(database, BASE_REVISION)
        asyncio.run(create_collision())
        result = _alembic(database, "head", check=False)
        assert result.returncode != 0
        asyncio.run(verify_rollback())
    finally:
        asyncio.run(_admin_execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))
