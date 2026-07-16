from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.schemas.vacancies import build_hh_query
from core.services.vacancies import VacancyService, VacancyServiceError, _preset_to_params
from infrastructure.hh import HHError
from models.filter_presets import FilterPreset


def _make_preset(**overrides: Any) -> FilterPreset:
    defaults = {
        "id": uuid4(),
        "hh_user_id": "test_user",
        "name": "Test Preset",
        "text": "python",
        "excluded_text": None,
        "salary": 100000,
        "currency": "RUR",
        "salary_mode": None,
        "period": None,
        "date_from": None,
        "date_to": None,
        "order_by": None,
        "premium": None,
        "accept_temporary": None,
        "no_magic": None,
        "top_lat": None,
        "bottom_lat": None,
        "left_lng": None,
        "right_lng": None,
        "sort_point_lat": None,
        "sort_point_lng": None,
        "values": [],
    }
    defaults.update(overrides)
    preset = MagicMock(spec=FilterPreset)
    for k, v in defaults.items():
        setattr(preset, k, v)
    return preset


class TestPresetToParams:
    def test_scalar_fields(self):
        preset = _make_preset(text="python", salary=100000, currency="RUR")
        params = _preset_to_params(preset)
        assert params["text"] == "python"
        assert params["salary"] == 100000
        assert params["currency"] == "RUR"

    def test_none_fields_excluded(self):
        preset = _make_preset(text="python", salary=None, currency=None)
        params = _preset_to_params(preset)
        assert "salary" not in params
        assert "currency" not in params
        assert params["text"] == "python"

    def test_multiselect_values(self):
        val1 = MagicMock()
        val1.parameter_name = "area"
        val1.value = "1"
        val2 = MagicMock()
        val2.parameter_name = "area"
        val2.value = "2"
        val3 = MagicMock()
        val3.parameter_name = "experience"
        val3.value = "between1And3"
        preset = _make_preset(text=None, values=[val1, val2, val3])
        params = _preset_to_params(preset)
        assert params["area"] == ["1", "2"]
        assert params["experience"] == ["between1And3"]


class TestBuildHhQuery:
    def test_no_preset_no_params(self):
        query = build_hh_query({}, None, set(), page=0, per_page=30)
        assert query == {"page": 0, "per_page": 30}

    def test_params_only(self):
        params = {"text": "python", "experience": "between1And3"}
        present = {"text", "experience"}
        query = build_hh_query(params, None, present, page=0, per_page=30)
        assert query["text"] == "python"
        assert query["experience"] == "between1And3"
        assert query["page"] == 0
        assert query["per_page"] == 30

    def test_preset_only(self):
        preset_params = {"text": "java", "salary": 200000}
        query = build_hh_query({}, preset_params, set(), page=0, per_page=30)
        assert query["text"] == "java"
        assert query["salary"] == 200000

    def test_preset_with_override(self):
        preset_params = {"text": "java", "salary": 200000}
        params = {"text": "python"}
        present = {"text"}
        query = build_hh_query(params, preset_params, present, page=0, per_page=30)
        assert query["text"] == "python"
        assert query["salary"] == 200000

    def test_empty_string_resets_preset_field(self):
        preset_params = {"text": "java", "salary": 200000}
        params = {"text": ""}
        present = {"text"}
        query = build_hh_query(params, preset_params, present, page=0, per_page=30)
        assert "text" not in query
        assert query["salary"] == 200000

    def test_none_resets_preset_field(self):
        preset_params = {"text": "java", "salary": 200000}
        params = {"text": None}
        present = {"text"}
        query = build_hh_query(params, preset_params, present, page=0, per_page=30)
        assert "text" not in query
        assert query["salary"] == 200000

    def test_multiselect_as_list(self):
        params = {"area": ["1", "2"]}
        present = {"area"}
        query = build_hh_query(params, None, present, page=0, per_page=30)
        assert query["area"] == ["1", "2"]

    def test_pagination_params(self):
        query = build_hh_query({}, None, set(), page=2, per_page=50)
        assert query["page"] == 2
        assert query["per_page"] == 50


class TestVacancyService:
    @pytest.fixture
    def mock_hh_client(self):
        client = MagicMock()
        client.search_vacancies = AsyncMock(return_value={"items": [], "found": 0, "pages": 0})
        client.get_vacancy = AsyncMock(return_value={"id": "123", "name": "Test"})
        return client

    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_hh_client, mock_session):
        return VacancyService(hh_client=mock_hh_client, session=mock_session)

    @pytest.mark.asyncio
    async def test_search_calls_hh(self, service, mock_hh_client):
        result = await service.search(
            hh_user_id="user-123",
            params={},
            present_keys=set(),
            page=0,
            per_page=30,
        )
        mock_hh_client.search_vacancies.assert_awaited_once()
        assert result == {"items": [], "found": 0, "pages": 0}

    @pytest.mark.asyncio
    async def test_search_with_params(self, service, mock_hh_client):
        await service.search(
            hh_user_id="user-123",
            params={"text": "python"},
            present_keys={"text"},
            page=0,
            per_page=30,
        )
        call_args = mock_hh_client.search_vacancies.call_args
        query = call_args[0][0]
        assert query["text"] == "python"

    @pytest.mark.asyncio
    async def test_search_hh_auth_error(self, service, mock_hh_client):
        mock_hh_client.search_vacancies = AsyncMock(side_effect=HHError("authorization failed"))
        with pytest.raises(VacancyServiceError) as exc_info:
            await service.search(
                hh_user_id="user-123",
                params={},
                present_keys=set(),
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_vacancy_success(self, service, mock_hh_client):
        result = await service.get_vacancy(vacancy_id="456")
        mock_hh_client.get_vacancy.assert_awaited_once_with("456")
        assert result == {"id": "123", "name": "Test"}

    @pytest.mark.asyncio
    async def test_get_vacancy_not_found(self, service, mock_hh_client):
        mock_hh_client.get_vacancy = AsyncMock(side_effect=HHError("unexpected status 404"))
        with pytest.raises(VacancyServiceError) as exc_info:
            await service.get_vacancy(vacancy_id="999")
        assert exc_info.value.status_code == 404
