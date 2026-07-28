"""
Brendingni qo'lda ko'zdan kechirish uchun — OpenAI ishlatmasdan.
Oddiy gradient rasm yaratadi va ustiga logo + kanal nomini joylab ko'rsatadi.

Ishga tushirish: python scripts/preview_branding.py
(Bu avtomatik test emas — natijani Explorer'da ochadi, faqat qo'lda tekshirish uchun.)
"""
from PIL import Image, ImageDraw
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from branding import add_branding

# 1. Oddiy gradient test rasm yaratish (OpenAIsiz)
W, H = 1536, 1024
img = Image.new("RGB", (W, H))
draw = ImageDraw.Draw(img)

# Ko'k-binafsha gradient
for y in range(H):
    r = int(10 + (30 - 10) * y / H)
    g = int(20 + (10 - 20) * y / H)
    b = int(80 + (120 - 80) * y / H)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# Markazga oddiy geometrik shakl (test vizual)
cx, cy = W // 2, H // 2
for i in range(5, 0, -1):
    r_val = i * 80
    alpha_color = (30 + i * 20, 60 + i * 15, 180 - i * 10)
    draw.ellipse([cx - r_val, cy - r_val, cx + r_val, cy + r_val], outline=alpha_color, width=3)

# Markazga matn
try:
    from PIL import ImageFont
    font = ImageFont.truetype(os.path.join("assets", "fonts", "Outfit-Bold.ttf"), 48)
except Exception:
    font = ImageFont.load_default()

text = "TEST RASM"
bbox = draw.textbbox((0, 0), text, font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
draw.text(((W - tw) // 2, (H - th) // 2), text, font=font, fill=(255, 255, 255, 200))

# Rasmni vaqtinchalik saqlash
os.makedirs("generated_images", exist_ok=True)
test_path = "generated_images/test_raw.png"
img.save(test_path)
print("OK: Test rasm yaratildi:", test_path)

# 2. Brendingni qo'llash
branded_path = add_branding(test_path)
print("OK: Brending qo'shildi:", branded_path)

# 3. Natijani ochish (faqat Windows)
if sys.platform == "win32":
    import subprocess
    subprocess.Popen(["explorer", os.path.abspath(branded_path)])
    print("Rasm ochilmoqda...")
print("Fayl manzili:", os.path.abspath(branded_path))
