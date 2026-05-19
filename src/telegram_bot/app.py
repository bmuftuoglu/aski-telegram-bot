from __future__ import annotations

import asyncio
import logging
import os
import signal
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

TELEGRAM_APP: Application | None = None


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    checker_base_url: str
    notify_host: str
    notify_port: int

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN must be set")

        return cls(
            telegram_bot_token=token,
            checker_base_url=os.getenv(
                "CHECKER_BASE_URL",
                "http://aski-checker:8000",
            ).rstrip("/"),
            notify_host=os.getenv("BOT_NOTIFY_HOST", "0.0.0.0"),
            notify_port=int(os.getenv("BOT_NOTIFY_PORT", "8080")),
        )


class NotifyRequest(BaseModel):
    event: str
    chat_ids: list[int]
    status: dict[str, Any]


notify_api = FastAPI(title="ASKİ Telegram Notifier")


@notify_api.post("/notify")
async def notify(request: NotifyRequest) -> dict[str, int]:
    if TELEGRAM_APP is None:
        return {"sent": 0, "failed": len(request.chat_ids)}

    text = format_notification_message(request.event, request.status)
    sent = 0
    failed = 0

    for chat_id in request.chat_ids:
        try:
            for part in split_telegram_message(text):
                await TELEGRAM_APP.bot.send_message(
                    chat_id=chat_id, text=part, parse_mode=None
                )
            sent += 1
        except Exception:
            failed += 1
            logger.exception("Could not send Telegram notification to %s", chat_id)

    return {"sent": sent, "failed": failed}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None or update.message is None:
        return

    settings: Settings = context.application.bot_data["settings"]
    chat_id = update.effective_chat.id

    try:
        await checker_post(settings, "/subscribe", {"chat_id": chat_id})
        status = await checker_get(settings, "/status")
    except Exception:
        logger.exception("Could not subscribe chat")
        await update.message.reply_text(
            "Abonelik oluşturulamadı. Checker servisi hazır olmayabilir.",
            parse_mode=None,
        )
        return

    await update.message.reply_text(
        "Bildirim aboneliği açıldı.\n\n" + format_status_message(status),
        parse_mode=None,
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None or update.message is None:
        return

    settings: Settings = context.application.bot_data["settings"]
    chat_id = update.effective_chat.id

    try:
        await checker_post(settings, "/unsubscribe", {"chat_id": chat_id})
    except Exception:
        logger.exception("Could not unsubscribe chat")
        await update.message.reply_text(
            "Abonelik kapatılamadı. Checker servisi hazır olmayabilir.",
            parse_mode=None,
        )
        return

    await update.message.reply_text("Bildirim aboneliği kapatıldı.", parse_mode=None)


async def durum(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    settings: Settings = context.application.bot_data["settings"]
    try:
        status = await checker_get(settings, "/status")
    except Exception:
        logger.exception("Could not get status from checker")
        await update.message.reply_text(
            "Durum alınamadı. Checker servisi hazır olmayabilir.",
            parse_mode=None,
        )
        return

    await update.message.reply_text(format_status_message(status), parse_mode=None)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    await update.message.reply_text(
        "/start - Bildirim aboneliğini aç\n"
        "/durum - Son ASKİ kontrol sonucunu göster\n"
        "/stop - Bildirim aboneliğini kapat",
        parse_mode=None,
    )


async def checker_get(settings: Settings, path: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{settings.checker_base_url}{path}")
        response.raise_for_status()
        return response.json()


async def checker_post(
    settings: Settings,
    path: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{settings.checker_base_url}{path}", json=payload)
        response.raise_for_status()
        return response.json()


def format_notification_message(event: str, status: dict[str, Any]) -> str:
    labels = {
        "outage_started": "ASKİ su kesintisi başladı.",
        "outage_cleared": "ASKİ su kesintisi sona ermiş görünüyor.",
        "outage_updated": "ASKİ su kesintisi durumu güncellendi.",
    }
    return labels.get(event, "ASKİ su kesintisi bildirimi.") + "\n\n" + format_status_message(status)


_TZ_TR = timezone(timedelta(hours=3))


def _format_checked_at(iso: str | None) -> str:
    if not iso:
        return "henüz yok"
    try:
        dt = datetime.fromisoformat(iso).astimezone(_TZ_TR)
        return dt.strftime("%d.%m.%Y %H:%M") + " (TR)"
    except ValueError:
        return iso


def format_status_message(status: dict[str, Any]) -> str:
    target = status.get("target", {})
    district = target.get("district", "hedef ilçe")
    neighborhood = target.get("neighborhood", "hedef mahalle")
    checked_at = _format_checked_at(status.get("checked_at"))

    error = status.get("error")
    suffix = ""
    if error:
        suffix = (
            "\n\nNot: Son kontrol sırasında ASKİ sayfası okunamadı. "
            f"Son hata: {error.get('message', 'bilinmeyen hata')}"
        )

    if not status.get("active"):
        return (
            f"{district} / {neighborhood} için aktif su kesintisi görünmüyor.\n"
            f"Son kontrol: {checked_at}"
            f"{suffix}"
        )

    lines = [
        f"{district} / {neighborhood} için aktif su kesintisi görünüyor.",
        f"Son kontrol: {checked_at}",
    ]

    for index, outage in enumerate(status.get("outages", []), start=1):
        lines.extend(
            [
                "",
                f"{index}. {outage.get('outage_type') or 'ASKİ arıza kaydı'}",
                f"Arıza Tarihi: {outage.get('fault_date') or '-'}",
                f"Tamir Tarihi: {outage.get('repair_date') or '-'}",
                f"Etkilenen Yerler: {outage.get('affected_places') or '-'}",
                f"Detay: {truncate(outage.get('detail') or '-', 900)}",
            ]
        )

    return "\n".join(lines) + suffix


def truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def split_telegram_message(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at < 1:
            split_at = limit
        parts.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        parts.append(remaining)
    return parts


async def main() -> None:
    global TELEGRAM_APP

    settings = Settings.from_env()
    application = Application.builder().token(settings.telegram_bot_token).build()
    application.bot_data["settings"] = settings
    TELEGRAM_APP = application

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("durum", durum))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("help", help_command))

    server = uvicorn.Server(
        uvicorn.Config(
            notify_api,
            host=settings.notify_host,
            port=settings.notify_port,
            log_level=os.getenv("UVICORN_LOG_LEVEL", "info"),
        )
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await application.initialize()
    await application.start()
    if application.updater is None:
        raise RuntimeError("Telegram updater is not available")
    await application.updater.start_polling()

    server_task = asyncio.create_task(server.serve())
    try:
        await stop_event.wait()
    finally:
        server.should_exit = True
        await server_task
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

