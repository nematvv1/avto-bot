import asyncio
import os

import pytest

import config
import database as db


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)
    asyncio.run(db.init_db())
    return db_path


def test_add_and_get_content(temp_db):
    content_id = asyncio.run(db.add_content(
        content_type="post", topic="test", text="Salom dunyo", created_by=1
    ))
    content = asyncio.run(db.get_content(content_id))
    assert content["text"] == "Salom dunyo"
    assert content["status"] == "draft"
    assert content["retry_count"] == 0


def test_update_options_and_correct_option(temp_db):
    content_id = asyncio.run(db.add_content(
        content_type="quiz", topic="t", text="q?",
        options=["a", "b", "c", "d"], correct_option=0, created_by=1
    ))
    asyncio.run(db.update_options(content_id, ["x", "y", "z"]))
    content = asyncio.run(db.get_content(content_id))
    import json
    assert json.loads(content["options_json"]) == ["x", "y", "z"]

    asyncio.run(db.update_correct_option(content_id, 2))
    content = asyncio.run(db.get_content(content_id))
    assert content["correct_option"] == 2


def test_schedule_and_due(temp_db):
    content_id = asyncio.run(db.add_content(
        content_type="post", topic="t", text="x", created_by=1
    ))
    asyncio.run(db.set_schedule(content_id, "2020-01-01T00:00:00"))
    due = asyncio.run(db.get_due_scheduled_before("2025-01-01T00:00:00"))
    assert any(item["id"] == content_id for item in due)


def test_publish_failure_backoff_and_final_failure(temp_db):
    content_id = asyncio.run(db.add_content(
        content_type="post", topic="t", text="x", created_by=1
    ))
    asyncio.run(db.set_schedule(content_id, "2020-01-01T00:00:00"))

    # Birinchi xato — hali scheduled, keyingi urinish vaqti kelajakda
    asyncio.run(db.record_publish_failure(
        content_id, "network error", next_attempt_time_iso="2999-01-01T00:00:00"
    ))
    content = asyncio.run(db.get_content(content_id))
    assert content["status"] == "scheduled"
    assert content["retry_count"] == 1

    # next_attempt_time kelajakda bo'lgani uchun due ro'yxatida chiqmasligi kerak
    due = asyncio.run(db.get_due_scheduled_before("2025-01-01T00:00:00"))
    assert not any(item["id"] == content_id for item in due)

    # Yakuniy muvaffaqiyatsizlik
    asyncio.run(db.record_publish_failure(content_id, "fatal error", mark_failed=True))
    content = asyncio.run(db.get_content(content_id))
    assert content["status"] == "failed"

    failed = asyncio.run(db.get_failed_list())
    assert any(item["id"] == content_id for item in failed)


def test_retry_failed_resets_state(temp_db):
    content_id = asyncio.run(db.add_content(
        content_type="post", topic="t", text="x", created_by=1
    ))
    asyncio.run(db.set_schedule(content_id, "2020-01-01T00:00:00"))
    asyncio.run(db.record_publish_failure(content_id, "err", mark_failed=True))
    asyncio.run(db.retry_failed(content_id))
    content = asyncio.run(db.get_content(content_id))
    assert content["status"] == "scheduled"
    assert content["retry_count"] == 0


def test_count_recent_generations(temp_db):
    asyncio.run(db.add_content(content_type="post", topic="t", text="x", created_by=1))
    count = asyncio.run(db.count_recent_generations(60, created_by=1))
    assert count == 1
    count_other_user = asyncio.run(db.count_recent_generations(60, created_by=2))
    assert count_other_user == 0
