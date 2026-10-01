"""Operator commands: `uv run python -m app.cli make-admin <email>`."""

import argparse
import asyncio

from app.db.session import get_sessionmaker
from app.modules.identity.service import grant_admin_by_email
from app.modules.library.service import load_seed


async def _make_admin(email: str) -> int:
    async with get_sessionmaker()() as session:
        result = await grant_admin_by_email(session, email)
        await session.commit()
    messages = {
        "granted": "granted",
        "not_found": "no user with that verified email (verify it in Keycloak, log in once)",
        "ambiguous": "more than one user has that email; refusing",
    }
    print(messages[result])
    return 0 if result == "granted" else 1


async def _load_library() -> int:
    async with get_sessionmaker()() as session:
        counts = await load_seed(session)
        await session.commit()
    print(counts)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    admin = sub.add_parser("make-admin", help="grant admin to an existing user by email")
    admin.add_argument("email")
    sub.add_parser("load-library", help="load bundled crop/recipe/rule seeds as drafts")
    args = parser.parse_args()
    if args.cmd == "make-admin":
        return asyncio.run(_make_admin(args.email))
    if args.cmd == "load-library":
        return asyncio.run(_load_library())
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
