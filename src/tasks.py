import asyncio
import logging
from datetime import UTC, datetime
from time import monotonic

from celery import Celery
from redis import Redis
from redis.exceptions import LockNotOwnedError
from sqlalchemy import select

from infrastructure.hh import HHClient
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
    ProfessionalRoleCategory,
    SyncState,
)
from repositories.dictionaries import apply_snapshot, due_dictionaries
from settings import settings
from utils.database import SessionFactory, close_database

log = logging.getLogger(__name__)
celery_app = Celery("vacancy", broker=str(settings.celery_broker_url), backend=str(settings.celery_result_backend))
celery_app.conf.beat_schedule = {"check-dictionaries-hourly": {"task": "vacancy.check_dictionaries", "schedule": 3600}}


def _client():
    return HHClient(
        base_url=str(settings.hh_api_url),
        user_agent=settings.hh_user_agent,
        timeout=settings.hh_timeout_seconds,
        retries=settings.hh_retry_count,
        backoff=settings.hh_retry_backoff_seconds,
    )


def flatten(nodes, parent=None):
    result = []
    for node in nodes:
        result.append({"hh_id": str(node["id"]), "name": str(node["name"]), "parent_hh_id": parent})
        result += flatten(node.get("areas", node.get("industries", [])), str(node["id"]))
    return result


async def _sync(name: str):
    started = monotonic()
    now = datetime.now(UTC)
    async with SessionFactory() as session:
        state = await session.scalar(select(SyncState).where(SyncState.name == name))
        if state is None:
            raise RuntimeError("Состояние синхронизации не найдено")
        state.status = "running"
        state.last_attempt_started_at = now
        await session.commit()
    try:
        client = _client()
        async with SessionFactory() as session:
            if name == "dictionaries":
                payload = await client.dictionaries()
                records = [
                    {
                        "dictionary_code": code,
                        "hh_id": str(x.get("id") or x.get("code")),
                        "name": str(x.get("name", x.get("id"))),
                    }
                    for code, values in payload.items()
                    if isinstance(values, list)
                    for x in values
                    if isinstance(x, dict) and (x.get("id") is not None or x.get("code") is not None)
                ]
                counts = await apply_snapshot(session, DictionaryItem, records)
            elif name == "areas":
                counts = await apply_snapshot(session, Area, flatten(await client.areas()))
            elif name == "countries":
                counts = await apply_snapshot(
                    session,
                    Country,
                    [{"hh_id": str(x["id"]), "name": str(x["name"])} for x in await client.countries()],
                )
            elif name == "industries":
                counts = await apply_snapshot(session, Industry, flatten(await client.industries()))
            elif name == "languages":
                counts = await apply_snapshot(
                    session,
                    Language,
                    [{"hh_id": str(x["id"]), "name": str(x["name"])} for x in await client.languages()],
                )
            elif name == "professional_roles":
                payload = await client.professional_roles()
                cats = [{"hh_id": str(c["id"]), "name": str(c["name"])} for c in payload["categories"]]
                category_counts = await apply_snapshot(session, ProfessionalRoleCategory, cats)
                await session.flush()
                records = [
                    {"hh_id": str(x["id"]), "name": str(x["name"]), "category_hh_id": str(c["id"])}
                    for c in payload["categories"]
                    for x in c["roles"]
                ]
                role_counts = await apply_snapshot(session, ProfessionalRole, records)
                counts = merge_counts(category_counts, role_counts)
            elif name == "metro":
                cities = await client.metro()
                city_counts = await apply_snapshot(
                    session, MetroCity, [{"hh_id": str(c["id"]), "name": str(c["name"])} for c in cities]
                )
                await session.flush()
                lines = []
                stations = []
                for c in cities:
                    detail = await client.metro_city(str(c["id"]))
                    for line in detail.get("lines", []):
                        lines.append({"hh_id": str(line["id"]), "name": str(line["name"]), "city_hh_id": str(c["id"])})
                        stations += [
                            {
                                "hh_id": str(s["id"]),
                                "name": str(s["name"]),
                                "line_hh_id": str(line["id"]),
                                "lat": str(s.get("lat")) if s.get("lat") is not None else None,
                                "lng": str(s.get("lng")) if s.get("lng") is not None else None,
                                "order": s.get("order"),
                            }
                            for s in line.get("stations", [])
                        ]
                line_counts = await apply_snapshot(session, MetroLine, lines)
                await session.flush()
                station_counts = await apply_snapshot(session, MetroStation, stations)
                counts = merge_counts(city_counts, line_counts, station_counts)
            success_state = await session.scalar(select(SyncState).where(SyncState.name == name))
            if success_state is None:
                raise RuntimeError("Состояние синхронизации не найдено")
            finished = datetime.now(UTC)
            success_state.status = "success"
            success_state.last_success_at = finished
            success_state.last_attempt_finished_at = finished
            success_state.last_error = None
            await session.commit()
        log.info(
            "dictionary_sync name=%s result=success duration_ms=%d counts=%s",
            name,
            int((monotonic() - started) * 1000),
            counts,
        )
    except Exception as exc:
        async with SessionFactory() as session:
            state = await session.scalar(select(SyncState).where(SyncState.name == name))
            if state is None:
                raise RuntimeError("Состояние синхронизации не найдено") from exc
            state.status = "failed"
            state.last_attempt_finished_at = datetime.now(UTC)
            state.last_error = type(exc).__name__
            await session.commit()
        log.error(
            "dictionary_sync name=%s result=failed duration_ms=%d error=%s",
            name,
            int((monotonic() - started) * 1000),
            type(exc).__name__,
        )
        raise


@celery_app.task(name="vacancy.sync_dictionary")
def sync_dictionary(name: str):
    lock = Redis.from_url(str(settings.dictionary_lock_url)).lock(
        f"vacancy:dictionary:{name}", timeout=settings.dictionary_lock_ttl_seconds, blocking=False
    )
    if not lock.acquire():
        return {"status": "locked"}
    try:

        async def run() -> None:
            try:
                await _sync(name)
            finally:
                await close_database()

        asyncio.run(run())
        return {"status": "success"}
    finally:
        try:
            lock.release()
        except LockNotOwnedError:
            log.warning("dictionary_lock result=expired name=%s", name)


@celery_app.task(name="vacancy.check_dictionaries")
def check_dictionaries():
    async def get_due():
        try:
            async with SessionFactory() as session:
                return await due_dictionaries(session, max_age_hours=settings.dictionary_max_age_hours)
        finally:
            await close_database()

    due = asyncio.run(get_due())
    for name in due:
        sync_dictionary.delay(name)
    return due


def merge_counts(*values: dict[str, int]) -> dict[str, int]:
    return {key: sum(value.get(key, 0) for value in values) for key in ("inserted", "updated", "deactivated")}
