import json
from functools import lru_cache
from pathlib import Path

_SECTORS_FILE = Path(__file__).resolve().parent.parent / "config" / "sectors.json"


@lru_cache()
def get_sectors() -> list[str]:
    """Neutral, swappable sector list. Not client-specific — see hard constraint 3."""
    return json.loads(_SECTORS_FILE.read_text())
