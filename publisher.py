"""
Tasdiqlangan kontentni haqiqiy Telegram kanaliga joylash.
Bu modul ham "hozir yuborish" tugmasi, ham rejalashtiruvchi (scheduler) tomonidan ishlatiladi.
"""
import json
from aiogram import Bot
from aiogram.types import FSInputFile
from config import CHANNEL_ID, POLL_ALLOWS_MULTIPLE
import database as db
from utils import safe_truncate_html


async def publish_content(bot: Bot, content: dict) -> int:
    """
    content - database.get_content() dan qaytgan dict.
    Kanalga joylaydi va channel_message_id ni qaytaradi.
    """
    content_type = content["content_type"]

    if content_type == "post":
        if content.get("image_path"):
            photo = FSInputFile(content["image_path"])
            msg = await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo,
                caption=safe_truncate_html(content["text"], 1024),
            )
        else:
            msg = await bot.send_message(
                chat_id=CHANNEL_ID, text=safe_truncate_html(content["text"], 4096)
            )
        message_id = msg.message_id

    elif content_type == "quiz":
        options = json.loads(content["options_json"])
        # Telegram API: savol max 300, har bir variant max 100 belgi
        safe_options = [opt[:100] for opt in options]
        msg = await bot.send_poll(
            chat_id=CHANNEL_ID,
            question=content["text"][:300],
            options=safe_options,
            type="quiz",
            correct_option_id=content["correct_option"],
            explanation=content.get("explanation") or None,
            is_anonymous=True,
        )
        message_id = msg.message_id

    elif content_type == "poll":
        options = json.loads(content["options_json"])
        # Telegram API: savol max 300, har bir variant max 100 belgi
        safe_options = [opt[:100] for opt in options]
        msg = await bot.send_poll(
            chat_id=CHANNEL_ID,
            question=content["text"][:300],
            options=safe_options,
            type="regular",
            is_anonymous=True,
            allows_multiple_answers=POLL_ALLOWS_MULTIPLE,
        )
        message_id = msg.message_id

    else:
        raise ValueError(f"Noma'lum kontent turi: {content_type}")

    await db.mark_published(content["id"], message_id)
    return message_id
