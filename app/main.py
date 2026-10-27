from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response

from .config import Settings
from .parser import ParseError, parse_schedule
from .storage import Storage


LOGGER = logging.getLogger("whatsapp_arbeitswecker")


def _texts(payload: dict[str, Any]) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []) or []:
                if message.get("type") == "text":
                    result.append((str(message.get("id", "")), str(message.get("from", "")), str(message.get("text", {}).get("body", ""))))
    return result


def create_app(settings: Settings | None = None, storage: Storage | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    storage = storage or Storage(settings.database_path)
    app = FastAPI(title="WhatsApp-Arbeitswecker", version="1.0.0", docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/webhook")
    async def verify_webhook(
        hub_mode: str = Query(alias="hub.mode"),
        hub_verify_token: str = Query(alias="hub.verify_token"),
        hub_challenge: str = Query(alias="hub.challenge"),
    ) -> Response:
        if hub_mode != "subscribe" or not hmac.compare_digest(hub_verify_token, settings.meta_verify_token):
            raise HTTPException(status_code=403, detail="Webhook-Verifizierung abgelehnt")
        return Response(content=hub_challenge, media_type="text/plain")

    @app.post("/webhook", status_code=200)
    async def receive_webhook(request: Request, x_hub_signature_256: str = Header(default="")) -> dict[str, str]:
        body = await request.body()
        expected = "sha256=" + hmac.new(settings.meta_app_secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Ungültige Webhook-Signatur")
        payload = await request.json()
        for message_id, sender, text in _texts(payload):
            if not message_id or storage.seen(message_id):
                continue
            if "".join(filter(str.isdigit, sender)) != settings.allowed_sender_wa_id:
                storage.record_message(message_id, sender, "ignored", "Absender nicht freigegeben")
                continue
            try:
                entries = parse_schedule(text, timezone=settings.timezone)
                storage.upsert_entries(entries, message_id)
                storage.record_message(message_id, sender, "accepted", f"{len(entries)} Einträge")
                if settings.ha_webhook_url:
                    async with httpx.AsyncClient(timeout=settings.ha_webhook_timeout_seconds) as client:
                        response = await client.post(settings.ha_webhook_url, json=storage.schedule())
                        response.raise_for_status()
            except ParseError as error:
                storage.record_message(message_id, sender, "rejected", str(error))
                LOGGER.warning("Nachricht %s konnte nicht ausgewertet werden: %s", message_id, error)
            except httpx.HTTPError as error:
                LOGGER.error("Home-Assistant-Webhook fehlgeschlagen: %s", error)
        return {"status": "received"}

    @app.get("/api/schedule")
    async def get_schedule(authorization: str = Header(default="")) -> dict[str, object]:
        expected = f"Bearer {settings.bridge_api_key}"
        if not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="Nicht autorisiert")
        return storage.schedule()

    return app
