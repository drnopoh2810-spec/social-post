"""
Image Text Overlay Service
===========================
يضع نص عربي على الصورة بعد الـ frame overlay.

الإعدادات الجديدة:
  overlay_font_name    : noto_naskh | noto_kufi | cairo | amiri | tajawal
  overlay_show_bg      : true/false — إظهار خلفية النص
  overlay_show_shadow  : true/false — إظهار ظل النص
  overlay_shadow_color : لون الظل hex — default #000000
  overlay_shadow_offset: إزاحة الظل (px) — default 3
"""

import io
import logging
import os
import re

logger = logging.getLogger(__name__)

# ── الـ 5 فونتات العربية المدعومة ────────────────────────────────────────────
# اسم الخط → اسم الملف في static/fonts/ أو مسارات النظام

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "fonts")

ARABIC_FONTS = {
    "noto_naskh": {
        "label": "Noto Naskh Arabic — نسخ كلاسيكي",
        "files": [
            os.path.join(FONTS_DIR, "NotoNaskhArabic-Regular.ttf"),
            os.path.join(FONTS_DIR, "NotoNaskhArabic-Bold.ttf"),
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
            "/usr/share/fonts/truetype/arabic/NotoNaskhArabic-Regular.ttf",
        ],
    },
    "noto_kufi": {
        "label": "Noto Kufi Arabic — كوفي عصري",
        "files": [
            os.path.join(FONTS_DIR, "NotoKufiArabic-Regular.ttf"),
            os.path.join(FONTS_DIR, "NotoKufiArabic-Bold.ttf"),
            "/usr/share/fonts/truetype/noto/NotoKufiArabic-Regular.ttf",
        ],
    },
    "cairo": {
        "label": "Cairo — عصري وواضح",
        "files": [
            os.path.join(FONTS_DIR, "Cairo-Regular.ttf"),
            os.path.join(FONTS_DIR, "Cairo-Bold.ttf"),
            os.path.join(FONTS_DIR, "Cairo-SemiBold.ttf"),
        ],
    },
    "amiri": {
        "label": "Amiri — أميري تقليدي",
        "files": [
            os.path.join(FONTS_DIR, "Amiri-Regular.ttf"),
            os.path.join(FONTS_DIR, "Amiri-Bold.ttf"),
            "/usr/share/fonts/truetype/fonts-hosny-amiri/Amiri-Regular.ttf",
        ],
    },
    "tajawal": {
        "label": "Tajawal — تجوال بسيط",
        "files": [
            os.path.join(FONTS_DIR, "Tajawal-Regular.ttf"),
            os.path.join(FONTS_DIR, "Tajawal-Bold.ttf"),
            os.path.join(FONTS_DIR, "Tajawal-Medium.ttf"),
        ],
    },
}

# Fallback system fonts
_SYSTEM_FALLBACKS = [
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
]


def _resolve_font(font_name: str) -> str | None:
    """Find the font file path for a given font name."""
    font_info = ARABIC_FONTS.get(font_name)
    if font_info:
        for path in font_info["files"]:
            if path and os.path.isfile(path):
                return path
    # Fallback to any available system font
    for path in _SYSTEM_FALLBACKS:
        if os.path.isfile(path):
            return path
    return None


def get_available_fonts() -> dict:
    """Return dict of font_name → {label, available} for UI."""
    result = {}
    for name, info in ARABIC_FONTS.items():
        available = any(os.path.isfile(p) for p in info["files"] if p)
        result[name] = {"label": info["label"], "available": available}
    return result


def _hex_to_rgba(hex_color: str, opacity: int = 100) -> tuple:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    a = int(opacity / 100 * 255)
    return (r, g, b, a)


