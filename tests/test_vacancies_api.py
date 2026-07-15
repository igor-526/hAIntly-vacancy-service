from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient

from main import app

USER_ID = "00000000-0000-0000-0000-000000000001"
ACCOUNT_ID = "00000000-0000-0000-0000-000000000010"
HEADERS = {"X-User-Id": USER_ID, "X-Hh-Account-Id": ACCOUNT_ID}

MOCK_SEARCH_RESULT = {
    "items": [{"id": "111", "name": "Python Dev", "alternate_url": "https://hh.ru/vacancy/111"}],
    "found": 1,
    "pages": 1,
    "per_page": 30,
    "page": 0,
}

MOCK_VACANCY = {
    "id": "111",
    "name": "Python Dev",
    "description": "desc",
    "alternate_url": "https://hh.ru/vacancy/111",
}


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _patch_profile(token: str = "fake_token"):
    return patch(
        "api.vacancies.ProfileServiceClient.get_hh_token",
        new_callable=AsyncMock,
        return_value=token,
    )


def _patch_hh_search(result=None):
    if result is None:
        result = MOCK_SEARCH_RESULT
    return patch(
        "api.vacancies.HHClient.search_vacancies",
        new_callable=AsyncMock,
        return_value=result,
    )


def _patch_hh_vacancy(result=None):
    if result is None:
        result = MOCK_VACANCY
    return patch(
        "api.vacancies.HHClient.get_vacancy",
        new_callable=AsyncMock,
        return_value=result,
    )


@pytest.mark.asyncio
async def test_search_without_filters(client: AsyncClient):
    with _patch_profile() as mock_token, _patch_hh_search() as mock_search:
        resp = await client.get("/internal/vacancies", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] == 1
        assert len(data["items"]) == 1
        mock_token.assert_awaited_once()
        mock_search.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_with_params(client: AsyncClient):
    with _patch_profile(), _patch_hh_search() as mock_search:
        resp = await client.get(
            "/internal/vacancies",
            params={"text": "python", "experience": "between1And3"},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        call_args = mock_search.call_args
        query = call_args[0][0]
        assert query["text"] == "python"
        assert query["experience"] == "between1And3"


@pytest.mark.asyncio
async def test_search_with_pagination(client: AsyncClient):
    with _patch_profile(), _patch_hh_search() as mock_search:
        resp = await client.get(
            "/internal/vacancies",
            params={"page": "2", "per_page": "50"},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        call_args = mock_search.call_args
        query = call_args[0][0]
        assert query["page"] == 2
        assert query["per_page"] == 50


@pytest.mark.asyncio
async def test_search_per_page_capped(client: AsyncClient):
    with _patch_profile(), _patch_hh_search() as mock_search:
        resp = await client.get(
            "/internal/vacancies",
            params={"per_page": "200"},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        call_args = mock_search.call_args
        query = call_args[0][0]
        assert query["per_page"] == 100


@pytest.mark.asyncio
async def test_search_missing_x_hh_account_id(client: AsyncClient):
    resp = await client.get("/internal/vacancies", headers={"X-User-Id": USER_ID})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_search_missing_x_user_id(client: AsyncClient):
    resp = await client.get("/internal/vacancies", headers={"X-Hh-Account-Id": ACCOUNT_ID})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_search_invalid_x_user_id(client: AsyncClient):
    resp = await client.get(
        "/internal/vacancies",
        headers={"X-User-Id": "not-a-uuid", "X-Hh-Account-Id": ACCOUNT_ID},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_search_invalid_x_hh_account_id(client: AsyncClient):
    resp = await client.get(
        "/internal/vacancies",
        headers={"X-User-Id": USER_ID, "X-Hh-Account-Id": "not-a-uuid"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_search_profile_service_refresh_failed(client: AsyncClient):
    from infrastructure.profile_service import ProfileServiceError

    with patch(
        "api.vacancies.ProfileServiceClient.get_hh_token",
        new_callable=AsyncMock,
        side_effect=ProfileServiceError("hh_token_refresh_failed"),
    ):
        resp = await client.get("/internal/vacancies", headers=HEADERS)
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_search_profile_service_unavailable(client: AsyncClient):
    from infrastructure.profile_service import ProfileServiceError

    with patch(
        "api.vacancies.ProfileServiceClient.get_hh_token",
        new_callable=AsyncMock,
        side_effect=ProfileServiceError("connection error: TimeoutError"),
    ):
        resp = await client.get("/internal/vacancies", headers=HEADERS)
        assert resp.status_code == 502


@pytest.mark.asyncio
async def test_get_vacancy_success(client: AsyncClient):
    with _patch_profile(), _patch_hh_vacancy():
        resp = await client.get("/internal/vacancies/111", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "111"
        assert data["name"] == "Python Dev"


@pytest.mark.asyncio
async def test_get_vacancy_not_found(client: AsyncClient):
    from infrastructure.hh import HHError

    with _patch_profile(), patch(
        "api.vacancies.HHClient.get_vacancy",
        new_callable=AsyncMock,
        side_effect=HHError("unexpected status 404"),
    ):
        resp = await client.get("/internal/vacancies/999", headers=HEADERS)
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_vacancy_missing_headers(client: AsyncClient):
    resp = await client.get("/internal/vacancies/111", headers={"X-User-Id": USER_ID})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_search_multiselect_params(client: AsyncClient):
    with _patch_profile(), _patch_hh_search() as mock_search:
        resp = await client.get(
            "/internal/vacancies",
            params=[("area", "1"), ("area", "2")],
            headers=HEADERS,
        )
        assert resp.status_code == 200
        call_args = mock_search.call_args
        query = call_args[0][0]
        assert query["area"] == ["1", "2"]
