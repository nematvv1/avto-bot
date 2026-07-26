from aiogram import Router

from handlers import admin, content, schedule, unauthorized

main_router = Router()
main_router.include_router(admin.router)
main_router.include_router(content.router)
main_router.include_router(schedule.router)
# unauthorized ENG OXIRIDA — faqat yuqoridagi admin-only routerlar mos kelmasa ishga tushadi
main_router.include_router(unauthorized.router)
