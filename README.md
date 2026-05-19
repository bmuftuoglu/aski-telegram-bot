# aski-water-watch

> **Türkçe dokümantasyon için aşağıya bakın / Turkish documentation is available below.**

An HTTP service that periodically checks the ASKİ (Ankara Water and Sewerage Administration) outage page and notifies a gateway when a water outage starts or ends for a configured district and neighborhood.

Designed to work with [telegram-home-server](https://github.com/bmuftuoglu/telegram-home-server).

```
ASKİ website
    ↓ (every 5 min, default)
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
| `CHECK_INTERVAL_SECONDS` | `300` | Check interval in seconds. |
| `ASKI_NOTIFY_EVERY_CHECK` | `false` | If `true`, sends a notification on every check. |

## Tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

---

## Türkçe Dokümantasyon

ASKİ (Ankara Su ve Kanalizasyon İdaresi) su kesintisi sayfasını periyodik olarak kontrol eden HTTP servisi. Belirlenen ilçe ve mahalle için kesinti başladığında veya sona erdiğinde bir gateway'e bildirim gönderir.

[telegram-home-server](https://github.com/bmuftuoglu/telegram-home-server) ile birlikte kullanılmak üzere tasarlanmıştır.

```
ASKİ sitesi
    ↓ (her 5 dakika, varsayılan)
aski-water-watch  ──POST /notify──▶  telegram-home-server  ──▶  Telegram
```

### Gereksinimler

- [Docker](https://docs.docker.com/get-docker/) ve [Docker Compose](https://docs.docker.com/compose/install/)
- Çalışan bir [telegram-home-server](https://github.com/bmuftuoglu/telegram-home-server)
- `homebot` adlı Docker network (home server kurulumunda oluşturulur)

### Kurulum

**1. Yapılandırma dosyasını oluştur**

```bash
cp .env.example .env
```

Şu değerleri doldur:

```env
INTERNAL_API_TOKEN=home_server_ile_ayni_token
ASKI_TARGET_DISTRICT=ÇANKAYA
ASKI_TARGET_NEIGHBORHOOD=Mahalle Adı
```

`INTERNAL_API_TOKEN`, `telegram-home-server`'daki `.env`'deki değerle aynı olmalıdır.

**2. Başlat**

```bash
docker compose up --build -d
```

### Telegram Komutları

Bu servis çalıştığında `telegram-home-server`'a aşağıdaki komutlar otomatik olarak eklenir:

| Komut | Açıklama |
| --- | --- |
| `/aski_durum` | Son kontrol durumunu göster |
| `/aski_kontrol` | Manuel kontrol başlat |

### API

Tüm endpoint'ler `Authorization: Bearer $INTERNAL_API_TOKEN` header'ı gerektirir (`/health` hariç).

| Endpoint | Açıklama |
| --- | --- |
| `GET /health` | Servis sağlık kontrolü |
| `GET /status` | Son kontrol durumunu döner |
| `POST /check` | Manuel kontrol başlatır |

### Ortam Değişkenleri

| Değişken | Varsayılan | Açıklama |
| --- | --- | --- |
| `INTERNAL_API_TOKEN` | zorunlu | Gateway ile paylaşılan gizli token. |
| `ASKI_TARGET_DISTRICT` | zorunlu | Takip edilecek ilçe (büyük harf, örn. `ÇANKAYA`). |
| `ASKI_TARGET_NEIGHBORHOOD` | zorunlu | Takip edilecek mahalle adı. |
| `GATEWAY_NOTIFY_URL` | `http://telegram-bot-gateway:8080/notify` | Bildirimlerin gönderileceği URL. |
| `ASKI_URL` | ASKİ kesinti sayfası | Değiştirme gerekmez. |
| `CHECK_INTERVAL_SECONDS` | `300` | Kontrol aralığı (saniye). |
| `ASKI_NOTIFY_EVERY_CHECK` | `false` | `true` yapılırsa her kontrolde bildirim gönderir. |

### Testler

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```
