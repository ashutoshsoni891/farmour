"""Operator commands: `uv run python -m app.cli make-admin <email>`."""

import argparse
import asyncio

from app.db.session import get_sessionmaker
from app.modules.identity.service import grant_admin_by_email
from app.modules.library.service import load_seed
from app.modules.site import service as site_service


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


async def _load_site_data() -> int:
    async with get_sessionmaker()() as session:
        print(await site_service.load_seed(session))
        await session.commit()
    return 0


async def _ingest_mandi() -> int:
    async with get_sessionmaker()() as session:
        print(await site_service.ingest_mandi_prices(session))
        await session.commit()
    return 0


async def _build_profile(farm_id: str) -> int:
    import uuid

    async with get_sessionmaker()() as session:
        print(await site_service.build_profile(session, uuid.UUID(farm_id)))
        await session.commit()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    admin = sub.add_parser("make-admin", help="grant admin to an existing user by email")
    admin.add_argument("email")
    sub.add_parser("load-library", help="load bundled crop/recipe/rule seeds as drafts")
    sub.add_parser("load-site-data", help="load curated district -> region lookups")
    sub.add_parser("ingest-mandi", help="pull Agmarknet prices now (needs DATA_GOV_IN_API_KEY)")
    build = sub.add_parser("build-site-profile", help="build a farm's site profile now")
    build.add_argument("farm_id")
    args = parser.parse_args()
    if args.cmd == "make-admin":
        return asyncio.run(_make_admin(args.email))
    if args.cmd == "load-library":
        return asyncio.run(_load_library())
    if args.cmd == "load-site-data":
        return asyncio.run(_load_site_data())
    if args.cmd == "ingest-mandi":
        return asyncio.run(_ingest_mandi())
    if args.cmd == "build-site-profile":
        return asyncio.run(_build_profile(args.farm_id))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
