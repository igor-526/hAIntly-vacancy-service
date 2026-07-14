import pytest
from pydantic import ValidationError

from infrastructure.hh_schemas import AreaList, Dictionaries, MetroCity, ProfessionalRoles
from tasks import merge_counts


def test_nested_area_requires_complete_child() -> None:
    with pytest.raises(ValidationError):
        AreaList.model_validate([{"id": "1", "name": "root", "areas": [{"id": "2"}]}])


def test_professional_roles_reject_empty_nested_roles() -> None:
    with pytest.raises(ValidationError):
        ProfessionalRoles.model_validate({"categories": [{"id": "1", "name": "x", "roles": []}]})


def test_metro_rejects_incomplete_station() -> None:
    with pytest.raises(ValidationError):
        MetroCity.model_validate(
            {"id": "1", "name": "city", "lines": [{"id": "l", "name": "line", "stations": [{"id": "s"}]}]}
        )


def test_dictionary_supports_currency_and_license_shapes() -> None:
    parsed = Dictionaries.model_validate({"currency": [{"code": "RUR", "name": "Рубли"}], "licenses": [{"id": "B"}]})
    assert parsed.root["currency"][0].code == "RUR"


def test_counts_include_all_nested_tables() -> None:
    assert merge_counts(
        {"inserted": 2, "updated": 1, "deactivated": 0},
        {"inserted": 3, "updated": 0, "deactivated": 4},
    ) == {"inserted": 5, "updated": 1, "deactivated": 4}
