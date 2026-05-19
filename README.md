# aski-water-watch

An HTTP service that periodically checks the ASKİ (Ankara Water and Sewerage Administration) outage page and notifies a gateway when a water outage starts or ends for a configured district and neighborhood.

Designed to work with [telegram-home-server](https://github.com/bmuftuoglu/telegram-home-server).

```
ASKİ website
    ↓ (every 1 hour, default)
aski-water-watch  ──POST /notify──▶  telegram-home-server  ──▶  Telegram
```

## Requirements

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- A running [telegram-home-server](https://github.com/bmuftuoglu/telegram-home-server)
- A Docker network named `homebot` (created during home server setup)

## Setup

### 1. Create the configuration file

```bash
cp .env.example .env
```

Fill in the values:

```env
INTERNAL_API_TOKEN=same_token_as_in_home_server
ASKI_TARGET_DISTRICT=ÇANKAYA
ASKI_TARGET_NEIGHBORHOOD=Your Neighborhood
```

`INTERNAL_API_TOKEN` must match the value in `telegram-home-server`'s `.env`.

### 2. Start

```bash
docker compose up --build -d
```

## Telegram Commands

When this service is running, the following commands become available in `telegram-home-server`:

| Command | Description |
| --- | --- |
| `/aski_durum` | Show the latest outage status |
| `/aski_kontrol` | Trigger a manual check |

## API

All endpoints require `Authorization: Bearer $INTERNAL_API_TOKEN` (except `/health`).

| Endpoint | Description |
| --- | --- |
| `GET /health` | Health check |
| `GET /status` | Returns the latest check result |
| `POST /check` | Triggers a manual check |

`GET /status` example response:

```json
{
  "lastCheckedAt": "2026-05-19T12:00:00+00:00",
  "lastError": null,
  "lastMatch": {
    "district": "DISTRICT_NAME",
    "faultDate": "19.05.2026 09:20:00",
    "repairDate": "19.05.2026 18:00:00",
    "affectedPlaces": "Neighborhood Name"
  }
}
```

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `INTERNAL_API_TOKEN` | required | Shared secret token with the gateway. |
| `ASKI_TARGET_DISTRICT` | required | District to monitor (uppercase, e.g. `ÇANKAYA`). |
| `ASKI_TARGET_NEIGHBORHOOD` | required | Neighborhood name to monitor. |
| `GATEWAY_NOTIFY_URL` | `http://telegram-bot-gateway:8080/notify` | URL to send notifications to. |
| `ASKI_URL` | ASKİ outage page | No need to change. |
| `CHECK_INTERVAL_SECONDS` | `3600` | Check interval in seconds. |
| `ASKI_NOTIFY_EVERY_CHECK` | `false` | If `true`, sends a notification on every check. |

## Tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```
