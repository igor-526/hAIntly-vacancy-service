import pytest

import main


@pytest.mark.asyncio
async def test_lifespan_seeds_before_readiness_and_cleans_up(monkeypatch) -> None:
    events = []

    async def seed():
        events.append("seed")

    async def close():
        events.append("close")

    monkeypatch.setattr(main, "seed_dictionary_sync_states", seed)
    monkeypatch.setattr(main, "close_database", close)
    async with main.lifespan(main.app):
        events.append("ready")
    assert events == ["seed", "ready", "close"]


@pytest.mark.asyncio
async def test_lifespan_seed_failure_prevents_readiness_and_cleans_up(monkeypatch) -> None:
    events = []

    async def seed():
        events.append("seed")
        raise RuntimeError("schema")

    async def close():
        events.append("close")

    monkeypatch.setattr(main, "seed_dictionary_sync_states", seed)
    monkeypatch.setattr(main, "close_database", close)
    with pytest.raises(RuntimeError, match="schema"):
        async with main.lifespan(main.app):
            events.append("ready")
    assert events == ["seed", "close"]
