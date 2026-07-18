from aiogram import Router

from handlers import admin, content, schedule

main_router = Router()
main_router.include_router(admin.router)
main_router.include_router(content.router)
main_router.include_router(schedule.router)
