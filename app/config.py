from __future__ import annotations

from dataclasses import dataclass
import os


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or (value.startswith("[") and value.endswith("]")):
        raise RuntimeError(f"Pflichtvariable {name} fehlt oder enthält nur einen Platzhalter")
    return value


@dataclass(frozen=True)
class Settings:
    meta_verify_token: str
    meta_app_secret: str
    allowed_sender_wa_id: str
    bridge_api_key: str
    timezone: str
    database_path: str
    ha_webhook_url: str | None
    ha_webhook_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            meta_verify_token=_required("META_VERIFY_TOKEN"),
            meta_app_secret=_required("META_APP_SECRET"),
            allowed_sender_wa_id="".join(filter(str.isdigit, _required("ALLOWED_SENDER_WA_ID"))),
            bridge_api_key=_required("BRIDGE_API_KEY"),
            timezone=os.getenv("TIMEZONE", "Europe/Berlin").strip() or "Europe/Berlin",
            database_path=os.getenv("DATABASE_PATH", "/data/arbeitswecker.db").strip(),
            ha_webhook_url=(os.getenv("HA_WEBHOOK_URL", "").strip() or None),
            ha_webhook_timeout_seconds=float(os.getenv("HA_WEBHOOK_TIMEOUT_SECONDS", "10")),
        )
