import pytest

from app.adapters.registry import Registry


def test_get_builds_once_and_caches() -> None:
    reg: Registry[object] = Registry("thing")
    reg.register("a", object)
    assert reg.get("a") is reg.get("a")


def test_unknown_name_lists_known() -> None:
    reg: Registry[object] = Registry("thing")
    reg.register("a", object)
    with pytest.raises(LookupError, match="known: a"):
        reg.get("b")


def test_duplicate_registration_rejected() -> None:
    reg: Registry[object] = Registry("thing")
    reg.register("a", object)
    with pytest.raises(ValueError, match="already registered"):
        reg.register("a", object)
