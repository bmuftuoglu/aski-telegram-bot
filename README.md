# aski-water-watch

ASKİ (Ankara Su ve Kanalizasyon İdaresi) su kesintisi sayfasını periyodik olarak kontrol eden HTTP servisi. Belirlenen ilçe ve mahalle için kesinti başladığında veya sona erdiğinde bir gateway'e bildirim gönderir.

[telegram-home-server](https://github.com/bmuftuoglu/telegram-home-server) ile birlikte kullanılmak üzere tasarlanmıştır.

```
ASKİ sitesi
    ↓ (her 1 saat, varsayılan)
aski-water-watch  ──POST /notify──▶  telegram-home-server  ──▶  Telegram
```

## Gereksinimler

- [Docker](https://docs.docker.com/get-docker/) ve [Docker Compose](https://docs.docker.com/compose/install/)
- Çalışan bir [telegram-home-server](https://github.com/bmuftuoglu/telegram-home-server)
- `homebot` adlı Docker network (home server kurulumunda oluşturulur)

## Kurulum

### 1. Yapılandırma dosyasını oluştur

```bash
cp .env.example .env
```

`.env` dosyasını açıp şu değerleri doldur:

```env
INTERNAL_API_TOKEN=home_server_ile_ayni_token
ASKI_TARGET_DISTRICT=ÇANKAYA
ASKI_TARGET_NEIGHBORHOOD=Mahalle Adı
```

`INTERNAL_API_TOKEN`, `telegram-home-server`'daki `.env`'deki değerle aynı olmalıdır.

### 2. Başlat

```bash
docker compose up --build -d
```

## API

Tüm endpoint'ler `Authorization: Bearer $INTERNAL_API_TOKEN` header'ı gerektirir (`/health` hariç).

| Endpoint | Açıklama |
| --- | --- |
| `GET /health` | Servis sağlık kontrolü |
| `GET /status` | Son kontrol durumunu döner |
| `POST /check` | Manuel kontrol başlatır |

`GET /status` örnek yanıt:

```json
{
  "lastCheckedAt": "2026-05-19T12:00:00+00:00",
  "lastError": null,
  "lastMatch": {
    "district": "İLÇE_ADI",
    "faultDate": "19.05.2026 09:20:00",
    "repairDate": "19.05.2026 18:00:00",
    "affectedPlaces": "Mahalle Adı"
  }
}
```

## Ortam Değişkenleri

| Değişken | Varsayılan | Açıklama |
| --- | --- | --- |
| `INTERNAL_API_TOKEN` | zorunlu | Gateway ile paylaşılan gizli token. |
| `ASKI_TARGET_DISTRICT` | zorunlu | Takip edilecek ilçe (büyük harf, örn. `ÇANKAYA`). |
| `ASKI_TARGET_NEIGHBORHOOD` | zorunlu | Takip edilecek mahalle adı. |
| `GATEWAY_NOTIFY_URL` | `http://telegram-bot-gateway:8080/notify` | Bildirimlerin gönderileceği URL. |
| `ASKI_URL` | ASKİ kesinti sayfası | Değiştirme gerekmez. |
| `CHECK_INTERVAL_SECONDS` | `600` | Kontrol aralığı (saniye). |
| `ASKI_NOTIFY_EVERY_CHECK` | `false` | `true` yapılırsa her kontrolde bildirim gönderir. |

## Testler

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```
