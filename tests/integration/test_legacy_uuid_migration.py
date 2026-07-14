import asyncio
import os
import subprocess
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg  # type: ignore[import-untyped]

from settings import settings
from utils.seeding import DICTIONARY_SYNC_STATE_SEEDS

SERVICE_ROOT = Path(__file__).resolve().parents[2]


def test_upgrade_legacy_rows_preserves_data_and_relations():
    database = f"vacancy_migration_{uuid4().hex}"

    async def provision() -> None:
        admin = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database="postgres",
        )
        try:
            await admin.execute(f'CREATE DATABASE "{database}"')
        finally:
            await admin.close()

    async def seed_legacy() -> None:
        connection = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=database,
        )
        try:
            # The historical migration imports model metadata. Reconstruct the
            # actually deployed integer/name-PK shape before seeding legacy rows.
            await connection.execute("ALTER TABLE languages ALTER COLUMN id DROP DEFAULT")
            await connection.execute("ALTER TABLE languages ALTER COLUMN id TYPE integer USING 1")
            await connection.execute("ALTER TABLE areas ALTER COLUMN id DROP DEFAULT")
            await connection.execute("ALTER TABLE areas ALTER COLUMN id TYPE integer USING 1")
            await connection.execute("DROP TABLE dictionary_sync_states")
            await connection.execute(
                "CREATE TABLE dictionary_sync_states ("
                "name varchar(50) PRIMARY KEY, status varchar(20) NOT NULL DEFAULT 'never', "
                "last_attempt_started_at timestamptz, last_attempt_finished_at timestamptz, "
                "last_success_at timestamptz, last_error text)"
            )
            await connection.execute("INSERT INTO languages (id, hh_id, name) VALUES (41, 'legacy-lang', 'Legacy')")
            await connection.execute(
                "INSERT INTO areas (id, hh_id, name, parent_hh_id) VALUES "
                "(51, 'legacy-parent', 'Parent', NULL), (52, 'legacy-child', 'Child', 'legacy-parent')"
            )
            await connection.execute(
                "INSERT INTO dictionary_sync_states "
                "(name, status, last_success_at) VALUES ('languages', 'success', now())"
            )
        finally:
            await connection.close()

    async def verify_and_drop() -> None:
        connection = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=database,
        )
        try:
            language = await connection.fetchrow("SELECT id, hh_id, name, active FROM languages")
            child = await connection.fetchrow("SELECT id, parent_hh_id FROM areas WHERE hh_id='legacy-child'")
            state = await connection.fetchrow("SELECT id, name, status, last_success_at FROM dictionary_sync_states")
            assert language and isinstance(language["id"], UUID)
            assert tuple(language.values())[1:] == ("legacy-lang", "Legacy", True)
            assert child and isinstance(child["id"], UUID) and child["parent_hh_id"] == "legacy-parent"
            assert state and isinstance(state["id"], UUID)
            assert state["id"] == DICTIONARY_SYNC_STATE_SEEDS["languages"]
            assert state["name"] == "languages" and state["status"] == "success" and state["last_success_at"]
        finally:
            await connection.close()
        admin = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database="postgres",
        )
        try:
            await admin.execute(f'DROP DATABASE "{database}"')
        finally:
            await admin.close()

    env = {**os.environ, "POSTGRES_DB": database}
    asyncio.run(provision())
    try:
        subprocess.run(
            ["uv", "run", "alembic", "-c", "src/alembic.ini", "upgrade", "b38196753410"],
            cwd=SERVICE_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        asyncio.run(seed_legacy())
        subprocess.run(
            ["uv", "run", "alembic", "-c", "src/alembic.ini", "upgrade", "head"],
            cwd=SERVICE_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        asyncio.run(verify_and_drop())
    except Exception:
        # Best-effort cleanup is intentionally omitted here: the random test DB
        # remains inspectable if migration execution itself fails.
        raise


def test_fixed_uuid_collision_rolls_back_migration() -> None:
    database = f"vacancy_collision_{uuid4().hex}"
    language_id = DICTIONARY_SYNC_STATE_SEEDS["languages"]
    original_area_id = uuid4()

    async def provision() -> None:
        admin = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database="postgres",
        )
        try:
            await admin.execute(f'CREATE DATABASE "{database}"')
        finally:
            await admin.close()

    async def seed_collision() -> None:
        connection = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=database,
        )
        try:
            await connection.execute(
                "INSERT INTO dictionary_sync_states(id,name,status,last_error) VALUES($1,'areas','failed','preserve')",
                original_area_id,
            )
            await connection.execute(
                "INSERT INTO dictionary_sync_states(id,name,status) VALUES($1,'foreign','never')", language_id
            )
        finally:
            await connection.close()

    async def recreate_legacy_sync_state_table() -> None:
        connection = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=database,
        )
        try:
            await connection.execute("DROP TABLE dictionary_sync_states")
            await connection.execute(
                "CREATE TABLE dictionary_sync_states ("
                "name varchar(50) PRIMARY KEY, status varchar(20) NOT NULL DEFAULT 'never', "
                "last_attempt_started_at timestamptz, last_attempt_finished_at timestamptz, "
                "last_success_at timestamptz, last_error text)"
            )
        finally:
            await connection.close()

    async def verify_and_drop() -> None:
        connection = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=database,
        )
        try:
            revision = await connection.fetchval("SELECT version_num FROM alembic_version")
            area = await connection.fetchrow(
                "SELECT id,status,last_error FROM dictionary_sync_states WHERE name='areas'"
            )
            assert revision == "20260714_0004"
            assert area and tuple(area.values()) == (original_area_id, "failed", "preserve")
        finally:
            await connection.close()
        admin = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database="postgres",
        )
        try:
            await admin.execute(f'DROP DATABASE "{database}"')
        finally:
            await admin.close()

    env = {**os.environ, "POSTGRES_DB": database}
    asyncio.run(provision())
    subprocess.run(
        ["uv", "run", "alembic", "-c", "src/alembic.ini", "upgrade", "b38196753410"],
        cwd=SERVICE_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    asyncio.run(recreate_legacy_sync_state_table())
    subprocess.run(
        ["uv", "run", "alembic", "-c", "src/alembic.ini", "upgrade", "20260714_0004"],
        cwd=SERVICE_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    asyncio.run(seed_collision())
    result = subprocess.run(
        ["uv", "run", "alembic", "-c", "src/alembic.ini", "upgrade", "head"],
        cwd=SERVICE_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    asyncio.run(verify_and_drop())
