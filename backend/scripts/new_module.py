"""Scaffold a module in the spec section 16 shape: `make new-module NAME=x`.

Creates api.py, service.py, schemas.py, repository.py, models.py, events.py, README.md and
tests/, and appends an import-linter contract so no other module can use its tables.
Registering the router in app/api/router.py and adding models to the Alembic env are printed
as next steps (they need a human decision on URL prefix and tables).
"""

import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

FILES = {
    "__init__.py": "",
    "api.py": '''"""Routes for the {name} module."""

from fastapi import APIRouter

router = APIRouter(prefix="/{name}", tags=["{name}"])
''',
    "service.py": '''"""Public entry point of the {name} module; other modules call only this."""
''',
    "schemas.py": '''"""Pydantic v2 contracts for the {name} module."""
''',
    "repository.py": '''"""Database access for the {name} module. Only this module imports it."""
''',
    "models.py": '''"""Tables owned by the {name} module."""
''',
    "events.py": '''"""Events published and consumed by the {name} module.

Published: none yet.
Consumed: none yet.
"""
''',
    "README.md": """# {name}

**Purpose:** TODO

**Owns tables:** none yet.

**Public service functions** (`service.py`): none yet.

**Events:** publishes none; consumes none.

**Settings used:** none.
""",
    "tests/__init__.py": "",
}

CONTRACT = """
[[tool.importlinter.contracts]]
name = "Module {name} owns its tables"
type = "protected"
protected_modules = ["app.modules.{name}.repository", "app.modules.{name}.models"]
allowed_importers = ["app.modules.{name}"]
"""


def main(name: str) -> int:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        print("NAME must be lowercase snake_case")
        return 1
    root = BACKEND / "app" / "modules" / name
    if root.exists():
        print(f"{root} already exists")
        return 1
    for rel, content in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.format(name=name))
    pyproject = BACKEND / "pyproject.toml"
    pyproject.write_text(pyproject.read_text() + CONTRACT.format(name=name))
    print(f"created app/modules/{name}/ and its import-linter contract")
    print("next: include its router in app/api/router.py, import its models in")
    print("app/db/migrations/env.py, then use the write-migration skill for tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
