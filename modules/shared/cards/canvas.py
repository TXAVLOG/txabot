import os
import random
import math
from io import BytesIO
from typing import List, Dict, Any, Tuple, Optional

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

from .constants import SIZES, COLORS, GRADIENTS, CACHE_PATH, FONT_MAIN, FONT_EMOJI
from .utils import (
    load_font,
    load_bold_font,
    get_text_size,
    truncate_text,
    wrap_text,
    format_number,
    draw_text_with_emoji,
    draw_rounded_shadow,
    load_remote_image,
    create_placeholder,
    pick_background,
    get_card_size,
)


def _interpolate_color(c1: Tuple[int, ...], c2: Tuple[int, ...], t: float) -> Tuple[int, ...]:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def _draw_gradient_header(
    draw: ImageDraw.Draw,
    width: int,
    height: int,
    colors: List[Tuple[int, int, int, int]],
) -> None:
    """Draw a horizontal gradient header."""
    for x in range(width):
        t = x / width if width > 0 else 0
        idx = int(t * (len(colors) - 1))
        next_idx = min(idx + 1, len(colors) - 1)
        local_t = (t * (len(colors) - 1)) - idx
        color = _interpolate_color(colors[idx], colors[next_idx], local_t)
        draw.line([(x, 0), (x, height)], fill=color)


def _build_fonts(scale: int):
    """Build a dict of fonts for a given scale."""
    return {
        "header": load_bold_font(24 * scale),
        "header_emoji": load_font(FONT_EMOJI, 24 * scale),
        "title": load_bold_font(20 * scale),
        "title_emoji": load_font(FONT_EMOJI, 20 * scale),
        "body": load_font(FONT_MAIN, 16 * scale),
        "body_emoji": load_font(FONT_EMOJI, 16 * scale),
        "small": load_font(FONT_MAIN, 13 * scale),
        "small_emoji": load_font(FONT_EMOJI, 13 * scale),
        "number": load_bold_font(32 * scale),
        "badge": load_bold_font(14 * scale),
    }


def _make_canvas(width: int, height: int) -> Tuple[Image.Image, ImageDraw.Draw]:
    """Create a canvas with blurred background."""
    bg = pick_background(width, height)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.paste(bg, (0, 0))
    draw = ImageDraw.Draw(canvas)
    return canvas, draw


def _save_image(canvas: Image.Image, prefix: str, identifier: str) -> str:
    """Save canvas to cache and return file path."""
    filename = f"{prefix}_{abs(hash(identifier)) & 0xFFFFFFFF:08x}.png"
    path = os.path.join(CACHE_PATH, filename)
    canvas.convert("RGB").save(path, format="PNG", optimize=True)
    return path


