from __future__ import annotations

import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.storage import Storage


def settings(path: str) -> Settings:
    return Settings(
        meta_verify_token="verify-test",
        meta_app_secret="secret-test",
        allowed_sender_wa_id="491701234567",
        bridge_api_key="bridge-test",
        timezone="Europe/Berlin",
        database_path=path,
        ha_webhook_url=None,
        ha_webhook_timeout_seconds=2,
    )


def signed(body: bytes) -> str:
    return "sha256=" + hmac.new(b"secret-test", body, hashlib.sha256).hexdigest()


def payload(message_id: str = "wamid.1", sender: str = "491701234567") -> dict:
    return {"entry": [{"changes": [{"value": {"messages": [{
        "id": message_id, "from": sender, "type": "text", "text": {"body": "Di 05:30, Mi frei"}
    }]}}]}]}


def test_verify_and_process_and_deduplicate(tmp_path):
    db = tmp_path / "state.db"
    client = TestClient(create_app(settings(str(db)), Storage(str(db))))
    response = client.get("/webhook", params={
        "hub.mode": "subscribe", "hub.verify_token": "verify-test", "hub.challenge": "12345"
    })
    assert response.text == "12345"
    body = json.dumps(payload(), separators=(",", ":")).encode()
    assert client.post("/webhook", content=body, headers={"X-Hub-Signature-256": signed(body)}).status_code == 200
    assert client.post("/webhook", content=body, headers={"X-Hub-Signature-256": signed(body)}).status_code == 200
    schedule = client.get("/api/schedule", headers={"Authorization": "Bearer bridge-test"}).json()
    assert schedule["count"] == 2


def test_rejects_invalid_signature_and_unknown_sender(tmp_path):
    db = tmp_path / "state.db"
    client = TestClient(create_app(settings(str(db)), Storage(str(db))))
    body = json.dumps(payload(sender="499999999999")).encode()
    assert client.post("/webhook", content=body, headers={"X-Hub-Signature-256": "sha256=bad"}).status_code == 401
    assert client.post("/webhook", content=body, headers={"X-Hub-Signature-256": signed(body)}).status_code == 200
    assert client.get("/api/schedule", headers={"Authorization": "Bearer bridge-test"}).json()["count"] == 0
