from aiogram import Router

from handlers import admin, content, schedule, settings, unauthorized

main_router = Router()
main_router.include_router(admin.router)
main_router.include_router(content.router)
main_router.include_router(schedule.router)
main_router.include_router(settings.router)
# unauthorized ENG OXIRIDA — faqat yuqoridagi admin-only routerlar mos kelmasa ishga tushadi
main_router.include_router(unauthorized.router)
