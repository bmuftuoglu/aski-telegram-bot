from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

from aski_checker.parser import find_matching_outages


logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


@dataclass(frozen=True)
class Settings:
    aski_url: str
    target_district: str
    target_neighborhood: str
    check_interval_seconds: int
    data_dir: Path
    bot_notify_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        target_district = os.getenv("TARGET_DISTRICT", "").strip()
        target_neighborhood = os.getenv("TARGET_NEIGHBORHOOD", "").strip()
        if not target_district or not target_neighborhood:
            raise RuntimeError(
                "TARGET_DISTRICT and TARGET_NEIGHBORHOOD must be set in .env"
            )

        return cls(
            aski_url=os.getenv(
                "ASKI_URL",
                "https://www.aski.gov.tr/tr/Kesinti.aspx",
            ),
            target_district=target_district,
            target_neighborhood=target_neighborhood,
            check_interval_seconds=int(os.getenv("CHECK_INTERVAL_SECONDS", "600")),
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            bot_notify_url=os.getenv(
                "BOT_NOTIFY_URL",
                "http://telegram-bot:8080/notify",
            ),
        )


class SubscribeRequest(BaseModel):
    chat_id: int = Field(..., description="Telegram chat id")


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._default_state()

        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, OSError):
            logger.exception("Could not read checker state; using defaults")
            return self._default_state()

        default = self._default_state()
        default.update(data)
        return default

    def save(self, state: dict[str, Any]) -> None:
        temp_path = self.path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, indent=2, sort_keys=True)
            file.write("\n")
        temp_path.replace(self.path)

    @staticmethod
    def _default_state() -> dict[str, Any]:
        return {
            "subscribers": [],
            "last_status": None,
            "last_signature": None,
            "last_error": None,
        }


