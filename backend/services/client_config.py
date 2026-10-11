"""
Loads client-specific config from clients/<client_id>/ at runtime. Nothing in
this module (or anything it's called from) should hard-code a client id,
dimension name, or framework name — see CLAUDE.md's amended hard constraints.
"""
from functools import lru_cache
from pathlib import Path

import yaml

from core.config import get_settings
from services.scoring_schema import ScoringConfig

CLIENTS_DIR = Path(__file__).resolve().parent.parent / "clients"


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


def load_report_template(client_id: str | None = None) -> str:
    path = client_dir(client_id) / "report" / "template.html"
    if not path.is_file():
        raise FileNotFoundError(f"No report template at {path}")
    return path.read_text()
