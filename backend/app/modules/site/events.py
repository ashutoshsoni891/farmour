"""Events published and consumed by the site module.

Published: none.
Consumed: `parcel.saved` -> queue a site profile build (the build runs in a worker).
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import Event, subscribe
from app.modules.site import service


@subscribe("parcel.saved", "site.build_profile")
async def on_parcel_saved(_: AsyncSession, event: Event) -> None:
    service.queue_build(uuid.UUID(event.payload["farm_id"]))
