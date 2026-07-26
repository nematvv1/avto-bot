"""
OpenAI API orqali kontent generatsiya qilish moduli.
- Matn: gpt-5.5 (chat completions)
- Rasm: gpt-image-2 (image generation)
"""
import json
import base64
import os
import uuid
from openai import AsyncOpenAI
from config import (
    OPENAI_API_KEY, TEXT_MODEL, IMAGE_MODEL, CHANNEL_TOPIC, IMAGE_STYLE, IMAGE_SIZE, IMAGES_DIR,
)
from branding import add_branding

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

os.makedirs(IMAGES_DIR, exist_ok=True)

MIN_POLL_OPTIONS = 2
MAX_POLL_OPTIONS = 6


class ContentValidationError(Exception):
    """AI qaytargan kontent talablarga mos kelmasa ko'tariladi."""


def _truncate(text: str, max_len: int) -> str:
    """Telegram chekloviga mos matnni qisqartirish."""
    return text if len(text) <= max_len else text[:max_len - 1] + "…"


def _avoid_line(previous_text: str | None) -> str:
    if not previous_text:
        return ""
    snippet = previous_text.strip().replace("\n", " ")[:300]
    return (
        f"\n\nMUHIM: Bu — qayta generatsiya so'rovi. Oldingi variant quyidagicha edi, "
        f"undan mazmunan va uslubda ANIQ FARQ QILADIGAN, yangi va original variant yoz "
        f"(bir xil g'oyani takrorlama):\n\"{snippet}\""
    )


async def _chat(system_prompt: str, user_prompt: str) -> str:
    """gpt-5.5 orqali matn generatsiya qilish, JSON formatda javob talab qilinadi."""
    response = await client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


