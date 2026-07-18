# 🤖 Kanal Kontent Boti

Telegram kanalingiz uchun AI yordamida **post, quiz (viktorina) va so'rovnoma**
generatsiya qiladigan, sizga tasdiqlash uchun yuboradigan va tasdiqlagandan
so'ng (darhol yoki rejalashtirilgan vaqtda) kanalga o'zi joylaydigan bot.

## ✨ Imkoniyatlari

- 📝 **Post** — sarlavha + matn, xohlasangiz **AI rasm** bilan (GPT Image 2)
- 🧠 **Quiz** — 4 variantli savol, to'g'ri javob va izoh bilan
- 📊 **So'rovnoma** — obunachilardan fikr so'rash
- 🎯 Mavzuni **siz belgilaysiz** yoki **AI o'zi tanlaydi** (kanal yo'nalishidan kelib chiqib)
- ✅ Har bir kontent kanalga chiqishdan oldin **sizga (adminga) tasdiqlash uchun** yuboriladi
- ✏️ Tahrirlash, 🔄 qayta generatsiya qilish, ❌ bekor qilish imkoniyati
- 🕒 **Rejalashtirish** — "1 soatdan keyin", "bugun 19:00", "ertaga 09:00" yoki o'zingiz sana/vaqt kiritish
- 📅 Rejalashtirilgan postlar ro'yxati va boshqaruvi
- 📊 Statistika
- Hammasi **tugmalar orqali** — buyruq yozish shart emas

## 🧠 Ishlatilayotgan AI modellari

- Matn: `gpt-5.5` (OpenAI Chat Completions API)
- Rasm: `gpt-image-2` (OpenAI Image API)

Modellarni `.env` faylida `TEXT_MODEL` va `IMAGE_MODEL` orqali o'zgartirish mumkin.

### 🎨 Rasmlar qanday professional bo'ladi

Post uchun rasm ikki bosqichda "professional" qilinadi:

