"""
FSM (Finite State Machine) holatlari.
Bot foydalanuvchidan ketma-ket ma'lumot so'rashi kerak bo'lgan joylarda ishlatiladi.
"""
from aiogram.fsm.state import State, StatesGroup


class ContentCreation(StatesGroup):
    choosing_type = State()          # post/quiz/poll tanlash
    choosing_topic_mode = State()    # AI o'zi / qo'lda mavzu
    waiting_topic_text = State()     # foydalanuvchi mavzuni yozmoqda
    choosing_image_option = State()  # post uchun rasm kerakmi
    generating = State()             # AI generatsiya qilmoqda
    previewing = State()             # natija ko'rsatilmoqda, tasdiqlash kutilmoqda
    waiting_edit_text = State()      # foydalanuvchi tahrirlangan matnni yozmoqda


class Scheduling(StatesGroup):
    waiting_datetime = State()       # foydalanuvchi sana/vaqt yozmoqda