def _draw_item_row(
    canvas: Image.Image,
    draw: ImageDraw.Draw,
    item: Dict[str, Any],
    index: int,
    box: Tuple[int, int, int, int],
    fonts: Dict[str, ImageFont.FreeTypeFont],
    cfg: Dict[str, Any],
    brand: str,
    content_type: str = "video",
) -> None:
    """Draw a single search result item row."""
    left, top, right, bottom = box
    scale = cfg["scale"]
    radius = cfg["radius"] * scale
    card_w = right - left
    card_h = bottom - top
    card_pad = cfg["card_padding"] * scale
    thumb_size = cfg["thumb_size"] * scale

    # Card shadow
    shadow = draw_rounded_shadow((card_w, card_h), radius, shadow_color=(0, 0, 0, 60), blur_radius=6 * scale)
    canvas.paste(shadow, (left - 12 * scale, top - 6 * scale), shadow)

    # Card background
    card_layer = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_layer)
    card_color = list(COLORS["card"])
    card_color[3] = 200
    card_draw.rounded_rectangle([0, 0, card_w, card_h], radius=radius, fill=tuple(card_color))
    canvas.paste(card_layer, (left, top), card_layer.split()[3])

    # Thumbnail
    cover_url = (
        item.get("cover")
        or item.get("origin_cover")
        or item.get("originCover")
        or item.get("thumb")
        or item.get("thumbnail")
        or item.get("dynamic_cover")
        or ""
    )
    thumb_x = left + card_pad
    thumb_y = top + (card_h - thumb_size) // 2
    thumb = load_remote_image(
        cover_url,
        (thumb_size, thumb_size),
        shape="rounded",
        radius=cfg["thumb_radius"] * scale,
    )
    if thumb:
        canvas.paste(thumb, (thumb_x, thumb_y), thumb)
    else:
        placeholder = create_placeholder((thumb_size, thumb_size))
        canvas.paste(placeholder, (thumb_x, thumb_y), placeholder)

    # Text area
    text_x = thumb_x + thumb_size + 14 * scale
    max_text_w = card_w - thumb_size - 2 * card_pad - 14 * scale - 50 * scale

    title = (item.get("title") or item.get("desc") or item.get("text") or "").strip()
    title = wrap_text(draw, title, max_text_w, fonts["title"], max_lines=cfg["max_title_lines"])
    y_text = top + card_pad + 4 * scale
    draw_text_with_emoji(
        draw, title, (text_x, y_text), fonts["title"], fonts["title_emoji"],
        COLORS["text_primary"], shadow_color=COLORS["shadow"], shadow_offset=(scale, scale)
    )

    author = item.get("author") or item.get("creator") or item.get("nickname") or item.get("unique_id") or "?"
    author_text = f"@{author}"
    y_author = y_text + (22 * scale * len(title.split("\n"))) + 4 * scale
    draw_text_with_emoji(
        draw, author_text, (text_x, y_author), fonts["body"], fonts["body_emoji"],
        COLORS["text_secondary"], shadow_color=COLORS["shadow_light"], shadow_offset=(1, 1)
    )

    # Stats
    views = format_number(
        item.get("view_count") or item.get("playCount") or item.get("play_count")
        or item.get("use_count") or item.get("used_count") or 0
    )
    likes = format_number(item.get("like_count") or item.get("diggCount") or item.get("digg_count") or 0)
    shares = format_number(item.get("shareCount") or item.get("share_count") or 0)
    uses = format_number(item.get("use_count") or item.get("used_count") or 0)

    if brand == "tiktok":
        stats_text = f"▶ {views}  ❤️ {likes}  🔁 {shares}"
    else:
        stats_text = f"👁️ {views}  ❤️ {likes}  🔁 {uses}"

    y_stats = bottom - card_pad - fonts["small"].size - 2 * scale
    draw_text_with_emoji(
        draw, stats_text, (text_x, y_stats), fonts["small"], fonts["small_emoji"],
        COLORS["text_muted"], shadow_color=COLORS["shadow_light"], shadow_offset=(1, 1)
    )

    # Number badge
    number_text = str(index + 1)
    nw, nh = get_text_size(draw, number_text, fonts["number"])
    number_x = right - nw - card_pad
    number_y = top + (card_h - nh) // 2
    accent = COLORS["accent_capcut"] if brand == "capcut" else COLORS["accent_tiktok"]
    draw_text_with_emoji(
        draw, number_text, (number_x, number_y), fonts["number"], fonts["number"],
        accent, shadow_color=COLORS["shadow"], shadow_offset=(2, 2)
    )


