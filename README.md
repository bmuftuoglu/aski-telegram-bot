# ASKİ Telegram Su Kesintisi Botu

ASKİ'nin ([Ankara Su ve Kanalizasyon İdaresi](https://www.aski.gov.tr)) su kesintisi sayfasını periyodik olarak kontrol eden, belirlediğin ilçe ve mahalle için aktif bir kesinti başladığında veya sona erdiğinde Telegram üzerinden bildirim gönderen bir bot.

## Nasıl Çalışır?

Bot iki servisten oluşur ve Docker Compose ile birlikte ayağa kalkar:

- **aski-checker** — ASKİ kesinti sayfasını her 10 dakikada bir çeker. Belirlediğin ilçe ve mahallede aktif bir kesinti görürse durumu kaydeder ve değişiklik olduğunda telegram-bot'u uyarır.
- **telegram-bot** — Telegram komutlarını dinler. Abone olan kullanıcılara kesinti başladığında veya sona erdiğinde otomatik mesaj gönderir.

## Gereksinimler

- [Docker](https://docs.docker.com/get-docker/) ve [Docker Compose](https://docs.docker.com/compose/install/)
- Bir Telegram hesabı

## Kurulum

### 1. Repoyu klonla

```bash
git clone https://github.com/bmuftuoglu/aski-telegram-bot.git
cd aski-telegram-bot
```

### 2. Telegram botu oluştur

1. Telegram'da **@BotFather**'ı aç
2. `/newbot` komutunu gönder
3. Bot için bir isim ve kullanıcı adı belirle (kullanıcı adı `bot` ile bitmeli, örn. `aski_bildirim_bot`)
4. BotFather'ın verdiği token'ı kopyala: `123456789:ABCdef...`

### 3. Yapılandırma dosyasını oluştur

```bash
cp .env.example .env
```

`.env` dosyasını bir metin editörüyle aç ve aşağıdaki değerleri doldur:

```env
TELEGRAM_BOT_TOKEN=BotFather_dan_aldigin_token

TARGET_DISTRICT=ÇANKAYA
TARGET_NEIGHBORHOOD=Mahalle Adı
```

`TARGET_DISTRICT` ilçe adıdır ve büyük harf olmalıdır (ASKİ sitesinde göründüğü şekilde). `TARGET_NEIGHBORHOOD` ise takip etmek istediğin mahallenin adıdır. Bu iki alan doldurulmadan bot başlamaz.

### 4. Botu başlat

```bash
docker compose up --build
```

İlk çalıştırmada Docker image'ları oluşturulur, bu biraz zaman alabilir. Sonraki başlatmalarda `--build` gerekmez.

Botu arka planda çalıştırmak için:

```bash
docker compose up --build -d
```

## Kullanım

Containerlar ayağa kalktıktan sonra Telegram'da oluşturduğun botu aç:

| Komut | Açıklama |
| --- | --- |
| `/start` | Bildirimlere abone ol. Mevcut kesinti durumunu da gösterir. |
| `/durum` | Son kontrol sonucunu göster. |
| `/stop` | Aboneliği kapat. |

Abone olduktan sonra herhangi bir şey yapman gerekmez. Bot, tanımladığın mahallede kesinti başladığında veya sona erdiğinde sana otomatik mesaj gönderir.

## Ortam Değişkenleri

| Değişken | Varsayılan | Açıklama |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | zorunlu | BotFather'dan alınan token. |
| `TARGET_DISTRICT` | zorunlu | Takip edilecek ilçe adı (büyük harf, örn. `ÇANKAYA`). |
| `TARGET_NEIGHBORHOOD` | zorunlu | Takip edilecek mahalle adı. |
| `ASKI_URL` | `https://www.aski.gov.tr/tr/Kesinti.aspx` | ASKİ kesinti sayfası URL'i. |
| `CHECK_INTERVAL_SECONDS` | `600` | Kontrol aralığı (saniye). Varsayılan 10 dakika. |

## Testleri Çalıştırma

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Güvenlik

- `.env` dosyasını kesinlikle Git'e commit etme.
- Token yanlışlıkla push edilirse BotFather'dan `/revoke` ile hemen iptal et ve yenisini oluştur.
