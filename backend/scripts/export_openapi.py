"""Write the API contract to backend/openapi.json (the frontend client is generated from it).

CI regenerates it and fails if the committed file differs (spec section 16).
"""

import json
import os
from pathlib import Path

os.environ.setdefault("LINK_SIGNING_SECRET", "x" * 40)

from app.main import create_app  # noqa: E402

out = Path(__file__).resolve().parents[1] / "openapi.json"
out.write_text(json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n")
print(f"wrote {out}")  # noqa: T201