async def generate_post(topic: str | None = None, previous_text: str | None = None) -> dict:
    """
    Kanal uchun oddiy post matni generatsiya qiladi.
    topic berilmasa, AI kanal mavzusidan kelib chiqib o'zi tanlaydi.
    Natija: {"title": str, "text": str, "image_prompt": str}
    """
    topic_line = f'Mavzu: "{topic}".' if topic else (
        f"Mavzuni o'zing tanla, kanal yo'nalishi: {CHANNEL_TOPIC}."
    )
    system_prompt = (
        "Sen o'quv markazi (ta'lim markazi) Telegram kanali uchun reklama/e'lon postlari yozadigan "
        "tajribali marketing-mutaxassis va bir vaqtning o'zida art-direktorsan. Postlar ko'pincha "
        "yangi kurs/guruhga ro'yxatga olish e'loni bo'ladi.\n\n"
        "MATN (text) uchun QAT'IY STRUKTURA — quyidagi bo'limlarni shu tartibda, ORASIDA BO'SH QATOR "
        "QOLDIRIB yoz (hammasini bitta uzun paragrafga siqma — bu O'QILMAYDI):\n"
        "1-QATOR: emoji + <b>qalin sarlavha</b> — kurs/mavzu nomi va harakat (masalan yangi guruh, "
        "start berilishi). 'Zamonaviy dunyoda...', 'Bugungi kunda...', 'Bilasizmi...' kabi charchagan "
        "klishelardan QOCH.\n"
        "KEYINGI QATOR (bo'sh qatordan keyin): 1-2 ta QISQA, kuchli gap — muammo/og'riq nuqtasi yoki "
        "kutilmagan KONKRET fakt/raqam bilan diqqatni tortadi (masalan: 'Kompyuter \"bilaman\" "
        "deganlarning aksariyati faylni to'g'ri saqlolmaydi.').\n"
        "KEYINGI BLOK (bo'sh qatordan keyin): emoji + <b>qalin mini-sarlavha</b> (masalan 'Nimalarni "
        "o'rganasiz:'), so'ng har biri YANGI QATORDA, '- ' bilan boshlanadigan 3-5 ta QISQA (bitta "
        "qatorlik) aniq foyda/ko'nikma ro'yxati.\n"
        "OXIRGI QATOR (bo'sh qatordan keyin): qisqa, chaqiruvchi CTA jumla yoki ritorik savol "
        "(masalan 'Birinchi qadamni qo'ymoqchimisiz?'). BU YERDA HECH QANDAY TELEFON RAQAM, "
        "FOYDALANUVCHI NOMI YOKI 'ro'yxatdan o'tish' havolasi YOZMA — bog'lanish ma'lumotlari "
        "postga AVTOMATIK, alohida qo'shiladi, ularni o'zing yozsang IKKI MARTA chiqib qoladi.\n\n"
        "MUHIM: joylar soni, narx, aniq sana kabi KONKRET raqamli va'dalarni FAQAT foydalanuvchi "
        "(admin) mavzu sifatida bergan bo'lsa yoz. Agar bunday aniq raqam berilmagan bo'lsa, "
        "TO'QIB CHIQARMA — o'rniga umumiy chaqiruv/qiziqish uyg'otuvchi CTA yoz.\n\n"
        "O'zbek tilida, tabiiy va samimiy ohangda yoz. Emoji 3-5 ta yetarli, har birini bo'lim "
        "boshida ishlat (matn ichiga tiqishtirma). text umumiy uzunligi (bo'sh qatorlar bilan birga) "
        "500-850 belgi oralig'ida bo'lsin.\n\n"
        "RASM (image_prompt) uchun qoidalar — shu postga MAZMUNAN ANIQ MOS keladigan, professional "
        "darajadagi rasm tavsifini tuzasan (ingliz tilida yoz, chunki rasm modeli shunda yaxshiroq "
        "tushunadi):\n"
        "1) GENERIC STOK-IKONKALARDAN QOCH: yolg'iz papka (folder), lampochka, tishli g'ildirak "
        "(gear), qog'oz-qalam, umumiy 'checklist' kabi klishe, hech narsa aytmaydigan obrazlarni "
        "ISHLATMA. Buning o'rniga, mavzu bilan bog'liq ANIQ sahna tanla: masalan odam(lar) noutbuk/"
        "kompyuter ekrani oldida aniq dastur interfeysi (jadval, hujjat, kod) bilan ishlayotgan "
        "holat, yoki mavzuga xos ANIQ vizual metafora (masalan mavzu 'Python ro'yxatlar' bo'lsa - "
        "kod bloklari yoki ma'lumotlar tuzilmasini ramziy tasvirlaydigan vizual).\n"
        "2) KOMPOZITSIYA SODDA bo'lishi SHART: bitta aniq fokus sahna/obyekt, ortiqcha mayda ikonka, "
        "gadjet yoki dekorativ shakllarni ko'paytirmang — rasmning katta qismi bo'sh/sokin fon "
        "(negative space) bo'lsin, band/to'lib-toshgan sahna emas.\n"
        "3) Kayfiyat/uslub (masalan: futuristik, minimalist, energetik, ilhomlantiruvchi)\n"
        "Rasmda hech qanday matn, harf yoki yozuv bo'lmasligini alohida ta'kidla. "
        "image_prompt 2-3 gapdan iborat, aniq va tasvirlashga oson bo'lsin - umumiy so'zlardan "
        "('technology', 'business' kabi) qoching, mavzuga xos detallar yozing.\n\n"
        "Faqat quyidagi JSON formatda javob ber, boshqa hech narsa yozma (text ichida \\n bilan "
        "qator ko'chirish va bo'sh qatorlarni ANIQ saqla): "
        '{"title": "post sarlavhasi", "text": "yuqoridagi struktura bo\'yicha, \\n bilan formatlangan '
        'to\'liq matn (500-850 belgi)", '
        '"image_prompt": "yuqoridagi talablarga mos, sodda kompozitsiyali, aniq rasm tavsifi (ingliz tilida)"}'
    )
    user_prompt = f"{topic_line} Kanal yo'nalishi: {CHANNEL_TOPIC}. Post yoz.{_avoid_line(previous_text)}"
    raw = await _chat(system_prompt, user_prompt)
    data = json.loads(raw)
    if not data.get("title") or not data.get("text"):
        raise ContentValidationError("AI post uchun sarlavha yoki matn qaytarmadi.")
    return data


