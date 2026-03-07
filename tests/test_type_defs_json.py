import pytest


def test_is_json_value_accepts_nested_structures() -> None:
    from src.type_defs import is_json_value

    value = {
        "name": "alfred",
        "count": 3,
        "active": True,
        "meta": {"tags": ["memory", "cron"], "score": 1.5},
        "items": [1, 2, 3, {"ok": None}],
    }

    assert is_json_value(value) is True


def test_is_json_value_rejects_invalid_types() -> None:
    from src.type_defs import is_json_value

    assert is_json_value({"bad": {1, 2}}) is False
    assert is_json_value({"bytes": b"nope"}) is False


def test_ensure_json_object_returns_dict() -> None:
    from src.type_defs import ensure_json_object

    value = {"ok": "yes", "count": 2}
    assert ensure_json_object(value) == value


def test_ensure_json_object_raises_for_non_dict() -> None:
    from src.type_defs import ensure_json_object

    with pytest.raises(TypeError):
        ensure_json_object(["nope"])


def test_ensure_json_object_raises_for_invalid_values() -> None:
    from src.type_defs import ensure_json_object

    with pytest.raises(TypeError):
        ensure_json_object({"bad": {"nope"}})
