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

# Kanal mavzusi/yo'nalishi - AI kontent generatsiya qilganda shu kontekstdan foydalanadi
CHANNEL_TOPIC = os.getenv("CHANNEL_TOPIC", "IT, dasturlash va texnologiyalar")

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

# --- Kanal brendi (logo + nom) ---
# Har bir generatsiya qilingan rasmga avtomatik logotip va kanal nomi joylanadimi
ADD_BRANDING = os.getenv("ADD_BRANDING", "true").lower() == "true"

# Kanal nomi (rasmda ko'rinadi)
BRAND_NAME = os.getenv("BRAND_NAME", "Iqtidor Academy")

# Logotip fayli manzili
LOGO_PATH = os.getenv("LOGO_PATH", os.path.join(os.path.dirname(__file__), "assets", "logo.png"))

# Brend rangida ajratuvchi chiziq (logotipingizdagi haqiqiy ko'k rang)
BRAND_ACCENT_COLOR = os.getenv("BRAND_ACCENT_COLOR", "#2033E9")

# Rejalashtirilgan postlarni necha soniyada bir tekshirish
SCHEDULER_CHECK_INTERVAL = 30

# Eski rasm fayllarini necha kundan keyin o'chirish (0 = o'chirmaslik)
IMAGE_CLEANUP_DAYS = int(os.getenv("IMAGE_CLEANUP_DAYS", "7"))
