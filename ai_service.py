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
from config import OPENAI_API_KEY, TEXT_MODEL, IMAGE_MODEL, CHANNEL_TOPIC, IMAGE_STYLE, IMAGE_SIZE
from branding import add_branding

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

IMAGES_DIR = "generated_images"
os.makedirs(IMAGES_DIR, exist_ok=True)


def _truncate(text: str, max_len: int) -> str:
    """Telegram chekloviga mos matnni qisqartirish."""
    return text if len(text) <= max_len else text[:max_len - 1] + "…"


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


async def generate_post(topic: str | None = None) -> dict:
    """
    Kanal uchun oddiy post matni generatsiya qiladi.
    topic berilmasa, AI kanal mavzusidan kelib chiqib o'zi tanlaydi.
    Natija: {"title": str, "text": str, "image_prompt": str}
    """
    topic_line = f'Mavzu: "{topic}".' if topic else (
        f"Mavzuni o'zing tanla, kanal yo'nalishi: {CHANNEL_TOPIC}."
    )
    system_prompt = (
        "Sen Telegram kanali uchun professional kontent-menejer va bir vaqtning o'zida "
        "tajribali art-direktorsan. O'zbek tilida, qiziqarli, ma'lumotli va o'quvchini "
        "o'ziga tortadigan post matnini yozasan. Emoji ishlatasan lekin haddan tashqari ko'p emas.\n\n"
        "Bundan tashqari, shu postga MAZMUNAN ANIQ MOS keladigan, professional darajadagi "
        "rasm tavsifini (image_prompt) tuzasan. Bu tavsif quyidagilarni albatta o'z ichiga olishi kerak "
        "(ingliz tilida yoz, chunki rasm modeli shunda yaxshiroq tushunadi):\n"
        "1) Postning ASOSIY G'OYASINI aniq aks ettiruvchi markaziy obraz/metafora "
        "(masalan mavzu 'Python ro'yxatlar' bo'lsa - kod bloklari yoki ma'lumotlar tuzilmasini "
        "ramziy tasvirlaydigan vizual, shunchaki umumiy 'noutbuk' emas)\n"
        "2) Kompozitsiya va fokus nuqtasi (nima markazda, nima fonda)\n"
        "3) Kayfiyat/uslub (masalan: futuristik, minimalist, energetik)\n"
        "Rasmda hech qanday matn, harf yoki yozuv bo'lmasligini alohida ta'kidla. "
        "image_prompt 2-3 gapdan iborat, aniq va tasvirlashga oson bo'lsin - umumiy so'zlardan "
        "('technology', 'business' kabi) qoching, mavzuga xos detallar yozing.\n\n"
        "Faqat quyidagi JSON formatda javob ber, boshqa hech narsa yozma: "
        '{"title": "post sarlavhasi", "text": "postning to\'liq matni (300-600 belgi)", '
        '"image_prompt": "yuqoridagi talablarga mos, batafsil va aniq rasm tavsifi (ingliz tilida)"}'
    )
    user_prompt = f"{topic_line} Kanal yo'nalishi: {CHANNEL_TOPIC}. Post yoz."
    raw = await _chat(system_prompt, user_prompt)
    data = json.loads(raw)
    return data


async def generate_quiz(topic: str | None = None) -> dict:
    """
    Quiz (viktorina) generatsiya qiladi - 4 variant va to'g'ri javob bilan.
    Natija: {"question": str, "options": [str,str,str,str], "correct_index": int, "explanation": str}
    """
    topic_line = f'Mavzu: "{topic}".' if topic else (
        f"Mavzuni o'zing tanla, kanal yo'nalishi: {CHANNEL_TOPIC}."
    )
    system_prompt = (
        "Sen Telegram kanali uchun quiz (viktorina) tuzuvchisan. "
        "O'zbek tilida qiziqarli va bilim beruvchi savol tuzasan. "
        "MUHIM CHEKLOVLAR (Telegram API talabi):\n"
        "- question: maksimal 255 belgi\n"
        "- har bir variant (option): maksimal 90 belgi\n"
        "- explanation: maksimal 200 belgi\n"
        "Faqat quyidagi JSON formatda javob ber, boshqa hech narsa yozma: "
        '{"question": "savol matni (max 255 belgi)", '
        '"options": ["variant1 (max 90 b)", "variant2 (max 90 b)", "variant3 (max 90 b)", "variant4 (max 90 b)"], '
        '"correct_index": 0, "explanation": "to\'g\'ri javob izohi (max 200 belgi)"}'
    )
    user_prompt = f"{topic_line} Kanal yo'nalishi: {CHANNEL_TOPIC}. Bitta quiz savoli tuz."
    raw = await _chat(system_prompt, user_prompt)
    data = json.loads(raw)
    # Xavfsizlik uchun qo'shimcha truncation
    data["question"] = _truncate(data.get("question", ""), 255)
    data["options"] = [_truncate(opt, 90) for opt in data.get("options", [])]
    data["explanation"] = _truncate(data.get("explanation", ""), 200)
    return data


async def generate_poll(topic: str | None = None) -> dict:
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
    user_prompt = f"{topic_line} Kanal yo'nalishi: {CHANNEL_TOPIC}. Bitta so'rovnoma tuz."
    raw = await _chat(system_prompt, user_prompt)
    data = json.loads(raw)
    # Xavfsizlik uchun qo'shimcha truncation
    data["question"] = _truncate(data.get("question", ""), 255)
    data["options"] = [_truncate(opt, 90) for opt in data.get("options", [])]
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
    """Foydalanuvchi 'boshqa variant' desa, avvalgisidan farqli yangi variant yaratadi."""
    if content_type == "post":
        base = await generate_post(topic)
    elif content_type == "quiz":
        base = await generate_quiz(topic)
    else:
        base = await generate_poll(topic)
    return base
