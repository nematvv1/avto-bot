"""
Barcha inline tugmalar (klaviaturalar) shu yerda to'plangan.
"""
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✨ Yangi kontent yaratish", callback_data="menu:new_content")
    kb.button(text="📅 Rejalashtirilganlar", callback_data="menu:scheduled")
    kb.button(text="📊 Statistika", callback_data="menu:stats")
    kb.button(text="⚙️ Sozlamalar", callback_data="menu:settings")
    kb.button(text="📖 Qo'llanma", callback_data="menu:help")
    kb.adjust(1)
    return kb.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Bosh menyu", callback_data="menu:main")
    return kb.as_markup()


def target_choice_menu(targets: dict) -> InlineKeyboardMarkup:
    """Bir nechta kanal/tashkilot sozlangan bo'lsa, qaysi biri uchun kontent yaratishni tanlash."""
    kb = InlineKeyboardBuilder()
    for key, target in targets.items():
        kb.button(text=target["label"], callback_data=f"target:{key}")
    kb.button(text="⬅️ Bosh menyu", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def content_type_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Post", callback_data="type:post")
    kb.button(text="🧠 Quiz (viktorina)", callback_data="type:quiz")
    kb.button(text="📊 So'rovnoma (poll)", callback_data="type:poll")
    kb.button(text="⬅️ Bosh menyu", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def topic_choice_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🤖 AI o'zi mavzu tanlasin", callback_data="topic:auto")
    kb.button(text="✍️ Men mavzu beraman", callback_data="topic:manual")
    kb.button(text="⬅️ Orqaga", callback_data="menu:new_content")
    kb.adjust(1)
    return kb.as_markup()


def image_choice_menu() -> InlineKeyboardMarkup:
    """Post uchun rasm kerakmi yo'qmi so'raladi."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🖼 Ha, rasm bilan", callback_data="img:yes")
    kb.button(text="🚫 Yo'q, rasmsiz", callback_data="img:no")
    kb.adjust(1)
    return kb.as_markup()


def preview_actions(content_id: int, content_type: str = "post") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"approve:{content_id}")
    kb.button(text="✏️ Matnni tahrirlash", callback_data=f"edit:{content_id}")
    if content_type in ("quiz", "poll"):
        kb.button(text="🔡 Variantlarni tahrirlash", callback_data=f"editopts:{content_id}")
    if content_type == "quiz":
        kb.button(text="💬 Izohni tahrirlash", callback_data=f"editexpl:{content_id}")
    kb.button(text="🔄 Qayta generatsiya", callback_data=f"regen:{content_id}")
    kb.button(text="❌ Bekor qilish", callback_data=f"reject:{content_id}")
    kb.adjust(1)
    return kb.as_markup()


def correct_option_menu(content_id: int, options: list) -> InlineKeyboardMarkup:
    """Variantlar yangilangach, to'g'ri javobni tanlash uchun."""
    kb = InlineKeyboardBuilder()
    for i, opt in enumerate(options):
        label = opt if len(opt) <= 40 else opt[:37] + "..."
        kb.button(text=f"✅ {label}", callback_data=f"setcorrect:{content_id}:{i}")
    kb.adjust(1)
    return kb.as_markup()


def publish_time_menu(content_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Hozir yuborish", callback_data=f"publish_now:{content_id}")
    kb.button(text="🕒 Vaqt belgilash", callback_data=f"publish_schedule:{content_id}")
    kb.adjust(1)
    return kb.as_markup()


def schedule_quick_menu(content_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⏰ 1 soatdan keyin", callback_data=f"quicksched:1h:{content_id}")
    kb.button(text="🌆 Bugun kechqurun 19:00", callback_data=f"quicksched:today19:{content_id}")
    kb.button(text="🌅 Ertaga ertalab 09:00", callback_data=f"quicksched:tom09:{content_id}")
    kb.button(text="✍️ Sana/vaqtni o'zim yozaman", callback_data=f"quicksched:manual:{content_id}")
    kb.adjust(1)
    return kb.as_markup()


def scheduled_item_actions(content_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 O'chirish", callback_data=f"ask_delete_scheduled:{content_id}")
    kb.adjust(1)
    return kb.as_markup()


def failed_item_actions(content_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔁 Qayta urinish", callback_data=f"retry_failed:{content_id}")
    kb.button(text="🗑 O'chirish", callback_data=f"ask_delete_scheduled:{content_id}")
    kb.adjust(1)
    return kb.as_markup()


def scheduled_nav(offset: int, page_size: int, total: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if offset > 0:
        kb.button(text="⬅️ Oldingi", callback_data=f"menu:scheduled:{max(0, offset - page_size)}")
    if offset + page_size < total:
        kb.button(text="Keyingi ➡️", callback_data=f"menu:scheduled:{offset + page_size}")
    kb.button(text="🏠 Bosh menyu", callback_data="menu:main")
    kb.adjust(2, 1)
    return kb.as_markup()


def confirm_delete_scheduled(content_id: int) -> InlineKeyboardMarkup:
    """Rejalashtirilgan postni o'chirishdan oldin tasdiqlash so'raydi."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ha, o'chir", callback_data=f"delete_scheduled:{content_id}")
    kb.button(text="❌ Yo'q, bekor", callback_data=f"cancel_delete:{content_id}")
    kb.adjust(2)
    return kb.as_markup()


# ---------- Sozlamalar: adminlar va kanallar boshqaruvi ----------

def settings_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Adminlar", callback_data="settings:admins")
    kb.button(text="📡 Kanallar", callback_data="settings:targets")
    kb.button(text="⬅️ Bosh menyu", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def admins_action_menu(runtime_admin_ids: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for admin_id in runtime_admin_ids:
        kb.button(text=f"🗑 {admin_id} ni o'chirish", callback_data=f"ask_remove_admin:{admin_id}")
    kb.button(text="➕ Admin qo'shish", callback_data="add_admin")
    kb.button(text="⬅️ Sozlamalar", callback_data="menu:settings")
    kb.adjust(1)
    return kb.as_markup()


def confirm_remove_admin(admin_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ha, o'chir", callback_data=f"remove_admin:{admin_id}")
    kb.button(text="❌ Yo'q, bekor", callback_data="settings:admins")
    kb.adjust(2)
    return kb.as_markup()


def targets_action_menu(runtime_target_keys: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key in runtime_target_keys:
        kb.button(text=f"🗑 {key} ni o'chirish", callback_data=f"ask_remove_target:{key}")
    kb.button(text="➕ Kanal qo'shish", callback_data="add_target")
    kb.button(text="⬅️ Sozlamalar", callback_data="menu:settings")
    kb.adjust(1)
    return kb.as_markup()


def confirm_remove_target(key: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ha, o'chir", callback_data=f"remove_target:{key}")
    kb.button(text="❌ Yo'q, bekor", callback_data="settings:targets")
    kb.adjust(2)
    return kb.as_markup()


def cancel_only_menu(back_callback: str = "menu:settings") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Bekor qilish", callback_data=back_callback)
    return kb.as_markup()