def _get_overlay_cfg() -> dict:
    """Load overlay settings from Config DB."""
    try:
        from database.models import Config
        return {
            "enabled":       Config.get("overlay_enabled", "false").lower() == "true",
            "text_source":   Config.get("overlay_text_source", "ai"),
            "custom_text":   Config.get("overlay_custom_text", ""),
            "position":      Config.get("overlay_position", "bottom-center"),
            "font_name":     Config.get("overlay_font_name", "cairo"),
            "font_size":     int(Config.get("overlay_font_size", "52") or 52),
            "font_color":    Config.get("overlay_font_color", "#FFFFFF"),
            # Background
            "show_bg":       Config.get("overlay_show_bg", "true").lower() == "true",
            "bg_color":      Config.get("overlay_bg_color", "#000000"),
            "bg_opacity":    int(Config.get("overlay_bg_opacity", "60") or 60),
            "padding":       int(Config.get("overlay_padding", "20") or 20),
            # Shadow
            "show_shadow":   Config.get("overlay_show_shadow", "true").lower() == "true",
            "shadow_color":  Config.get("overlay_shadow_color", "#000000"),
            "shadow_offset": int(Config.get("overlay_shadow_offset", "3") or 3),
            # Text
            "max_chars":     int(Config.get("overlay_max_chars", "60") or 60),
        }
    except Exception:
        return {
            "enabled": False, "text_source": "ai", "custom_text": "",
            "position": "bottom-center", "font_name": "cairo", "font_size": 52,
            "font_color": "#FFFFFF", "show_bg": True, "bg_color": "#000000",
            "bg_opacity": 60, "padding": 20, "show_shadow": True,
            "shadow_color": "#000000", "shadow_offset": 3, "max_chars": 60,
        }


def generate_overlay_text(post_content: str, idea: str, provider: str = None) -> str:
    """Generate a short teaser/title for the image overlay using AI."""
    try:
        from services.ai_service import call_ai
        system = "أنت متخصص في كتابة عناوين جذابة وقصيرة للسوشال ميديا."
        user = (
            f"اكتب عنواناً أو جملة تشويقية قصيرة جداً (بحد أقصى 8 كلمات) "
            f"تُوضع على صورة لهذا المنشور.\n\n"
            f"الفكرة: {idea[:200]}\n\n"
            f"أول جزء من المنشور:\n{post_content[:300]}\n\n"
            f"القواعد:\n"
            f"- بالعربية فقط\n- بدون علامات اقتباس\n- بدون هاشتاق\n"
            f"- جملة واحدة فقط\n- مثيرة للاهتمام وتشجع على القراءة\n\n"
            f"الناتج: الجملة فقط بدون أي نص إضافي"
        )
        result = call_ai(
            provider or "gemini", "gemini-2.0-flash",
            system, user, temperature=0.7, max_tokens=50
        )
        result = result.strip().strip('"\'').strip()
        result = re.sub(r'[#@]', '', result).strip()
        return result[:80] if result else ""
    except Exception as e:
        logger.warning(f"Overlay text AI generation failed: {e}")
        return ""


def _extract_first_line(post_content: str, max_chars: int = 60) -> str:
    if not post_content:
        return ""
    lines = [l.strip() for l in post_content.split('\n') if l.strip()]
    for line in lines:
        clean = re.sub(r'[#@\U0001F300-\U0001FFFF]', '', line).strip()
        if len(clean) > 10:
            return line[:max_chars]
    return lines[0][:max_chars] if lines else ""


def _wrap_arabic_text(text: str, max_width_chars: int = 25) -> list:
    if not text:
        return []
    words = text.split()
    lines, current, current_len = [], [], 0
    for word in words:
        if current_len + len(word) + 1 > max_width_chars and current:
            lines.append(" ".join(current))
            current, current_len = [word], len(word)
        else:
            current.append(word)
            current_len += len(word) + 1
    if current:
        lines.append(" ".join(current))
    return lines


