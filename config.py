"""
Konfiguratsiya fayli.
Barcha maxfiy ma'lumotlar (tokenlar, kalitlar) .env faylidan o'qiladi.
"""
import os
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# --- Vaqt zonasi ---
TIMEZONE_STR = os.getenv("TIMEZONE", "Asia/Tashkent")
try:
    TIMEZONE = ZoneInfo(TIMEZONE_STR)
except Exception:
    TIMEZONE = ZoneInfo("Asia/Tashkent")

# --- Telegram sozlamalari ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Kanal ID yoki username (masalan: @mening_kanalim yoki -1001234567890)
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

# Admin(lar) Telegram ID raqami(lari). Bir nechta bo'lsa vergul bilan ajrating: "123456,789012"
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# --- OpenAI sozlamalari ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Matn generatsiyasi uchun model
TEXT_MODEL = os.getenv("TEXT_MODEL", "gpt-5.5")

# Rasm generatsiyasi uchun model
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "gpt-image-2")

# --- Bot ichki sozlamalari ---
DB_PATH = os.getenv("DB_PATH", "bot_database.db")

# Generatsiya qilingan (va brendlangan) rasmlar saqlanadigan papka.
# Render kabi platformalarda bu qiymatni doimiy diskka (persistent disk) yo'naltiring,
# aks holda har deploy'da rasmlar o'chib ketadi.
IMAGES_DIR = os.getenv("IMAGES_DIR", "generated_images")

# Kanalning yagona vizual uslubi (brendi) - barcha rasmlar shu uslubda generatsiya qilinadi.
# Bo'sh qoldirsangiz, AI har safar o'zi mos uslub tanlaydi (uslublar bir-biriga o'xshamasligi mumkin).
IMAGE_STYLE = os.getenv(
    "IMAGE_STYLE",
    "modern flat-design digital illustration, clean minimalist tech aesthetic, "
    "soft gradient background (deep blue to purple), subtle geometric shapes, "
    "high contrast, professional and polished, no text or letters in the image"
)

# Rasm o'lchami: 1536x1024 (gorizontal, Telegram feed uchun eng yaxshi), 1024x1024 (kvadrat), 1024x1536 (vertikal)
IMAGE_SIZE = os.getenv("IMAGE_SIZE", "1536x1024")

# So'rovnomada bir nechta javob tanlash mumkinmi (true/false)
POLL_ALLOWS_MULTIPLE = os.getenv("POLL_ALLOWS_MULTIPLE", "false").lower() == "true"

# Har bir generatsiya qilingan rasmga avtomatik logotip va nom joylanadimi (barcha targetlar uchun)
ADD_BRANDING = os.getenv("ADD_BRANDING", "true").lower() == "true"


def _abs_path(raw: str) -> str:
    return raw if os.path.isabs(raw) else os.path.join(os.path.dirname(__file__), raw)


_DEFAULT_LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")


def _target_env(key: str, field: str, default: str = "") -> str:
    return os.getenv(f"TARGET_{key.upper()}_{field}", default)


# --- Kanal(lar) va brend(lar) ---
# Bot bir nechta turli kanalga (masalan turli tashkilot/brendga) xizmat qilishi mumkin —
# har biri o'z kanal ID'si, mavzusi, brend nomi, logotipi va kontakt ma'lumotiga ega.
#
# Ko'p-kanal sozlash uchun: TARGETS=kalit1,kalit2,... va har bir kalit uchun
# TARGET_<KALIT>_CHANNEL_ID, TARGET_<KALIT>_LABEL, TARGET_<KALIT>_TOPIC,
# TARGET_<KALIT>_BRAND_NAME, TARGET_<KALIT>_LOGO_PATH, TARGET_<KALIT>_ACCENT_COLOR,
# TARGET_<KALIT>_CONTACT_FOOTER kabi o'zgaruvchilarni belgilang.
# TARGETS bo'sh qoldirilsa — eski (bitta kanalli) CHANNEL_ID/BRAND_NAME/... sozlamalari ishlatiladi.
_target_keys = [k.strip() for k in os.getenv("TARGETS", "").split(",") if k.strip()]

