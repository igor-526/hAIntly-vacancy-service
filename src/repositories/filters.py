from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.schemas.filters import FilterPresetCreate, FilterPresetUpdate
from models.dictionaries import (
    Area,
    DictionaryItem,
    Industry,
    MetroStation,
    ProfessionalRole,
)
from models.filter_presets import FilterPreset, FilterPresetValue

VALID_PARAMETER_NAMES = {
    "area",
    "professional_role",
    "industry",
    "metro",
    "label",
    "experience",
    "employment_form",
    "work_format",
    "work_schedule_by_days",
    "working_hours",
    "education",
    "salary_frequency",
    "driver_license_types",
    "search_field",
    "employer_id",
}

DICTIONARY_MODELS: dict[str, Any] = {
    "area": Area,
    "professional_role": ProfessionalRole,
    "industry": Industry,
    "metro": MetroStation,
}

DICTIONARY_ITEM_CODES = {
    "label",
    "experience",
    "employment_form",
    "work_format",
    "work_schedule_by_days",
    "working_hours",
    "education",
    "salary_frequency",
    "driver_license_types",
    "search_field",
}


async def validate_dictionary_values(session: AsyncSession, values: list[dict[str, str]]) -> None:
    from fastapi import HTTPException

    errors: list[str] = []
    for item in values:
        param = item["parameter_name"]
        val = item["value"]

        if param not in VALID_PARAMETER_NAMES:
            errors.append(f"Неизвестный параметр: {param}")
            continue

        if param == "employer_id":
            continue

        if param in DICTIONARY_MODELS:
            model = DICTIONARY_MODELS[param]
            exists = await session.scalar(select(model.id).where(model.hh_id == val, model.active.is_(True)).limit(1))
            if not exists:
                errors.append(f"Значение '{val}' не найдено в справочнике '{param}'")
        elif param in DICTIONARY_ITEM_CODES:
            exists = await session.scalar(
                select(DictionaryItem.id)
                .where(
                    DictionaryItem.dictionary_code == param,
                    DictionaryItem.hh_id == val,
                    DictionaryItem.active.is_(True),
                )
                .limit(1)
            )
            if not exists:
                errors.append(f"Значение '{val}' не найдено в справочнике '{param}'")

    if errors:
        raise HTTPException(422, detail=errors)


async def get_preset(session: AsyncSession, preset_id: UUID, hh_user_id: str) -> FilterPreset | None:
    return await session.scalar(
        select(FilterPreset)
        .options(selectinload(FilterPreset.values))
        .where(FilterPreset.id == preset_id, FilterPreset.hh_user_id == hh_user_id, FilterPreset.active.is_(True))
    )


async def list_presets(
    session: AsyncSession, hh_user_id: str, q: str | None, limit: int, offset: int
) -> list[FilterPreset]:
    stmt = select(FilterPreset).where(FilterPreset.hh_user_id == hh_user_id, FilterPreset.active.is_(True))
    if q:
        from sqlalchemy import func

        stmt = stmt.where(func.lower(FilterPreset.name).contains(q.lower(), autoescape=True))
    stmt = stmt.order_by(FilterPreset.created_at.desc()).limit(limit).offset(offset)
    return list((await session.scalars(stmt)).all())


async def create_preset(session: AsyncSession, hh_user_id: str, data: FilterPresetCreate) -> FilterPreset:

    existing = await session.scalar(
        select(FilterPreset.id).where(
            FilterPreset.hh_user_id == hh_user_id,
            FilterPreset.name == data.name,
            FilterPreset.active.is_(True),
        )
    )
    if existing:
        from fastapi import HTTPException

        raise HTTPException(409, detail="Пресет с таким именем уже существует")

    if data.values:
        await validate_dictionary_values(session, [v.model_dump() for v in data.values])

    preset = FilterPreset(
        hh_user_id=hh_user_id,
        name=data.name,
        text=data.text,
        excluded_text=data.excluded_text,
        salary=data.salary,
        currency=data.currency,
        salary_mode=data.salary_mode,
        period=data.period,
        date_from=data.date_from,
        date_to=data.date_to,
        order_by=data.order_by,
        premium=data.premium,
        accept_temporary=data.accept_temporary,
        no_magic=data.no_magic,
        top_lat=data.top_lat,
        bottom_lat=data.bottom_lat,
        left_lng=data.left_lng,
        right_lng=data.right_lng,
        sort_point_lat=data.sort_point_lat,
        sort_point_lng=data.sort_point_lng,
        values=[FilterPresetValue(parameter_name=v.parameter_name, value=v.value) for v in data.values],
    )
    session.add(preset)
    await session.flush()
    return preset


async def update_preset(
    session: AsyncSession, preset_id: UUID, hh_user_id: str, data: FilterPresetUpdate
) -> FilterPreset:
    from fastapi import HTTPException

    preset = await get_preset(session, preset_id, hh_user_id)
    if not preset:
        raise HTTPException(404, detail="Пресет не найден")

    if data.name is not None:
        existing = await session.scalar(
            select(FilterPreset.id).where(
                FilterPreset.hh_user_id == hh_user_id,
                FilterPreset.name == data.name,
                FilterPreset.active.is_(True),
                FilterPreset.id != preset_id,
            )
        )
        if existing:
            raise HTTPException(409, detail="Пресет с таким именем уже существует")
        preset.name = data.name

    scalar_fields = [
        "text",
        "excluded_text",
        "salary",
        "currency",
        "salary_mode",
        "period",
        "date_from",
        "date_to",
        "order_by",
        "premium",
        "accept_temporary",
        "no_magic",
        "top_lat",
        "bottom_lat",
        "left_lng",
        "right_lng",
        "sort_point_lat",
        "sort_point_lng",
    ]
    for field in scalar_fields:
        value = getattr(data, field)
        if value is not None:
            setattr(preset, field, value)

    if data.values is not None:
        await validate_dictionary_values(session, [v.model_dump() for v in data.values])
        for val in preset.values:
            await session.delete(val)
        await session.flush()
        preset.values = [FilterPresetValue(parameter_name=v.parameter_name, value=v.value) for v in data.values]

    await session.flush()
    await session.refresh(preset)
    return preset


async def delete_preset(session: AsyncSession, preset_id: UUID, hh_user_id: str) -> None:
    from fastapi import HTTPException

    preset = await get_preset(session, preset_id, hh_user_id)
    if not preset:
        raise HTTPException(404, detail="Пресет не найден")
    await session.delete(preset)
    await session.flush()
