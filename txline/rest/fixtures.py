"""REST client for fixture snapshots — GET /api/fixtures/snapshot."""

import logging
from typing import Optional

import httpx

from txline.models import Fixture

logger = logging.getLogger(__name__)

FIXTURES_URL = "https://txline.txodds.com/api/fixtures/snapshot"


async def get_fixtures(
    client: httpx.AsyncClient,
    jwt: str,
    api_token: str,
    start_epoch_day: Optional[int] = None,
    competition_id: Optional[int] = None,
) -> list[Fixture]:
    headers = {
        "Authorization": f"Bearer {jwt}",
        "X-Api-Token": api_token,
    }
    params = {}
    if start_epoch_day is not None:
        params["startEpochDay"] = str(start_epoch_day)
    if competition_id is not None:
        params["competitionId"] = str(competition_id)

    resp = await client.get(FIXTURES_URL, headers=headers, params=params)
    resp.raise_for_status()
    return [Fixture(**item) for item in resp.json()]
