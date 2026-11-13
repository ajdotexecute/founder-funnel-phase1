import httpx
import pytest

import main
from core.config import get_settings
from services.client_config import load_theme


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_get_theme_returns_demo_by_default(client):
    res = await client.get("/api/theme")
    assert res.status_code == 200
    body = res.json()
    assert body["product_name"] == "Founder Funnel"
    assert body["logo_url"] is None


async def test_get_theme_returns_fg_when_client_id_set(client, monkeypatch):
    monkeypatch.setenv("CLIENT_ID", "fg")
    get_settings.cache_clear()
    load_theme.cache_clear()
    try:
        res = await client.get("/api/theme")
        assert res.status_code == 200
        assert res.json()["product_name"] == "Funding Gap Founder Scan"
    finally:
        monkeypatch.delenv("CLIENT_ID", raising=False)
        get_settings.cache_clear()
        load_theme.cache_clear()


async def test_client_asset_404s_when_no_logo_dropped(client):
    res = await client.get("/client-assets/fg/logo.png")
    assert res.status_code == 404


async def test_client_asset_path_traversal_rejected(client):
    res = await client.get("/client-assets/fg/..%2F..%2Fmain.py")
    assert res.status_code in (404, 422)


async def test_client_asset_serves_a_real_dropped_file(client, tmp_path):
    assets_dir = main.CLIENTS_DIR / "fg" / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    test_file = assets_dir / "logo.png"
    test_file.write_bytes(b"\x89PNG\r\n\x1a\nfake png bytes")
    try:
        res = await client.get("/client-assets/fg/logo.png")
        assert res.status_code == 200
        assert res.content == b"\x89PNG\r\n\x1a\nfake png bytes"
    finally:
        test_file.unlink(missing_ok=True)
