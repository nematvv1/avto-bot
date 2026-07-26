"""
Tasdiqlangan kontentni: darhol joylash yoki kelajakka rejalashtirish,
shuningdek rejalashtirilganlar ro'yxatini boshqarish.
"""
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from publisher import publish_content
from states import Scheduling
from handlers.filters import IsAdmin
from config import TIMEZONE, SCHEDULED_PAGE_SIZE

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

TYPE_ICON = {"post": "📝", "quiz": "🧠", "poll": "📊"}


# ---------- Hozir yuborish ----------

@router.callback_query(F.data.startswith("publish_now:"))
async def publish_now(callback: CallbackQuery, state: FSMContext):
    content_id = int(callback.data.split(":")[1])
    content = await db.get_content(content_id)
    if not content:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    try:
        await publish_content(callback.bot, content)
        await callback.message.edit_text("🚀 Kanalga muvaffaqiyatli joylandi!")
    except Exception as e:
        await callback.message.edit_text(f"⚠️ Xatolik: <code>{e}</code>")
    await callback.answer()
    await state.clear()


# ---------- Rejalashtirish menyusi ----------

@router.callback_query(F.data.startswith("publish_schedule:"))
async def publish_schedule_menu(callback: CallbackQuery):
    content_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "🕒 Qachon joylaymiz?", reply_markup=kb.schedule_quick_menu(content_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("quicksched:"))
async def quick_schedule(callback: CallbackQuery, state: FSMContext):
    _, mode, content_id_str = callback.data.split(":")
    content_id = int(content_id_str)
    # Timezone-aware vaqt
    now = datetime.now(tz=TIMEZONE)

    if mode == "manual":
        await state.update_data(scheduling_content_id=content_id)
        await state.set_state(Scheduling.waiting_datetime)
        await callback.message.edit_text(
            "✍️ Sana va vaqtni shu formatda yozing:\n<code>KK.OO.YYYY SS:DD</code>\n"
            "Masalan: <code>20.07.2026 18:30</code>"
        )
        await callback.answer()
        return

    if mode == "1h":
        target = now + timedelta(hours=1)
    elif mode == "today19":
        target = now.replace(hour=19, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
    elif mode == "tom09":
        target = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        await callback.answer("Noma'lum variant.", show_alert=True)
        return

    # DB ga timezone-naive (local vaqt) saqlash
    await db.set_schedule(content_id, target.replace(tzinfo=None).isoformat())
    await callback.message.edit_text(
        f"✅ Rejalashtirildi! Kanalga <b>{target.strftime('%d.%m.%Y %H:%M')}</b> da joylanadi."
    )
    await callback.answer()
    await state.clear()


@router.message(Scheduling.waiting_datetime)
async def manual_datetime_received(message: Message, state: FSMContext):
    data = await state.get_data()
    content_id = data["scheduling_content_id"]

    try:
        target = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer(
            "⚠️ Format noto'g'ri. Iltimos shunday yozing: <code>20.07.2026 18:30</code>"
        )
        return

    now_local = datetime.now(tz=TIMEZONE).replace(tzinfo=None)
    if target <= now_local:
        await message.answer("⚠️ Vaqt kelajakda bo'lishi kerak. Qaytadan urinib ko'ring.")
        return

    await db.set_schedule(content_id, target.isoformat())
    await message.answer(
        f"✅ Rejalashtirildi! Kanalga <b>{target.strftime('%d.%m.%Y %H:%M')}</b> da joylanadi.",
        reply_markup=kb.main_menu(),
    )
    await state.clear()


# ---------- Rejalashtirilganlar ro'yxati ----------

@router.callback_query(F.data.startswith("menu:scheduled"))
async def scheduled_list(callback: CallbackQuery):
    parts = callback.data.split(":")
    offset = int(parts[2]) if len(parts) > 2 else 0

    total = await db.count_scheduled()
    if total == 0:
        failed = await db.get_failed_list()
        if not failed:
            await callback.message.edit_text(
                "📅 Hozircha rejalashtirilgan postlar yo'q.", reply_markup=kb.back_to_menu()
            )
            await callback.answer()
            return
        await callback.message.edit_text(
            "📅 Rejalashtirilgan postlar yo'q.", reply_markup=kb.back_to_menu()
        )
        await callback.answer()
        await _show_failed_list(callback.message, failed)
        return

    items = await db.get_scheduled_list(limit=SCHEDULED_PAGE_SIZE, offset=offset)
    page_end = min(offset + len(items), total)
    await callback.message.edit_text(
        f"📅 Rejalashtirilgan postlar ({offset + 1}-{page_end} / {total} ta):",
        reply_markup=kb.scheduled_nav(offset, SCHEDULED_PAGE_SIZE, total),
    )
    for item in items:
        target = datetime.fromisoformat(item["scheduled_time"])
        icon = TYPE_ICON.get(item["content_type"], "📄")
        preview = item["text"][:120].replace("\n", " ")
        retry_note = ""
        if item.get("retry_count"):
            retry_note = f"\n⚠️ {item['retry_count']} marta joylashga urinildi, qayta rejalashtirilgan."
        text = (
            f"{icon} <b>{item['content_type'].upper()}</b> — "
            f"{target.strftime('%d.%m.%Y %H:%M')}\n\n{preview}...{retry_note}"
        )
        await callback.message.answer(text, reply_markup=kb.scheduled_item_actions(item["id"]))
    await callback.answer()

    failed = await db.get_failed_list()
    if failed:
        await _show_failed_list(callback.message, failed)


async def _show_failed_list(message: Message, failed: list):
    await message.answer(f"❌ Muvaffaqiyatsiz bo'lgan postlar ({len(failed)} ta):")
    for item in failed:
        icon = TYPE_ICON.get(item["content_type"], "📄")
        preview = item["text"][:120].replace("\n", " ")
        error = (item.get("last_error") or "")[:200]
        text = (
            f"{icon} <b>{item['content_type'].upper()}</b> — muvaffaqiyatsiz\n\n"
            f"{preview}...\n\n⚠️ <i>{error}</i>"
        )
        await message.answer(text, reply_markup=kb.failed_item_actions(item["id"]))


@router.callback_query(F.data.startswith("retry_failed:"))
async def retry_failed(callback: CallbackQuery):
    content_id = int(callback.data.split(":")[1])
    await db.retry_failed(content_id)
    await callback.message.edit_text("🔁 Post qayta rejalashtirildi, tez orada joylanadi.")
    await callback.answer()


@router.callback_query(F.data.startswith("ask_delete_scheduled:"))
async def ask_delete_scheduled(callback: CallbackQuery):
    """Birinchi bosqich: tasdiqlash so'raydi."""
    content_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "🗑 Ushbu rejalashtirilgan postni o'chirishni tasdiqlaysizmi?",
        reply_markup=kb.confirm_delete_scheduled(content_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_scheduled:"))
async def delete_scheduled(callback: CallbackQuery):
    """Ikkinchi bosqich: haqiqatda o'chiradi."""
    content_id = int(callback.data.split(":")[1])
    await db.delete_content(content_id)
    await callback.message.edit_text("🗑 O'chirildi.")
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_delete:"))
async def cancel_delete_scheduled(callback: CallbackQuery):
    """O'chirishni bekor qilish — ro'yxatga qaytadi."""
    await callback.message.edit_text("✅ Bekor qilindi.", reply_markup=kb.back_to_menu())
    await callback.answer()
