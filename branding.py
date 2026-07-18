"""
AI generatsiya qilgan rasmlarga kanal brendini (logo + nom) avtomatik joylash.

Uslub: PASTKI QISMDA — rasm bilan uyg'un gradient,
logotip dumaloq burchakli (rounded), qattiq ajratgich yo'q.
"""
import os
from PIL import Image, ImageDraw, ImageFont

from config import BRAND_NAME, LOGO_PATH, ADD_BRANDING, BRAND_ACCENT_COLOR

FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "Outfit-Bold.ttf")
BRANDED_DIR = "generated_images"


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple:
    hex_color = hex_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return (r, g, b, alpha)


def _make_rounded_logo(logo: Image.Image, radius_ratio: float = 0.22) -> Image.Image:
    """Logotipga dumaloq burchak beradi (rounded rectangle mask)."""
    logo = logo.convert("RGBA")
    w, h = logo.size
    radius = int(min(w, h) * radius_ratio)

    mask = Image.new("L", (w, h), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)

    result = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    result.paste(logo, (0, 0), mask)
    return result


def add_branding(base_image_path: str) -> str:
    """
    Rasmning PASTKI qismiga logotip (dumaloq burchakli) + kanal nomini joylab saqlaydi.
    Rasm bilan uyg'un — yumshoq gradient, qattiq ajratgich yo'q.
    """
    if not ADD_BRANDING or not os.path.exists(LOGO_PATH):
        return base_image_path

    img = Image.open(base_image_path).convert("RGBA")
    W, H = img.size

    draw = ImageDraw.Draw(img)

    # --- 2. O'lchamlar ---
    logo_h = int(H * 0.085)
    logo_h = max(logo_h, 52)
    padding_x = int(W * 0.045)
    padding_y = int(H * 0.03)

    # --- 3. Logotip — dumaloq burchakli ---
    logo_raw = Image.open(LOGO_PATH).convert("RGBA")
    lw_orig, lh_orig = logo_raw.size
    logo_w = int(logo_h * lw_orig / lh_orig)
    logo_raw = logo_raw.resize((logo_w, logo_h), Image.LANCZOS)
    logo_rounded = _make_rounded_logo(logo_raw, radius_ratio=0.22)

    logo_x = padding_x
    logo_y = H - logo_h - padding_y

    # --- 4. Font va matn ---
    font_size = int(logo_h * 0.68)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()

    name_upper = BRAND_NAME.upper()
    bbox = draw.textbbox((0, 0), name_upper, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    gap = int(logo_h * 0.32)
    text_x = logo_x + logo_w + gap
    # Matnni logotip bilan vertikal markazlashtirish
    text_y = logo_y + (logo_h - text_h) // 2 - bbox[1]

    # Soya
    shadow = max(2, font_size // 18)
    draw.text((text_x + shadow, text_y + shadow),
              name_upper, font=font, fill=(0, 0, 0, 100))

    # Asosiy matn — oq
    draw.text((text_x, text_y), name_upper, font=font, fill=(255, 255, 255, 250))

    # --- 5. Logotipni rasmga joylashtirish ---
    img.paste(logo_rounded, (logo_x, logo_y), logo_rounded)

    # --- 6. Saqlash ---
    final = img.convert("RGB")
    os.makedirs(BRANDED_DIR, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(base_image_path))[0]
    out_path = os.path.join(BRANDED_DIR, f"{base_name}_branded.jpg")
    final.save(out_path, quality=95)
    return out_path
