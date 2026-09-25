"""Runtime settings, read from environment variables once at startup."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    bing_api_key: str | None
    data_dir: Path
    min_delay: float
    proxy: str | None
    cache_ttl_days: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            bing_api_key=os.environ.get("FREE_SEO_BING_API_KEY") or None,
            data_dir=Path(os.environ.get("FREE_SEO_DATA_DIR", "./seo-data")).expanduser(),
            min_delay=float(os.environ.get("FREE_SEO_MIN_DELAY", "0.4")),
            proxy=os.environ.get("FREE_SEO_PROXY") or None,
            cache_ttl_days=float(os.environ.get("FREE_SEO_CACHE_TTL_DAYS", "7")),
        )
