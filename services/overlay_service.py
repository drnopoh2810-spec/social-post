"""
Image Text Overlay Service
===========================
يضع نص عربي على الصورة بعد الـ frame overlay.

Flow:
  صورة مولّدة → frame overlay → text overlay → رفع Cloudinary

الإعدادات (من Config DB):
  overlay_enabled      : true/false
  overlay_text_source  : ai | first_line | custom
  overlay_custom_text  : نص ثابت (لو source=custom)
  overlay_position     : top-left | top-center | top-right |
                         center-left | center | center-right |
                         bottom-left | bottom-center | bottom-right
  overlay_font_size    : حجم الخط (px) — default 52
  overlay_font_color   : لون النص hex — default #FFFFFF
  overlay_bg_color     : لون خلفية النص hex — default #000000
  overlay_bg_opacity   : شفافية الخلفية 0-100 — default 60
  overlay_padding      : padding حول النص (px) — default 20
  overlay_max_chars    : حد الأحرف للنص — default 60
"""

import io
import logging
import os
import re
import textwrap
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Arabic font path ──────────────────────────────────────────────────────────
# يبحث عن خط عربي مثبّت أو يستخدم fallback
_FONT_CANDIDATES = [
    # Linux / PythonAnywhere
    "/usr/share/fonts/truetype/arabic/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    # macOS
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    # Windows
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    # Project-local (يمكن وضع خط في static/fonts/)
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "fonts", "arabic.ttf"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "fonts", "NotoNaskhArabic-Regular.ttf"),
]


def _get_font_path() -> str | None:
    for p in _FONT_CANDIDATES:
        if p and os.path.isfile(p):
            return p
    return None


def _hex_to_rgba(hex_color: str, opacity: int = 100) -> tuple:
    """Convert #RRGGBB + opacity% → (R, G, B, A)."""
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
            "enabled":     Config.get("overlay_enabled", "false").lower() == "true",
            "text_source": Config.get("overlay_text_source", "ai"),
            "custom_text": Config.get("overlay_custom_text", ""),
            "position":    Config.get("overlay_position", "bottom-center"),
            "font_size":   int(Config.get("overlay_font_size", "52") or 52),
            "font_color":  Config.get("overlay_font_color", "#FFFFFF"),
            "bg_color":    Config.get("overlay_bg_color", "#000000"),
            "bg_opacity":  int(Config.get("overlay_bg_opacity", "60") or 60),
            "padding":     int(Config.get("overlay_padding", "20") or 20),
            "max_chars":   int(Config.get("overlay_max_chars", "60") or 60),
        }
    except Exception:
        return {
            "enabled": False, "text_source": "ai", "custom_text": "",
            "position": "bottom-center", "font_size": 52,
            "font_color": "#FFFFFF", "bg_color": "#000000",
            "bg_opacity": 60, "padding": 20, "max_chars": 60,
        }


def generate_overlay_text(post_content: str, idea: str, provider: str = None) -> str:
    """
    Generate a short teaser/title for the image overlay using AI.
    Falls back to extracting first line of post_content.
    """
    try:
        from services.ai_service import call_ai
        from database.models import Config

        niche = Config.get("niche", "")
        system = "أنت متخصص في كتابة عناوين جذابة وقصيرة للسوشال ميديا."
        user = (
            f"اكتب عنواناً أو جملة تشويقية قصيرة جداً (بحد أقصى 8 كلمات) "
            f"تُوضع على صورة لهذا المنشور.\n\n"
            f"الفكرة: {idea[:200]}\n\n"
            f"أول جزء من المنشور:\n{post_content[:300]}\n\n"
            f"القواعد:\n"
            f"- بالعربية فقط\n"
            f"- بدون علامات اقتباس\n"
            f"- بدون هاشتاق\n"
            f"- جملة واحدة فقط\n"
            f"- مثيرة للاهتمام وتشجع على القراءة\n\n"
            f"الناتج: الجملة فقط بدون أي نص إضافي"
        )
        result = call_ai(
            provider or "gemini", "gemini-2.0-flash",
            system, user, temperature=0.7, max_tokens=50
        )
        # Clean result
        result = result.strip().strip('"\'').strip()
        result = re.sub(r'[#@]', '', result).strip()
        return result[:80] if result else ""
    except Exception as e:
        logger.warning(f"Overlay text AI generation failed: {e}")
        return ""


def _extract_first_line(post_content: str, max_chars: int = 60) -> str:
    """Extract first meaningful line from post content."""
    if not post_content:
        return ""
    lines = [l.strip() for l in post_content.split('\n') if l.strip()]
    for line in lines:
        # Skip lines that are just emojis or hashtags
        clean = re.sub(r'[#@\U0001F300-\U0001FFFF]', '', line).strip()
        if len(clean) > 10:
            return line[:max_chars]
    return lines[0][:max_chars] if lines else ""


