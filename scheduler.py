"""
Fon rejimida ishlovchi rejalashtiruvchi:
- Har necha soniyada bazani tekshirib, vaqti kelgan postlarni kanalga joylaydi
- Haftada bir marta eski rasm fayllarini diskdan tozalaydi
"""
import logging
import os
import time
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

import database as db
from publisher import publish_content
from config import (
    ADMIN_IDS, SCHEDULER_CHECK_INTERVAL, TIMEZONE, IMAGE_CLEANUP_DAYS,
    SCHEDULE_MAX_RETRIES, SCHEDULE_RETRY_BASE_MINUTES, SCHEDULE_RETRY_MAX_MINUTES,
)

logger = logging.getLogger(__name__)

IMAGES_DIR = "generated_images"


async def _notify_admins(bot: Bot, text: str):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass


def _next_attempt_delay_minutes(retry_count: int) -> int:
    """Eksponensial backoff: 1-urinishdan keyin 2 daq, keyin 4, 8... maks. chegaragacha."""
    delay = SCHEDULE_RETRY_BASE_MINUTES * (2 ** (retry_count - 1))
    return min(delay, SCHEDULE_RETRY_MAX_MINUTES)


async def check_and_publish(bot: Bot):
    """Vaqti kelgan rejalashtirilgan postlarni kanalga joylaydi."""
    # Timezone-aware vaqtdan isoformat olamiz, lekin DB da naive saqlanadi,
    # shuning uchun local vaqtni ishlatamiz (server local == TIMEZONE bo'lishi kerak)
    now = datetime.now(tz=TIMEZONE).replace(tzinfo=None)
    now_iso = now.isoformat()
    due_items = await db.get_due_scheduled_before(now_iso)
    for content in due_items:
        try:
            await publish_content(bot, content)
            icon = {"post": "📝", "quiz": "🧠", "poll": "📊"}.get(
                content["content_type"], "📄"
            )
            await _notify_admins(
                bot,
                f"✅ Rejalashtirilgan {icon} {content['content_type']} "
                f"kanalga muvaffaqiyatli joylandi!",
            )
        except Exception as e:
            retry_count = (content.get("retry_count") or 0) + 1
            logger.error(
                f"Rejalashtirilgan postni joylashda xatolik "
                f"(id={content['id']}, urinish={retry_count}): {e}"
            )
            if retry_count >= SCHEDULE_MAX_RETRIES:
                await db.record_publish_failure(content["id"], str(e), mark_failed=True)
                await _notify_admins(
                    bot,
                    f"❌ Rejalashtirilgan post (id={content['id']}) {retry_count} marta "
                    f"urinishdan so'ng joylanmadi va bekor qilindi.\nOxirgi xato: {e}\n"
                    "Rejalashtirilganlar ro'yxatida qayta urinishingiz mumkin.",
                )
            else:
                delay_minutes = _next_attempt_delay_minutes(retry_count)
                next_attempt = (now + timedelta(minutes=delay_minutes)).isoformat()
                await db.record_publish_failure(content["id"], str(e), next_attempt_time=next_attempt)
                if retry_count == 1:
                    await _notify_admins(
                        bot,
                        f"⚠️ Rejalashtirilgan post (id={content['id']}) joylanmadi.\n"
                        f"Xato: {e}\n{delay_minutes} daqiqadan keyin avtomatik qayta uriniladi "
                        f"(jami {SCHEDULE_MAX_RETRIES} marta).",
                    )


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
