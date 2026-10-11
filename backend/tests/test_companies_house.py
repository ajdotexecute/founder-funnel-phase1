import httpx
import pytest

from core.config import get_settings
from services import companies_house


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    async def instant_sleep(_seconds):
        return None

    monkeypatch.setattr(companies_house.asyncio, "sleep", instant_sleep)


async def test_no_api_key_skips_lookup_without_network_call(monkeypatch):
    monkeypatch.setenv("COMPANIES_HOUSE_API_KEY", "")
    get_settings.cache_clear()

    called = False

    async def fail_if_called(self, *a, **kw):
        nonlocal called
        called = True

    monkeypatch.setattr(httpx.AsyncClient, "get", fail_if_called)

    result = await companies_house.lookup_company("SC123456")

    assert result is None
    assert not called
    get_settings.cache_clear()


async def test_successful_lookup_parses_fields(monkeypatch):
    monkeypatch.setenv("COMPANIES_HOUSE_API_KEY", "test-key")
    get_settings.cache_clear()

    async def fake_get(self, url, **kwargs):
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=request,
            json={"company_status": "active", "date_of_creation": "2020-01-01", "sic_codes": ["62012"]},
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = await companies_house.lookup_company("SC123456")

    assert result.status == "active"
    assert result.incorporation_date == "2020-01-01"
    assert result.sic_codes == ["62012"]
    get_settings.cache_clear()


async def test_404_returns_none(monkeypatch):
    monkeypatch.setenv("COMPANIES_HOUSE_API_KEY", "test-key")
    get_settings.cache_clear()

    async def fake_get(self, url, **kwargs):
        return httpx.Response(404, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    assert await companies_house.lookup_company("SC123456") is None
    get_settings.cache_clear()


async def test_retries_on_5xx_then_succeeds(monkeypatch):
    monkeypatch.setenv("COMPANIES_HOUSE_API_KEY", "test-key")
    get_settings.cache_clear()

    attempts = {"count": 0}

    async def flaky_get(self, url, **kwargs):
        attempts["count"] += 1
        request = httpx.Request("GET", url)
        if attempts["count"] < 2:
            return httpx.Response(503, request=request)
        return httpx.Response(200, request=request, json={"company_status": "active", "date_of_creation": None, "sic_codes": []})

    monkeypatch.setattr(httpx.AsyncClient, "get", flaky_get)

    result = await companies_house.lookup_company("SC123456")

    assert result.status == "active"
    assert attempts["count"] == 2
    get_settings.cache_clear()


async def test_gives_up_after_max_retries_returns_none(monkeypatch):
    monkeypatch.setenv("COMPANIES_HOUSE_API_KEY", "test-key")
    get_settings.cache_clear()

    async def always_503(self, url, **kwargs):
        return httpx.Response(503, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", always_503)

    assert await companies_house.lookup_company("SC123456") is None
    get_settings.cache_clear()