def _wrap_arabic_text(text: str, max_width_chars: int = 25) -> list[str]:
    """
    Wrap Arabic text into lines.
    Arabic is RTL so we wrap by character count.
    """
    if not text:
        return []
    words = text.split()
    lines = []
    current = []
    current_len = 0
    for word in words:
        if current_len + len(word) + 1 > max_width_chars and current:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += len(word) + 1
    if current:
        lines.append(" ".join(current))
    return lines


def apply_text_overlay(image_bytes: bytes, text: str, cfg: dict = None) -> bytes:
    """
    Apply Arabic text overlay on image using Pillow.

    Args:
        image_bytes: Raw image bytes
        text: Text to overlay
        cfg: Overlay config dict (from _get_overlay_cfg())

    Returns:
        Modified image bytes (JPEG)
    """
    from PIL import Image, ImageDraw, ImageFont

    if not text or not text.strip():
        return image_bytes

    if cfg is None:
        cfg = _get_overlay_cfg()

    # Open image
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    W, H = img.size

    # Load font
    font_path = _get_font_path()
    font_size = cfg["font_size"]
    try:
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
            logger.warning("No Arabic font found — using default font (Arabic may not render correctly)")
    except Exception:
        font = ImageFont.load_default()

    # Wrap text
    max_chars_per_line = max(10, int(W / (font_size * 0.6)))
    lines = _wrap_arabic_text(text, max_chars_per_line)

    # Measure text block
    padding = cfg["padding"]
    draw_tmp = ImageDraw.Draw(img)
    line_heights = []
    line_widths  = []
    for line in lines:
        bbox = draw_tmp.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    line_spacing = int(font_size * 0.3)
    block_w = max(line_widths) + padding * 2
    block_h = sum(line_heights) + line_spacing * (len(lines) - 1) + padding * 2

    # Calculate position
    position = cfg["position"]  # e.g. "bottom-center"
    parts = position.split("-")
    v_pos = parts[0] if len(parts) > 0 else "bottom"
    h_pos = parts[1] if len(parts) > 1 else "center"

    margin = int(H * 0.04)  # 4% margin from edges

    if h_pos == "left":
        x = margin
    elif h_pos == "right":
        x = W - block_w - margin
    else:  # center
        x = (W - block_w) // 2

    if v_pos == "top":
        y = margin
    elif v_pos == "center":
        y = (H - block_h) // 2
    else:  # bottom
        y = H - block_h - margin

    # Draw background rectangle
    overlay_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay_layer)

    bg_rgba = _hex_to_rgba(cfg["bg_color"], cfg["bg_opacity"])
    # Rounded rectangle (Pillow 9+)
    try:
        draw.rounded_rectangle(
            [x, y, x + block_w, y + block_h],
            radius=12, fill=bg_rgba
        )
    except AttributeError:
        draw.rectangle([x, y, x + block_w, y + block_h], fill=bg_rgba)

    # Composite background
    img = Image.alpha_composite(img, overlay_layer)
    draw = ImageDraw.Draw(img)

    # Draw text lines
    text_color = _hex_to_rgba(cfg["font_color"], 100)
    current_y = y + padding
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]

        # Horizontal alignment within block
        if h_pos == "left":
            tx = x + padding
        elif h_pos == "right":
            tx = x + block_w - lw - padding
        else:
            tx = x + (block_w - lw) // 2

        # Draw text shadow for readability
        shadow_color = (0, 0, 0, 180)
        draw.text((tx + 2, current_y + 2), line, font=font, fill=shadow_color)
        draw.text((tx, current_y), line, font=font, fill=text_color)

        current_y += lh + line_spacing

    # Convert back to RGB JPEG
    result = img.convert("RGB")
    out = io.BytesIO()
    result.save(out, format="JPEG", quality=92)
    return out.getvalue()


def process_overlay(image_bytes: bytes, post_content: str, idea: str,
                    provider: str = None) -> bytes:
    """
    Main entry point — called from image pipeline.
    Generates text (via AI or extraction) then applies overlay.

    Returns original image_bytes if overlay is disabled or fails.
    """
    try:
        cfg = _get_overlay_cfg()

        if not cfg["enabled"]:
            return image_bytes

        # Get text based on source
        text = ""
        source = cfg["text_source"]

        if source == "custom" and cfg["custom_text"]:
            text = cfg["custom_text"][:cfg["max_chars"]]

        elif source == "first_line":
            text = _extract_first_line(post_content, cfg["max_chars"])

        else:  # ai (default)
            text = generate_overlay_text(post_content, idea, provider)
            if not text:
                # Fallback to first line
                text = _extract_first_line(post_content, cfg["max_chars"])

        if not text:
            logger.info("Overlay: no text generated — skipping")
            return image_bytes

        logger.info(f"Overlay: applying text '{text[:50]}' at {cfg['position']}")
        result = apply_text_overlay(image_bytes, text, cfg)
        logger.info("Overlay: text applied successfully")
        return result

    except Exception as e:
        logger.warning(f"Overlay failed (returning original): {e}")
        return image_bytes  # Never break the pipeline