CHANNEL_TARGETS: dict[str, dict] = {}
if _target_keys:
    for _key in _target_keys:
        CHANNEL_TARGETS[_key] = {
            "label": _target_env(_key, "LABEL", _key),
            "channel_id": _target_env(_key, "CHANNEL_ID", ""),
            "topic": _target_env(_key, "TOPIC", ""),
            "brand_name": _target_env(_key, "BRAND_NAME", _key),
            "logo_path": _abs_path(_target_env(_key, "LOGO_PATH", _DEFAULT_LOGO_PATH)),
            "accent_color": _target_env(_key, "ACCENT_COLOR", "#2033E9"),
            "contact_footer": _target_env(_key, "CONTACT_FOOTER", "").replace("\\n", "\n"),
        }
else:
    CHANNEL_TARGETS["default"] = {
        "label": os.getenv("BRAND_NAME", "Kanal"),
        "channel_id": os.getenv("CHANNEL_ID", ""),
        "topic": os.getenv("CHANNEL_TOPIC", "IT, dasturlash va texnologiyalar"),
        "brand_name": os.getenv("BRAND_NAME", "Kanal"),
        "logo_path": _abs_path(os.getenv("LOGO_PATH", _DEFAULT_LOGO_PATH)),
        "accent_color": os.getenv("BRAND_ACCENT_COLOR", "#2033E9"),
        "contact_footer": os.getenv("POST_CONTACT_FOOTER", "").replace("\\n", "\n"),
    }

DEFAULT_TARGET_KEY = next(iter(CHANNEL_TARGETS))


def get_target(key: str | None = None) -> dict:
    """Berilgan target kaliti uchun sozlamalarni qaytaradi (topilmasa/berilmasa — birinchisi)."""
    if key and key in CHANNEL_TARGETS:
        return CHANNEL_TARGETS[key]
    return CHANNEL_TARGETS[DEFAULT_TARGET_KEY]


# Rejalashtirilgan postlarni necha soniyada bir tekshirish
SCHEDULER_CHECK_INTERVAL = 30

# Eski rasm fayllarini necha kundan keyin o'chirish (0 = o'chirmaslik)
IMAGE_CLEANUP_DAYS = int(os.getenv("IMAGE_CLEANUP_DAYS", "7"))

# --- Joylashda xatolik bo'lganda qayta urinish ---
# Necha marta urinilgach, post "failed" deb belgilanadi va qayta avtomatik urinilmaydi
SCHEDULE_MAX_RETRIES = int(os.getenv("SCHEDULE_MAX_RETRIES", "5"))
# Urinishlar orasidagi boshlang'ich kutish vaqti (daqiqa) — har urinishda 2 barobar oshadi
SCHEDULE_RETRY_BASE_MINUTES = int(os.getenv("SCHEDULE_RETRY_BASE_MINUTES", "2"))
# Urinishlar orasidagi maksimal kutish vaqti (daqiqa)
SCHEDULE_RETRY_MAX_MINUTES = int(os.getenv("SCHEDULE_RETRY_MAX_MINUTES", "60"))

# --- AI generatsiya uchun rate-limit ---
# Bir soat ichida nechta kontent generatsiya qilish mumkinligi (OpenAI xarajatini nazorat qilish uchun)
MAX_GENERATIONS_PER_HOUR = int(os.getenv("MAX_GENERATIONS_PER_HOUR", "20"))

# Rejalashtirilganlar ro'yxatida bir sahifada nechta element ko'rsatiladi
SCHEDULED_PAGE_SIZE = int(os.getenv("SCHEDULED_PAGE_SIZE", "8"))

# Admin bo'lmagan foydalanuvchiga "ruxsat yo'q" xabari bilan birga yuboriladigan stiker
# (Telegram'ning rasmiy "AnimatedEmojies" to'plamidagi 😔 stikeri)
UNAUTHORIZED_STICKER_ID = os.getenv(
    "UNAUTHORIZED_STICKER_ID",
    "CAACAgEAAxUAAWpme9wsVw8iqmKKezg5j3DKDd1eAAJxAgAC8LkwR76SIULuzaFKPQQ",
)
