"""
Sozlamalar: adminlarni va kanal/tashkilotlarni (target) bot orqali boshqarish.

.env'dagi ADMIN_IDS/TARGETS "doimiy" (bootstrap) hisoblanadi va faqat serverda
.env tahrirlanib qayta ishga tushirilsagina o'zgaradi (🔒 belgisi bilan ko'rsatiladi).
Bot orqali qo'shilgan adminlar/kanallar bazada saqlanadi va shu yerdan o'chirilishi mumkin.
"""
import re

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import SettingsManagement
from handlers.filters import IsAdmin
from config import ADMIN_IDS, CHANNEL_TARGETS

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,19}$")


# ---------- Adminlar ----------

@router.callback_query(F.data == "settings:admins")
async def show_admins(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    runtime_admins = await db.get_runtime_admin_ids()
    lines = ["👥 <b>Adminlar</b>\n"]
    lines += [f"🔒 <code>{a}</code> (doimiy, .env)" for a in ADMIN_IDS]
    lines += [f"🗑 <code>{a}</code> (bot orqali qo'shilgan)" for a in runtime_admins]
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=kb.admins_action_menu(runtime_admins)
    )
    await callback.answer()


@router.callback_query(F.data == "add_admin")
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsManagement.waiting_new_admin_id)
    await callback.message.edit_text(
        "➕ Yangi adminning Telegram ID raqamini yuboring "
        "(ID bilish uchun u @userinfobot'ga /start yozishi kerak):",
        reply_markup=kb.cancel_only_menu("settings:admins"),
    )
    await callback.answer()


