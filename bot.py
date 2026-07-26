"""
Botni ishga tushirish nuqtasi.
Ishga tushirish: python bot.py
"""
import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent
from aiohttp import web

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db
from handlers import main_router
from scheduler import start_scheduler

# Render "Web Service" turi $PORT'ni tinglashni talab qiladi, aks holda deploy'ni
# muvaffaqiyatsiz deb hisoblaydi — bot o'zi esa Telegram bilan polling orqali ishlaydi,
# bu server faqat Render'ning health-check'iga javob berish uchun kerak.
PORT = int(os.environ.get("PORT", 8080))


async def _health_check(request: web.Request) -> web.Response:
    return web.Response(text="Bot is running!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", _health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health-check server {PORT}-portda ishga tushdi.")

LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_formatter)

_file_handler = RotatingFileHandler(
    os.path.join(LOGS_DIR, "bot.log"), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_file_handler.setFormatter(_formatter)

logging.basicConfig(level=logging.INFO, handlers=[_console_handler, _file_handler])
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

    @dp.error()
    async def global_error_handler(event: ErrorEvent):
        """Handlerda kutilmagan xatolik chiqsa, botni yiqitmasdan log qiladi va adminga xabar beradi."""
        logger.exception(
            "Handlerda kutilmagan xatolik: %s", event.exception, exc_info=event.exception
        )
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id, f"⚠️ Ichki xatolik yuz berdi:\n<code>{event.exception}</code>"
                )
            except Exception:
                pass
        return True

    scheduler = start_scheduler(bot)
    logger.info("Rejalashtiruvchi ishga tushdi.")

    await start_web_server()

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
