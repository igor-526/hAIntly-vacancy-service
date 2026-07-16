from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas.filters import (
    FilterPresetCreate,
    FilterPresetListItem,
    FilterPresetListResponse,
    FilterPresetOut,
    FilterPresetUpdate,
)
from repositories.filters import create_preset, delete_preset, get_preset, list_presets, update_preset
from utils.database import get_session

router = APIRouter(prefix="/internal/filters", tags=["Filters"])


def user_context(x_user_id: Annotated[str | None, Header()] = None) -> UUID:
    if x_user_id is None:
        raise HTTPException(400, "Требуется X-User-Id")
    try:
        return UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(400, "Некорректный X-User-Id") from exc


def hh_user_context(x_hh_user_id: Annotated[str | None, Header()] = None) -> str:
    if x_hh_user_id is None:
        raise HTTPException(400, "Требуется X-Hh-User-Id")
    if not x_hh_user_id.strip():
        raise HTTPException(400, "Некорректный X-Hh-User-Id")
    return x_hh_user_id


@router.get("", response_model=FilterPresetListResponse)
async def list_filter_presets(
    _: Annotated[UUID, Depends(user_context)],
    hh_user_id: Annotated[str, Depends(hh_user_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    presets = await list_presets(session, hh_user_id, q, limit, offset)
    return FilterPresetListResponse(
        items=[FilterPresetListItem(id=p.id, name=p.name) for p in presets],
        limit=limit,
        offset=offset,
    )


@router.get("/{preset_id}", response_model=FilterPresetOut)
async def get_filter_preset(
    preset_id: UUID,
    _: Annotated[UUID, Depends(user_context)],
    hh_user_id: Annotated[str, Depends(hh_user_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    preset = await get_preset(session, preset_id, hh_user_id)
    if not preset:
        raise HTTPException(404, "Пресет не найден")
    return preset


@router.post("", response_model=FilterPresetOut, status_code=201)
async def create_filter_preset(
    data: FilterPresetCreate,
    _: Annotated[UUID, Depends(user_context)],
    hh_user_id: Annotated[str, Depends(hh_user_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await create_preset(session, hh_user_id, data)


@router.patch("/{preset_id}", response_model=FilterPresetOut)
async def update_filter_preset(
    preset_id: UUID,
    data: FilterPresetUpdate,
    _: Annotated[UUID, Depends(user_context)],
    hh_user_id: Annotated[str, Depends(hh_user_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await update_preset(session, preset_id, hh_user_id, data)


@router.delete("/{preset_id}", status_code=204)
async def delete_filter_preset(
    preset_id: UUID,
    _: Annotated[UUID, Depends(user_context)],
    hh_user_id: Annotated[str, Depends(hh_user_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    await delete_preset(session, preset_id, hh_user_id)
