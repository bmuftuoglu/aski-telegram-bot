from pathlib import Path

from fastapi.testclient import TestClient

from app import Settings, StateStore, WatcherService, create_app


AUTH = {"authorization": "Bearer test-token-123"}


def _make_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        aski_url="https://example.test/kesinti",
        target_district="ÇANKAYA",
        target_neighborhood="Test Mahallesi",
        check_interval_seconds=600,
        notify_every_check=False,
        gateway_notify_url="http://localhost:8080/notify",
        internal_api_token="test-token-123",
        data_dir=tmp_path,
    )
    store = StateStore(tmp_path / "state.json")
    return TestClient(create_app(WatcherService(settings, store), start_background=False))


def test_health(tmp_path: Path) -> None:
    response = _make_client(tmp_path).get("/health")
    assert response.status_code == 200


def test_status_requires_auth(tmp_path: Path) -> None:
    assert _make_client(tmp_path).get("/status").status_code == 401


def test_check_requires_auth(tmp_path: Path) -> None:
    assert _make_client(tmp_path).post("/check").status_code == 401


def test_status_returns_last_match(tmp_path: Path) -> None:
    settings = Settings(
        aski_url="https://example.test/kesinti",
        target_district="ÇANKAYA",
        target_neighborhood="Test Mahallesi",
        check_interval_seconds=600,
        notify_every_check=False,
        gateway_notify_url="http://localhost:8080/notify",
        internal_api_token="test-token-123",
        data_dir=tmp_path,
    )
    store = StateStore(tmp_path / "state.json")
    store.save({
        "lastNotifiedHash": "",
        "lastCheckedAt": "2026-05-19T12:00:00+00:00",
        "lastError": None,
        "lastMatch": None,
    })
    client = TestClient(create_app(WatcherService(settings, store), start_background=False))
    response = client.get("/status", headers=AUTH)
    assert response.status_code == 200
    assert response.json()["lastMatch"] is None
    assert response.json()["lastCheckedAt"] == "2026-05-19T12:00:00+00:00"
