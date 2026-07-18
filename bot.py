"""
Botni ishga tushirish nuqtasi.
Ishga tushirish: python bot.py
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db
from handlers import main_router
from scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN topilmadi! .env faylida BOT_TOKEN ni to'g'ri kiriting."
        )
    if not ADMIN_IDS:
        logger.warning(
            "ADMIN_IDS bo'sh! Hech kim botdan foydalana olmaydi. .env faylida ADMIN_IDS ni kiriting."
        )

    await init_db()
    logger.info("Ma'lumotlar bazasi tayyor.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(main_router)

    scheduler = start_scheduler(bot)
    logger.info("Rejalashtiruvchi ishga tushdi.")

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🤖 Bot ishga tushdi va tayyor!")
        except Exception:
            pass

    try:
        logger.info("Bot polling boshlandi...")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
