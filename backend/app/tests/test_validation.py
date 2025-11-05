import pytest

from app.schemas.databases import DatabaseCreateRequest


def test_database_name_validation() -> None:
    payload = DatabaseCreateRequest(name="test_db")
    assert payload.name == "test_db"


def test_database_name_validation_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        DatabaseCreateRequest(name="bad-name")