def apply_text_overlay(image_bytes: bytes, text: str, cfg: dict = None) -> bytes:
    """Apply Arabic text overlay on image using Pillow."""
    from PIL import Image, ImageDraw, ImageFont

    if not text or not text.strip():
        return image_bytes

    if cfg is None:
        cfg = _get_overlay_cfg()

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    W, H = img.size

    # ── Load font ─────────────────────────────────────────────────────────────
    font_path = _resolve_font(cfg.get("font_name", "cairo"))
    font_size = cfg["font_size"]
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
        logger.warning(f"Font '{cfg.get('font_name')}' not found — using default")

    # ── Wrap text ─────────────────────────────────────────────────────────────
    max_chars_per_line = max(10, int(W / (font_size * 0.6)))
    lines = _wrap_arabic_text(text, max_chars_per_line)

    # ── Measure text block ────────────────────────────────────────────────────
    padding      = cfg["padding"] if cfg["show_bg"] else 0
    draw_tmp     = ImageDraw.Draw(img)
    line_heights = []
    line_widths  = []
    for line in lines:
        bbox = draw_tmp.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    line_spacing = int(font_size * 0.3)
    block_w = max(line_widths) + padding * 2
    block_h = sum(line_heights) + line_spacing * (len(lines) - 1) + padding * 2

    # ── Calculate position ────────────────────────────────────────────────────
    parts = cfg["position"].split("-")
    v_pos = parts[0] if parts else "bottom"
    h_pos = parts[1] if len(parts) > 1 else "center"
    margin = int(H * 0.04)

    x = margin if h_pos == "left" else (W - block_w - margin if h_pos == "right" else (W - block_w) // 2)
    y = margin if v_pos == "top" else ((H - block_h) // 2 if v_pos == "center" else H - block_h - margin)

    # ── Draw background ───────────────────────────────────────────────────────
    if cfg["show_bg"] and cfg["bg_opacity"] > 0:
        overlay_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw_bg = ImageDraw.Draw(overlay_layer)
        bg_rgba = _hex_to_rgba(cfg["bg_color"], cfg["bg_opacity"])
        try:
            draw_bg.rounded_rectangle([x, y, x + block_w, y + block_h], radius=12, fill=bg_rgba)
        except AttributeError:
            draw_bg.rectangle([x, y, x + block_w, y + block_h], fill=bg_rgba)
        img = Image.alpha_composite(img, overlay_layer)

    draw = ImageDraw.Draw(img)
    text_color   = _hex_to_rgba(cfg["font_color"], 100)
    shadow_color = _hex_to_rgba(cfg.get("shadow_color", "#000000"), 200)
    shadow_off   = cfg.get("shadow_offset", 3)
    current_y    = y + padding

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]

        tx = (x + padding if h_pos == "left"
              else x + block_w - lw - padding if h_pos == "right"
              else x + (block_w - lw) // 2)

        # ── Draw shadow ───────────────────────────────────────────────────────
        if cfg["show_shadow"] and shadow_off > 0:
            draw.text((tx + shadow_off, current_y + shadow_off), line,
                      font=font, fill=shadow_color)

        # ── Draw text ─────────────────────────────────────────────────────────
        draw.text((tx, current_y), line, font=font, fill=text_color)
        current_y += lh + line_spacing

    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=92)
    return out.getvalue()


def process_overlay(image_bytes: bytes, post_content: str, idea: str,
                    provider: str = None) -> bytes:
    """Main entry point — called from image pipeline."""
    try:
        cfg = _get_overlay_cfg()
        if not cfg["enabled"]:
            return image_bytes

        text = ""
        source = cfg["text_source"]
        if source == "custom" and cfg["custom_text"]:
            text = cfg["custom_text"][:cfg["max_chars"]]
        elif source == "first_line":
            text = _extract_first_line(post_content, cfg["max_chars"])
        else:
            text = generate_overlay_text(post_content, idea, provider)
            if not text:
                text = _extract_first_line(post_content, cfg["max_chars"])

        if not text:
            return image_bytes

        logger.info(f"Overlay: '{text[:50]}' | font={cfg['font_name']} | pos={cfg['position']} | bg={cfg['show_bg']} | shadow={cfg['show_shadow']}")
        return apply_text_overlay(image_bytes, text, cfg)

    except Exception as e:
        logger.warning(f"Overlay failed (returning original): {e}")
        return image_bytes
