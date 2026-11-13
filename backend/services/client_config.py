"""
Loads client-specific config from clients/<client_id>/ at runtime. Nothing in
this module (or anything it's called from) should hard-code a client id,
dimension name, or framework name — see CLAUDE.md's amended hard constraints.
"""
import json
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

from core.config import get_settings
from services.scoring_schema import ScoringConfig

CLIENTS_DIR = Path(__file__).resolve().parent.parent / "clients"


class Theme(BaseModel):
    product_name: str = "Founder Funnel"
    primary: str = "#2C5282"
    secondary: str = "#15151a"
    accent: str = "#2C5282"
    background: str = "#0A0A0B"
    text: str = "#FFFFFF"
    font_family: str = "Inter"
    logo_path: str | None = None
    footer_text: str | None = None
    # Resolved at load time, not stored in theme.json: None if logo_path is unset,
    # or if it is set but the file isn't actually on disk (dropped locally, gitignored).
    logo_url: str | None = None


def get_client_id() -> str:
    """CLIENT_ID env var, defaulting to the neutral demo config."""
    return get_settings().client_id or "demo"


def client_dir(client_id: str | None = None) -> Path:
    return CLIENTS_DIR / (client_id or get_client_id())


def list_frameworks(client_id: str | None = None) -> list[str]:
    scoring_dir = client_dir(client_id) / "scoring"
    if not scoring_dir.is_dir():
        return []
    return sorted(p.stem for p in scoring_dir.glob("*.yaml"))


@lru_cache()
def load_scoring_config(client_id: str | None = None, framework_id: str | None = None) -> ScoringConfig:
    resolved_client = client_id or get_client_id()
    frameworks = list_frameworks(resolved_client)

    if framework_id is None:
        if len(frameworks) != 1:
            raise ValueError(
                f"Client {resolved_client!r} has {len(frameworks)} scoring frameworks "
                f"({frameworks}); pass framework_id explicitly."
            )
        framework_id = frameworks[0]
    elif framework_id not in frameworks:
        raise ValueError(f"Client {resolved_client!r} has no framework {framework_id!r}. Available: {frameworks}")

    path = client_dir(resolved_client) / "scoring" / f"{framework_id}.yaml"
    raw = yaml.safe_load(path.read_text())
    return ScoringConfig.model_validate(raw)


@lru_cache()
def load_theme(client_id: str | None = None) -> Theme:
    resolved_client = client_id or get_client_id()
    path = client_dir(resolved_client) / "theme.json"
    if not path.is_file():
        return Theme()  # neutral defaults — never crash the app over a missing theme file

    theme = Theme.model_validate(json.loads(path.read_text()))
    if theme.logo_path:
        logo_file = client_dir(resolved_client) / "assets" / theme.logo_path
        if logo_file.is_file():
            theme.logo_url = f"/client-assets/{resolved_client}/{theme.logo_path}"
    return theme


def load_report_template(client_id: str | None = None) -> str:
    path = client_dir(client_id) / "report" / "template.html"
    if not path.is_file():
        raise FileNotFoundError(f"No report template at {path}")
    return path.read_text()
