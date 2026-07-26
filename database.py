"""
Ma'lumotlar bazasi bilan ishlash moduli (SQLite, async).
Barcha kontent (post/quiz/so'rovnoma) shu yerda saqlanadi.
"""
import json
from contextlib import asynccontextmanager
from datetime import datetime

import aiosqlite

from config import DB_PATH


@asynccontextmanager
async def _connect():
    """
    Har bir ulanishda WAL rejimi va busy_timeout ni yoqadi — bu bir nechta
    joydan (handler + scheduler) bir vaqtda bazaga yozilganda "database is
    locked" xatosining oldini oladi.
    """
    async with aiosqlite.connect(DB_PATH, timeout=30) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=30000")
        yield db


async def init_db():
    """Bazani va jadvallarni yaratish (birinchi ishga tushirishda)."""
    async with _connect() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type TEXT NOT NULL,          -- 'post', 'quiz', 'poll'
                topic TEXT,
                text TEXT,
                options_json TEXT,                    -- quiz/poll variantlari (JSON)
                correct_option INTEGER,                -- quiz uchun to'g'ri javob indeksi
                explanation TEXT,                      -- quiz uchun izoh
                image_path TEXT,                       -- generatsiya qilingan rasm fayli
                status TEXT DEFAULT 'draft',           -- draft, approved, scheduled, published, rejected, failed
                scheduled_time TEXT,                   -- ISO format vaqt
                created_by INTEGER,
                created_at TEXT,
                published_at TEXT,
                channel_message_id INTEGER,
                retry_count INTEGER DEFAULT 0,
                next_attempt_time TEXT,
                last_error TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.commit()

        # --- Migration: eski bazalarga yangi ustunlarni qo'shish ---
        cursor = await db.execute("PRAGMA table_info(content)")
        columns = {row[1] for row in await cursor.fetchall()}
        migrations = {
            "explanation": "ALTER TABLE content ADD COLUMN explanation TEXT",
            "retry_count": "ALTER TABLE content ADD COLUMN retry_count INTEGER DEFAULT 0",
            "next_attempt_time": "ALTER TABLE content ADD COLUMN next_attempt_time TEXT",
            "last_error": "ALTER TABLE content ADD COLUMN last_error TEXT",
        }
        for column, statement in migrations.items():
            if column not in columns:
                await db.execute(statement)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_content_status ON content(status)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_content_scheduled ON content(status, scheduled_time)"
        )
        await db.commit()


