from app.core.i18n import LANGS, catalogue, t


def test_every_key_exists_in_every_language() -> None:
    keys = {lang: set(catalogue(lang)) for lang in LANGS}
    assert keys["en"] == keys["hi"]


def test_no_empty_strings() -> None:
    for lang in LANGS:
        assert all(v.strip() for v in catalogue(lang).values())


def test_translate_formats_params() -> None:
    assert "https://x" in t("auth.login_link", "hi", url="https://x", minutes=15)
    assert "15" in t("auth.login_link", "en", url="https://x", minutes=15)


def test_unknown_key_falls_back_to_key() -> None:
    assert t("no.such.key", "hi") == "no.such.key"
