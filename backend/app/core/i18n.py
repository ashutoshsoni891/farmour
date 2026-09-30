"""Server-side message catalogue for text the backend sends itself (messaging channels).

API responses carry keys, not text. Catalogues: app/core/locales/{en,hi}.json.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

Lang = Literal["en", "hi"]
LANGS: tuple[Lang, ...] = ("en", "hi")
_DIR = Path(__file__).parent / "locales"


@lru_cache
def catalogue(lang: Lang) -> dict[str, str]:
    data: dict[str, str] = json.loads((_DIR / f"{lang}.json").read_text(encoding="utf-8"))
    return data


def t(key: str, lang: Lang, **params: object) -> str:
    """Translate `key`; falls back to English, then to the key itself."""
    text = catalogue(lang).get(key) or catalogue("en").get(key) or key
    return text.format(**params)
