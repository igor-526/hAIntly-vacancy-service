import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from main import app
from models.dictionaries import Language
from utils.database import SessionFactory

HEADERS = {"X-User-Id": "11111111-1111-4111-8111-111111111111"}


@pytest.fixture(scope="module")
def client():
    async def seed_languages() -> None:
        async with SessionFactory() as session:
            for hh_id, name in (("en", "Английский"), ("es", "Испанский")):
                item = await session.scalar(select(Language).where(Language.hh_id == hh_id))
                if item is None:
                    session.add(Language(hh_id=hh_id, name=name, active=True))
            await session.commit()

    asyncio.run(seed_languages())
    with TestClient(app) as value:
        yield value


def test_list_get_pagination_search_and_not_found(client):
    response = client.get(
        "/internal/dictionaries/languages", headers=HEADERS, params={"limit": 2, "offset": 0, "q": "а"}
    )
    assert response.status_code == 200 and len(response.json()["items"]) <= 2
    item = response.json()["items"][0]
    assert client.get(f"/internal/dictionaries/languages/{item['id']}", headers=HEADERS).status_code == 200
    assert client.get("/internal/dictionaries/languages/__missing__", headers=HEADERS).status_code == 404
    first = client.get("/internal/dictionaries/languages", headers=HEADERS, params={"limit": 1, "offset": 0}).json()
    second = client.get("/internal/dictionaries/languages", headers=HEADERS, params={"limit": 1, "offset": 1}).json()
    assert first["items"][0]["id"] != second["items"][0]["id"]


def test_uuid_and_query_limits_and_literal_search(client):
    assert client.get("/internal/dictionaries/languages").status_code == 400
    assert client.get("/internal/dictionaries/languages", headers={"X-User-Id": "bad"}).status_code == 400
    assert client.get("/internal/dictionaries/languages", headers=HEADERS, params={"q": "x" * 101}).status_code == 400
    literal = client.get("/internal/dictionaries/languages", headers=HEADERS, params={"q": ".*"})
    assert literal.status_code == 200 and literal.json()["items"] == []


def test_parent_filter_and_write_routes_absent(client):
    filtered = client.get("/internal/dictionaries/areas", headers=HEADERS, params={"parent_id": "113"})
    assert filtered.status_code == 200
    assert all(item["parent_hh_id"] == "113" for item in filtered.json()["items"])
    assert client.post("/internal/dictionaries/languages", headers=HEADERS).status_code == 405


def test_inactive_item_is_absent_from_list_and_get(client):
    async def seed():
        async with SessionFactory() as session:
            item = await session.scalar(select(Language).where(Language.hh_id == "__inactive_api_test__"))
            if item is None:
                session.add(Language(hh_id="__inactive_api_test__", name="Invisible", active=False))
            else:
                item.name = "Invisible"
                item.active = False
            await session.commit()

    asyncio.run(seed())
    listed = client.get("/internal/dictionaries/languages", headers=HEADERS, params={"q": "Invisible"})
    assert listed.json()["items"] == []
    assert client.get("/internal/dictionaries/languages/__inactive_api_test__", headers=HEADERS).status_code == 404
