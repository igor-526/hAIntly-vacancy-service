from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import String, func, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.ext.asyncio import AsyncSession

from models.dictionaries import (
    Area,
    Country,
    DictionaryItem,
    Industry,
    Language,
    MetroCity,
    MetroLine,
    MetroStation,
    ProfessionalRole,
)
from utils.database import get_session

router = APIRouter(prefix="/internal/dictionaries", tags=["Dictionaries"])
MODELS = {
    "areas": Area,
    "countries": Country,
    "professional-roles": ProfessionalRole,
    "industries": Industry,
    "metro-cities": MetroCity,
    "metro-lines": MetroLine,
    "metro-stations": MetroStation,
    "languages": Language,
}


def user_context(x_user_id: Annotated[str | None, Header()] = None) -> UUID:
    if x_user_id is None:
        raise HTTPException(400, "Требуется X-User-Id")
    try:
        return UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(400, "Некорректный X-User-Id") from exc


def serialize(item) -> dict[str, object]:
    result = {"id": item.hh_id, "name": item.name}
    for field in (
        "dictionary_code",
        "parent_hh_id",
        "category_hh_id",
        "city_hh_id",
        "line_hh_id",
        "lat",
        "lng",
        "order",
    ):
        if hasattr(item, field):
            result[field] = getattr(item, field)
    return result


async def query_items(model, session: AsyncSession, q: str | None, limit: int, offset: int, filters: dict):
    stmt = select(model).where(model.active.is_(True))
    if q:
        stmt = stmt.where(func.lower(model.name).contains(q.lower(), autoescape=True))
    for key, value in filters.items():
        if value is not None and hasattr(model, key):
            stmt = stmt.where(sql_cast(getattr(model, key), String) == value)
    rows = (await session.scalars(stmt.order_by(model.name, model.hh_id).limit(limit).offset(offset))).all()
    return {"items": [serialize(row) for row in rows], "limit": limit, "offset": offset}


@router.get("/dictionary-items")
async def list_dictionary_items(
    _: Annotated[UUID, Depends(user_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    dictionary_code: str | None = None,
):
    return await query_items(DictionaryItem, session, q, limit, offset, {"dictionary_code": dictionary_code})


@router.get("/dictionary-items/{dictionary_code}/{hh_id}")
async def get_dictionary_item(
    dictionary_code: str,
    hh_id: str,
    _: Annotated[UUID, Depends(user_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    item = await session.scalar(
        select(DictionaryItem).where(
            DictionaryItem.dictionary_code == dictionary_code,
            DictionaryItem.hh_id == hh_id,
            DictionaryItem.active.is_(True),
        )
    )
    if item is None:
        raise HTTPException(404, "Элемент не найден")
    return serialize(item)


@router.get("/{family}")
async def list_family(
    family: str,
    _: Annotated[UUID, Depends(user_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    parent_id: str | None = None,
    category_id: str | None = None,
    city_id: str | None = None,
    line_id: str | None = None,
):
    model = MODELS.get(family)
    if model is None:
        raise HTTPException(404, "Справочник не найден")
    return await query_items(
        model,
        session,
        q,
        limit,
        offset,
        {"parent_hh_id": parent_id, "category_hh_id": category_id, "city_hh_id": city_id, "line_hh_id": line_id},
    )


@router.get("/{family}/{hh_id}")
async def get_family(
    family: str,
    hh_id: str,
    _: Annotated[UUID, Depends(user_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    model = MODELS.get(family)
    if model is None:
        raise HTTPException(404, "Справочник не найден")
    typed_model = cast(Any, model)
    item = await session.scalar(select(typed_model).where(typed_model.hh_id == hh_id, typed_model.active.is_(True)))
    if item is None:
        raise HTTPException(404, "Элемент не найден")
    return serialize(item)
