"""Configuration for the single supported scientific dataset."""

import os
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_PATH = REPOSITORY_ROOT / "data/raw/giovanni_merra2_gambia_t2m_1991_2025.csv"
EXPECTED_START = date(1991, 1, 1)
EXPECTED_END = date(2025, 12, 1)
VALUE_COLUMN = "mean_M2IMNXASM_5_12_4_T2M"
FILL_VALUE = 1_000_000_000_000_000.0
DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def data_path() -> Path:
    """Read environment at app creation; never depend on the launch directory."""
    path = Path(os.environ.get("EARTHSCOPE_DATA_PATH", str(DEFAULT_DATA_PATH))).expanduser()
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def cors_origins() -> tuple[str, ...]:
    """An explicit environment list replaces local defaults; empty disables CORS."""
    configured = os.environ.get("EARTHSCOPE_CORS_ORIGINS")
    if configured is None:
        return DEFAULT_CORS_ORIGINS
    if not configured.strip():
        return ()
    origins = tuple(dict.fromkeys(item.strip() for item in configured.split(",")))
    for origin in origins:
        try:
            parsed = urlsplit(origin)
            if (
                not origin.isascii()
                or any(char.isspace() or ord(char) < 32 for char in origin)
                or "*" in origin
                or parsed.scheme not in ("http", "https")
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError
            _ = parsed.port  # Validate malformed/out-of-range ports as well.
        except ValueError as exc:
            raise ValueError(
                "EARTHSCOPE_CORS_ORIGINS must be a comma-separated list of exact HTTP(S) "
                "origins (scheme://host[:port]); wildcards, paths and credentials are forbidden."
            ) from exc
    return origins
