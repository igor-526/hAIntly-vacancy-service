from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.hh import HHClient, HHError
from models.filter_presets import FilterPreset
from repositories.filters import get_preset


def _preset_to_params(preset: FilterPreset) -> dict[str, Any]:
    params: dict[str, Any] = {}
    scalar_fields = [
        "text", "excluded_text", "salary", "currency", "salary_mode", "period",
        "date_from", "date_to", "order_by", "premium", "accept_temporary", "no_magic",
        "top_lat", "bottom_lat", "left_lng", "right_lng", "sort_point_lat", "sort_point_lng",
    ]
    for field in scalar_fields:
        value = getattr(preset, field)
        if value is not None:
            params[field] = value

    multiselect: dict[str, list[str]] = {}
    for pv in preset.values:
        multiselect.setdefault(pv.parameter_name, [])
        multiselect[pv.parameter_name].append(pv.value)
    params.update(multiselect)
    return params


class VacancyService:
    def __init__(
        self,
        *,
        hh_client: HHClient,
        session: AsyncSession,
    ) -> None:
        self.hh_client = hh_client
        self.session = session

    async def _load_preset(self, preset_id: str, hh_user_id: str) -> dict[str, Any]:
        try:
            uuid = UUID(preset_id)
        except ValueError as exc:
            raise VacancyServiceError("invalid_preset_id", status_code=400) from exc
        preset = await get_preset(self.session, uuid, hh_user_id)
        if not preset:
            raise VacancyServiceError("preset_not_found", status_code=404)
        return _preset_to_params(preset)

    async def search(
        self,
        *,
        hh_user_id: str | None,
        params: dict[str, Any],
        present_keys: set[str],
        page: int = 0,
        per_page: int = 30,
    ) -> dict[str, Any]:
        from core.schemas.vacancies import build_hh_query

        preset_params = None
        if "preset_id" in present_keys and params.get("preset_id"):
            if not hh_user_id:
                raise VacancyServiceError("hh_user_id_required_for_preset", status_code=400)
            preset_params = await self._load_preset(params["preset_id"], hh_user_id)

        query = build_hh_query(params, preset_params, present_keys, page, per_page)

        try:
            return await self.hh_client.search_vacancies(query)
        except HHError as exc:
            if "authorization" in str(exc) or "403" in str(exc):
                raise VacancyServiceError("hh_authorization_failed", status_code=401) from exc
            raise VacancyServiceError(f"hh_error: {exc}", status_code=502) from exc

    async def get_vacancy(self, *, vacancy_id: str) -> dict[str, Any]:
        try:
            return await self.hh_client.get_vacancy(vacancy_id)
        except HHError as exc:
            if "unexpected status 404" in str(exc):
                raise VacancyServiceError("vacancy_not_found", status_code=404) from exc
            if "authorization" in str(exc) or "403" in str(exc):
                raise VacancyServiceError("hh_authorization_failed", status_code=401) from exc
            raise VacancyServiceError(f"hh_error: {exc}", status_code=502) from exc


class VacancyServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)
