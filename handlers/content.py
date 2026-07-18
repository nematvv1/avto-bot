"""
Kontent yaratish jarayoni:
tur tanlash -> mavzu tanlash -> (post uchun rasm tanlash) -> AI generatsiya ->
preview -> tasdiqlash/tahrirlash/qayta generatsiya/bekor qilish -> joylash/rejalashtirish
"""
import json
import os
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
import ai_service
from publisher import publish_content
from states import ContentCreation
from handlers.filters import IsAdmin

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def _delete_image_files(image_path: str) -> None:
    """Rasm fayli va uning branded versiyasini diskdan o'chiradi."""
    for path in [image_path]:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


TYPE_LABELS = {"post": "📝 Post", "quiz": "🧠 Quiz", "poll": "📊 So'rovnoma"}


# ---------- 1. Kontent turini tanlash ----------

@router.callback_query(F.data == "menu:new_content")
async def start_new_content(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(ContentCreation.choosing_type)
    await callback.message.edit_text(
        "Qaysi turdagi kontent yaratamiz?", reply_markup=kb.content_type_menu()
    )
    await callback.answer()


@router.callback_query(ContentCreation.choosing_type, F.data.startswith("type:"))
async def choose_type(callback: CallbackQuery, state: FSMContext):
    content_type = callback.data.split(":")[1]
    await state.update_data(content_type=content_type)
    await state.set_state(ContentCreation.choosing_topic_mode)
    await callback.message.edit_text(
        f"{TYPE_LABELS[content_type]} tanlandi.\n\nMavzuni qanday belgilaymiz?",
        reply_markup=kb.topic_choice_menu(),
    )
    await callback.answer()


# ---------- 2. Mavzu tanlash ----------

@router.callback_query(ContentCreation.choosing_topic_mode, F.data == "topic:auto")
async def topic_auto(callback: CallbackQuery, state: FSMContext):
    await state.update_data(topic=None)
    await _after_topic_chosen(callback.message, state, callback.bot)
    await callback.answer()


@router.callback_query(ContentCreation.choosing_topic_mode, F.data == "topic:manual")
async def topic_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ContentCreation.waiting_topic_text)
    await callback.message.edit_text(
        "✍️ Mavzuni yozing (masalan: <i>«Python'da ro'yxatlar bilan ishlash»</i>):"
    )
    await callback.answer()


@router.message(ContentCreation.waiting_topic_text)
async def topic_text_received(message: Message, state: FSMContext):
    await state.update_data(topic=message.text.strip())
    await _after_topic_chosen(message, state, message.bot)