async def generate_quiz(topic: str | None = None, previous_text: str | None = None) -> dict:
    """
    Quiz (viktorina) generatsiya qiladi - 4 variant va to'g'ri javob bilan.
    Natija: {"question": str, "options": [str,str,str,str], "correct_index": int, "explanation": str}
    """
    topic_line = f'Mavzu: "{topic}".' if topic else (
        f"Mavzuni o'zing tanla, kanal yo'nalishi: {CHANNEL_TOPIC}."
    )
    system_prompt = (
        "Sen Telegram kanali uchun quiz (viktorina) tuzuvchisan. "
        "O'zbek tilida qiziqarli va bilim beruvchi savol tuzasan.\n\n"
        "MAVZUGA SODIQLIK: agar foydalanuvchi aniq mavzu bergan bo'lsa, savol ANIQ SHU MAVZUGA oid "
        "bo'lishi SHART — mavzuni boshqa yo'nalishga burib yubormang, umumiy kanal yo'nalishi "
        "(context) faqat fon sifatida, mavzuni almashtirmasdan hisobga olinsin. Agar berilgan mavzu "
        "ochiq/subyektiv fikr so'raydigan (masalan 'sizningcha...', 'nima uchun foydalanasiz' kabi) "
        "bo'lsa, o'sha mavzu ORQASIDAGI aniq, ob'ektiv FAKTni top va shu fakt asosida savol tuz — "
        "lekin mavzudan chetlashma.\n\n"
        "VARIANTLAR SIFATI (juda muhim): noto'g'ri variantlar (distractors) ISHONARLI va mavzuga "
        "OID bo'lishi SHART — ya'ni bilimi yetarli bo'lmagan odam chindan ham adashishi mumkin "
        "bo'lgan, jiddiy eshitiladigan javoblar. Kulgili, absurd, mavzuga aloqasi yo'q yoki "
        "birinchi qarashda ham noto'g'riligi shubhasiz bo'lgan variantlar YOZISH QAT'IYAN "
        "TAQIQLANADI (masalan 'kompyuterni elektrsiz ishlatish' kabi bema'ni javoblar YARATMA).\n\n"
        "MUHIM CHEKLOVLAR (Telegram API talabi):\n"
        "- question: maksimal 255 belgi\n"
        "- aniq 4 ta variant (options) bo'lishi shart\n"
        "- har bir variant (option): maksimal 90 belgi\n"
        "- correct_index: 0 dan 3 gacha, options ro'yxatidagi to'g'ri javob indeksi\n"
        "- explanation: maksimal 200 belgi\n"
        "Faqat quyidagi JSON formatda javob ber, boshqa hech narsa yozma: "
        '{"question": "savol matni (max 255 belgi)", '
        '"options": ["variant1 (max 90 b)", "variant2 (max 90 b)", "variant3 (max 90 b)", "variant4 (max 90 b)"], '
        '"correct_index": 0, "explanation": "to\'g\'ri javob izohi (max 200 belgi)"}'
    )
    user_prompt = (
        f"{topic_line} Bitta quiz savoli tuz. Mavzuga qat'iy amal qil "
        f"(kanal yo'nalishi faqat qo'shimcha kontekst uchun: {CHANNEL_TOPIC})."
        f"{_avoid_line(previous_text)}"
    )
    raw = await _chat(system_prompt, user_prompt)
    data = json.loads(raw)

    options = data.get("options") or []
    correct_index = data.get("correct_index")
    if not data.get("question") or not isinstance(options, list) or len(options) < 2:
        raise ContentValidationError("AI quiz uchun savol yoki variantlarni to'g'ri qaytarmadi.")
    if not isinstance(correct_index, int) or not (0 <= correct_index < len(options)):
        raise ContentValidationError("AI quiz uchun to'g'ri javob indeksini noto'g'ri qaytardi.")

    # Xavfsizlik uchun qo'shimcha truncation
    data["question"] = _truncate(data.get("question", ""), 255)
    data["options"] = [_truncate(opt, 90) for opt in options]
    data["explanation"] = _truncate(data.get("explanation", ""), 200)
    data["correct_index"] = correct_index
    return data