@router.message(SettingsManagement.waiting_new_admin_id)
async def add_admin_receive(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("⚠️ Faqat raqam yuboring (masalan: 123456789). Qaytadan urinib ko'ring.")
        return
    new_admin_id = int(text)
    if new_admin_id in ADMIN_IDS:
        await message.answer("Bu ID allaqachon doimiy admin sifatida sozlangan.")
    else:
        await db.add_runtime_admin(new_admin_id)
        await message.answer(f"✅ <code>{new_admin_id}</code> admin sifatida qo'shildi.")
    await state.clear()
    runtime_admins = await db.get_runtime_admin_ids()
    lines = ["👥 <b>Adminlar</b>\n"]
    lines += [f"🔒 <code>{a}</code> (doimiy, .env)" for a in ADMIN_IDS]
    lines += [f"🗑 <code>{a}</code> (bot orqali qo'shilgan)" for a in runtime_admins]
    await message.answer("\n".join(lines), reply_markup=kb.admins_action_menu(runtime_admins))


@router.callback_query(F.data.startswith("ask_remove_admin:"))
async def ask_remove_admin(callback: CallbackQuery):
    admin_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        f"🗑 <code>{admin_id}</code> ni adminlikdan olib tashlashni tasdiqlaysizmi?",
        reply_markup=kb.confirm_remove_admin(admin_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_admin:"))
async def remove_admin(callback: CallbackQuery):
    admin_id = int(callback.data.split(":")[1])
    await db.remove_runtime_admin(admin_id)
    await callback.message.edit_text(f"✅ <code>{admin_id}</code> adminlikdan olib tashlandi.")
    await callback.answer()


# ---------- Kanallar (targetlar) ----------

def _format_target(key: str, t: dict, locked: bool) -> str:
    icon = "🔒" if locked else "🗑"
    return (
        f"{icon} <b>{t['label']}</b> (<code>{key}</code>)\n"
        f"   📢 {t['channel_id'] or 'belgilanmagan'}\n"
        f"   🎯 {t['topic'][:100]}"
    )


@router.callback_query(F.data == "settings:targets")
async def show_targets(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    runtime_targets = await db.get_runtime_targets()
    lines = ["📡 <b>Kanallar</b>\n"]
    lines += [_format_target(k, t, locked=True) for k, t in CHANNEL_TARGETS.items()]
    lines += [_format_target(k, t, locked=False) for k, t in runtime_targets.items()]
    await callback.message.edit_text(
        "\n\n".join(lines), reply_markup=kb.targets_action_menu(list(runtime_targets.keys()))
    )
    await callback.answer()


@router.callback_query(F.data == "add_target")
async def add_target_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsManagement.waiting_new_target_key)
    await callback.message.edit_text(
        "➕ Yangi kanal uchun qisqa kalit so'z kiriting (faqat kichik lotin harflar/raqam, "
        "bo'sh joysiz, masalan: <code>sport</code>):",
        reply_markup=kb.cancel_only_menu("settings:targets"),
    )
    await callback.answer()


@router.message(SettingsManagement.waiting_new_target_key)
async def add_target_key_received(message: Message, state: FSMContext):
    key = message.text.strip().lower()
    if not _KEY_RE.match(key):
        await message.answer(
            "⚠️ Kalit faqat kichik lotin harflar, raqam va pastki chiziqdan iborat bo'lishi "
            "kerak, harf bilan boshlanishi shart (masalan: sport, til_markazi). Qaytadan yozing:"
        )
        return
    all_targets = {**CHANNEL_TARGETS, **await db.get_runtime_targets()}
    if key in all_targets:
        await message.answer("⚠️ Bu kalit allaqachon band. Boshqa kalit so'z kiriting:")
        return
    await state.update_data(new_target_key=key)
    await state.set_state(SettingsManagement.waiting_new_target_label)
    await message.answer(
        "✏️ Kanal yorlig'ini kiriting (menyuda ko'rinadi, emoji qo'shsangiz ham bo'ladi, "
        "masalan: <i>🏃 Sport Klub</i>):"
    )


@router.message(SettingsManagement.waiting_new_target_label)
async def add_target_label_received(message: Message, state: FSMContext):
    await state.update_data(new_target_label=message.text.strip()[:64])
    await state.set_state(SettingsManagement.waiting_new_target_channel_id)
    await message.answer(
        "📢 Kanal username (<code>@kanalim</code>) yoki ID sini kiriting "
        "(bot shu kanalda admin bo'lishi shart!):"
    )


@router.message(SettingsManagement.waiting_new_target_channel_id)
async def add_target_channel_id_received(message: Message, state: FSMContext):
    await state.update_data(new_target_channel_id=message.text.strip())
    await state.set_state(SettingsManagement.waiting_new_target_topic)
    await message.answer(
        "🎯 Bu kanal/tashkilot uchun qisqa tavsif yozing — AI kontent yaratganda shu "
        "kontekstdan foydalanadi (masalan: <i>Sport klub — bolalar va kattalar uchun "
        "jismoniy tarbiya guruhlari</i>):"
    )


@router.message(SettingsManagement.waiting_new_target_topic)
async def add_target_topic_received(message: Message, state: FSMContext):
    await state.update_data(new_target_topic=message.text.strip())
    await state.set_state(SettingsManagement.waiting_new_target_brand_name)
    data = await state.get_data()
    await message.answer(
        "🖌 Rasmlarda ko'rinadigan brend nomini kiriting (emojisiz, masalan: "
        f"<i>{data['new_target_label']}</i> emojisiz varianti):"
    )


@router.message(SettingsManagement.waiting_new_target_brand_name)
async def add_target_brand_name_received(message: Message, state: FSMContext):
    data = await state.get_data()
    brand_name = message.text.strip()[:64]

    # Logotip/rang/kontakt uchun standart qiymatlar — mavjud (birinchi) targetdan meros olinadi,
    # keyinroq TARGET_<KALIT>_* environment o'zgaruvchilari orqali aniq sozlash mumkin.
    fallback = next(iter(CHANNEL_TARGETS.values()), {
        "logo_path": "", "accent_color": "#2033E9", "contact_footer": "",
    })

    key = data["new_target_key"]
    target = {
        "label": data["new_target_label"],
        "channel_id": data["new_target_channel_id"],
        "topic": data["new_target_topic"],
        "brand_name": brand_name,
        "logo_path": fallback["logo_path"],
        "accent_color": fallback["accent_color"],
        "contact_footer": "",  # yangi tashkilotning kontakti oldingisidan farq qilishi mumkin
    }
    await db.add_runtime_target(key, target)
    await state.clear()
    await message.answer(
        f"✅ <b>{target['label']}</b> kanal sifatida qo'shildi!\n\n"
        "Rasmlarga hozircha standart logotip/rang qo'llanadi va kontakt bloki bo'sh — "
        "buni o'zgartirish kerak bo'lsa ayting, birga sozlaymiz.",
        reply_markup=kb.back_to_menu(),
    )


@router.callback_query(F.data.startswith("ask_remove_target:"))
async def ask_remove_target(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    await callback.message.edit_text(
        f"🗑 <code>{key}</code> kanalini o'chirishni tasdiqlaysizmi? "
        "(bu faqat botdagi ro'yxatdan o'chiradi, kanalning o'zi o'zgarmaydi)",
        reply_markup=kb.confirm_remove_target(key),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_target:"))
async def remove_target(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    await db.remove_runtime_target(key)
    await callback.message.edit_text(f"✅ <code>{key}</code> kanali ro'yxatdan o'chirildi.")
    await callback.answer()
