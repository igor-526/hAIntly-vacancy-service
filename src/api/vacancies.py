from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas.vacancies import MULTI_PARAMS
from core.services.vacancies import VacancyService, VacancyServiceError
from infrastructure.hh import HHClient
from settings import settings
from utils.database import get_session

router = APIRouter(prefix="/internal/vacancies", tags=["Vacancies"])

MULTI_QUERY_PARAMS = MULTI_PARAMS | {"preset_id"}


def user_context(x_user_id: Annotated[str | None, Header()] = None) -> UUID:
    if x_user_id is None:
        raise HTTPException(400, "Требуется X-User-Id")
    try:
        return UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(400, "Некорректный X-User-Id") from exc


def _get_hh_client() -> HHClient:
    return HHClient(
        base_url=str(settings.hh_api_url),
        user_agent=settings.hh_user_agent,
        app_token=settings.hh_app_token,
        timeout=settings.hh_timeout_seconds,
        retries=settings.hh_retry_count,
        backoff=settings.hh_retry_backoff_seconds,
    )


def _parse_query_params(request: Request) -> tuple[dict[str, object], set[str]]:
    params: dict[str, object] = {}
    present_keys: set[str] = set()

    for key in request.query_params:
        present_keys.add(key)

    for key in present_keys:
        values = request.query_params.getlist(key)
        if key in MULTI_QUERY_PARAMS:
            params[key] = values if len(values) > 1 else (values[0] if values else None)
        else:
            raw = values[0] if values else None
            if raw is None or raw == "":
                params[key] = None
            else:
                params[key] = raw

    return params, present_keys


@router.get("")
async def search_vacancies(
    user_id: Annotated[UUID, Depends(user_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
    x_hh_user_id: Annotated[str | None, Header()] = None,
    page: Annotated[int, Query(ge=0)] = 0,
    per_page: Annotated[int, Query(ge=1)] = 30,
):
    per_page = min(per_page, 100)
    params, present_keys = _parse_query_params(request)

    service = VacancyService(
        hh_client=_get_hh_client(),
        session=session,
    )

    try:
        return await service.search(
            hh_user_id=x_hh_user_id,
            params=params,
            present_keys=present_keys,
            page=page,
            per_page=per_page,
        )
    except VacancyServiceError as exc:
        raise HTTPException(exc.status_code, exc.message)


@router.get("/{vacancy_id}")
async def get_vacancy(
    vacancy_id: str,
    user_id: Annotated[UUID, Depends(user_context)],
):
    service = VacancyService(
        hh_client=_get_hh_client(),
        session=None,  # type: ignore[arg-type]
    )

    try:
        return await service.get_vacancy(vacancy_id=vacancy_id)
    except VacancyServiceError as exc:
        raise HTTPException(exc.status_code, exc.message)