class CheckerService:
    def __init__(self, settings: Settings, store: StateStore) -> None:
        self.settings = settings
        self.store = store
        self._lock = asyncio.Lock()

    async def get_status(self) -> dict[str, Any]:
        async with self._lock:
            state = self.store.load()
            if state["last_status"] is None:
                status, _, _ = await self._check_once_locked(state, send_notifications=False)
                return status
            return self._with_error(state["last_status"], state.get("last_error"))

    async def check_once(self, send_notifications: bool = True) -> dict[str, Any]:
        async with self._lock:
            state = self.store.load()
            status, notify_event, notify_chat_ids = await self._check_once_locked(
                state, send_notifications
            )

        # Notifications are sent outside the lock so the lock is not held
        # during the outbound HTTP call to telegram-bot.
        if notify_event and notify_chat_ids:
            await self._notify_subscribers(
                event=notify_event,
                status=status,
                chat_ids=notify_chat_ids,
            )

        return status

    async def subscribe(self, chat_id: int) -> dict[str, Any]:
        async with self._lock:
            state = self.store.load()
            subscribers = {int(item) for item in state.get("subscribers", [])}
            subscribers.add(chat_id)
            state["subscribers"] = sorted(subscribers)
            self.store.save(state)
            return {"subscribed": True, "subscriber_count": len(subscribers)}

    async def unsubscribe(self, chat_id: int) -> dict[str, Any]:
        async with self._lock:
            state = self.store.load()
            subscribers = {int(item) for item in state.get("subscribers", [])}
            subscribers.discard(chat_id)
            state["subscribers"] = sorted(subscribers)
            self.store.save(state)
            return {"subscribed": False, "subscriber_count": len(subscribers)}

    async def _check_once_locked(
        self,
        state: dict[str, Any],
        send_notifications: bool,
    ) -> tuple[dict[str, Any], str | None, list[int]]:
        """Fetch status and persist it. Returns (status, notify_event, chat_ids).

        notify_event and chat_ids are non-empty only when a notification should
        be dispatched; the caller is responsible for sending it *after* releasing
        the lock.
        """
        previous_status = state.get("last_status")
        previous_signature = state.get("last_signature")

        try:
            status = await self._fetch_status()
        except Exception as exc:
            logger.exception("ASKİ check failed")
            state["last_error"] = {
                "message": str(exc),
                "checked_at": _now_iso(),
            }
            self.store.save(state)
            return self._with_error(previous_status, state["last_error"]), None, []

        new_signature = _status_signature(status)
        state["last_status"] = status
        state["last_signature"] = new_signature
        state["last_error"] = None
        self.store.save(state)

        should_notify = (
            send_notifications
            and previous_signature is not None
            and previous_signature != new_signature
        )
        if should_notify:
            return (
                status,
                _event_name(previous_status, status),
                list(state.get("subscribers", [])),
            )

        return status, None, []

    async def _fetch_status(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(self.settings.aski_url)
            response.raise_for_status()

        outages = [
            outage.to_dict()
            for outage in find_matching_outages(
                response.text,
                self.settings.target_district,
                self.settings.target_neighborhood,
            )
        ]

        return {
            "active": bool(outages),
            "checked_at": _now_iso(),
            "source_url": self.settings.aski_url,
            "target": {
                "district": self.settings.target_district,
                "neighborhood": self.settings.target_neighborhood,
            },
            "outages": outages,
            "error": None,
        }

    async def _notify_subscribers(
        self,
        event: str,
        status: dict[str, Any],
        chat_ids: list[int],
    ) -> None:
        if not chat_ids:
            return

        payload = {
            "event": event,
            "chat_ids": chat_ids,
            "status": status,
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(self.settings.bot_notify_url, json=payload)
                response.raise_for_status()
        except Exception:
            logger.exception("Could not send notification to telegram-bot")

    def _with_error(
        self,
        status: dict[str, Any] | None,
        error: dict[str, str] | None,
    ) -> dict[str, Any]:
        if status is None:
            status = {
                "active": False,
                "checked_at": None,
                "source_url": self.settings.aski_url,
                "target": {
                    "district": self.settings.target_district,
                    "neighborhood": self.settings.target_neighborhood,
                },
                "outages": [],
            }

        status_with_error = dict(status)
        status_with_error["error"] = error
        return status_with_error


def create_app(
    service: CheckerService,
    start_background: bool = True,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ARG001
        poll_task: asyncio.Task[None] | None = None
        if start_background:
            poll_task = asyncio.create_task(_poll_loop(service))
        try:
            yield
        finally:
            if poll_task:
                poll_task.cancel()
                try:
                    await poll_task
                except asyncio.CancelledError:
                    pass

    app = FastAPI(title="ASKİ Checker", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/status")
    async def status() -> dict[str, Any]:
        return await service.get_status()

    @app.post("/subscribe")
    async def subscribe(request: SubscribeRequest) -> dict[str, Any]:
        return await service.subscribe(request.chat_id)

    @app.post("/unsubscribe")
    async def unsubscribe(request: SubscribeRequest) -> dict[str, Any]:
        return await service.unsubscribe(request.chat_id)

    return app


async def _poll_loop(service: CheckerService) -> None:
    await service.check_once(send_notifications=False)
    while True:
        await asyncio.sleep(service.settings.check_interval_seconds)
        await service.check_once(send_notifications=True)


def _status_signature(status: dict[str, Any]) -> str:
    payload = {
        "active": status["active"],
        "outages": status["outages"],
        "target": status["target"],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _event_name(
    previous_status: dict[str, Any] | None,
    current_status: dict[str, Any],
) -> str:
    if previous_status is None:
        return "outage_updated"

    if not previous_status.get("active") and current_status.get("active"):
        return "outage_started"
    if previous_status.get("active") and not current_status.get("active"):
        return "outage_cleared"
    return "outage_updated"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


settings = Settings.from_env()
store = StateStore(settings.data_dir / "checker_state.json")
service = CheckerService(settings, store)
app = create_app(service)


if __name__ == "__main__":
    uvicorn.run("aski_checker.app:app", host="0.0.0.0", port=8000)
