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
from fastapi import FastAPI, HTTPException, Request

from aski_parser import Outage, find_matching_outage, outage_hash


logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


@dataclass(frozen=True)
class Settings:
    aski_url: str
    target_district: str
    target_neighborhood: str
    check_interval_seconds: int
    notify_every_check: bool
    gateway_notify_url: str
    internal_api_token: str
    data_dir: Path

    @classmethod
    def from_env(cls) -> Settings:
        district = os.getenv("ASKI_TARGET_DISTRICT", "").strip()
        neighborhood = os.getenv("ASKI_TARGET_NEIGHBORHOOD", "").strip()
        if not district or not neighborhood:
            raise RuntimeError("ASKI_TARGET_DISTRICT and ASKI_TARGET_NEIGHBORHOOD must be set")

        token = os.getenv("INTERNAL_API_TOKEN", "").strip()
        if not token:
            raise RuntimeError("INTERNAL_API_TOKEN must be set")

        return cls(
            aski_url=os.getenv("ASKI_URL", "https://www.aski.gov.tr/tr/Kesinti.aspx"),
            target_district=district,
            target_neighborhood=neighborhood,
            check_interval_seconds=int(os.getenv("CHECK_INTERVAL_SECONDS", "300")),
            notify_every_check=os.getenv("ASKI_NOTIFY_EVERY_CHECK", "false").lower() == "true",
            gateway_notify_url=os.getenv(
                "GATEWAY_NOTIFY_URL", "http://telegram-bot-gateway:8080/notify"
            ),
            internal_api_token=token,
            data_dir=Path(os.getenv("DATA_DIR", "/data")),
        )


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._default()
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.exception("Could not read state; using defaults")
            return self._default()
        default = self._default()
        default.update(data)
        return default

    def save(self, state: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        tmp.replace(self.path)

    @staticmethod
    def _default() -> dict[str, Any]:
        return {
            "lastNotifiedHash": "",
            "lastCheckedAt": None,
            "lastError": None,
            "lastMatch": None,
        }


class WatcherService:
    def __init__(self, settings: Settings, store: StateStore) -> None:
        self.settings = settings
        self.store = store
        self._lock = asyncio.Lock()

    async def get_status(self) -> dict[str, Any]:
        async with self._lock:
            state = self.store.load()
        return {
            "lastCheckedAt": state.get("lastCheckedAt"),
            "lastError": state.get("lastError"),
            "lastMatch": state.get("lastMatch"),
        }

    async def check_now(self) -> dict[str, Any]:
        async with self._lock:
            state = self.store.load()
            result, notify_text = await self._do_check(state)

        if notify_text:
            await self._notify(notify_text)

        return result

    async def run_loop(self) -> None:
        await self.check_now()
        while True:
            await asyncio.sleep(self.settings.check_interval_seconds)
            await self.check_now()

    async def _do_check(
        self, state: dict[str, Any]
    ) -> tuple[dict[str, Any], str | None]:
        checked_at = _now_iso()

        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                response = await client.get(self.settings.aski_url)
                response.raise_for_status()
            html = response.text
        except Exception as exc:
            logger.exception("ASKİ fetch failed")
            state["lastError"] = str(exc)
            state["lastCheckedAt"] = checked_at
            self.store.save(state)
            return (
                {
                    "lastCheckedAt": checked_at,
                    "lastError": str(exc),
                    "lastMatch": state.get("lastMatch"),
                },
                None,
            )

        match = find_matching_outage(
            html, self.settings.target_district, self.settings.target_neighborhood
        )
        match_dict = match.to_api_dict() if match else None
        current_hash = outage_hash(match)

        state["lastCheckedAt"] = checked_at
        state["lastError"] = None
        state["lastMatch"] = match_dict
        self.store.save(state)

        notify_text: str | None = None
        if self.settings.notify_every_check:
            notify_text = _format_notification(match, self.settings)
        elif current_hash != state.get("lastNotifiedHash", ""):
            notify_text = _format_notification(match, self.settings)
            state["lastNotifiedHash"] = current_hash
            self.store.save(state)

        return (
            {
                "ok": True,
                "lastCheckedAt": checked_at,
                "match": match_dict,
                "notified": notify_text is not None,
            },
            notify_text,
        )

    async def _notify(self, text: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    self.settings.gateway_notify_url,
                    json={"text": text},
                    headers={"authorization": f"Bearer {self.settings.internal_api_token}"},
                )
                response.raise_for_status()
        except Exception:
            logger.exception("Could not notify gateway")


def _format_notification(match: Outage | None, settings: Settings) -> str:
    neighborhood = settings.target_neighborhood
    url = settings.aski_url

    if not match:
        return (
            f"{neighborhood} için aktif su kesintisi yok.\n\n"
            f"Otomatik ASKİ kontrolü tamamlandı.\n\n"
            f"{url}"
        )

    return "\n".join([
        f"{neighborhood} için su kesintisi var.",
        "",
        f"Arıza tarihi:     {match.fault_date or '-'}",
        f"Tahmini bitiş:    {match.repair_date or '-'}",
        f"Etkilenen yerler: {match.affected_places or '-'}",
        f"Detay:            {match.detail or '-'}",
        "",
        url,
    ])


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _require_auth(req: Request, settings: Settings) -> None:
    auth = req.headers.get("authorization", "")
    bearer = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
    header_token = req.headers.get("x-internal-token", "")
    if bearer != settings.internal_api_token and header_token != settings.internal_api_token:
        raise HTTPException(status_code=401, detail="unauthorized")


def create_app(service: WatcherService, start_background: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ARG001
        task: asyncio.Task[None] | None = None
        if start_background:
            task = asyncio.create_task(service.run_loop())
        try:
            yield
        finally:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    app = FastAPI(title="ASKİ Water Watch", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/status")
    async def status(req: Request) -> dict[str, Any]:
        _require_auth(req, service.settings)
        return await service.get_status()

    @app.post("/check")
    async def check(req: Request) -> dict[str, Any]:
        _require_auth(req, service.settings)
        return await service.check_now()

    return app


settings = Settings.from_env()
store = StateStore(settings.data_dir / "aski-state.json")
service = WatcherService(settings, store)
app = create_app(service)


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8081")))
