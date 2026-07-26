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

# Har bir "post" turidagi kontent oxiriga avtomatik qo'shiladigan kontakt bloki
# (bog'lanish uchun raqamlar, ro'yxatdan o'tish manzili va h.k.). Bo'sh qoldirilsa, qo'shilmaydi.
# .env faylida qatorlarni "\n" bilan ajrating (masalan: "Qator1\nQator2").
_post_contact_footer_raw = os.getenv("POST_CONTACT_FOOTER", "")
POST_CONTACT_FOOTER = _post_contact_footer_raw.replace("\\n", "\n")

# --- Kanal brendi (logo + nom) ---
# Har bir generatsiya qilingan rasmga avtomatik logotip va kanal nomi joylanadimi
ADD_BRANDING = os.getenv("ADD_BRANDING", "true").lower() == "true"

# Kanal nomi (rasmda ko'rinadi)
BRAND_NAME = os.getenv("BRAND_NAME", "Iqtidor Academy")

# Logotip fayli manzili. Nisbiy yo'l berilsa (masalan "assets/logo.png"), loyiha papkasiga
# nisbatan hal qilinadi — shunda bot qaysi joriy papkadan ishga tushirilishidan qat'i nazar ishlaydi.
_logo_path_raw = os.getenv("LOGO_PATH", os.path.join(os.path.dirname(__file__), "assets", "logo.png"))
LOGO_PATH = (
    _logo_path_raw if os.path.isabs(_logo_path_raw)
    else os.path.join(os.path.dirname(__file__), _logo_path_raw)
)

# Brend rangida ajratuvchi chiziq (logotipingizdagi haqiqiy ko'k rang)
BRAND_ACCENT_COLOR = os.getenv("BRAND_ACCENT_COLOR", "#2033E9")

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
