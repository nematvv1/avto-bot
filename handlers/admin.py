"""
Asosiy admin panel: /start, /help, bosh menyu, statistika, sozlamalar.
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from handlers.filters import IsAdmin
from config import CHANNEL_TARGETS, TEXT_MODEL, IMAGE_MODEL, IMAGE_STYLE, IMAGE_SIZE

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


WELCOME_TEXT = (
    "👋 Assalomu alaykum! Men <b>Kanal Kontent Boti</b>man.\n\n"
    "Men sizning Telegram kanalingiz uchun AI yordamida post, quiz va so'rovnomalar "
    "yarataman, sizga tasdiqlash uchun yuboraman va siz tasdiqlagandan so'ng "
    "kanalga o'zim (yoki belgilagan vaqtda) joylayman.\n\n"
    "Quyidagi tugmalardan birini tanlang 👇"
)

HELP_TEXT = (
    "📖 <b>Qo'llanma</b>\n\n"
    "<b>✨ Yangi kontent yaratish</b> — post, quiz yoki so'rovnoma yaratish jarayonini boshlaydi. "
    "Mavzuni o'zingiz yozishingiz yoki AI'ga topshirishingiz mumkin.\n\n"
    "<b>Tasdiqlash jarayoni:</b>\n"
    "AI kontent tayyorlagach, sizga ko'rsatadi. Siz:\n"
    "  ✅ <i>Tasdiqlash</i> — kontent tayyor, joylash bosqichiga o'tadi\n"
    "  ✏️ <i>Tahrirlash</i> — matnni o'zingiz qo'lda o'zgartirasiz\n"
    "  🔄 <i>Qayta generatsiya</i> — AI boshqa variant yaratadi\n"
    "  ❌ <i>Bekor qilish</i> — kontent o'chiriladi\n\n"
    "<b>Tasdiqlangandan keyin:</b>\n"
    "  🚀 <i>Hozir yuborish</i> — darhol kanalga joylanadi\n"
    "  🕒 <i>Vaqt belgilash</i> — kelajakdagi sana/vaqtga rejalashtiriladi\n\n"
    "<b>📅 Rejalashtirilganlar</b> — hali joylanmagan, vaqti belgilangan postlar ro'yxati. "
    "Bekor qilish/o'chirish mumkin.\n\n"
    "<b>📊 Statistika</b> — nechta post/quiz/poll joylangani.\n\n"
    "<b>Buyruqlar:</b>\n"
    "/start — botni ishga tushirish\n"
    "/menu — bosh menyuni ko'rsatish\n"
    "/help — shu qo'llanma\n"
    "/cancel — joriy amalni bekor qilish"
)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=kb.main_menu())


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Bosh menyu", reply_markup=kb.main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, reply_markup=kb.back_to_menu())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Amal bekor qilindi.", reply_markup=kb.main_menu())


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🏠 Bosh menyu", reply_markup=kb.main_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def cb_help(callback: CallbackQuery):
    await callback.message.edit_text(HELP_TEXT, reply_markup=kb.back_to_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:settings")
async def cb_settings(callback: CallbackQuery):
    targets_text = "\n\n".join(
        f"<b>{t['label']}</b>\n"
        f"📢 Kanal: <code>{t['channel_id'] or 'belgilanmagan'}</code>\n"
        f"🎯 Mavzu: <i>{t['topic'][:150]}</i>"
        for t in CHANNEL_TARGETS.values()
    )
    text = (
        "⚙️ <b>Joriy sozlamalar</b>\n\n"
        f"{targets_text}\n\n"
        f"🧠 Matn modeli: <code>{TEXT_MODEL}</code>\n"
        f"🎨 Rasm modeli: <code>{IMAGE_MODEL}</code>\n"
        f"📐 Rasm o'lchami: <code>{IMAGE_SIZE}</code>\n"
        f"🖌 Rasm uslubi: <i>{IMAGE_STYLE[:120]}...</i>\n\n"
        "Sozlamalarni o'zgartirish uchun serverdagi <code>.env</code> faylini tahrirlang "
        "va botni qayta ishga tushiring."
    )
    await callback.message.edit_text(text, reply_markup=kb.back_to_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:stats")
async def cb_stats(callback: CallbackQuery):
    stats = await db.get_stats()
    by_type = stats.get("by_type", {})
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"✅ Joylangan: {stats.get('published', 0)}\n"
        f"🕒 Rejalashtirilgan: {stats.get('scheduled', 0)}\n"
        f"📝 Qoralama: {stats.get('draft', 0)}\n"
        f"❌ Bekor qilingan: {stats.get('rejected', 0)}\n"
        f"⚠️ Muvaffaqiyatsiz: {stats.get('failed', 0)}\n\n"
        "<b>Turlar bo'yicha (joylanganlar):</b>\n"
        f"📝 Post: {by_type.get('post', 0)}\n"
        f"🧠 Quiz: {by_type.get('quiz', 0)}\n"
        f"📊 So'rovnoma: {by_type.get('poll', 0)}"
    )
    await callback.message.edit_text(text, reply_markup=kb.back_to_menu())
    await callback.answer()
