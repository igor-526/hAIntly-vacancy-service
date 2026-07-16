import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Settings is instantiated during application module imports. Keep these test-only
# values before every src import so pytest collection does not depend on a local
# .env file. setdefault preserves real values loaded by make test-infra.
os.environ.setdefault("HH_APP_TOKEN", "test-application-token")
os.environ.setdefault("HH_API_URL", "https://hh-api.example.invalid")
os.environ.setdefault("HH_USER_AGENT", "HAIntly vacancy-service tests")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/12")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/13")
os.environ.setdefault("DICTIONARY_LOCK_URL", "redis://localhost:6379/14")
os.environ.setdefault("VACANCY_DICTIONARY_MAX_AGE_HOURS", "24")
os.environ.setdefault("PROFILE_SERVICE_URL", "https://profile-service.example.invalid")

from models.dictionaries import (  # noqa: E402
    Area,
    Base,
    DictionaryItem,
    Industry,
    MetroCity,
    MetroLine,
    MetroStation,
    ProfessionalRole,
    ProfessionalRoleCategory,
)
from settings import settings  # noqa: E402

engine = create_async_engine(settings.database_url, poolclass=NullPool)
TestSessionFactory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
async def setup_database(request: pytest.FixtureRequest):
    if not any(item.get_closest_marker("infrastructure") for item in request.session.items):
        yield
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with TestSessionFactory() as s:
        yield s
        await s.rollback()


@pytest.fixture
async def seed_dictionaries(session: AsyncSession):
    area = Area(hh_id="1", name="Москва", active=True)
    role = ProfessionalRole(hh_id="10", name="Программист", category_hh_id="1", active=True)
    role_category = ProfessionalRoleCategory(hh_id="1", name="ИТ", active=True)
    industry = Industry(hh_id="7", name="Информационные технологии", active=True)
    metro = MetroStation(hh_id="100", name="Тверская", line_hh_id="1", active=True)
    metro_city = MetroCity(hh_id="1", name="Москва", active=True)
    metro_line = MetroLine(hh_id="1", name="Замоскворецкая", city_hh_id="1", active=True)
    label_item = DictionaryItem(dictionary_code="label", hh_id="direct", name="Без посредников", active=True)
    exp_item = DictionaryItem(dictionary_code="experience", hh_id="between1And3", name="От 1 до 3 лет", active=True)

    session.add_all([role_category, metro_city])
    await session.flush()
    session.add(metro_line)
    await session.flush()
    session.add_all([area, role, industry, metro, label_item, exp_item])
    await session.flush()
    return {
        "area": area,
        "role": role,
        "industry": industry,
        "metro": metro,
        "label": label_item,
        "experience": exp_item,
    }


@pytest.fixture
def hh_user_id():
    return "test_hh_user_123"
