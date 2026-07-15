from uuid import uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from models.dictionaries import Area, DictionaryItem, ProfessionalRole
from models.filter_presets import FilterPreset, FilterPresetValue

HH_USER_ID = "test_hh_user_api"


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
async def seed_api_dictionaries(session: AsyncSession):
    area = Area(hh_id="1", name="Москва", active=True)
    role = ProfessionalRole(hh_id="10", name="Программист", category_hh_id="1", active=True)
    label_item = DictionaryItem(dictionary_code="label", hh_id="direct", name="Без посредников", active=True)
    session.add_all([area, role, label_item])
    await session.flush()


HEADERS = {"X-User-Id": "00000000-0000-0000-0000-000000000001", "X-Hh-User-Id": HH_USER_ID}


@pytest.mark.asyncio
async def test_create_filter_preset(client: AsyncClient):
    resp = await client.post(
        "/internal/filters",
        json={
            "name": "API Пресет",
            "text": "python",
            "values": [{"parameter_name": "area", "value": "1"}],
        },
        headers=HEADERS,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "API Пресет"
    assert data["text"] == "python"
    assert len(data["values"]) == 1


@pytest.mark.asyncio
async def test_list_filter_presets(client: AsyncClient):
    await client.post("/internal/filters", json={"name": "List1"}, headers=HEADERS)
    await client.post("/internal/filters", json={"name": "List2"}, headers=HEADERS)

    resp = await client.get("/internal/filters", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_list_filter_presets_search(client: AsyncClient):
    await client.post("/internal/filters", json={"name": "SearchUniqueXYZ"}, headers=HEADERS)

    resp = await client.get("/internal/filters", params={"q": "uniquexyz"}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert any(item["name"] == "SearchUniqueXYZ" for item in data["items"])


@pytest.mark.asyncio
async def test_list_filter_presets_pagination(client: AsyncClient):
    for i in range(4):
        await client.post("/internal/filters", json={"name": f"Page{i}"}, headers=HEADERS)

    resp = await client.get("/internal/filters", params={"limit": 2, "offset": 0}, headers=HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2

    resp2 = await client.get("/internal/filters", params={"limit": 2, "offset": 2}, headers=HEADERS)
    assert resp2.status_code == 200
    assert len(resp2.json()["items"]) == 2


@pytest.mark.asyncio
async def test_get_filter_preset_detail(client: AsyncClient):
    create_resp = await client.post(
        "/internal/filters",
        json={"name": "Detail", "salary": 50000, "values": [{"parameter_name": "area", "value": "1"}]},
        headers=HEADERS,
    )
    preset_id = create_resp.json()["id"]

    resp = await client.get(f"/internal/filters/{preset_id}", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Detail"
    assert data["salary"] == 50000
    assert len(data["values"]) == 1


@pytest.mark.asyncio
async def test_get_filter_preset_not_found(client: AsyncClient):
    resp = await client.get(f"/internal/filters/{uuid4()}", headers=HEADERS)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_filter_preset(client: AsyncClient):
    create_resp = await client.post("/internal/filters", json={"name": "ToUpdate"}, headers=HEADERS)
    preset_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/internal/filters/{preset_id}",
        json={"name": "Updated", "text": "new query"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"
    assert resp.json()["text"] == "new query"


@pytest.mark.asyncio
async def test_update_filter_preset_values(client: AsyncClient):
    create_resp = await client.post("/internal/filters", json={"name": "UpdateVals"}, headers=HEADERS)
    preset_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/internal/filters/{preset_id}",
        json={"values": [{"parameter_name": "area", "value": "1"}, {"parameter_name": "professional_role", "value": "10"}]},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert len(resp.json()["values"]) == 2


@pytest.mark.asyncio
async def test_delete_filter_preset(client: AsyncClient):
    create_resp = await client.post("/internal/filters", json={"name": "ToDelete"}, headers=HEADERS)
    preset_id = create_resp.json()["id"]

    resp = await client.delete(f"/internal/filters/{preset_id}", headers=HEADERS)
    assert resp.status_code == 204

    get_resp = await client.get(f"/internal/filters/{preset_id}", headers=HEADERS)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_create_duplicate_name(client: AsyncClient):
    await client.post("/internal/filters", json={"name": "DupName"}, headers=HEADERS)
    resp = await client.post("/internal/filters", json={"name": "DupName"}, headers=HEADERS)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_invalid_dictionary_value(client: AsyncClient):
    resp = await client.post(
        "/internal/filters",
        json={"name": "BadDict", "values": [{"parameter_name": "area", "value": "999999"}]},
        headers=HEADERS,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_invalid_dictionary_item(client: AsyncClient):
    resp = await client.post(
        "/internal/filters",
        json={"name": "BadDictItem", "values": [{"parameter_name": "label", "value": "nonexistent"}]},
        headers=HEADERS,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_user_isolation(client: AsyncClient):
    await client.post("/internal/filters", json={"name": "UserA"}, headers=HEADERS)

    other_headers = {"X-User-Id": "00000000-0000-0000-0000-000000000099", "X-Hh-User-Id": "other_hh_user"}
    resp = await client.get("/internal/filters", headers=other_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 0


@pytest.mark.asyncio
async def test_missing_x_user_id(client: AsyncClient):
    resp = await client.get("/internal/filters", headers={"X-Hh-User-Id": HH_USER_ID})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_missing_x_hh_user_id(client: AsyncClient):
    resp = await client.get("/internal/filters", headers={"X-User-Id": "00000000-0000-0000-0000-000000000001"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invalid_x_user_id(client: AsyncClient):
    resp = await client.get("/internal/filters", headers={"X-User-Id": "not-a-uuid", "X-Hh-User-Id": HH_USER_ID})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_preset_with_all_fields(client: AsyncClient):
    payload = {
        "name": "FullPreset",
        "text": "developer",
        "excluded_text": "junior",
        "salary": 150000,
        "currency": "RUR",
        "salary_mode": "after_taxes",
        "period": 30,
        "date_from": "2025-01-01",
        "date_to": "2025-12-31",
        "order_by": "publication_time",
        "premium": True,
        "accept_temporary": False,
        "no_magic": True,
        "top_lat": 55.9,
        "bottom_lat": 55.5,
        "left_lng": 37.3,
        "right_lng": 37.9,
        "sort_point_lat": 55.75,
        "sort_point_lng": 37.62,
        "values": [
            {"parameter_name": "area", "value": "1"},
            {"parameter_name": "professional_role", "value": "10"},
            {"parameter_name": "label", "value": "direct"},
            {"parameter_name": "employer_id", "value": "any_company"},
        ],
    }
    resp = await client.post("/internal/filters", json=payload, headers=HEADERS)
    assert resp.status_code == 201
    data = resp.json()
    assert data["salary"] == 150000
    assert data["currency"] == "RUR"
    assert data["premium"] is True
    assert len(data["values"]) == 4


@pytest.mark.asyncio
async def test_update_presets_cascade_replace(client: AsyncClient):
    create_resp = await client.post(
        "/internal/filters",
        json={"name": "CascadeTest", "values": [{"parameter_name": "area", "value": "1"}]},
        headers=HEADERS,
    )
    preset_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/internal/filters/{preset_id}",
        json={"values": [{"parameter_name": "professional_role", "value": "10"}]},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["values"]) == 1
    assert data["values"][0]["parameter_name"] == "professional_role"


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
