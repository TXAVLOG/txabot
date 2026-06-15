# -*- coding: UTF-8 -*-
"""
Module: tiktok.py
Lệnh: tt, tiktok, ttdl, tksearch, tiktoksearch, downtik, tiktokinfo, in4tiktok
- tt <từ khóa>              → Tìm kiếm video/ảnh TikTok
- tt img <từ khóa>          → Tìm ảnh TikTok
- ttdl <link>               → Tải video TikTok không watermark
- tiktokinfo <username>     → Xem thông tin profile TikTok
"""

import sys
import os
import json
import glob
import random
import tempfile
import requests
from io import BytesIO

sys.dont_write_bytecode = True

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from colorsys import hsv_to_rgb

KAIROBOT_BASE_URL = "https://kairobot.qzz.io"
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../txa.json"))
BACKGROUND_PATH = "background/"
CACHE_PATH = "modules/cache/"
os.makedirs(CACHE_PATH, exist_ok=True)

# ─── METADATA ─────────────────────────────────────────────────────────────────
txa = {
    "name": "TikTok Search & Download",
    "desc": {
        "tt": "Tìm kiếm video/ảnh TikTok",
        "tiktok": "Tìm kiếm video/ảnh TikTok",
        "ttdl": "Tải video TikTok không watermark",
        "downtik": "Tải video TikTok không watermark",
        "tksearch": "Tìm kiếm video/ảnh TikTok",
        "tiktoksearch": "Tìm kiếm video/ảnh TikTok",
        "tiktokinfo": "Xem thông tin profile TikTok",
        "in4tiktok": "Xem thông tin profile TikTok",
    },
    "author": "TXA",
    "command": ["tt", "tiktok", "ttdl", "downtik", "tksearch", "tiktoksearch", "tiktokinfo", "in4tiktok"],
}

# ─── CONFIG ───────────────────────────────────────────────────────────────────

def _read_api_key():
    for key in ("KAIROBOT_APIKEY", "KAIROBOT_API_KEY", "TXA_APIKEY", "TXA_API_KEY"):
        value = os.getenv(key)
        if value:
            return value.strip()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        bot_data = (config.get("data") or [{}])[0]
        for key in ("kairobot_api_key", "kairobot_apikey", "apikey", "api_key"):
            value = bot_data.get(key)
            if value:
                return str(value).strip()
    except Exception:
        pass
    return ""


def _api_get(path, params):
    api_key = _read_api_key()
    if not api_key:
        raise RuntimeError("Thiếu API key KaiRobot.")
    payload = dict(params)
    payload["apikey"] = api_key
    response = requests.get(f"{KAIROBOT_BASE_URL}{path}", params=payload, timeout=30)
    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text}
    if response.status_code == 401:
        msg = data.get("message") if isinstance(data, dict) else None
        raise RuntimeError(msg or "API key KaiRobot không hợp lệ.")
    if response.status_code == 400:
        msg = data.get("message") if isinstance(data, dict) else None
        if not msg and isinstance(data, dict) and data.get("success") is False:
            msg = "API không thể xử lý yêu cầu."
        raise RuntimeError(msg or "Yêu cầu không hợp lệ.")
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        raise RuntimeError(f"Lỗi kết nối API: {e}")
    if isinstance(data, dict) and data.get("success") is False:
        msg = data.get("message") or data.get("error") or "API trả về trạng thái thất bại."
        raise RuntimeError(msg)
    return data

# ─── IMAGE HELPERS ────────────────────────────────────────────────────────────

def _num_fmt(n) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n) if n else "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _format_number(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "0"
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _random_contrast_color(base_color):
    r, g, b = base_color[:3]
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    if brightness > 128:
        return (30, 30, 30, 255)
    return (255, 255, 255, 255)


