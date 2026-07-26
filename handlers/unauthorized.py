"""
Admin bo'lmagan foydalanuvchilarga javob.
Bu router main_router'da ENG OXIRIDA ro'yxatga olinishi shart — shunda faqat boshqa
(admin-only) routerlar mos kelmagan holatlargina bu yerga yetib keladi.
"""
from aiogram import Router
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS, UNAUTHORIZED_STICKER_ID

router = Router()

NO_ACCESS_TEXT = "😔 Kechirasiz, sizda bu botdan foydalanish uchun ruxsat yo'q."


@router.message()
async def unauthorized_message(message: Message):
    if message.from_user.id in ADMIN_IDS:
        return  # adminning hech qanday handlerga mos kelmagan xabari — e'tiborsiz qoldiramiz
    try:
        await message.answer_sticker(UNAUTHORIZED_STICKER_ID)
    except Exception:
        pass
    await message.answer(NO_ACCESS_TEXT)


@router.callback_query()
async def unauthorized_callback(callback: CallbackQuery):
    if callback.from_user.id in ADMIN_IDS:
        await callback.answer()
        return
    await callback.answer(NO_ACCESS_TEXT, show_alert=True)
