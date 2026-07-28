"""
Faqat adminlarga ruxsat berish uchun filter.
"""
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from config import ADMIN_IDS
import database as db


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = event.from_user.id
        if user_id in ADMIN_IDS:
            return True
        runtime_admins = await db.get_runtime_admin_ids()
        return user_id in runtime_admins
