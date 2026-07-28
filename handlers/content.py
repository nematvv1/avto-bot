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
from utils import safe_truncate_html
from config import MAX_GENERATIONS_PER_HOUR, CHANNEL_TARGETS, DEFAULT_TARGET_KEY, get_target

MIN_QUIZ_OPTIONS = 2
MAX_QUIZ_OPTIONS = 10

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def _delete_image_files(image_path: str) -> None:
    """Rasm faylini diskdan o'chiradi."""
    try:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
    except OSError:
        pass


TYPE_LABELS = {"post": "📝 Post", "quiz": "🧠 Quiz", "poll": "📊 So'rovnoma"}


# ---------- 0. Kanal/tashkilot tanlash (bir nechta target sozlangan bo'lsa) ----------

@router.callback_query(F.data == "menu:new_content")
async def start_new_content(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if len(CHANNEL_TARGETS) > 1:
        await state.set_state(ContentCreation.choosing_target)
        await callback.message.edit_text(
            "Qaysi kanal/tashkilot uchun kontent yaratamiz?",
            reply_markup=kb.target_choice_menu(CHANNEL_TARGETS),
        )
    else:
        await state.update_data(target_key=DEFAULT_TARGET_KEY)
        await state.set_state(ContentCreation.choosing_type)
        await callback.message.edit_text(
            "Qaysi turdagi kontent yaratamiz?", reply_markup=kb.content_type_menu()
        )
    await callback.answer()


@router.callback_query(ContentCreation.choosing_target, F.data.startswith("target:"))
async def choose_target(callback: CallbackQuery, state: FSMContext):
    target_key = callback.data.split(":", 1)[1]
    if target_key not in CHANNEL_TARGETS:
        await callback.answer("Noma'lum tanlov.", show_alert=True)
        return
    await state.update_data(target_key=target_key)
    await state.set_state(ContentCreation.choosing_type)
    label = CHANNEL_TARGETS[target_key]["label"]
    await callback.message.edit_text(
        f"🏷 {label}\n\nQaysi turdagi kontent yaratamiz?", reply_markup=kb.content_type_menu()
    )
    await callback.answer()


# ---------- 1. Kontent turini tanlash ----------

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
        "✍️ G'oyangizni erkin yozing (xom bo'lsa ham bo'ladi) — kerak bo'lsa AI "
        "aniqlashtiruvchi savol(lar) beradi, so'ng shu asosda mukammal kontent tuzadi:"
    )
    await callback.answer()


@router.message(ContentCreation.waiting_topic_text)
async def topic_text_received(message: Message, state: FSMContext):
    await state.update_data(
        brainstorm_history=[{"role": "user", "content": message.text.strip()}],
        brainstorm_turns=0,
    )
    await _brainstorm_continue(message, state)


@router.message(ContentCreation.brainstorming)
async def brainstorm_answer_received(message: Message, state: FSMContext):
    data = await state.get_data()
    history = data.get("brainstorm_history", [])
    history.append({"role": "user", "content": message.text.strip()})
    await state.update_data(brainstorm_history=history)
    await _brainstorm_continue(message, state)


async def _brainstorm_continue(message: Message, state: FSMContext):
    """AI bilan qisqa suhbat orqali xom g'oyani aniqlashtiradi, so'ng odatdagi generatsiya oqimiga o'tadi."""
    data = await state.get_data()
    history = data.get("brainstorm_history", [])
    turns = data.get("brainstorm_turns", 0)
    target = get_target(data.get("target_key"))

    thinking_msg = await message.answer("🤔 ...")
    try:
        result = await ai_service.brainstorm_step(
            history, channel_topic=target["topic"], force_finish=turns >= ai_service.MAX_BRAINSTORM_TURNS
        )
    except Exception:
        # AI bilan aloqa uzilsa — foydalanuvchini bloklab qo'ymaslik uchun,
        # yozilgan xom g'oyani to'g'ridan-to'g'ri mavzu sifatida ishlatamiz.
        await thinking_msg.delete()
        combined = " ".join(h["content"] for h in history if h["role"] == "user")
        await state.update_data(topic=combined)
        await _after_topic_chosen(message, state, message.bot)
        return

    if result["done"]:
        await thinking_msg.edit_text(f"✅ Tushundim!\n\n<i>{result['brief']}</i>")
        history.append({"role": "assistant", "content": result["brief"]})
        await state.update_data(topic=result["brief"], brainstorm_history=history)
        await _after_topic_chosen(message, state, message.bot)
    else:
        history.append({"role": "assistant", "content": result["question"]})
        await state.update_data(brainstorm_history=history, brainstorm_turns=turns + 1)
        await state.set_state(ContentCreation.brainstorming)
        await thinking_msg.edit_text(f"❓ {result['question']}")


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