1. **Mazmunga moslik** — `gpt-5.5` post matnini yozayotganda, aynan shu postning
   g'oyasiga mos, aniq va batafsil rasm tavsifini (`image_prompt`) ham tuzadi
   (umumiy "noutbuk" yoki "texnologiya" rasmlari o'rniga, mavzuga xos vizual metafora).
2. **Yagona vizual uslub (brend)** — `.env` faylidagi `IMAGE_STYLE` sozlamasi har bir
   rasmga qo'shiladi, shu orqali barcha postlaringizdagi rasmlar bir xil uslubda
   (masalan, bir xil ranglar palitrasi va dizayn tili) chiqadi — kanalingiz o'ziga
   xos vizual "brend"ga ega bo'ladi.

`IMAGE_STYLE`ni o'zingizga moslab o'zgartirishingiz mumkin, masalan:
- `flat illustration, pastel colors, playful cartoon style` — yumshoq, o'ynoqi uslub
- `dark cyberpunk aesthetic, neon accents, high-tech` — zamonaviy IT-kanal uchun
- `realistic photography style, natural lighting` — real hayotiy rasmlar uchun

`IMAGE_SIZE` orqali rasm o'lchamini ham tanlashingiz mumkin (`1536x1024` — gorizontal,
Telegram feedda eng chiroyli ko'rinadi).

### 🏷 Avtomatik brendlash (logo + kanal nomi)

Har bir generatsiya qilingan rasmning **pastki qismiga** avtomatik ravishda:
- Sizning logotipingiz (`assets/logo.png`)
- Kanal nomi (`Iqtidor Academy`)

chiroyli, qorong'i gradient fon va brend rangidagi ajratuvchi chiziq bilan joylanadi.
Bu AI'ning o'zi matn/logo chizishiga ishonib qolishdan ko'ra ancha ishonchli — natija
har doim bir xil aniqlikda va professional chiqadi (`branding.py` moduli, Pillow orqali).

**Sozlash uchun** (`.env` faylida):
```
ADD_BRANDING=true                 # yoqish/o'chirish
BRAND_NAME=Iqtidor Academy        # rasmda ko'rinadigan nom
LOGO_PATH=assets/logo.png         # logotip fayli manzili
BRAND_ACCENT_COLOR=#2033E9        # brend rangi (ajratuvchi chiziq)
```

Logotipingizni almashtirish uchun `assets/logo.png` faylini o'z rasmingiz bilan
almashtiring (kvadrat, kamida 512x512px tavsiya etiladi).

---

## ⚙️ O'rnatish

### 1. Talablar
- Python 3.11 yoki undan yuqori
- Telegram bot tokeni ([@BotFather](https://t.me/BotFather) orqali oling)
- OpenAI API kaliti ([platform.openai.com](https://platform.openai.com/api-keys))
- Sizning Telegram kanalingiz (bot **admin** sifatida qo'shilgan bo'lishi shart —
  "Post yuborish" va "Ovoz so'rovlarini boshqarish" huquqlari bilan)

### 2. Kutubxonalarni o'rnatish

```bash
cd channel_bot
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Sozlamalarni kiritish

`.env.example` faylidan nusxa oling va o'z ma'lumotlaringizni kiriting:

```bash
cp .env .env
```

`.env` faylini oching va to'ldiring:

| O'zgaruvchi | Tavsif |
|---|---|
| `BOT_TOKEN` | BotFather bergan token |
| `CHANNEL_ID` | Kanal username (`@kanalim`) yoki ID (`-1001234567890`) |
| `ADMIN_IDS` | Sizning Telegram ID raqamingiz. ID bilish uchun [@userinfobot](https://t.me/userinfobot) ga yozing. Bir nechta admin bo'lsa vergul bilan: `111,222` |
| `OPENAI_API_KEY` | OpenAI API kaliti |
| `CHANNEL_TOPIC` | Kanalingiz mavzusi (AI shu asosda kontent generatsiya qiladi) |

### 4. Botni kanalga admin qilib qo'shish

Kanalingiz sozlamalari → Administrators → botingizni qo'shing → quyidagi
huquqlarni bering:
- ✅ Post messages (Xabar yuborish)
- ✅ Manage polls / Send polls (So'rovnoma va quiz yuborish)

### 5. Ishga tushirish

```bash
python bot.py
```

Bot ishga tushgach, Telegram'da botga `/start` yozing — bosh menyu chiqadi.

---

## 📁 Loyiha strukturasi

```
channel_bot/
├── bot.py              # Ishga tushirish nuqtasi
├── config.py           # Sozlamalar (.env dan o'qiydi)
├── database.py         # SQLite baza bilan ishlash
├── ai_service.py       # OpenAI (matn + rasm) generatsiya
├── branding.py         # Rasmlarga logo + kanal nomini avtomatik joylash
├── publisher.py        # Kanalga joylash logikasi
├── scheduler.py        # Rejalashtirilgan postlarni avtomatik joylash
├── keyboards.py        # Barcha inline tugmalar
├── states.py           # FSM holatlari (bosqichma-bosqich muloqot)
├── handlers/
│   ├── filters.py       # Faqat admin filter
│   ├── admin.py         # /start, /help, bosh menyu, statistika
│   ├── content.py       # Kontent yaratish jarayoni
│   └── schedule.py      # Joylash va rejalashtirish
├── requirements.txt
├── .env.example
├── assets/
│   ├── logo.png          # Kanal logotipi
│   └── fonts/            # Brend matni uchun shrift
└── generated_images/    # AI generatsiya qilgan (va brendlangan) rasmlar shu yerda saqlanadi
```

## 🔄 Ishlash jarayoni (foydalanuvchi nuqtai nazaridan)

1. `/start` → **✨ Yangi kontent yaratish** tugmasi
2. Turini tanlaysiz: Post / Quiz / So'rovnoma
3. Mavzuni tanlaysiz: o'zingiz yozasiz yoki AI o'zi tanlasin
4. (Post uchun) Rasm kerakmi — ha/yo'q
5. AI kontentni tayyorlaydi va sizga ko'rsatadi
6. Siz: ✅ Tasdiqlaysiz / ✏️ Tahrirlaysiz / 🔄 Qayta so'raysiz / ❌ Bekor qilasiz
7. Tasdiqlagach: 🚀 Hozir yuborish yoki 🕒 Vaqt belgilash
8. Agar rejalashtirilgan bo'lsa — bot belgilangan vaqtda **o'zi** kanalga joylaydi
   va sizga xabar beradi

## 💡 Kengaytirish g'oyalari

- Bir nechta kanalga bir vaqtda joylash
- Har kunlik avtomatik jadval (masalan har kuni 10:00 da post, har juma quiz)
- Statistika grafigi (haftalik/oylik)
- Kontentni post qilishdan oldin ikkinchi admin ham tasdiqlashi (ikki bosqichli tasdiq)

## ⚠️ Eslatma

- OpenAI API pullik xizmat — har bir generatsiya (ayniqsa rasm) uchun to'lov olinadi
- Bot serverni doim ishlab turadigan joyda (VPS, server) ishga tushirish tavsiya
  etiladi, aks holda kompyuter o'chganda rejalashtirilgan postlar joylanmaydi
