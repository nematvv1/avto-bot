import asyncio
from unittest.mock import AsyncMock

import config
from handlers import unauthorized


def _make_message(user_id):
    message = AsyncMock()
    message.from_user.id = user_id
    return message


def _make_callback(user_id):
    callback = AsyncMock()
    callback.from_user.id = user_id
    return callback


def test_admin_message_is_ignored(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_IDS", [111])
    monkeypatch.setattr(unauthorized, "ADMIN_IDS", [111])
    message = _make_message(111)
    asyncio.run(unauthorized.unauthorized_message(message))
    message.answer_sticker.assert_not_called()
    message.answer.assert_not_called()


def test_non_admin_message_gets_sticker_and_text(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_IDS", [111])
    monkeypatch.setattr(unauthorized, "ADMIN_IDS", [111])
    message = _make_message(999)
    asyncio.run(unauthorized.unauthorized_message(message))
    message.answer_sticker.assert_awaited_once_with(unauthorized.UNAUTHORIZED_STICKER_ID)
    message.answer.assert_awaited_once_with(unauthorized.NO_ACCESS_TEXT)


def test_admin_callback_is_just_answered(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_IDS", [111])
    monkeypatch.setattr(unauthorized, "ADMIN_IDS", [111])
    callback = _make_callback(111)
    asyncio.run(unauthorized.unauthorized_callback(callback))
    callback.answer.assert_awaited_once_with()


def test_non_admin_callback_gets_alert(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_IDS", [111])
    monkeypatch.setattr(unauthorized, "ADMIN_IDS", [111])
    callback = _make_callback(999)
    asyncio.run(unauthorized.unauthorized_callback(callback))
    callback.answer.assert_awaited_once_with(unauthorized.NO_ACCESS_TEXT, show_alert=True)


def test_sticker_send_failure_does_not_block_text_reply(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_IDS", [111])
    monkeypatch.setattr(unauthorized, "ADMIN_IDS", [111])
    message = _make_message(999)
    message.answer_sticker.side_effect = Exception("network error")
    asyncio.run(unauthorized.unauthorized_message(message))
    message.answer.assert_awaited_once_with(unauthorized.NO_ACCESS_TEXT)
