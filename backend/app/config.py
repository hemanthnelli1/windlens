import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def load_project_env() -> None:
    """Load a simple root .env file without replacing real environment values."""
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    """Environment-backed configuration with safe local defaults."""

    app_name: str = "WindLens API"
    bmrs_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    request_timeout_seconds: float = 20.0
    cache_ttl_seconds: int = 21600
    default_cutoff_hour_local: int = 12
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    load_project_env()
    return Settings(
        app_name=os.getenv("APP_NAME", "WindLens API"),
        bmrs_base_url=os.getenv("BMRS_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1").rstrip("/"),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "21600")),
        default_cutoff_hour_local=int(os.getenv("DEFAULT_CUTOFF_HOUR_LOCAL", "12")),
        allowed_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"),
    )
