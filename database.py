"""
Ma'lumotlar bazasi bilan ishlash moduli (SQLite, async).
Barcha kontent (post/quiz/so'rovnoma) shu yerda saqlanadi.
"""
import json
import aiosqlite
from datetime import datetime
from config import DB_PATH


async def init_db():
    """Bazani va jadvallarni yaratish (birinchi ishga tushirishda)."""
    async with aiosqlite.connect(DB_PATH) as db:
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
                status TEXT DEFAULT 'draft',           -- draft, approved, scheduled, published, rejected
                scheduled_time TEXT,                   -- ISO format vaqt
                created_by INTEGER,
                created_at TEXT,
                published_at TEXT,
                channel_message_id INTEGER
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
        if "explanation" not in columns:
            await db.execute("ALTER TABLE content ADD COLUMN explanation TEXT")
            await db.commit()


async def add_content(content_type, topic, text, options=None, correct_option=None,
                       explanation=None, image_path=None, created_by=None, status="draft"):
    async with aiosqlite.connect(DB_PATH) as db:
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
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM content WHERE id = ?", (content_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_content_text(content_id, new_text):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE content SET text = ? WHERE id = ?", (new_text, content_id))
        await db.commit()


async def update_explanation(content_id, explanation):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE content SET explanation = ? WHERE id = ?", (explanation, content_id))
        await db.commit()


async def update_status(content_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE content SET status = ? WHERE id = ?", (status, content_id))
        await db.commit()


async def set_schedule(content_id, scheduled_time_iso):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE content SET status = 'scheduled', scheduled_time = ? WHERE id = ?",
            (scheduled_time_iso, content_id)
        )
        await db.commit()


async def mark_published(content_id, channel_message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE content SET status = 'published', channel_message_id = ?,
               published_at = ? WHERE id = ?""",
            (channel_message_id, datetime.now().isoformat(), content_id)
        )
        await db.commit()


async def get_due_scheduled():
    """Vaqti kelgan, hali joylanmagan postlarni olish (fallback, timezone-naive)."""
    now = datetime.now().isoformat()
    return await get_due_scheduled_before(now)


async def get_due_scheduled_before(now_iso: str):
    """Vaqti kelgan postlarni olish. now_iso — timezone-aware vaqt isoformat."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM content WHERE status = 'scheduled' AND scheduled_time <= ?",
            (now_iso,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_scheduled_list():
    """Barcha rejalashtirilgan postlar ro'yxati (kelajakdagi)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM content WHERE status = 'scheduled' ORDER BY scheduled_time ASC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def delete_content(content_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM content WHERE id = ?", (content_id,))
        await db.commit()


async def get_stats():
    """Statistika: nechta post, quiz, so'rovnoma joylangan va h.k."""
    async with aiosqlite.connect(DB_PATH) as db:
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
