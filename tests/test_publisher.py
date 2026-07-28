import asyncio
from unittest.mock import AsyncMock

import config
import publisher


def _targets():
    return {
        "academy": {
            "label": "Academy", "channel_id": "@academy_channel", "topic": "IT",
            "brand_name": "Academy", "logo_path": "x", "accent_color": "#fff", "contact_footer": "",
        },
        "school": {
            "label": "School", "channel_id": "-100999", "topic": "School",
            "brand_name": "School", "logo_path": "x", "accent_color": "#fff", "contact_footer": "",
        },
    }


def test_publish_uses_correct_channel_for_target(monkeypatch):
    targets = _targets()
    monkeypatch.setattr(config, "CHANNEL_TARGETS", targets)
    monkeypatch.setattr(config, "DEFAULT_TARGET_KEY", "academy")

    async def fake_mark_published(content_id, message_id):
        pass

    monkeypatch.setattr(publisher.db, "mark_published", fake_mark_published)

    bot = AsyncMock()
    bot.send_message.return_value.message_id = 42

    content = {
        "id": 1, "content_type": "post", "text": "hello", "image_path": None,
        "target_key": "school",
    }
    asyncio.run(publisher.publish_content(bot, content))

    bot.send_message.assert_awaited_once()
    _, kwargs = bot.send_message.call_args
    assert kwargs["chat_id"] == "-100999"


def test_publish_raises_when_channel_not_configured(monkeypatch):
    targets = {
        "empty": {
            "label": "Empty", "channel_id": "", "topic": "", "brand_name": "x",
            "logo_path": "x", "accent_color": "#fff", "contact_footer": "",
        },
    }
    monkeypatch.setattr(config, "CHANNEL_TARGETS", targets)
    monkeypatch.setattr(config, "DEFAULT_TARGET_KEY", "empty")

    bot = AsyncMock()
    content = {"id": 1, "content_type": "post", "text": "hello", "image_path": None, "target_key": "empty"}
    try:
        asyncio.run(publisher.publish_content(bot, content))
        assert False, "ValueError kutilgan edi"
    except ValueError:
        pass
