import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.dictionaries import user_context
from settings import Settings
from tasks import flatten


def test_flatten_preserves_hierarchy() -> None:
    assert flatten([{"id": "1", "name": "Root", "areas": [{"id": "2", "name": "Child"}]}]) == [
        {"hh_id": "1", "name": "Root", "parent_hh_id": None},
        {"hh_id": "2", "name": "Child", "parent_hh_id": "1"},
    ]


def test_user_context_requires_uuid() -> None:
    with pytest.raises(HTTPException):
        user_context("invalid")


def test_positive_max_age_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VACANCY_DICTIONARY_MAX_AGE_HOURS", "0")
    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]