async def _after_topic_chosen(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    content_type = data["content_type"]
    if content_type == "post":
        await state.set_state(ContentCreation.choosing_image_option)
        await message.answer(
            "🖼 Post uchun AI orqali rasm ham generatsiya qilaylikmi?",
            reply_markup=kb.image_choice_menu(),
        )
    else:
        await _generate_and_preview(message, state, bot)


# ---------- 3. Post uchun rasm tanlovi ----------

@router.callback_query(ContentCreation.choosing_image_option, F.data.startswith("img:"))
async def image_choice(callback: CallbackQuery, state: FSMContext):
    want_image = callback.data.split(":")[1] == "yes"
    await state.update_data(want_image=want_image)
    await callback.answer()
    await _generate_and_preview(callback.message, state, callback.bot)


# ---------- 4. AI generatsiya va preview ----------

async def _generate_and_preview(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    content_type = data["content_type"]
    topic = data.get("topic")
    want_image = data.get("want_image", False)

    await state.set_state(ContentCreation.generating)
    status_msg = await message.answer("⏳ AI kontent tayyorlamoqda, biroz kuting...")

    try:
        if content_type == "post":
            generated = await ai_service.generate_post(topic)
            text = f"<b>{generated['title']}</b>\n\n{generated['text']}"
            image_path = None
            if want_image:
                await status_msg.edit_text("🎨 Rasm generatsiya qilinmoqda...")
                image_path = await ai_service.generate_image(generated["image_prompt"])
            content_id = await db.add_content(
                content_type="post", topic=topic, text=text,
                image_path=image_path, created_by=message.chat.id,
            )

        elif content_type == "quiz":
            generated = await ai_service.generate_quiz(topic)
            content_id = await db.add_content(
                content_type="quiz", topic=topic, text=generated["question"],
                options=generated["options"], correct_option=generated["correct_index"],
                explanation=generated.get("explanation", ""),
                created_by=message.chat.id,
            )
            await db.update_content_text(content_id, generated["question"])

        else:  # poll
            generated = await ai_service.generate_poll(topic)
            content_id = await db.add_content(
                content_type="poll", topic=topic, text=generated["question"],
                options=generated["options"], created_by=message.chat.id,
            )

    except Exception as e:
        err_str = str(e).lower()
        if "insufficient_quota" in err_str or "quota" in err_str:
            msg = "💳 OpenAI hisobingizda balans yetarli emas.\nTarif rejangizni tekshiring va to'ldiring."
        elif "rate_limit" in err_str:
            msg = "⏳ So'rovlar juda ko'p yuborildi. Bir oz kuting va qaytadan urinib ko'ring."
        elif "invalid_api_key" in err_str or "api key" in err_str:
            msg = "🔑 OpenAI API kalit noto'g'ri. .env faylini tekshiring."
        elif "timeout" in err_str or "timed out" in err_str:
            msg = "🌐 Server javob bermadi (timeout). Qaytadan urinib ko'ring."
        elif "connection" in err_str:
            msg = "🌐 Internet ulanishida muammo. Qaytadan urinib ko'ring."
        else:
            msg = "⚠️ Xatolik yuz berdi. Keyinroq urinib ko'ring."
        await status_msg.edit_text(msg, reply_markup=kb.back_to_menu())
        await state.clear()
        return

    await status_msg.delete()
    await state.update_data(content_id=content_id)
    await state.set_state(ContentCreation.previewing)
    await _show_preview(message, state, bot, content_id)


async def _show_preview(message: Message, state: FSMContext, bot: Bot, content_id: int):
    content = await db.get_content(content_id)
    data = await state.get_data()

    if content["content_type"] == "post":
        caption = "👀 <b>Ko'rib chiqing:</b>\n\n" + content["text"]
        if content.get("image_path"):
            photo = FSInputFile(content["image_path"])
            await bot.send_photo(
                chat_id=message.chat.id, photo=photo,
                caption=caption[:1024], reply_markup=kb.preview_actions(content_id),
            )
        else:
            await bot.send_message(
                chat_id=message.chat.id, text=caption,
                reply_markup=kb.preview_actions(content_id),
            )

    elif content["content_type"] == "quiz":
        options = json.loads(content["options_json"])
        options_text = "\n".join(
            f"{'✅' if i == content['correct_option'] else '▫️'} {opt}"
            for i, opt in enumerate(options)
        )
        # Izohni DB dan o'qiymiz (FSM state'dan emas)
        explanation = content.get("explanation") or data.get("explanation", "")
        text = (
            f"👀 <b>Quiz ko'rib chiqing:</b>\n\n"
            f"❓ {content['text']}\n\n{options_text}\n\n"
            f"💡 <i>{explanation}</i>"
        )
        await bot.send_message(
            chat_id=message.chat.id, text=text, reply_markup=kb.preview_actions(content_id)
        )

    else:  # poll
        options = json.loads(content["options_json"])
        options_text = "\n".join(f"▫️ {opt}" for opt in options)
        text = f"👀 <b>So'rovnoma ko'rib chiqing:</b>\n\n❓ {content['text']}\n\n{options_text}"
        await bot.send_message(
            chat_id=message.chat.id, text=text, reply_markup=kb.preview_actions(content_id)
        )


# ---------- 5. Preview ustidagi amallar ----------

@router.callback_query(ContentCreation.previewing, F.data.startswith("approve:"))
async def approve_content(callback: CallbackQuery, state: FSMContext):
    content_id = int(callback.data.split(":")[1])
    await db.update_status(content_id, "approved")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "✅ Tasdiqlandi! Endi qachon joylaymiz?",
        reply_markup=kb.publish_time_menu(content_id),
    )
    await callback.answer()


@router.callback_query(ContentCreation.previewing, F.data.startswith("reject:"))
async def reject_content(callback: CallbackQuery, state: FSMContext):
    content_id = int(callback.data.split(":")[1])
    # Eski rasm faylini o'chirish
    old_content = await db.get_content(content_id)
    if old_content and old_content.get("image_path"):
        _delete_image_files(old_content["image_path"])
    await db.delete_content(content_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("❌ Bekor qilindi va o'chirildi.", reply_markup=kb.main_menu())
    await state.clear()
    await callback.answer()


@router.callback_query(ContentCreation.previewing, F.data.startswith("regen:"))
async def regenerate_content(callback: CallbackQuery, state: FSMContext):
    content_id = int(callback.data.split(":")[1])
    old_content = await db.get_content(content_id)
    # Eski rasm faylini o'chirish
    if old_content and old_content.get("image_path"):
        _delete_image_files(old_content["image_path"])
    await db.delete_content(content_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("🔄 Qayta generatsiya qilinmoqda...")

    # callback.message — bu bot xabari, foydalanuvchi chat.id uchun from_user ishlatamiz
    class _FakeMsg:
        """Minimal Message-like ob'ekt, faqat zarur atributlar bilan."""
        def __init__(self, original_msg, user_id):
            self._msg = original_msg
            self.chat = type("Chat", (), {"id": user_id})()
            self.bot = original_msg.bot

        async def answer(self, *args, **kwargs):
            return await self._msg.answer(*args, **kwargs)

    fake_message = _FakeMsg(callback.message, callback.from_user.id)
    await _generate_and_preview(fake_message, state, callback.bot)


@router.callback_query(ContentCreation.previewing, F.data.startswith("edit:"))
async def edit_content_start(callback: CallbackQuery, state: FSMContext):
    content_id = int(callback.data.split(":")[1])
    await state.update_data(editing_content_id=content_id)
    await state.set_state(ContentCreation.waiting_edit_text)
    await callback.message.answer(
        "✏️ Yangi matnni to'liq yozib yuboring (HTML teglar qo'llab-quvvatlanadi: <b>, <i>):"
    )
    await callback.answer()


@router.message(ContentCreation.waiting_edit_text)
async def edit_content_receive(message: Message, state: FSMContext):
    data = await state.get_data()
    content_id = data["editing_content_id"]
    await db.update_content_text(content_id, message.text)
    await state.set_state(ContentCreation.previewing)
    await message.answer("✅ Matn yangilandi.")
    await _show_preview(message, state, message.bot, content_id)
