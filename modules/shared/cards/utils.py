import os
import random
import glob
import requests
from io import BytesIO
from typing import Tuple, Optional

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

from .constants import (
    FONT_MAIN,
    FONT_MAIN_BOLD,
    FONT_EMOJI,
    FONT_FALLBACKS,
    FONT_FALLBACKS_BOLD,
    COLORS,
    BACKGROUND_PATH,
    SIZES,
)


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a TrueType font with fallback chain."""
    candidates = [path] + FONT_FALLBACKS
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except (OSError, IOError):
                continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def load_bold_font(size: int) -> ImageFont.FreeTypeFont:
    """Load a bold font with fallback chain."""
    candidates = [FONT_MAIN_BOLD] + FONT_FALLBACKS_BOLD
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except (OSError, IOError):
                continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def is_emoji(char: str) -> bool:
    """Check if a character is an emoji."""
    try:
        import emoji
        return char in emoji.EMOJI_DATA
    except Exception:
        return ord(char) >= 0x1F000


def get_text_size(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    """Return (width, height) of text using the given font."""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        try:
            width = int(font.getlength(text))
        except Exception:
            width = len(text) * font.size // 2
        return width, font.size


def truncate_text(draw: ImageDraw.Draw, text: str, max_width: int, font: ImageFont.FreeTypeFont) -> str:
    """Truncate text with ellipsis if it exceeds max_width."""
    if not text:
        return ""
    w, _ = get_text_size(draw, text, font)
    if w <= max_width:
        return text
    while len(text) > 0:
        w, _ = get_text_size(draw, text + "...", font)
        if w <= max_width:
            return text + "..."
        text = text[:-1]
    return "..."


def wrap_text(draw: ImageDraw.Draw, text: str, max_width: int, font: ImageFont.FreeTypeFont, max_lines: int = 2) -> str:
    """Wrap text into max_lines, truncating with ellipsis if needed."""
    if not text:
        return ""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = current + " " + word if current else word
        w, _ = get_text_size(draw, test, font)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)

    result = "\n".join(lines[:max_lines])
    if len(lines) >= max_lines and len(words) > sum(len(l.split()) for l in lines):
        result = truncate_text(draw, result.replace("\n", " "), max_width, font)
    return result


def format_number(n) -> str:
    """Format a number into K/M/B shorthand."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n) if n else "0"
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def draw_text_with_emoji(
    draw: ImageDraw.Draw,
    text: str,
    position: Tuple[int, int],
    font: ImageFont.FreeTypeFont,
    emoji_font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int, int],
    shadow_color: Tuple[int, int, int, int] = None,
    shadow_offset: Tuple[int, int] = (2, 2),
) -> Tuple[int, int]:
    """Draw text char by char, switching to emoji font for emoji characters.
    Returns the next x position.
    """
    x, y = position
    for char in text:
        if char == "\ufe0f":
            continue
        try:
            font_used = emoji_font if is_emoji(char) and emoji_font else font
        except Exception:
            font_used = font

        if shadow_color:
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), char, font=font_used, fill=shadow_color)
        draw.text((x, y), char, font=font_used, fill=fill)
        x += get_text_size(draw, char, font_used)[0]
    return x, y


def draw_rounded_rect(
    draw: ImageDraw.Draw,
    xy: Tuple[int, int, int, int],
    radius: int,
    fill: Tuple[int, int, int, int] = None,
    outline: Tuple[int, int, int, int] = None,
    width: int = 1,
) -> None:
    """Draw a rounded rectangle with optional fill and outline."""
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_rounded_shadow(
    size: Tuple[int, int],
    radius: int,
    shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 60),
    blur_radius: int = 8,
    offset: Tuple[int, int] = (0, 4),
) -> Image.Image:
    """Create a blurred rounded shadow layer."""
    sw, sh = size
    pad = blur_radius * 2
    shadow = Image.new("RGBA", (sw + pad * 2, sh + pad * 2), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        [(pad + offset[0], pad + offset[1]), (pad + offset[0] + sw, pad + offset[1] + sh)],
        radius=radius,
        fill=shadow_color,
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    return shadow


def load_remote_image(
    url: str,
    size: Tuple[int, int],
    shape: str = "rounded",
    radius: int = 12,
    timeout: int = 8,
) -> Optional[Image.Image]:
    """Download an image and fit it into a rounded/ellipse shape."""
    if not url or not url.startswith("http"):
        return None
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        img = ImageOps.fit(img, size, centering=(0.5, 0.5))
        mask = Image.new("L", size, 0)
        mask_draw = ImageDraw.Draw(mask)
        if shape == "ellipse":
            mask_draw.ellipse((0, 0, size[0], size[1]), fill=255)
        else:
            mask_draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
        img = img.convert("RGBA")
        img.putalpha(mask)
        return img
    except Exception:
        return None


def create_placeholder(size: Tuple[int, int], color: Tuple[int, int, int, int] = COLORS["placeholder"]) -> Image.Image:
    """Create a placeholder image."""
    return Image.new("RGBA", size, color)


def pick_background(width: int, height: int) -> Image.Image:
    """Pick a random background image and blur it, or use solid dark color."""
    bg_images = (
        glob.glob(BACKGROUND_PATH + "*.jpg")
        + glob.glob(BACKGROUND_PATH + "*.png")
        + glob.glob(BACKGROUND_PATH + "*.jpeg")
    )
    if bg_images:
        try:
            bg_path = random.choice(bg_images)
            bg = Image.open(bg_path).convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=8))
            # Dark overlay for readability
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 120))
            bg = Image.alpha_composite(bg, overlay)
            return bg
        except Exception:
            pass
    return Image.new("RGBA", (width, height), COLORS["bg"])


def get_card_size() -> str:
    """Return configured card size. Supports sm, md, lg. Default md."""
    size = os.environ.get("TXA_CARD_SIZE", "md").lower()
    return size if size in SIZES else "md"


def draw_watermark(
    draw: ImageDraw.Draw,
    text: str = "TXA Bot",
    position: Tuple[int, int] = None,
    font_size: int = 12,
    fill: Tuple[int, int, int, int] = None,
) -> None:
    """Draw a small watermark at bottom-right corner."""
    if fill is None:
        fill = (255, 255, 255, 80)
    # Not implemented here because we need canvas size; use position argument.
    font = load_font(FONT_MAIN, font_size)
    draw.text(position, text, font=font, fill=fill)