async def generate_poll(topic: str | None = None, previous_text: str | None = None) -> dict:
    """
    So'rovnoma (poll) generatsiya qiladi - savol va 2-6 variant.
    Natija: {"question": str, "options": [str, ...]}
    """
    topic_line = f'Mavzu: "{topic}".' if topic else (
        f"Mavzuni o'zing tanla, kanal yo'nalishi: {CHANNEL_TOPIC}."
    )
    system_prompt = (
        "Sen Telegram kanali uchun qiziqarli so'rovnoma (poll) tuzuvchisan. "
        "O'zbek tilida, obunachilarni fikr bildirishga undaydigan savol tuzasan. "
        "MUHIM CHEKLOVLAR (Telegram API talabi):\n"
        "- question: maksimal 255 belgi\n"
        "- har bir variant (option): maksimal 90 belgi, 2-6 ta variant\n"
        "Faqat quyidagi JSON formatda javob ber, boshqa hech narsa yozma: "
        '{"question": "so\'rovnoma savoli (max 255 belgi)", '
        '"options": ["variant1 (max 90 b)", "variant2 (max 90 b)", "variant3 (max 90 b)"]}'
    )
    user_prompt = f"{topic_line} Kanal yo'nalishi: {CHANNEL_TOPIC}. Bitta so'rovnoma tuz.{_avoid_line(previous_text)}"
    raw = await _chat(system_prompt, user_prompt)
    data = json.loads(raw)

    options = data.get("options") or []
    if not data.get("question") or not isinstance(options, list):
        raise ContentValidationError("AI so'rovnoma uchun savol yoki variantlarni to'g'ri qaytarmadi.")
    if not (MIN_POLL_OPTIONS <= len(options) <= MAX_POLL_OPTIONS):
        raise ContentValidationError(
            f"AI so'rovnoma uchun {len(options)} ta variant qaytardi "
            f"({MIN_POLL_OPTIONS}-{MAX_POLL_OPTIONS} ta bo'lishi kerak)."
        )

    # Xavfsizlik uchun qo'shimcha truncation
    data["question"] = _truncate(data.get("question", ""), 255)
    data["options"] = [_truncate(opt, 90) for opt in options]
    return data


async def generate_image(prompt: str) -> str:
    """
    gpt-image-2 orqali post matniga mos, professional darajadagi rasm generatsiya qiladi.
    Kanal uchun belgilangan yagona vizual uslub (IMAGE_STYLE) va sifat kuchaytirgichlari
    postning aniq tavsifiga (prompt) qo'shib yuboriladi - shu orqali rasmlar ham mazmunan
    postga mos, ham vizual jihatdan bir xil "brend"ga ega bo'ladi.
    Rasmni diskka saqlaydi va fayl yo'lini qaytaradi.
    """
    full_prompt = (
        f"{prompt}\n\n"
        f"Visual style (apply consistently): {IMAGE_STYLE}.\n"
        "Composition requirements: ONE clear focal subject only, generous negative space, "
        "uncluttered and minimal — do NOT scatter multiple small icons, gadgets, gears, or "
        "decorative shapes around the scene. Fewer, larger, more deliberate visual elements "
        "beat many small ones. If in doubt, simplify further.\n"
        "Quality requirements: professional, polished, high production value, "
        "sharp focus, well balanced composition, no watermarks, no logos, "
        "no distorted shapes, no text/letters/numbers anywhere in the image. "
        "Keep the bottom 15% of the image visually simple/uncluttered (soft background only, "
        "no important subject details there) since a brand footer will be overlaid on it."
    )

    result = await client.images.generate(
        model=IMAGE_MODEL,
        prompt=full_prompt,
        size=IMAGE_SIZE,
        quality="high",
    )
    b64_data = result.data[0].b64_json
    image_bytes = base64.b64decode(b64_data)

    filename = os.path.join(IMAGES_DIR, f"{uuid.uuid4().hex}.png")
    with open(filename, "wb") as f:
        f.write(image_bytes)

    # Rasmga kanal logotipi va nomini avtomatik joylash (professional brend ko'rinishi uchun)
    branded_path = add_branding(filename)
    return branded_path


async def regenerate_text_variation(content_type: str, previous_text: str, topic: str | None) -> dict:
    """Foydalanuvchi 'boshqa variant' desa, avvalgisidan mazmunan farqli yangi variant yaratadi."""
    if content_type == "post":
        return await generate_post(topic, previous_text=previous_text)
    elif content_type == "quiz":
        return await generate_quiz(topic, previous_text=previous_text)
    else:
        return await generate_poll(topic, previous_text=previous_text)
