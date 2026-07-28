import asyncio
from unittest.mock import AsyncMock

import pytest

import config
import database as db
from handlers.filters import IsAdmin


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)
    asyncio.run(db.init_db())
    return db_path


def test_add_and_remove_runtime_admin(temp_db):
    assert asyncio.run(db.get_runtime_admin_ids()) == []
    asyncio.run(db.add_runtime_admin(999))
    assert asyncio.run(db.get_runtime_admin_ids()) == [999]
    asyncio.run(db.remove_runtime_admin(999))
    assert asyncio.run(db.get_runtime_admin_ids()) == []


def test_add_runtime_admin_is_idempotent(temp_db):
    asyncio.run(db.add_runtime_admin(999))
    asyncio.run(db.add_runtime_admin(999))
    assert asyncio.run(db.get_runtime_admin_ids()) == [999]


def test_get_all_admin_ids_merges_env_and_runtime(temp_db, monkeypatch):
    monkeypatch.setattr(db, "ADMIN_IDS", [111])
    asyncio.run(db.add_runtime_admin(999))
    assert asyncio.run(db.get_all_admin_ids()) == [111, 999]


def test_add_and_remove_runtime_target(temp_db):
    target = {
        "label": "Sport", "channel_id": "@sport", "topic": "sport",
        "brand_name": "Sport", "logo_path": "x", "accent_color": "#fff", "contact_footer": "",
    }
    asyncio.run(db.add_runtime_target("sport", target))
    targets = asyncio.run(db.get_runtime_targets())
    assert targets["sport"]["label"] == "Sport"

    asyncio.run(db.remove_runtime_target("sport"))
    assert asyncio.run(db.get_runtime_targets()) == {}


def test_get_all_targets_merges_env_and_runtime(temp_db, monkeypatch):
    env_targets = {"academy": {"label": "Academy", "channel_id": "@a", "topic": "t",
                                "brand_name": "A", "logo_path": "x", "accent_color": "#fff",
                                "contact_footer": ""}}
    monkeypatch.setattr(db, "CHANNEL_TARGETS", env_targets)
    asyncio.run(db.add_runtime_target("sport", {
        "label": "Sport", "channel_id": "@sport", "topic": "sport", "brand_name": "Sport",
        "logo_path": "x", "accent_color": "#fff", "contact_footer": "",
    }))
    all_targets = asyncio.run(db.get_all_targets())
    assert set(all_targets.keys()) == {"academy", "sport"}


def _make_event(user_id):
    event = AsyncMock()
    event.from_user.id = user_id
    return event


def test_is_admin_true_for_env_admin(temp_db, monkeypatch):
    monkeypatch.setattr("handlers.filters.ADMIN_IDS", [111])
    result = asyncio.run(IsAdmin()(_make_event(111)))
    assert result is True


def test_is_admin_true_for_runtime_admin(temp_db, monkeypatch):
    monkeypatch.setattr("handlers.filters.ADMIN_IDS", [111])
    asyncio.run(db.add_runtime_admin(999))
    result = asyncio.run(IsAdmin()(_make_event(999)))
    assert result is True


def test_is_admin_false_for_unknown_user(temp_db, monkeypatch):
    monkeypatch.setattr("handlers.filters.ADMIN_IDS", [111])
    result = asyncio.run(IsAdmin()(_make_event(42)))
    assert result is False
