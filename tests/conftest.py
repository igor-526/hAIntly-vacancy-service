import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models.dictionaries import Area, Base, DictionaryItem, Industry, MetroStation, ProfessionalRole
from models.filter_presets import FilterPreset, FilterPresetValue
from settings import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
TestSessionFactory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
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
    industry = Industry(hh_id="7", name="Информационные технологии", active=True)
    metro = MetroStation(hh_id="100", name="Тверская", line_hh_id="1", active=True)
    label_item = DictionaryItem(dictionary_code="label", hh_id="direct", name="Без посредников", active=True)
    exp_item = DictionaryItem(dictionary_code="experience", hh_id="between1And3", name="От 1 до 3 лет", active=True)

    session.add_all([area, role, industry, metro, label_item, exp_item])
    await session.flush()
    return {"area": area, "role": role, "industry": industry, "metro": metro, "label": label_item, "experience": exp_item}


@pytest.fixture
def hh_user_id():
    return "test_hh_user_123"
