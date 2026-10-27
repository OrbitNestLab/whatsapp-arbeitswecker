# WhatsApp-Arbeitswecker

Sichere Bridge zwischen der offiziellen WhatsApp Cloud API und Home Assistant. Sie akzeptiert ausschließlich signierte Webhooks von Meta und Arbeitszeiten der freigegebenen WhatsApp-ID von „Günna“. Erkannte Termine werden dedupliziert in SQLite gespeichert und als geschützte REST-Datenstruktur für Home Assistant bereitgestellt.

## Funktionen

- Meta-Webhook-Verifizierung und Prüfung von `X-Hub-Signature-256`
- Absender-Whitelist, Deduplizierung nach WhatsApp-Nachrichten-ID
- Parser für `Di 05:30`, `Fr 13 Uhr`, `27.10 07:15`, `Sa frei` und mehrere Angaben pro Nachricht
- Kein Überschreiben des Plans bei unklaren Nachrichten
- Persistente Speicherung, Healthcheck und geschützte Schedule-API
- Home-Assistant-Package für `sensor.whatsapp_arbeitsplan` und den vorhandenen Weckerskript-Aufruf
- Automatisierte Tests und GitHub Actions

## Schnellstart

```bash
cp .env.example .env
# Platzhalter in .env lokal ersetzen
docker compose up -d --build
curl http://127.0.0.1:8080/health
```

Der Meta-Webhook lautet öffentlich `https://[PUBLIC_BRIDGE_HOST]/webhook`. Nur dieser Pfad muss per HTTPS erreichbar sein. Port `8080` sollte nicht direkt am Router veröffentlicht werden; empfohlen ist ein abgesicherter Reverse Proxy oder Tunnel.

Für Home Assistant:

1. `home_assistant/package_whatsapp_arbeitswecker.yaml` nach `/config/packages/` kopieren.
2. Die Werte aus `home_assistant/secrets.example.yaml` in `/config/secrets.yaml` eintragen.
3. Sicherstellen, dass `homeassistant: packages: !include_dir_named packages` aktiv ist.
4. Konfiguration prüfen und Home Assistant neu laden beziehungsweise einmal kontrolliert neu starten.

Das vorhandene Skript `script.test_arbeitswecker_fire_hd_start` wurde als Ziel übernommen. Die bestehende Entität `sensor.arbeitsplan_marcel` bleibt unverändert; für die neue Quelle entsteht separat `sensor.whatsapp_arbeitsplan`.

## Dokumentation

- [Vollständige technische Anleitung](docs/Anleitung.md)
- [Weitergebbare PDF](docs/WhatsApp_Arbeitswecker_Anleitung.pdf)

## Entwicklung und Tests

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest
```

## Sicherheit

Echte Telefonnummern, App-Secrets, Tokens und URLs gehören ausschließlich in `.env`, Home-Assistant-Secrets oder einen Secret-Store. Die Beispieldateien enthalten nur deutlich markierte Platzhalter. Das Projekt verwendet ausschließlich die offizielle WhatsApp Cloud API und keine Browser-Automatisierung von WhatsApp Web.

## Lizenz

MIT – siehe [LICENSE](LICENSE).
