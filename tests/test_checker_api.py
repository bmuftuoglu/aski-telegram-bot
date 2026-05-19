from pathlib import Path

from fastapi.testclient import TestClient

from aski_checker.app import CheckerService, Settings, StateStore, create_app


def test_status_endpoint_returns_cached_status(tmp_path: Path) -> None:
    settings = Settings(
        aski_url="https://example.test/kesinti",
        target_district="ÇANKAYA",
        target_neighborhood="İşçi Blokları",
        check_interval_seconds=600,
        data_dir=tmp_path,
        bot_notify_url="http://telegram-bot:8080/notify",
    )
    store = StateStore(tmp_path / "state.json")
    store.save(
        {
            "subscribers": [],
            "last_status": {
                "active": False,
                "checked_at": "2026-05-19T12:00:00+00:00",
                "source_url": settings.aski_url,
                "target": {
                    "district": settings.target_district,
                    "neighborhood": settings.target_neighborhood,
                },
                "outages": [],
                "error": None,
            },
            "last_signature": "cached",
            "last_error": None,
        }
    )

    client = TestClient(create_app(CheckerService(settings, store), start_background=False))
    response = client.get("/status")

    assert response.status_code == 200
    assert response.json()["active"] is False
    assert response.json()["target"]["district"] == "ÇANKAYA"


def test_subscribe_and_unsubscribe(tmp_path: Path) -> None:
    settings = Settings(
        aski_url="https://example.test/kesinti",
        target_district="ÇANKAYA",
        target_neighborhood="İşçi Blokları",
        check_interval_seconds=600,
        data_dir=tmp_path,
        bot_notify_url="http://telegram-bot:8080/notify",
    )
    store = StateStore(tmp_path / "state.json")
    client = TestClient(create_app(CheckerService(settings, store), start_background=False))

    subscribe_response = client.post("/subscribe", json={"chat_id": 12345})
    unsubscribe_response = client.post("/unsubscribe", json={"chat_id": 12345})

    assert subscribe_response.status_code == 200
    assert subscribe_response.json()["subscriber_count"] == 1
    assert unsubscribe_response.status_code == 200
    assert unsubscribe_response.json()["subscriber_count"] == 0

