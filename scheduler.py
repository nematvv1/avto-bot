"""
Fon rejimida ishlovchi rejalashtiruvchi:
- Har necha soniyada bazani tekshirib, vaqti kelgan postlarni kanalga joylaydi
- Haftada bir marta eski rasm fayllarini diskdan tozalaydi
"""
import logging
import os
import time
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

import database as db
from publisher import publish_content
from config import ADMIN_IDS, SCHEDULER_CHECK_INTERVAL, TIMEZONE, IMAGE_CLEANUP_DAYS

logger = logging.getLogger(__name__)

IMAGES_DIR = "generated_images"


async def check_and_publish(bot: Bot):
    """Vaqti kelgan rejalashtirilgan postlarni kanalga joylaydi."""
    # Timezone-aware vaqtdan isoformat olamiz, lekin DB da naive saqlanadi,
    # shuning uchun local vaqtni ishlatamiz (server local == TIMEZONE bo'lishi kerak)
    now_iso = datetime.now(tz=TIMEZONE).replace(tzinfo=None).isoformat()
    due_items = await db.get_due_scheduled_before(now_iso)
    for content in due_items:
        try:
            await publish_content(bot, content)
            for admin_id in ADMIN_IDS:
                try:
                    icon = {"post": "📝", "quiz": "🧠", "poll": "📊"}.get(
                        content["content_type"], "📄"
                    )
                    await bot.send_message(
                        admin_id,
                        f"✅ Rejalashtirilgan {icon} {content['content_type']} "
                        f"kanalga muvaffaqiyatli joylandi!",
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Rejalashtirilgan postni joylashda xatolik (id={content['id']}): {e}")
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"⚠️ Rejalashtirilgan post (id={content['id']}) joylanmadi.\nXato: {e}",
                    )
                except Exception:
                    pass


async def cleanup_old_images():
    """
    IMAGE_CLEANUP_DAYS kundan eski rasm fayllarini diskdan o'chiradi.
    Bu funksiya scheduler tomonidan haftada bir marta chaqiriladi.
    """
    if IMAGE_CLEANUP_DAYS <= 0:
        return
    if not os.path.isdir(IMAGES_DIR):
        return

    cutoff = time.time() - IMAGE_CLEANUP_DAYS * 86400
    removed = 0
    for fname in os.listdir(IMAGES_DIR):
        fpath = os.path.join(IMAGES_DIR, fname)
        try:
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
                removed += 1
        except OSError as e:
            logger.warning(f"Faylni o'chirishda xatolik ({fpath}): {e}")
    if removed:
        logger.info(f"Cleanup: {removed} ta eski rasm fayli o'chirildi.")


def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        check_and_publish,
        "interval",
        seconds=SCHEDULER_CHECK_INTERVAL,
        args=[bot],
        id="publish_due_content",
    )
    scheduler.add_job(
        cleanup_old_images,
        "interval",
        days=1,
        id="cleanup_images",
    )
    scheduler.start()
    return scheduler
