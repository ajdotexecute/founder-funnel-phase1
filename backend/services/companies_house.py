"""
UK Companies House lookup (status, incorporation date, SIC codes) for a
number that's already passed format validation (services/file_validation.py).

Never raises for "lookup didn't work" (missing key, network error, 404, rate
limit) — a submission must still complete without this. Only a genuinely
unexpected bug should raise here.
"""
import asyncio
import logging
from dataclasses import dataclass

import httpx

from core.config import get_settings

logger = logging.getLogger("founder_funnel.companies_house")

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 2


@dataclass
class CompanyInfo:
    status: str | None
    incorporation_date: str | None
    sic_codes: list[str]


async def lookup_company(number: str) -> CompanyInfo | None:
    """Returns None if the lookup is unavailable (no API key) or fails after retries."""
    settings = get_settings()
    if not settings.companies_house_api_key:
        logger.info("Companies House lookup skipped: no API key configured.")
        return None

    url = f"{settings.companies_house_base_url}/company/{number}"

    attempt = 0
    async with httpx.AsyncClient(timeout=15.0) as client:
        while True:
            try:
                response = await client.get(url, auth=(settings.companies_house_api_key, ""))
            except httpx.HTTPError as e:
                attempt += 1
                if attempt > MAX_RETRIES:
                    logger.warning("Companies House lookup failed for %s: %s", number, e)
                    return None
                await asyncio.sleep(2**attempt)
                continue

            if response.status_code == 404:
                logger.info("Companies House: no company found for %s", number)
                return None

            if response.status_code in RETRY_STATUS_CODES:
                attempt += 1
                if attempt > MAX_RETRIES:
                    logger.warning(
                        "Companies House lookup failed for %s: HTTP %s", number, response.status_code
                    )
                    return None
                await asyncio.sleep(2**attempt)
                continue

            if response.status_code != 200:
                logger.warning("Companies House lookup failed for %s: HTTP %s", number, response.status_code)
                return None

            body = response.json()
            return CompanyInfo(
                status=body.get("company_status"),
                incorporation_date=body.get("date_of_creation"),
                sic_codes=body.get("sic_codes", []),
            )