async def add_content(content_type, topic, text, options=None, correct_option=None,
                       explanation=None, image_path=None, created_by=None, status="draft"):
    async with _connect() as db:
        cursor = await db.execute(
            """INSERT INTO content
               (content_type, topic, text, options_json, correct_option, explanation,
                image_path, status, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (content_type, topic, text,
             json.dumps(options, ensure_ascii=False) if options else None,
             correct_option, explanation, image_path, status, created_by,
             datetime.now().isoformat())
        )
        await db.commit()
        return cursor.lastrowid


async def get_content(content_id):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM content WHERE id = ?", (content_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_content_text(content_id, new_text):
    async with _connect() as db:
        await db.execute("UPDATE content SET text = ? WHERE id = ?", (new_text, content_id))
        await db.commit()


async def update_options(content_id, options, correct_option=None):
    """Quiz/poll variantlarini yangilaydi. correct_option berilsa, to'g'ri javobni ham yangilaydi."""
    async with _connect() as db:
        if correct_option is not None:
            await db.execute(
                "UPDATE content SET options_json = ?, correct_option = ? WHERE id = ?",
                (json.dumps(options, ensure_ascii=False), correct_option, content_id),
            )
        else:
            await db.execute(
                "UPDATE content SET options_json = ? WHERE id = ?",
                (json.dumps(options, ensure_ascii=False), content_id),
            )
        await db.commit()


async def update_correct_option(content_id, correct_option):
    async with _connect() as db:
        await db.execute(
            "UPDATE content SET correct_option = ? WHERE id = ?", (correct_option, content_id)
        )
        await db.commit()


async def update_explanation(content_id, explanation):
    async with _connect() as db:
        await db.execute("UPDATE content SET explanation = ? WHERE id = ?", (explanation, content_id))
        await db.commit()


async def update_status(content_id, status):
    async with _connect() as db:
        await db.execute("UPDATE content SET status = ? WHERE id = ?", (status, content_id))
        await db.commit()


async def set_schedule(content_id, scheduled_time_iso):
    async with _connect() as db:
        await db.execute(
            """UPDATE content SET status = 'scheduled', scheduled_time = ?,
               retry_count = 0, next_attempt_time = NULL, last_error = NULL WHERE id = ?""",
            (scheduled_time_iso, content_id)
        )
        await db.commit()


async def mark_published(content_id, channel_message_id):
    async with _connect() as db:
        await db.execute(
            """UPDATE content SET status = 'published', channel_message_id = ?,
               published_at = ?, next_attempt_time = NULL, last_error = NULL WHERE id = ?""",
            (channel_message_id, datetime.now().isoformat(), content_id)
        )
        await db.commit()


async def record_publish_failure(content_id, error_text, next_attempt_time_iso=None, mark_failed=False):
    """
    Rejalashtirilgan joylash muvaffaqiyatsiz bo'lganda chaqiriladi.
    mark_failed=True bo'lsa, ko'p urinishdan keyin butunlay 'failed' holatiga o'tkazadi.
    """
    async with _connect() as db:
        status = "failed" if mark_failed else "scheduled"
        await db.execute(
            """UPDATE content SET retry_count = retry_count + 1, last_error = ?,
               next_attempt_time = ?, status = ? WHERE id = ?""",
            (error_text[:500] if error_text else None, next_attempt_time_iso, status, content_id)
        )
        await db.commit()


async def retry_failed(content_id):
    """Muvaffaqiyatsiz postni darhol qayta urinish uchun rejalashtiradi."""
    async with _connect() as db:
        await db.execute(
            """UPDATE content SET status = 'scheduled', retry_count = 0,
               next_attempt_time = NULL, last_error = NULL WHERE id = ?""",
            (content_id,)
        )
        await db.commit()


async def get_due_scheduled():
    """Vaqti kelgan, hali joylanmagan postlarni olish (fallback, timezone-naive)."""
    now = datetime.now().isoformat()
    return await get_due_scheduled_before(now)


async def get_due_scheduled_before(now_iso: str):
    """
    Vaqti kelgan va (agar avval xato bergan bo'lsa) keyingi urinish vaqti ham
    kelgan postlarni olish. now_iso — timezone-aware vaqt isoformat.
    """
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM content WHERE status = 'scheduled' AND scheduled_time <= ?
               AND (next_attempt_time IS NULL OR next_attempt_time <= ?)""",
            (now_iso, now_iso)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_scheduled_list(limit=None, offset=0):
    """Barcha rejalashtirilgan postlar ro'yxati (kelajakdagi)."""
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM content WHERE status = 'scheduled' ORDER BY scheduled_time ASC"
        params = ()
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params = (limit, offset)
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def count_scheduled():
    async with _connect() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM content WHERE status = 'scheduled'")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_failed_list():
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM content WHERE status = 'failed' ORDER BY id DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def delete_content(content_id):
    async with _connect() as db:
        await db.execute("DELETE FROM content WHERE id = ?", (content_id,))
        await db.commit()


async def count_recent_generations(minutes: int, created_by: int | None = None) -> int:
    """So'nggi `minutes` daqiqada nechta kontent generatsiya qilingani (rate-limit uchun)."""
    async with _connect() as db:
        cutoff = (datetime.now().timestamp() - minutes * 60)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()
        if created_by is not None:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM content WHERE created_at >= ? AND created_by = ?",
                (cutoff_iso, created_by),
            )
        else:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM content WHERE created_at >= ?", (cutoff_iso,)
            )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_stats():
    """Statistika: nechta post, quiz, so'rovnoma joylangan va h.k."""
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        stats = {}
        cursor = await db.execute(
            "SELECT status, COUNT(*) as cnt FROM content GROUP BY status"
        )
        for row in await cursor.fetchall():
            stats[row["status"]] = row["cnt"]

        cursor = await db.execute(
            "SELECT content_type, COUNT(*) as cnt FROM content WHERE status='published' GROUP BY content_type"
        )
        by_type = {}
        for row in await cursor.fetchall():
            by_type[row["content_type"]] = row["cnt"]
        stats["by_type"] = by_type
        return stats
