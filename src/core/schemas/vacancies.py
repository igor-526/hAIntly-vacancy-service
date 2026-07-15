from typing import Any

from core.schemas.base import Schema


class VacancySearchParams(Schema):
    preset_id: str | None = None
    text: str | None = None
    excluded_text: str | None = None
    search_field: list[str] | str | None = None
    experience: list[str] | str | None = None
    area: list[str] | str | None = None
    metro: list[str] | str | None = None
    professional_role: list[str] | str | None = None
    industry: list[str] | str | None = None
    employer_id: list[str] | str | None = None
    currency: str | None = None
    salary: int | None = None
    salary_frequency: list[str] | str | None = None
    salary_mode: str | None = None
    label: list[str] | str | None = None
    period: int | None = None
    date_from: str | None = None
    date_to: str | None = None
    top_lat: float | None = None
    bottom_lat: float | None = None
    left_lng: float | None = None
    right_lng: float | None = None
    order_by: str | None = None
    sort_point_lat: float | None = None
    sort_point_lng: float | None = None
    no_magic: bool | None = None
    premium: bool | None = None
    accept_temporary: bool | None = None
    employment_form: list[str] | str | None = None
    work_schedule_by_days: list[str] | str | None = None
    working_hours: list[str] | str | None = None
    work_format: list[str] | str | None = None
    education: list[str] | str | None = None
    driver_license_types: list[str] | str | None = None


MULTI_PARAMS = {
    "search_field",
    "experience",
    "area",
    "metro",
    "professional_role",
    "industry",
    "employer_id",
    "salary_frequency",
    "label",
    "employment_form",
    "work_schedule_by_days",
    "working_hours",
    "work_format",
    "education",
    "driver_license_types",
}


def build_hh_query(
    params: dict[str, Any],
    preset_params: dict[str, Any] | None,
    present_keys: set[str],
    page: int,
    per_page: int,
) -> dict[str, Any]:
    base: dict[str, Any] = {}
    if preset_params:
        base.update(preset_params)

    for key in present_keys:
        if key == "preset_id":
            continue
        value = params.get(key)
        if value is None or value == "":
            base.pop(key, None)
        else:
            base[key] = value

    result: dict[str, Any] = {}
    for key, value in base.items():
        if value is None or value == "":
            continue
        if key in MULTI_PARAMS and isinstance(value, list):
            for item in value:
                result.setdefault(key, [])
                result[key].append(item)
        else:
            result[key] = value

    result["page"] = page
    result["per_page"] = per_page
    return result
