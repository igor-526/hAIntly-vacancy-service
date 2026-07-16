from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas.filters import FilterPresetCreate, FilterPresetUpdate, FilterPresetValueIn
from repositories.filters import create_preset, delete_preset, get_preset, list_presets, update_preset

pytestmark = pytest.mark.infrastructure


@pytest.mark.asyncio
async def test_create_preset(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    data = FilterPresetCreate(
        name="Тестовый пресет",
        text="python developer",
        salary=100000,
        values=[
            FilterPresetValueIn(parameter_name="area", value="1"),
            FilterPresetValueIn(parameter_name="professional_role", value="10"),
            FilterPresetValueIn(parameter_name="experience", value="between1And3"),
        ],
    )
    preset = await create_preset(session, hh_user_id, data)
    assert preset.name == "Тестовый пресет"
    assert preset.hh_user_id == hh_user_id
    assert preset.text == "python developer"
    assert preset.salary == 100000
    assert len(preset.values) == 3


@pytest.mark.asyncio
async def test_create_preset_duplicate_name(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    data = FilterPresetCreate(name="Дубликат")
    await create_preset(session, hh_user_id, data)

    with pytest.raises(HTTPException) as exc_info:
        await create_preset(session, hh_user_id, data)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_create_preset_invalid_area(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    data = FilterPresetCreate(
        name="Невалидный",
        values=[FilterPresetValueIn(parameter_name="area", value="999999")],
    )
    with pytest.raises(HTTPException) as exc_info:
        await create_preset(session, hh_user_id, data)
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_create_preset_invalid_dictionary_item(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    data = FilterPresetCreate(
        name="Невалидный label",
        values=[FilterPresetValueIn(parameter_name="label", value="nonexistent")],
    )
    with pytest.raises(HTTPException) as exc_info:
        await create_preset(session, hh_user_id, data)
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_create_preset_employer_id_any_value(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    data = FilterPresetCreate(
        name="С произвольным employer_id",
        values=[FilterPresetValueIn(parameter_name="employer_id", value="any_company_123")],
    )
    preset = await create_preset(session, hh_user_id, data)
    assert len(preset.values) == 1
    assert preset.values[0].value == "any_company_123"


@pytest.mark.asyncio
async def test_list_presets(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    await create_preset(session, hh_user_id, FilterPresetCreate(name="Пресет A"))
    await create_preset(session, hh_user_id, FilterPresetCreate(name="Пресет B"))
    await create_preset(session, hh_user_id, FilterPresetCreate(name="Пресет C"))

    result = await list_presets(session, hh_user_id, None, 50, 0)
    assert len(result) >= 3


@pytest.mark.asyncio
async def test_list_presets_search(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    await create_preset(session, hh_user_id, FilterPresetCreate(name="ПоискПитон"))
    await create_preset(session, hh_user_id, FilterPresetCreate(name="ДругойПресет"))

    result = await list_presets(session, hh_user_id, "питон", 50, 0)
    assert all("поискпитон" in p.name.lower() for p in result)


@pytest.mark.asyncio
async def test_list_presets_pagination(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    for i in range(5):
        await create_preset(session, hh_user_id, FilterPresetCreate(name=f"Page{i}"))

    result = await list_presets(session, hh_user_id, "Page", 2, 0)
    assert len(result) == 2

    result2 = await list_presets(session, hh_user_id, "Page", 2, 2)
    assert len(result2) == 2


@pytest.mark.asyncio
async def test_get_preset(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    data = FilterPresetCreate(
        name="Детальный",
        text="query",
        values=[FilterPresetValueIn(parameter_name="area", value="1")],
    )
    created = await create_preset(session, hh_user_id, data)

    fetched = await get_preset(session, created.id, hh_user_id)
    assert fetched is not None
    assert fetched.name == "Детальный"
    assert len(fetched.values) == 1


@pytest.mark.asyncio
async def test_get_preset_not_found(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    result = await get_preset(session, uuid4(), hh_user_id)
    assert result is None


@pytest.mark.asyncio
async def test_update_preset_name(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    created = await create_preset(session, hh_user_id, FilterPresetCreate(name="Старое имя"))
    updated = await update_preset(session, created.id, hh_user_id, FilterPresetUpdate(name="Новое имя"))
    assert updated.name == "Новое имя"


@pytest.mark.asyncio
async def test_update_preset_values(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    created = await create_preset(session, hh_user_id, FilterPresetCreate(name="Обновление значений"))
    updated = await update_preset(
        session,
        created.id,
        hh_user_id,
        FilterPresetUpdate(values=[FilterPresetValueIn(parameter_name="area", value="1")]),
    )
    assert len(updated.values) == 1
    assert updated.values[0].parameter_name == "area"


@pytest.mark.asyncio
async def test_update_preset_not_found(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    with pytest.raises(HTTPException) as exc_info:
        await update_preset(session, uuid4(), hh_user_id, FilterPresetUpdate(name="X"))
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_preset(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    created = await create_preset(session, hh_user_id, FilterPresetCreate(name="Удалить"))
    await delete_preset(session, created.id, hh_user_id)
    assert await get_preset(session, created.id, hh_user_id) is None


@pytest.mark.asyncio
async def test_delete_preset_not_found(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    with pytest.raises(HTTPException) as exc_info:
        await delete_preset(session, uuid4(), hh_user_id)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_user_isolation(session: AsyncSession, seed_dictionaries: dict):
    user_a = "user_a_123"
    user_b = "user_b_456"

    await create_preset(session, user_a, FilterPresetCreate(name="Пресет A"))

    result = await list_presets(session, user_b, None, 50, 0)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_update_preset_duplicate_name(session: AsyncSession, seed_dictionaries: dict, hh_user_id: str):
    await create_preset(session, hh_user_id, FilterPresetCreate(name="Имя1"))
    preset2 = await create_preset(session, hh_user_id, FilterPresetCreate(name="Имя2"))

    with pytest.raises(HTTPException) as exc_info:
        await update_preset(session, preset2.id, hh_user_id, FilterPresetUpdate(name="Имя1"))
    assert exc_info.value.status_code == 409
