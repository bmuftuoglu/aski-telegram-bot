from telegram_bot.app import _format_checked_at, format_status_message, split_telegram_message


def test_format_status_message_for_inactive_status() -> None:
    message = format_status_message(
        {
            "active": False,
            "checked_at": "2026-05-19T12:00:00+00:00",
            "target": {
                "district": "ÇANKAYA",
                "neighborhood": "İşçi Blokları",
            },
            "outages": [],
            "error": None,
        }
    )

    assert "aktif su kesintisi görünmüyor" in message
    assert "ÇANKAYA / İşçi Blokları" in message
    assert "(TR)" in message


def test_format_checked_at_converts_to_turkey_time() -> None:
    # 12:00 UTC → 15:00 TR (UTC+3)
    result = _format_checked_at("2026-05-19T12:00:00+00:00")
    assert result == "19.05.2026 15:00 (TR)"


def test_format_checked_at_handles_none() -> None:
    assert _format_checked_at(None) == "henüz yok"


def test_split_telegram_message_keeps_short_messages_intact() -> None:
    assert split_telegram_message("short") == ["short"]

