from datetime import datetime
from uuid import UUID

from pydantic import Field

from core.schemas.base import Schema


class FilterPresetValueOut(Schema):
    parameter_name: str
    value: str


class FilterPresetListItem(Schema):
    id: UUID
    name: str


class FilterPresetOut(Schema):
    id: UUID
    hh_user_id: str
    name: str
    text: str | None = None
    excluded_text: str | None = None
    salary: int | None = None
    currency: str | None = None
    salary_mode: str | None = None
    period: int | None = None
    date_from: str | None = None
    date_to: str | None = None
    order_by: str | None = None
    premium: bool | None = None
    accept_temporary: bool | None = None
    no_magic: bool | None = None
    top_lat: float | None = None
    bottom_lat: float | None = None
    left_lng: float | None = None
    right_lng: float | None = None
    sort_point_lat: float | None = None
    sort_point_lng: float | None = None
    values: list[FilterPresetValueOut] = []
    created_at: datetime
    updated_at: datetime


class FilterPresetValueIn(Schema):
    parameter_name: str = Field(max_length=100)
    value: str = Field(max_length=200)


class FilterPresetCreate(Schema):
    name: str = Field(min_length=1, max_length=63)
    text: str | None = None
    excluded_text: str | None = None
    salary: int | None = None
    currency: str | None = None
    salary_mode: str | None = None
    period: int | None = None
    date_from: str | None = None
    date_to: str | None = None
    order_by: str | None = None
    premium: bool | None = None
    accept_temporary: bool | None = None
    no_magic: bool | None = None
    top_lat: float | None = None
    bottom_lat: float | None = None
    left_lng: float | None = None
    right_lng: float | None = None
    sort_point_lat: float | None = None
    sort_point_lng: float | None = None
    values: list[FilterPresetValueIn] = []


class FilterPresetUpdate(Schema):
    name: str | None = Field(default=None, max_length=63)
    text: str | None = None
    excluded_text: str | None = None
    salary: int | None = None
    currency: str | None = None
    salary_mode: str | None = None
    period: int | None = None
    date_from: str | None = None
    date_to: str | None = None
    order_by: str | None = None
    premium: bool | None = None
    accept_temporary: bool | None = None
    no_magic: bool | None = None
    top_lat: float | None = None
    bottom_lat: float | None = None
    left_lng: float | None = None
    right_lng: float | None = None
    sort_point_lat: float | None = None
    sort_point_lng: float | None = None
    values: list[FilterPresetValueIn] | None = None


class FilterPresetListResponse(Schema):
    items: list[FilterPresetListItem]
    limit: int
    offset: int