async def _generate_and_preview(message: Message, state: FSMContext, bot: Bot,
                                 previous_text: str | None = None):
    data = await state.get_data()
    content_type = data["content_type"]
    topic = data.get("topic")
    want_image = data.get("want_image", False)
    target_key = data.get("target_key")
    target = get_target(target_key)

    recent = await db.count_recent_generations(60, created_by=message.chat.id)
    if recent >= MAX_GENERATIONS_PER_HOUR:
        await message.answer(
            f"⏳ Bir soat ichida generatsiya limiti ({MAX_GENERATIONS_PER_HOUR} ta) "
            "tugadi. Iltimos, keyinroq urinib ko'ring.",
            reply_markup=kb.back_to_menu(),
        )
        await state.clear()
        return

    await state.set_state(ContentCreation.generating)
    status_msg = await message.answer("⏳ AI kontent tayyorlamoqda, biroz kuting...")

    try:
        if content_type == "post":
            generated = await ai_service.generate_post(
                topic, previous_text=previous_text, channel_topic=target["topic"]
            )
            text = f"<b>{generated['title']}</b>\n\n{generated['text']}"
            if target["contact_footer"]:
                text += f"\n\n{target['contact_footer']}"
            image_path = None
            if want_image:
                await status_msg.edit_text("🎨 Rasm generatsiya qilinmoqda...")
                image_path = await ai_service.generate_image(
                    generated["image_prompt"], brand_name=target["brand_name"],
                    logo_path=target["logo_path"], accent_color=target["accent_color"],
                )
            content_id = await db.add_content(
                content_type="post", topic=topic, text=text,
                image_path=image_path, created_by=message.chat.id, target_key=target_key,
            )

        elif content_type == "quiz":
            generated = await ai_service.generate_quiz(
                topic, previous_text=previous_text, channel_topic=target["topic"]
            )
            content_id = await db.add_content(
                content_type="quiz", topic=topic, text=generated["question"],
                options=generated["options"], correct_option=generated["correct_index"],
                explanation=generated.get("explanation", ""),
                created_by=message.chat.id, target_key=target_key,
            )
            await db.update_content_text(content_id, generated["question"])

        else:  # poll
            generated = await ai_service.generate_poll(
                topic, previous_text=previous_text, channel_topic=target["topic"]
            )
            content_id = await db.add_content(
                content_type="poll", topic=topic, text=generated["question"],
                options=generated["options"], created_by=message.chat.id, target_key=target_key,
            )

    except ai_service.ContentValidationError as e:
        await status_msg.edit_text(
            f"⚠️ AI noto'g'ri formatda javob qaytardi: {e}\n"
            "Iltimos, qaytadan urinib ko'ring.",
            reply_markup=kb.back_to_menu(),
        )
        await state.clear()
        return
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
    target_prefix = ""
    if len(CHANNEL_TARGETS) > 1:
        target_prefix = f"🏷 {get_target(content.get('target_key'))['label']}\n"

    if content["content_type"] == "post":
        caption = f"{target_prefix}👀 <b>Ko'rib chiqing:</b>\n\n" + content["text"]
        if content.get("image_path"):
            photo = FSInputFile(content["image_path"])
            await bot.send_photo(
                chat_id=message.chat.id, photo=photo,
                caption=safe_truncate_html(caption, 1024),
                reply_markup=kb.preview_actions(content_id, "post"),
            )
        else:
            await bot.send_message(
                chat_id=message.chat.id, text=caption,
                reply_markup=kb.preview_actions(content_id, "post"),
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
            f"{target_prefix}👀 <b>Quiz ko'rib chiqing:</b>\n\n"
            f"❓ {content['text']}\n\n{options_text}\n\n"
            f"💡 <i>{explanation}</i>"
        )
        await bot.send_message(
            chat_id=message.chat.id, text=text, reply_markup=kb.preview_actions(content_id, "quiz")
        )

    else:  # poll
        options = json.loads(content["options_json"])
        options_text = "\n".join(f"▫️ {opt}" for opt in options)
        text = f"{target_prefix}👀 <b>So'rovnoma ko'rib chiqing:</b>\n\n❓ {content['text']}\n\n{options_text}"
        await bot.send_message(
            chat_id=message.chat.id, text=text, reply_markup=kb.preview_actions(content_id, "poll")
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
    previous_text = old_content["text"] if old_content else None
    # Eski rasm faylini o'chirish
    if old_content and old_content.get("image_path"):
        _delete_image_files(old_content["image_path"])
    await db.delete_content(content_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("🔄 Boshqa variant tayyorlanmoqda...")

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
    await _generate_and_preview(fake_message, state, callback.bot, previous_text=previous_text)


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
    new_text = message.text
    warning = ""
    if len(new_text) > 4096:
        new_text = safe_truncate_html(new_text, 4096)
        warning = "\n\n⚠️ Matn juda uzun edi, 4096 belgigacha qisqartirildi."
    await db.update_content_text(content_id, new_text)
    await state.set_state(ContentCreation.previewing)
    await message.answer(f"✅ Matn yangilandi.{warning}")
    await _show_preview(message, state, message.bot, content_id)


# ---------- 6. Variantlarni tahrirlash (quiz/poll) ----------

@router.callback_query(ContentCreation.previewing, F.data.startswith("editopts:"))
async def edit_options_start(callback: CallbackQuery, state: FSMContext):
    content_id = int(callback.data.split(":")[1])
    content = await db.get_content(content_id)
    if not content:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    options = json.loads(content["options_json"] or "[]")
    limits = (
        f"{MIN_QUIZ_OPTIONS}-{MAX_QUIZ_OPTIONS}"
        if content["content_type"] == "quiz"
        else f"{ai_service.MIN_POLL_OPTIONS}-{ai_service.MAX_POLL_OPTIONS}"
    )
    await state.update_data(editing_content_id=content_id)
    await state.set_state(ContentCreation.waiting_edit_options)
    await callback.message.answer(
        "🔡 Yangi variantlarni har birini alohida qatorda yozing "
        f"({limits} ta variant, har biri max 90 belgi).\n\n"
        "Hozirgi variantlar:\n" + "\n".join(f"• {o}" for o in options)
    )
    await callback.answer()


@router.message(ContentCreation.waiting_edit_options)
async def edit_options_receive(message: Message, state: FSMContext):
    data = await state.get_data()
    content_id = data["editing_content_id"]
    content = await db.get_content(content_id)
    if not content:
        await message.answer("⚠️ Kontent topilmadi.", reply_markup=kb.main_menu())
        await state.clear()
        return

    options = [line.strip() for line in message.text.split("\n") if line.strip()]
    options = [o[:90] for o in options]

    if content["content_type"] == "quiz":
        lo, hi = MIN_QUIZ_OPTIONS, MAX_QUIZ_OPTIONS
    else:
        lo, hi = ai_service.MIN_POLL_OPTIONS, ai_service.MAX_POLL_OPTIONS

    if not (lo <= len(options) <= hi):
        await message.answer(
            f"⚠️ {len(options)} ta variant kiritdingiz, {lo}-{hi} ta bo'lishi kerak. "
            "Qaytadan urinib ko'ring (har biri alohida qatorda)."
        )
        return

    if content["content_type"] == "quiz":
        await db.update_options(content_id, options)
        await state.set_state(ContentCreation.choosing_correct_option)
        await message.answer(
            "✅ Variantlar yangilandi. Endi to'g'ri javobni tanlang:",
            reply_markup=kb.correct_option_menu(content_id, options),
        )
    else:
        await db.update_options(content_id, options)
        await state.set_state(ContentCreation.previewing)
        await message.answer("✅ Variantlar yangilandi.")
        await _show_preview(message, state, message.bot, content_id)


@router.callback_query(ContentCreation.choosing_correct_option, F.data.startswith("setcorrect:"))
async def set_correct_option(callback: CallbackQuery, state: FSMContext):
    _, content_id_str, idx_str = callback.data.split(":")
    content_id = int(content_id_str)
    await db.update_correct_option(content_id, int(idx_str))
    await state.set_state(ContentCreation.previewing)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("✅ To'g'ri javob belgilandi.")
    await _show_preview(callback.message, state, callback.bot, content_id)


# ---------- 7. Izohni tahrirlash (quiz) ----------

@router.callback_query(ContentCreation.previewing, F.data.startswith("editexpl:"))
async def edit_explanation_start(callback: CallbackQuery, state: FSMContext):
    content_id = int(callback.data.split(":")[1])
    await state.update_data(editing_content_id=content_id)
    await state.set_state(ContentCreation.waiting_edit_explanation)
    await callback.message.answer("💬 Yangi izohni yozing (max 200 belgi):")
    await callback.answer()


@router.message(ContentCreation.waiting_edit_explanation)
async def edit_explanation_receive(message: Message, state: FSMContext):
    data = await state.get_data()
    content_id = data["editing_content_id"]
    explanation = message.text.strip()
    warning = ""
    if len(explanation) > 200:
        explanation = explanation[:199] + "…"
        warning = "\n\n⚠️ Izoh 200 belgigacha qisqartirildi."
    await db.update_explanation(content_id, explanation)
    await state.set_state(ContentCreation.previewing)
    await message.answer(f"✅ Izoh yangilandi.{warning}")
    await _show_preview(message, state, message.bot, content_id)