def _get_text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _truncate_text(draw, text, max_width, font):
    if not text:
        return ""
    w = _get_text_width(draw, text, font)
    if w <= max_width:
        return text
    while len(text) > 0 and _get_text_width(draw, text + "…", font) > max_width:
        text = text[:-1]
    return text + "…"


def _draw_text_with_shadow(draw, position, text, font, fill, shadow_color=(0, 0, 0, 150), shadow_offset=(2, 2)):
    x, y = position
    draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=fill)


# ─── TIKTOK SEARCH IMAGE ─────────────────────────────────────────────────────

def create_tiktok_search_image(items, keywords, content_type="video"):
    try:
        scale = 2
        font_path = "font/arial unicode ms.otf"
        emoji_font_path = "font/NotoEmoji-Bold.ttf"

        title_font = ImageFont.truetype(font_path, 26 * scale)
        title_emoji_font = ImageFont.truetype(emoji_font_path, 26 * scale)
        author_font = ImageFont.truetype(font_path, 18 * scale)
        author_emoji_font = ImageFont.truetype(emoji_font_path, 18 * scale)
        info_font = ImageFont.truetype(font_path, 14 * scale)
        info_emoji_font = ImageFont.truetype(emoji_font_path, 14 * scale)
        number_font = ImageFont.truetype(font_path, 36 * scale)
        header_font = ImageFont.truetype(font_path, 22 * scale)
        header_emoji_font = ImageFont.truetype(emoji_font_path, 22 * scale)

        card_height = 110 * scale
        card_width = 580 * scale
        thumb_size = 90 * scale
        padding = 20 * scale
        spacing_y = 10 * scale
        card_padding = 8 * scale

        items_to_draw = items[:5]
        N = len(items_to_draw)

        img_width = card_width + 2 * padding
        header_height = 70 * scale
        img_height = header_height + padding + N * card_height + (N - 1) * spacing_y + padding

        bg_images = glob.glob(BACKGROUND_PATH + "*.jpg") + glob.glob(BACKGROUND_PATH + "*.png") + glob.glob(BACKGROUND_PATH + "*.jpeg")
        if bg_images:
            try:
                bg_path = random.choice(bg_images)
                background = Image.open(bg_path).convert("RGBA").resize((img_width, img_height), Image.Resampling.LANCZOS)
                background = background.filter(ImageFilter.GaussianBlur(radius=7))
            except Exception:
                background = Image.new("RGBA", (img_width, img_height), (20, 20, 20, 255))
        else:
            background = Image.new("RGBA", (img_width, img_height), (20, 20, 20, 255))

        image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        image.paste(background, (0, 0))
        draw = ImageDraw.Draw(image)

        box_colors = [
            (255, 20, 147, 110),
            (128, 0, 128, 110),
            (0, 100, 0, 110),
            (0, 0, 139, 110),
            (184, 134, 11, 110),
            (138, 3, 3, 110),
            (0, 0, 0, 80),
        ]
        box_color = random.choice(box_colors)
        title_color = _random_contrast_color(box_color)
        number_color = _random_contrast_color(box_color)
        info_color = (255, 255, 255, 255)

        icon = "🎬" if content_type == "video" else "🖼️"
        header_text = f"{icon} TikTok Search: {keywords}"
        x_header = padding
        y_header = padding
        for char in header_text:
            if char == '\ufe0f':
                continue
            try:
                import emoji as emoji_mod
                font_used = header_emoji_font if emoji_mod.is_emoji(char) else header_font
            except Exception:
                font_used = header_font
            _draw_text_with_shadow(draw, (x_header, y_header), char, font_used, title_color)
            x_header += _get_text_width(draw, char, font_used)

        y_start = padding + header_height

        for i, item in enumerate(items_to_draw):
            title = (item.get("title") or item.get("desc") or item.get("text") or "").strip()
            title = title[:60] + "…" if len(title) > 60 else title
            author = item.get("author") or item.get("nickname") or item.get("unique_id") or "?"
            likes = _format_number(item.get("diggCount") or item.get("like_count") or item.get("digg_count") or 0)
            comments = _format_number(item.get("commentCount") or item.get("comment_count") or 0)
            plays = _format_number(item.get("playCount") or item.get("play_count") or 0)
            shares = _format_number(item.get("shareCount") or item.get("share_count") or 0)
            ctype = (item.get("type") or "video").lower()

            cover_url = (
                item.get("cover")
                or item.get("origin_cover")
                or item.get("originCover")
                or item.get("thumb")
                or item.get("dynamic_cover")
                or ""
            )

            left = padding
            top = y_start + i * (card_height + spacing_y)

            card_img = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
            card_draw = ImageDraw.Draw(card_img)
            radius = 20 * scale
            card_draw.rounded_rectangle([0, 0, card_width, card_height], radius=radius, fill=box_color)
            image.paste(card_img, (left, top), card_img.split()[3])

            if cover_url and cover_url.startswith("http"):
                try:
                    resp = requests.get(cover_url, timeout=8)
                    resp.raise_for_status()
                    cover = Image.open(BytesIO(resp.content)).convert("RGB")
                    cover = ImageOps.fit(cover, (thumb_size, thumb_size), centering=(0.5, 0.5))
                    mask = Image.new("L", (thumb_size, thumb_size), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.ellipse((0, 0, thumb_size, thumb_size), fill=255)
                    cover.putalpha(mask)

                    border_size = thumb_size + 10
                    rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
                    draw_border = ImageDraw.Draw(rainbow_border)
                    steps = 360
                    for j in range(steps):
                        h = j / steps
                        r, g, b = hsv_to_rgb(h, 1.0, 1.0)
                        draw_border.arc(
                            [(0, 0), (border_size - 1, border_size - 1)],
                            j, j + (360 / steps),
                            fill=(int(r * 255), int(g * 255), int(b * 255), 255),
                            width=5,
                        )
                    cover_y = top + (card_height - thumb_size) // 2
                    image.paste(rainbow_border, (left + card_padding - 5, cover_y - 5), rainbow_border)
                    image.paste(cover, (left + card_padding, cover_y), cover)
                except Exception:
                    placeholder = Image.new("RGBA", (thumb_size, thumb_size), (60, 60, 60, 255))
                    image.paste(placeholder, (left + card_padding, top + (card_height - thumb_size) // 2), placeholder)
            else:
                placeholder = Image.new("RGBA", (thumb_size, thumb_size), (60, 60, 60, 255))
                image.paste(placeholder, (left + card_padding, top + (card_height - thumb_size) // 2), placeholder)

            x_text = left + card_padding + thumb_size + 20 * scale
            max_text_width = card_width - thumb_size - 3 * card_padding - 20 * scale

            y_text = top + card_padding + 5 * scale
            truncated_title = _truncate_text(draw, title, max_text_width, title_font)
            for char in truncated_title:
                if char == '\ufe0f':
                    continue
                try:
                    import emoji as emoji_mod
                    font_used = title_emoji_font if emoji_mod.is_emoji(char) else title_font
                except Exception:
                    font_used = title_font
                _draw_text_with_shadow(draw, (x_text, y_text), char, font_used, title_color)
                x_text += _get_text_width(draw, char, font_used)

            y_author = y_text + int(32 * scale)
            truncated_author = _truncate_text(draw, f"@{author}", max_text_width, author_font)
            x_author = x_text - _get_text_width(draw, truncated_title[-1] if truncated_title else "", title_font) if truncated_title else x_text
            x_author = left + card_padding + thumb_size + 20 * scale
            for char in truncated_author:
                if char == '\ufe0f':
                    continue
                try:
                    import emoji as emoji_mod
                    font_used = author_emoji_font if emoji_mod.is_emoji(char) else author_font
                except Exception:
                    font_used = author_font
                _draw_text_with_shadow(draw, (x_author, y_author), char, font_used, info_color, shadow_offset=(1, 1))
                x_author += _get_text_width(draw, char, font_used)

            type_icon = "🎬" if ctype == "video" else "🖼️"
            info_text = f"{type_icon} {plays}  ❤️ {likes}  💬 {comments}  🔁 {shares}"
            x_info = left + card_padding + thumb_size + 20 * scale
            info_height = info_font.size
            y_info = top + card_height - card_padding - info_height - 2 * scale
            for char in info_text:
                if char == '\ufe0f':
                    continue
                try:
                    import emoji as emoji_mod
                    font_used = info_emoji_font if emoji_mod.is_emoji(char) else info_font
                except Exception:
                    font_used = info_font
                _draw_text_with_shadow(draw, (x_info, y_info), char, font_used, info_color, shadow_offset=(1, 1))
                x_info += _get_text_width(draw, char, font_used)

            number_text = str(i + 1)
            number_width = _get_text_width(draw, number_text, number_font)
            number_x = left + card_width - number_width - card_padding
            number_y = top + (card_height - number_font.size) // 2
            _draw_text_with_shadow(draw, (number_x, number_y), number_text, number_font, number_color)

        file_path = os.path.join(CACHE_PATH, f"tt_search_{hash(keywords) & 0xFFFFFF:06x}.png")
        image.convert("RGB").save(file_path, format="JPEG", quality=95, optimize=True)
        return file_path
    except Exception as e:
        print(f"[TikTok] Error creating search image: {e}")
        return None


# ─── TEXT CARDS (fallback) ───────────────────────────────────────────────────

def _build_download_card(data: dict) -> str:
    title = (data.get("title") or data.get("desc") or "").strip()
    title = title[:100] + "…" if len(title) > 100 else title
    author = data.get("author") or data.get("nickname") or data.get("unique_id") or "?"
    dur = data.get("duration") or 0
    dur_s = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "?"
    likes = _num_fmt(data.get("diggCount") or data.get("like_count") or 0)

    return "\n".join([
        "╔══════════════════════╗",
        "║  🎵  TikTok Download  ║",
        "╚══════════════════════╝",
        f"📝 {title or '(Không có tiêu đề)'}",
        f"👤 @{author}",
        f"⏱️ {dur_s}  ❤️ {likes}",
        "✅ Video không watermark đang gửi…",
    ])


def _build_profile_card(data: dict) -> str:
    nickname = data.get("nickname") or data.get("nickName") or "Không rõ"
    unique_id = data.get("unique_id") or data.get("uniqueId") or data.get("username") or "?"
    signature = (data.get("signature") or data.get("desc") or "").strip()
    signature = signature[:100] + "…" if len(signature) > 100 else signature
    followers = _num_fmt(data.get("followerCount") or data.get("follower_count") or data.get("fans") or 0)
    following = _num_fmt(data.get("followingCount") or data.get("following_count") or data.get("following") or 0)
    likes = _num_fmt(data.get("heartCount") or data.get("heart_count") or data.get("heart") or data.get("totalFavorited") or 0)
    videos = _num_fmt(data.get("videoCount") or data.get("video_count") or data.get("awemeCount") or 0)
    verified = data.get("verified") or data.get("isVerified") or False
    badge = " ✅" if verified else ""

    lines = [
        "╔══════════════════════╗",
        "║  🎵  TikTok Profile   ║",
        "╚══════════════════════╝",
        f"👤 @{unique_id}{badge}",
        f"📛 {nickname}",
    ]
    if signature:
        lines.append(f"📝 {signature}")
    lines += [
        f"❤️ {likes}  👥 {followers}  ➡️ {following}",
        f"🎬 {videos} video",
    ]

    avatar = data.get("avatar") or data.get("avatarThumb") or data.get("avatarLarger") or data.get("avatar_medium") or ""
    if avatar:
        lines.append(f"🖼️ Avatar: {avatar}")

    return "\n".join(lines)

# ─── API CALLS ────────────────────────────────────────────────────────────────

def _search_tiktok(keywords: str, content_type: str = "video", count: int = 5, cursor: int = 0):
    params = {"keywords": keywords, "count": count, "cursor": cursor}
    if content_type:
        params["type"] = content_type
    return _api_get("/tiktok/search", params)


def _download_tiktok(video_url: str):
    return _api_get("/tiktok/download", {"url": video_url})


def _get_profile(username: str):
    return _api_get("/tiktok/profile", {"username": username})

# ─── NORMALIZE ────────────────────────────────────────────────────────────────

def _normalize_items(resp):
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        for key in ("data", "results", "items", "videos"):
            val = resp.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                for sub in ("data", "list", "items", "videos"):
                    subval = val.get(sub)
                    if isinstance(subval, list):
                        return subval
                return [val] if val else []
        return []
    return []


def _normalize_profile(resp):
    if isinstance(resp, dict):
        for key in ("data", "user", "profile"):
            val = resp.get(key)
            if isinstance(val, dict):
                return val
        if "nickname" in resp or "unique_id" in resp or "uniqueId" in resp:
            return resp
    return resp if isinstance(resp, dict) else {}

# ─── COMMAND HANDLER ──────────────────────────────────────────────────────────

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    from zlapi.models import Message

    parts = message_text.strip().split(None, 1)
    cmd = parts[0].lstrip("*!./").lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    if not _read_api_key():
        bot.replyMessage(
            Message(text="⚠️ Chưa cấu hình kairobot_api_key trong txa.json!"),
            message_object, thread_id, thread_type,
        )
        return

    # ── HELP ──────────────────────────────────────────────────────────────
    if not arg and cmd in ("tiktok", "tt", "tksearch", "tiktoksearch"):
        bot.replyMessage(
            Message(text=(
                "🎵 TikTok Search & Download\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📌 Lệnh:\n"
                "  *tt <từ khóa>           → Tìm video\n"
                "  *tt img <từ khóa>       → Tìm ảnh\n"
                "  *ttdl <link>            → Tải video no-WM\n"
                "  *tiktokinfo <username>  → Xem profile"
            )),
            message_object, thread_id, thread_type,
        )
        return

    # ── PROFILE ───────────────────────────────────────────────────────────
    if cmd in ("tiktokinfo", "in4tiktok"):
        if not arg:
            bot.replyMessage(
                Message(text="🎵 Dùng: *tiktokinfo <username>\nVí dụ: *tiktokinfo @nguyenhung07"),
                message_object, thread_id, thread_type,
            )
            return

        username = arg.lstrip("@")
        bot.replyMessage(
            Message(text=f"🔍 Đang lấy thông tin profile: @{username}…"),
            message_object, thread_id, thread_type,
        )

        try:
            resp = _get_profile(username)
        except Exception as e:
            bot.replyMessage(
                Message(text=f"❌ Lỗi lấy profile: {e}"),
                message_object, thread_id, thread_type,
            )
            return

        profile = _normalize_profile(resp)
        if not profile or not profile.get("nickname"):
            bot.replyMessage(
                Message(text=f"😔 Không tìm thấy profile: @{username}"),
                message_object, thread_id, thread_type,
            )
            return

        card = _build_profile_card(profile)
        bot.replyMessage(Message(text=card), message_object, thread_id, thread_type)

        avatar = profile.get("avatar") or profile.get("avatarThumb") or profile.get("avatarLarger") or ""
        if avatar and avatar.startswith("http"):
            try:
                bot.sendRemoteImage(
                    avatar,
                    thumbnailUrl=avatar,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    message=Message(text=f"🖼️ Avatar: @{profile.get('unique_id') or profile.get('uniqueId', '')}"),
                )
            except Exception:
                pass
        return

    # ── DOWNLOAD ──────────────────────────────────────────────────────────
    if cmd in ("ttdl", "downtik"):
        if not arg or not arg.startswith("http"):
            bot.replyMessage(
                Message(text="🎬 Dùng: *ttdl <link TikTok>\nVí dụ: *ttdl https://www.tiktok.com/@user/video/xxx"),
                message_object, thread_id, thread_type,
            )
            return

        bot.replyMessage(Message(text="⏳ Đang tải video TikTok…"), message_object, thread_id, thread_type)

        try:
            data = _download_tiktok(arg)
        except Exception as e:
            bot.replyMessage(
                Message(text=f"❌ Lỗi API: {e}"),
                message_object, thread_id, thread_type,
            )
            return

        inner = data.get("data") if isinstance(data, dict) else data

        video_dl = (
            (inner or {}).get("video_url_no_watermark")
            or (inner or {}).get("video")
            or (inner or {}).get("url")
            or data.get("video_url_no_watermark")
            or data.get("video")
            or data.get("url")
        )

        card = _build_download_card(inner or data)
        bot.replyMessage(Message(text=card), message_object, thread_id, thread_type)

        if video_dl:
            try:
                cover = (inner or data).get("cover") or ""
                dur = int((inner or data).get("duration") or 0)
                bot.sendRemoteVideo(
                    videoUrl=video_dl,
                    thumbnailUrl=cover,
                    duration=dur,
                    thread_id=thread_id,
                    thread_type=thread_type,
                )
            except Exception:
                bot.replyMessage(
                    Message(text=f"⚠️ Không gửi được video trực tiếp.\n🔗 Link tải: {video_dl}"),
                    message_object, thread_id, thread_type,
                )
        return

    # ── SEARCH ────────────────────────────────────────────────────────────
    content_type = "video"
    keywords = arg
    if arg.lower().startswith(("img ", "image ", "ảnh ", "photo ")):
        content_type = "image"
        keywords = arg.split(None, 1)[1] if " " in arg else arg

    if not keywords:
        bot.replyMessage(
            Message(text="❌ Vui lòng nhập từ khóa tìm kiếm."),
            message_object, thread_id, thread_type,
        )
        return

    bot.replyMessage(
        Message(text=f"🔍 Đang tìm TikTok {content_type}: **{keywords}**…"),
        message_object, thread_id, thread_type,
    )

    try:
        resp = _search_tiktok(keywords, content_type, count=5)
    except Exception as e:
        bot.replyMessage(
            Message(text=f"❌ Lỗi tìm kiếm: {e}"),
            message_object, thread_id, thread_type,
        )
        return

    items = _normalize_items(resp)

    if not items:
        bot.replyMessage(
            Message(text=f"😔 Không tìm thấy kết quả cho: **{keywords}**"),
            message_object, thread_id, thread_type,
        )
        return

    total = min(len(items), 5)
    image_path = create_tiktok_search_image(items[:total], keywords, content_type)

    if image_path and os.path.exists(image_path):
        try:
            with Image.open(image_path) as img:
                w, h = img.size
            bot.sendLocalImage(
                image_path,
                message=Message(text=f"🎵 TikTok Search: {keywords} ({total} kết quả)"),
                thread_id=thread_id,
                thread_type=thread_type,
                width=w,
                height=h,
            )
        except Exception:
            bot.replyMessage(
                Message(text=f"🎵 Tìm thấy {total} kết quả TikTok cho: **{keywords}**"),
                message_object, thread_id, thread_type,
            )
        finally:
            try:
                os.remove(image_path)
            except Exception:
                pass
    else:
        bot.replyMessage(
            Message(text=f"🎵 Tìm thấy {total} kết quả TikTok cho: **{keywords}**"),
            message_object, thread_id, thread_type,
        )

    bot.replyMessage(
        Message(text="💡 Dùng *ttdl <link> để tải video không watermark"),
        message_object, thread_id, thread_type,
    )
