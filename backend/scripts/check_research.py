"""Check pass for AI research files (seeds/library/research/crops/*.json).

For every cited source, open the page and confirm the quoted sentence is really on it. Found ->
`checked_on` is set to today; not found -> `checked_on` is removed, so the loader keeps the crop a
draft. Pages that only render with JavaScript cannot be read here; they are listed as "manual"
and must be confirmed another way (then set `checked_on` by hand with --confirm URL).

    uv run python -m scripts.check_research [--confirm URL ...]
"""

import argparse
import html
import json
import re
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

FOLDER = Path(__file__).resolve().parents[1] / "seeds" / "library" / "research" / "crops"
MIN_TEXT = 500  # shorter page text means the page needs JavaScript


def _norm(text: str) -> str:
    text = html.unescape(text).replace("­", "")  # soft hyphens
    return re.sub(r"\s+", " ", text).strip()


def _page_text(url: str, cache: dict[str, str]) -> str:
    if url not in cache:
        if not url.startswith("https://"):
            return ""
        req = urllib.request.Request(  # noqa: S310 (https only, checked above)
            url, headers={"User-Agent": "Mozilla/5.0 (farmour research)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:  # noqa: S310 (cited https urls)
                raw = resp.read().decode("utf-8", "replace")
        except OSError:
            raw = ""
        raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
        cache[url] = _norm(re.sub(r"<[^>]+>", " ", raw))
    return cache[url]


def _sources(data: dict[str, Any]) -> list[dict[str, Any]]:
    found = [s for entries in (data.get("sources") or {}).values() for s in entries]
    for region in (data.get("regional") or {}).values():
        found += [s for entries in (region.get("sources") or {}).values() for s in entries]
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", nargs="*", default=[], help="URLs confirmed by hand")
    args = parser.parse_args()
    today, cache = date.today().isoformat(), {}  # type: ignore[var-annotated]
    manual: set[str] = set()
    for path in sorted(FOLDER.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        ok = bad = 0
        for src in _sources(data):
            url, quote = src.get("url"), src.get("quote")
            if not url or not quote:
                src.pop("checked_on", None)
                bad += 1
                continue
            if url in args.confirm:
                src["checked_on"] = today
                ok += 1
                continue
            text = _page_text(url, cache)
            if len(text) < MIN_TEXT:
                manual.add(url)
                if "checked_on" not in src:
                    bad += 1
                continue
            if _norm(quote) in text:
                src["checked_on"] = today
                ok += 1
            else:
                src.pop("checked_on", None)
                print(f"  NOT FOUND {path.stem}: {quote!r} at {url}")
                bad += 1
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{path.stem}: {ok} confirmed, {bad} not confirmed")
    for url in sorted(manual):
        print(f"manual: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
