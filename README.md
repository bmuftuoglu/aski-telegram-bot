# ASKİ Telegram Water Outage Bot

Ankara Su ve Kanalizasyon İdaresi (ASKİ) su kesintisi duyurularını takip eden, yapılandırılmış ilçe ve mahalle için Telegram bildirimi gönderen Docker tabanlı bir bot.

## Mimari

İki container, aynı Docker Compose ağında çalışır:

- `aski-checker`: ASKİ kesinti sayfasını periyodik olarak çeker, aktif duyuruları parse eder, durumu saklar ve dahili bir HTTP API sunar.
- `telegram-bot`: Telegram komutlarını dinler, durum değiştiğinde abonelere bildirim gönderir.

Telegram bot token'ı yalnızca `telegram-bot` container'ında kullanılır. Git'e asla commit edilmemelidir.

## Kurulum

`.env` dosyasını örnek dosyadan oluşturun:

```bash
cp .env.example .env
```

`.env` dosyasını açıp aşağıdaki değerleri doldurun:

```env
TELEGRAM_BOT_TOKEN=123456789:your_real_token
TARGET_DISTRICT=ÇANKAYA
TARGET_NEIGHBORHOOD=Mahalle Adı
```

`TARGET_DISTRICT` ve `TARGET_NEIGHBORHOOD` zorunludur; boş bırakılırsa uygulama başlamaz.

## Ortam Değişkenleri

| Değişken | Varsayılan | Açıklama |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | zorunlu | BotFather'dan alınan token. |
| `TARGET_DISTRICT` | zorunlu | Eşleştirilecek ilçe adı (büyük harf, örn. `ÇANKAYA`). |
| `TARGET_NEIGHBORHOOD` | zorunlu | Eşleştirilecek mahalle adı. |
| `ASKI_URL` | `https://www.aski.gov.tr/tr/Kesinti.aspx` | ASKİ kesinti sayfası URL'i. |
| `CHECK_INTERVAL_SECONDS` | `600` | ASKİ sayfası kontrol aralığı (saniye). |

## Çalıştırma

```bash
docker compose up --build
```

Telegram'da:

- `/start` — Bildirimlere abone ol
- `/durum` — Son kontrol sonucunu göster
- `/stop` — Aboneliği kapat

Checker API'si Docker ağının dışına açılmaz; yalnızca container'lar arası kullanılır.

## Testler

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Güvenlik

- `.env` dosyasını commit etme.
- `data/` altındaki çalışma zamanı verilerini commit etme.
- Token veya chat ID'yi README, test, ekran görüntüsü veya commit mesajına yazma.
- Token yanlışlıkla push edilirse BotFather'dan hemen iptal et ve yenisini oluştur.
- Push öncesinde `scripts/pre_push_check.sh` çalıştır.

## Dahili API

`aski-checker`:

- `GET /health`
- `GET /status`
- `POST /subscribe`
- `POST /unsubscribe`

`telegram-bot`:

- `POST /notify`