def create_search_card(
    items: List[Dict[str, Any]],
    header_title: str,
    footer_text: str,
    brand: str = "tiktok",
    content_type: str = "video",
    size: str = None,
) -> Optional[str]:
    """Create a search result card image."""
    try:
        size = size or get_card_size()
        cfg = SIZES.get(size, SIZES["md"])
        scale = cfg["scale"]
        card_w = cfg["card_width"] * scale
        card_h = cfg["card_height"] * scale
        padding = cfg["padding"] * scale
        spacing_y = cfg["spacing_y"] * scale
        header_h = cfg["header_height"] * scale
        footer_h = cfg["footer_height"] * scale

        items = items[:5]
        n = len(items)
        img_w = card_w + 2 * padding
        img_h = header_h + padding + n * card_h + max(0, n - 1) * spacing_y + footer_h + padding

        canvas, draw = _make_canvas(img_w, img_h)
        fonts = _build_fonts(scale)

        # Gradient header
        header_layer = Image.new("RGBA", (img_w, header_h), (0, 0, 0, 0))
        header_draw = ImageDraw.Draw(header_layer)
        colors = GRADIENTS.get(brand, GRADIENTS["dark"])
        _draw_gradient_header(header_draw, img_w, header_h, colors)
        canvas.paste(header_layer, (0, 0))

        # Header text
        icon = "🎬" if content_type == "video" else "🖼️"
        full_header = f"{icon} {header_title}"
        header_w, header_h_text = get_text_size(draw, full_header, fonts["header"])
        header_x = padding
        header_y = (header_h - header_h_text) // 2
        draw_text_with_emoji(
            draw, full_header, (header_x, header_y), fonts["header"], fonts["header_emoji"],
            COLORS["text_primary"], shadow_color=COLORS["shadow"], shadow_offset=(2, 2)
        )

        # Items
        y_start = header_h + padding
        for i, item in enumerate(items):
            top = y_start + i * (card_h + spacing_y)
            _draw_item_row(
                canvas, draw, item, i,
                (padding, top, padding + card_w, top + card_h),
                fonts, cfg, brand, content_type
            )

        # Footer
        footer_y = y_start + n * card_h + max(0, n - 1) * spacing_y + (footer_h - fonts["small"].size) // 2
        draw_text_with_emoji(
            draw, footer_text, (padding, footer_y), fonts["small"], fonts["small_emoji"],
            COLORS["text_secondary"], shadow_color=COLORS["shadow_light"], shadow_offset=(1, 1)
        )

        # Watermark
        wm_text = "TXA Bot"
        wm_w, wm_h = get_text_size(draw, wm_text, fonts["small"])
        draw.text(
            (img_w - wm_w - padding, img_h - wm_h - padding // 2),
            wm_text,
            font=fonts["small"],
            fill=(255, 255, 255, 100),
        )

        return _save_image(canvas, f"{brand}_search", header_title)
    except Exception as e:
        print(f"[{brand.upper()}] Error creating search card: {e}")
        return None


def create_download_card(
    data: Dict[str, Any],
    brand: str = "tiktok",
    size: str = None,
) -> Optional[str]:
    """Create a download preview card."""
    try:
        size = size or get_card_size()
        cfg = SIZES.get(size, SIZES["md"])
        scale = cfg["scale"]
        card_w = cfg["card_width"] * scale
        padding = cfg["padding"] * scale
        thumb_size = min(180 * scale, card_w - 2 * padding)
        fonts = _build_fonts(scale)

        title = (data.get("title") or data.get("desc") or "").strip()
        author = data.get("author") or data.get("creator") or data.get("nickname") or data.get("unique_id") or "?"
        duration = data.get("duration") or 0
        duration_str = f"{int(duration) // 60}:{int(duration) % 60:02d}" if duration else "?"
        likes = format_number(data.get("like_count") or data.get("diggCount") or data.get("digg_count") or 0)

        cover_url = (
            data.get("cover")
            or data.get("thumb")
            or data.get("thumbnail")
            or data.get("origin_cover")
            or ""
        )

        header_h = 70 * scale
        img_w = card_w + 2 * padding
        img_h = header_h + padding + thumb_size + 20 * scale + (len(title.split("\n")) + 3) * 24 * scale + padding

        canvas, draw = _make_canvas(img_w, img_h)

        # Header
        header_layer = Image.new("RGBA", (img_w, header_h), (0, 0, 0, 0))
        header_draw = ImageDraw.Draw(header_layer)
        colors = GRADIENTS.get(brand, GRADIENTS["dark"])
        _draw_gradient_header(header_draw, img_w, header_h, colors)
        canvas.paste(header_layer, (0, 0))

        header_icon = "🎞️"
        header_text = f"{header_icon} {brand.upper()} Download"
        header_w, header_h_text = get_text_size(draw, header_text, fonts["header"])
        header_x = padding
        header_y = (header_h - header_h_text) // 2
        draw_text_with_emoji(
            draw, header_text, (header_x, header_y), fonts["header"], fonts["header_emoji"],
            COLORS["text_primary"], shadow_color=COLORS["shadow"], shadow_offset=(2, 2)
        )

        # Thumbnail centered
        thumb_x = (img_w - thumb_size) // 2
        thumb_y = header_h + padding
        thumb = load_remote_image(
            cover_url,
            (thumb_size, thumb_size),
            shape="rounded",
            radius=cfg["thumb_radius"] * scale,
        )
        if thumb:
            canvas.paste(thumb, (thumb_x, thumb_y), thumb)
        else:
            placeholder = create_placeholder((thumb_size, thumb_size))
            canvas.paste(placeholder, (thumb_x, thumb_y), placeholder)

        # No watermark badge
        badge_text = "✅ No Watermark"
        badge_w, badge_h = get_text_size(draw, badge_text, fonts["badge"])
        badge_pad = 8 * scale
        badge_x = (img_w - (badge_w + 2 * badge_pad)) // 2
        badge_y = thumb_y + thumb_size + 12 * scale
        badge_layer = Image.new("RGBA", (badge_w + 2 * badge_pad, badge_h + 2 * badge_pad), (0, 0, 0, 0))
        badge_draw = ImageDraw.Draw(badge_layer)
        accent = COLORS["accent_capcut"] if brand == "capcut" else COLORS["accent_tiktok"]
        badge_draw.rounded_rectangle([0, 0, badge_w + 2 * badge_pad, badge_h + 2 * badge_pad], radius=8 * scale, fill=accent)
        canvas.paste(badge_layer, (badge_x, badge_y), badge_layer.split()[3])
        draw_text_with_emoji(
            draw, badge_text, (badge_x + badge_pad, badge_y + badge_pad), fonts["badge"], fonts["badge"],
            COLORS["text_primary"]
        )

        # Info
        y_info = badge_y + badge_h + 2 * badge_pad + 16 * scale
        title_wrapped = wrap_text(draw, title, card_w, fonts["title"], max_lines=2)
        draw_text_with_emoji(
            draw, title_wrapped, (padding, y_info), fonts["title"], fonts["title_emoji"],
            COLORS["text_primary"], shadow_color=COLORS["shadow"], shadow_offset=(1, 1)
        )

        y_meta = y_info + (22 * scale * len(title_wrapped.split("\n"))) + 8 * scale
        meta_text = f"👤 @{author}  ⏱️ {duration_str}  ❤️ {likes}"
        draw_text_with_emoji(
            draw, meta_text, (padding, y_meta), fonts["body"], fonts["body_emoji"],
            COLORS["text_secondary"], shadow_color=COLORS["shadow_light"], shadow_offset=(1, 1)
        )

        # Watermark
        wm_text = "TXA Bot"
        wm_w, wm_h = get_text_size(draw, wm_text, fonts["small"])
        draw.text(
            (img_w - wm_w - padding, img_h - wm_h - padding // 2),
            wm_text,
            font=fonts["small"],
            fill=(255, 255, 255, 100),
        )

        return _save_image(canvas, f"{brand}_download", title or str(id(data)))
    except Exception as e:
        print(f"[{brand.upper()}] Error creating download card: {e}")
        return None


def create_profile_card(
    profile: Dict[str, Any],
    brand: str = "tiktok",
    size: str = None,
) -> Optional[str]:
    """Create a profile card (mainly for TikTok)."""
    try:
        size = size or get_card_size()
        cfg = SIZES.get(size, SIZES["md"])
        scale = cfg["scale"]
        card_w = cfg["card_width"] * scale
        padding = cfg["padding"] * scale
        fonts = _build_fonts(scale)

        nickname = profile.get("nickname") or profile.get("nickName") or "Không rõ"
        unique_id = profile.get("unique_id") or profile.get("uniqueId") or profile.get("username") or "?"
        signature = (profile.get("signature") or profile.get("desc") or "").strip()
        followers = format_number(profile.get("followerCount") or profile.get("follower_count") or profile.get("fans") or 0)
        following = format_number(profile.get("followingCount") or profile.get("following_count") or 0)
        likes = format_number(profile.get("heartCount") or profile.get("heart_count") or profile.get("totalFavorited") or 0)
        videos = format_number(profile.get("videoCount") or profile.get("video_count") or profile.get("awemeCount") or 0)
        verified = bool(profile.get("verified") or profile.get("isVerified") or False)

        avatar_url = (
            profile.get("avatar")
            or profile.get("avatarLarger")
            or profile.get("avatarThumb")
            or profile.get("avatar_medium")
            or ""
        )

        header_h = 100 * scale
        avatar_size = 80 * scale
        img_w = card_w + 2 * padding
        img_h = header_h + padding + avatar_size + 20 * scale + (len(signature.split("\n")) + 4) * 24 * scale + padding

        canvas, draw = _make_canvas(img_w, img_h)

        # Header gradient
        header_layer = Image.new("RGBA", (img_w, header_h), (0, 0, 0, 0))
        header_draw = ImageDraw.Draw(header_layer)
        colors = GRADIENTS.get(brand, GRADIENTS["dark"])
        _draw_gradient_header(header_draw, img_w, header_h, colors)
        canvas.paste(header_layer, (0, 0))

        # Avatar (circular)
        avatar_x = padding
        avatar_y = header_h + padding
        avatar = load_remote_image(
            avatar_url,
            (avatar_size, avatar_size),
            shape="ellipse",
            radius=0,
        )
        if avatar:
            canvas.paste(avatar, (avatar_x, avatar_y), avatar)
        else:
            placeholder = create_placeholder((avatar_size, avatar_size))
            canvas.paste(placeholder, (avatar_x, avatar_y), placeholder)

        # Nickname & username
        text_x = avatar_x + avatar_size + 14 * scale
        nick_y = avatar_y + 8 * scale
        draw_text_with_emoji(
            draw, nickname, (text_x, nick_y), fonts["header"], fonts["header_emoji"],
            COLORS["text_primary"], shadow_color=COLORS["shadow"], shadow_offset=(2, 2)
        )

        uid_text = f"@{unique_id}"
        if verified:
            uid_text += " ✅"
        uid_y = nick_y + 28 * scale
        draw_text_with_emoji(
            draw, uid_text, (text_x, uid_y), fonts["body"], fonts["body_emoji"],
            COLORS["text_secondary"], shadow_color=COLORS["shadow_light"], shadow_offset=(1, 1)
        )

        # Bio
        bio_y = avatar_y + avatar_size + 16 * scale
        if signature:
            bio_wrapped = wrap_text(draw, signature, card_w, fonts["body"], max_lines=3)
            draw_text_with_emoji(
                draw, bio_wrapped, (padding, bio_y), fonts["body"], fonts["body_emoji"],
                COLORS["text_primary"], shadow_color=COLORS["shadow"], shadow_offset=(1, 1)
            )
            bio_y += 22 * scale * len(bio_wrapped.split("\n")) + 16 * scale

        # Stats grid
        stats = [
            ("❤️", likes),
            ("👥", followers),
            ("➡️", following),
            ("🎬", videos),
        ]
        col_width = card_w // 4
        for i, (icon, value) in enumerate(stats):
            x = padding + i * col_width
            stat_text = f"{icon}\n{value}"
            draw_text_with_emoji(
                draw, stat_text, (x, bio_y), fonts["body"], fonts["body_emoji"],
                COLORS["text_secondary"], shadow_color=COLORS["shadow_light"], shadow_offset=(1, 1)
            )

        # Watermark
        wm_text = "TXA Bot"
        wm_w, wm_h = get_text_size(draw, wm_text, fonts["small"])
        draw.text(
            (img_w - wm_w - padding, img_h - wm_h - padding // 2),
            wm_text,
            font=fonts["small"],
            fill=(255, 255, 255, 100),
        )

        return _save_image(canvas, f"{brand}_profile", unique_id)
    except Exception as e:
        print(f"[{brand.upper()}] Error creating profile card: {e}")
        return None


def create_help_card(
    brand: str = "tiktok",
    commands: List[Tuple[str, str]] = None,
    size: str = None,
) -> Optional[str]:
    """Create a help card listing available commands."""
    try:
        size = size or get_card_size()
        cfg = SIZES.get(size, SIZES["md"])
        scale = cfg["scale"]
        card_w = cfg["card_width"] * scale
        padding = cfg["padding"] * scale
        fonts = _build_fonts(scale)

        if commands is None:
            commands = []

        header_h = 70 * scale
        line_h = 26 * scale
        img_w = card_w + 2 * padding
        img_h = header_h + padding + len(commands) * line_h + padding

        canvas, draw = _make_canvas(img_w, img_h)

        # Header
        header_layer = Image.new("RGBA", (img_w, header_h), (0, 0, 0, 0))
        header_draw = ImageDraw.Draw(header_layer)
        colors = GRADIENTS.get(brand, GRADIENTS["dark"])
        _draw_gradient_header(header_draw, img_w, header_h, colors)
        canvas.paste(header_layer, (0, 0))

        header_text = f"❓ {brand.upper()} Help"
        header_w, header_h_text = get_text_size(draw, header_text, fonts["header"])
        header_x = padding
        header_y = (header_h - header_h_text) // 2
        draw_text_with_emoji(
            draw, header_text, (header_x, header_y), fonts["header"], fonts["header_emoji"],
            COLORS["text_primary"], shadow_color=COLORS["shadow"], shadow_offset=(2, 2)
        )

        # Commands
        y = header_h + padding
        for cmd, desc in commands:
            line = f"• {cmd}: {desc}"
            draw_text_with_emoji(
                draw, line, (padding, y), fonts["body"], fonts["body_emoji"],
                COLORS["text_primary"], shadow_color=COLORS["shadow_light"], shadow_offset=(1, 1)
            )
            y += line_h

        # Watermark
        wm_text = "TXA Bot"
        wm_w, wm_h = get_text_size(draw, wm_text, fonts["small"])
        draw.text(
            (img_w - wm_w - padding, img_h - wm_h - padding // 2),
            wm_text,
            font=fonts["small"],
            fill=(255, 255, 255, 100),
        )

        return _save_image(canvas, f"{brand}_help", brand)
    except Exception as e:
        print(f"[{brand.upper()}] Error creating help card: {e}")
        return None
