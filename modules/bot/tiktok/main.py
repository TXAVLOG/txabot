# -*- coding: UTF-8 -*-
"""
Module: tiktok.py
Lệnh: tt, tiktok, ttdl, tksearch, tiktoksearch, downtik, tiktokinfo, in4tiktok
- tt <từ khóa>              → Tìm kiếm video/ảnh TikTok
- tt img <từ khóa>          → Tìm ảnh TikTok
- ttdl <link>               → Tải video TikTok không watermark
- ttdl <số>                 → Chọn video từ kết quả tìm kiếm trước
- tiktokinfo <username>     → Xem thông tin profile TikTok
"""

import sys
import os
import json
import glob
import random
import time
import requests
from io import BytesIO

sys.dont_write_bytecode = True

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from colorsys import hsv_to_rgb
from zlapi.models import Message, Mention

KAIROBOT_BASE_URL = "https://kairobot.qzz.io"
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../txa.json"))
BACKGROUND_PATH = "background/"
CACHE_PATH = "modules/cache/"
os.makedirs(CACHE_PATH, exist_ok=True)

SEARCH_TIMEOUT = 10560

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

try:
    from core.bot_sys import USER_MUSIC_STATES, zalo_len, zalo_offset, _music_styled_msg
    user_states = USER_MUSIC_STATES
    HAS_MUSIC_STATES = True
except ImportError:
    user_states = {}
    HAS_MUSIC_STATES = False

def zalo_len(text):
    return len(text) if text else 0

def zalo_offset(full_text, username):
    if not username:
        return -1
    idx = full_text.find(username)
    return idx if idx != -1 else -1

def _music_styled_msg(text, mention=None):
    return Message(text=text, mention=mention)

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
    while len(text) > 0 and _get_text_width(draw, text + "...", font) > max_width:
        text = text[:-1]
    return text + "..."


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

        title_font = ImageFont.truetype(font_path, 24 * scale)
        title_emoji_font = ImageFont.truetype(emoji_font_path, 24 * scale)
        info_font = ImageFont.truetype(font_path, 16 * scale)
        info_emoji_font = ImageFont.truetype(emoji_font_path, 16 * scale)
        number_font = ImageFont.truetype(font_path, 32 * scale)
        header_font = ImageFont.truetype(font_path, 22 * scale)
        header_emoji_font = ImageFont.truetype(emoji_font_path, 22 * scale)

        card_height = 100 * scale
        card_width = 580 * scale
        thumb_size = 80 * scale
        padding = 20 * scale
        spacing_y = 10 * scale
        card_padding = 10 * scale

        items_to_draw = items[:5]
        N = len(items_to_draw)

        img_width = card_width + 2 * padding
        header_height = 60 * scale
        footer_height = 50 * scale
        img_height = header_height + padding + N * card_height + (N - 1) * spacing_y + footer_height + padding

        bg_images = glob.glob(BACKGROUND_PATH + "*.jpg") + glob.glob(BACKGROUND_PATH + "*.png") + glob.glob(BACKGROUND_PATH + "*.jpeg")
        if bg_images:
            try:
                bg_path = random.choice(bg_images)
                background = Image.open(bg_path).convert("RGBA").resize((img_width, img_height), Image.Resampling.LANCZOS)
                background = background.filter(ImageFilter.GaussianBlur(radius=8))
            except Exception:
                background = Image.new("RGBA", (img_width, img_height), (18, 18, 24, 255))
        else:
            background = Image.new("RGBA", (img_width, img_height), (18, 18, 24, 255))

        image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        image.paste(background, (0, 0))
        draw = ImageDraw.Draw(image)

        header_bg = Image.new("RGBA", (img_width, header_height + padding), (0, 0, 0, 120))
        image.paste(header_bg, (0, 0), header_bg)

        icon = "🎬" if content_type == "video" else "🖼️"
        header_text = f"{icon} TikTok Search: {keywords}"
        x_header = padding
        y_header = padding + 10 * scale
        for char in header_text:
            if char == '\ufe0f':
                continue
            try:
                import emoji as emoji_mod
                font_used = header_emoji_font if emoji_mod.is_emoji(char) else header_font
            except Exception:
                font_used = header_font
            _draw_text_with_shadow(draw, (x_header, y_header), char, font_used, (255, 255, 255, 255))
            x_header += _get_text_width(draw, char, font_used)

        y_start = padding + header_height

        for i, item in enumerate(items_to_draw):
            title = (item.get("title") or item.get("desc") or item.get("text") or "").strip()
            title = title[:55] + "..." if len(title) > 55 else title
            likes = _format_number(item.get("diggCount") or item.get("like_count") or item.get("digg_count") or 0)
            plays = _format_number(item.get("playCount") or item.get("play_count") or 0)
            shares = _format_number(item.get("shareCount") or item.get("share_count") or 0)

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
            radius = 16 * scale
            card_color = (40, 40, 50, 180)
            card_draw.rounded_rectangle([0, 0, card_width, card_height], radius=radius, fill=card_color)
            image.paste(card_img, (left, top), card_img.split()[3])

            if cover_url and cover_url.startswith("http"):
                try:
                    resp = requests.get(cover_url, timeout=8)
                    resp.raise_for_status()
                    cover = Image.open(BytesIO(resp.content)).convert("RGB")
                    cover = ImageOps.fit(cover, (thumb_size, thumb_size), centering=(0.5, 0.5))
                    mask = Image.new("L", (thumb_size, thumb_size), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.rounded_rectangle([0, 0, thumb_size, thumb_size], radius=8 * scale, fill=255)
                    cover.putalpha(mask)

                    cover_y = top + (card_height - thumb_size) // 2
                    image.paste(cover, (left + card_padding, cover_y), cover)
                except Exception:
                    placeholder = Image.new("RGBA", (thumb_size, thumb_size), (60, 60, 70, 255))
                    image.paste(placeholder, (left + card_padding, top + (card_height - thumb_size) // 2), placeholder)
            else:
                placeholder = Image.new("RGBA", (thumb_size, thumb_size), (60, 60, 70, 255))
                image.paste(placeholder, (left + card_padding, top + (card_height - thumb_size) // 2), placeholder)

            x_text = left + card_padding + thumb_size + 16 * scale
            max_text_width = card_width - thumb_size - 3 * card_padding - 16 * scale

            y_text = top + card_padding + 8 * scale
            truncated_title = _truncate_text(draw, title, max_text_width, title_font)
            for char in truncated_title:
                if char == '\ufe0f':
                    continue
                try:
                    import emoji as emoji_mod
                    font_used = title_emoji_font if emoji_mod.is_emoji(char) else title_font
                except Exception:
                    font_used = title_font
                _draw_text_with_shadow(draw, (x_text, y_text), char, font_used, (255, 255, 255, 255))
                x_text += _get_text_width(draw, char, font_used)

            info_text = f"▶ {plays}  ❤️ {likes}  🔁 {shares}"
            x_info = left + card_padding + thumb_size + 16 * scale
            info_height = info_font.size
            y_info = top + card_height - card_padding - info_height - 6 * scale
            for char in info_text:
                if char == '\ufe0f':
                    continue
                try:
                    import emoji as emoji_mod
                    font_used = info_emoji_font if emoji_mod.is_emoji(char) else info_font
                except Exception:
                    font_used = info_font
                _draw_text_with_shadow(draw, (x_info, y_info), char, font_used, (180, 180, 190, 255), shadow_offset=(1, 1))
                x_info += _get_text_width(draw, char, font_used)

            number_text = str(i + 1)
            number_width = _get_text_width(draw, number_text, number_font)
            number_x = left + card_width - number_width - card_padding
            number_y = top + (card_height - number_font.size) // 2
            num_color = (0, 200, 120, 255)
            _draw_text_with_shadow(draw, (number_x, number_y), number_text, number_font, num_color)

        footer_text = "💡 Nhập ttdl <số> để chọn video"
        y_footer = y_start + N * card_height + (N - 1) * spacing_y + 10 * scale
        for char in footer_text:
            if char == '\ufe0f':
                continue
            try:
                import emoji as emoji_mod
                font_used = info_emoji_font if emoji_mod.is_emoji(char) else info_font
            except Exception:
                font_used = info_font
            _draw_text_with_shadow(draw, (padding, y_footer), char, font_used, (150, 150, 160, 200), shadow_offset=(1, 1))
            padding_temp = _get_text_width(draw, char, font_used)

        file_path = os.path.join(CACHE_PATH, f"tt_search_{hash(keywords) & 0xFFFF:04x}.png")
        image.convert("RGB").save(file_path, format="JPEG", quality=95, optimize=True)
        return file_path
    except Exception as e:
        print(f"[TikTok] Error creating search image: {e}")
        return None


# ─── TEXT CARDS (fallback) ───────────────────────────────────────────────────

def _build_download_card(data: dict) -> str:
    title = (data.get("title") or data.get("desc") or "").strip()
    title = title[:100] + "..." if len(title) > 100 else title
    author = data.get("author") or data.get("nickname") or data.get("unique_id") or "?"
    dur = data.get("duration") or 0
    dur_s = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "?"
    likes = _format_number(data.get("diggCount") or data.get("like_count") or 0)

    return "\n".join([
        "╔══════════════════════╗",
        "║  🎵  TikTok Download  ║",
        "╚══════════════════════╝",
        f"📝 {title or '(Không có tiêu đề)'}",
        f"👤 @{author}",
        f"⏱️ {dur_s}  ❤️ {likes}",
        "✅ Video không watermark đang gửi...",
    ])


def _build_profile_card(data: dict) -> str:
    nickname = data.get("nickname") or data.get("nickName") or "Không rõ"
    unique_id = data.get("unique_id") or data.get("uniqueId") or data.get("username") or "?"
    signature = (data.get("signature") or data.get("desc") or "").strip()
    signature = signature[:100] + "..." if len(signature) > 100 else signature
    followers = _format_number(data.get("followerCount") or data.get("follower_count") or data.get("fans") or 0)
    following = _format_number(data.get("followingCount") or data.get("following_count") or data.get("following") or 0)
    likes = _format_number(data.get("heartCount") or data.get("heart_count") or data.get("heart") or data.get("totalFavorited") or 0)
    videos = _format_number(data.get("videoCount") or data.get("video_count") or data.get("awemeCount") or 0)
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

# ─── DOWNLOAD VIDEO HELPER ───────────────────────────────────────────────────

def _do_download_video(bot, message_object, thread_id, thread_type, author_id, video_url):
    from zlapi.models import Message
    bot.replyMessage(Message(text="⏳ Đang tải video TikTok..."), message_object, thread_id, thread_type)
    try:
        data = _download_tiktok(video_url)
    except Exception as e:
        bot.replyMessage(Message(text=f"❌ Lỗi API: {e}"), message_object, thread_id, thread_type)
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

# ─── GET USERNAME HELPER ─────────────────────────────────────────────────────

def _get_username(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id)
        if user_info and hasattr(user_info, 'changed_profiles') and author_id in user_info.changed_profiles:
            user = user_info.changed_profiles[author_id]
            return getattr(user, 'name', None) or getattr(user, 'displayName', None) or f"ID_{author_id}"
    except Exception:
        pass
    return f"ID_{author_id}"

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

    # ── DIRECT DIGIT SELECTION (from txa.py router) ──────────────────────────
    if cmd.isdigit() and not arg:
        if not HAS_MUSIC_STATES or author_id not in user_states or user_states[author_id].get('source') != 'tiktok':
            return

        state = user_states[author_id]
        if time.time() - state.get('time_of_search', 0) > SEARCH_TIMEOUT:
            del user_states[author_id]
            return

        items = state.get('items', [])
        selected_index = int(cmd) - 1

        if selected_index < 0 or selected_index >= len(items):
            return

        search_msg = state.get('search_msg')
        if search_msg and hasattr(search_msg, 'msgId') and hasattr(search_msg, 'cliMsgId'):
            try:
                bot.undoMessage(search_msg.msgId, search_msg.cliMsgId, thread_id, thread_type)
            except Exception:
                pass

        query_msg_id = state.get('query_msg_id')
        query_cli_msg_id = state.get('query_cli_msg_id')
        if query_msg_id and query_cli_msg_id:
            try:
                bot.deleteGroupMsg(query_msg_id, author_id, query_cli_msg_id, thread_id)
            except Exception:
                pass

        if message_object and hasattr(message_object, 'msgId') and hasattr(message_object, 'cliMsgId'):
            try:
                bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
            except Exception:
                pass

        del user_states[author_id]

        item = items[selected_index]
        video_url = item.get("url") or item.get("play") or item.get("video_url") or item.get("link") or ""
        if video_url and video_url.startswith("http"):
            _do_download_video(bot, message_object, thread_id, thread_type, author_id, video_url)
        else:
            bot.replyMessage(
                Message(text="❌ Không tìm thấy link video để tải."),
                message_object, thread_id, thread_type,
            )
        return

    # ── TTDL WITH NUMBER SELECTION ────────────────────────────────────────────
    if cmd in ("ttdl", "downtik"):
        if arg and arg.isdigit():
            if not HAS_MUSIC_STATES:
                bot.replyMessage(Message(text="❌ Hệ thống state chưa sẵn sàng."), message_object, thread_id, thread_type)
                return

            if author_id not in user_states or user_states[author_id].get('source') != 'tiktok':
                bot.replyMessage(
                    Message(text="❌ Không có kết quả tìm kiếm TikTok nào để chọn.\n💡 Dùng *tt <từ khóa> để tìm trước."),
                    message_object, thread_id, thread_type,
                )
                return

            state = user_states[author_id]
            if time.time() - state.get('time_of_search', 0) > SEARCH_TIMEOUT:
                del user_states[author_id]
                bot.replyMessage(
                    Message(text="⏰ Hết thời gian chọn! Vui lòng tìm kiếm lại."),
                    message_object, thread_id, thread_type,
                )
                return

            items = state.get('items', [])
            selected_index = int(arg) - 1

            if selected_index < 0 or selected_index >= len(items):
                bot.replyMessage(
                    Message(text=f"❌ Số thứ tự không hợp lệ: {arg}"),
                    message_object, thread_id, thread_type,
                )
                return

            search_msg = state.get('search_msg')
            if search_msg and hasattr(search_msg, 'msgId') and hasattr(search_msg, 'cliMsgId'):
                try:
                    bot.undoMessage(search_msg.msgId, search_msg.cliMsgId, thread_id, thread_type)
                except Exception:
                    pass

            query_msg_id = state.get('query_msg_id')
            query_cli_msg_id = state.get('query_cli_msg_id')
            if query_msg_id and query_cli_msg_id:
                try:
                    bot.deleteGroupMsg(query_msg_id, author_id, query_cli_msg_id, thread_id)
                except Exception:
                    pass

            if message_object and hasattr(message_object, 'msgId') and hasattr(message_object, 'cliMsgId'):
                try:
                    bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
                except Exception:
                    pass

            del user_states[author_id]

            item = items[selected_index]
            video_url = item.get("url") or item.get("play") or item.get("video_url") or item.get("link") or ""
            if video_url and video_url.startswith("http"):
                _do_download_video(bot, message_object, thread_id, thread_type, author_id, video_url)
            else:
                bot.replyMessage(
                    Message(text="❌ Không tìm thấy link video để tải."),
                    message_object, thread_id, thread_type,
                )
            return

        if not arg or not arg.startswith("http"):
            bot.replyMessage(
                Message(text=(
                    "🎬 Dùng:\n"
                    "  *ttdl <link>    → Tải video TikTok\n"
                    "  *ttdl <số>      → Chọn từ kết quả tìm kiếm\n"
                    "💡 Ví dụ: *ttdl https://www.tiktok.com/@user/video/xxx"
                )),
                message_object, thread_id, thread_type,
            )
            return

        _do_download_video(bot, message_object, thread_id, thread_type, author_id, arg)
        return

    # ── HELP ──────────────────────────────────────────────────────────────────
    if not arg and cmd in ("tiktok", "tt", "tksearch", "tiktoksearch"):
        bot.replyMessage(
            Message(text=(
                "🎵 TikTok Search & Download\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📌 Lệnh:\n"
                "  *tt <từ khóa>           → Tìm video\n"
                "  *tt img <từ khóa>       → Tìm ảnh\n"
                "  *ttdl <link>            → Tải video no-WM\n"
                "  *ttdl <số>              → Chọn từ kết quả\n"
                "  *tiktokinfo <username>  → Xem profile"
            )),
            message_object, thread_id, thread_type,
        )
        return

    # ── PROFILE ───────────────────────────────────────────────────────────────
    if cmd in ("tiktokinfo", "in4tiktok"):
        if not arg:
            bot.replyMessage(
                Message(text="🎵 Dùng: *tiktokinfo <username>\nVí dụ: *tiktokinfo @nguyenhung07"),
                message_object, thread_id, thread_type,
            )
            return

        username = arg.lstrip("@")
        bot.replyMessage(
            Message(text=f"🔍 Đang lấy thông tin profile: @{username}..."),
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

    # ── SEARCH ────────────────────────────────────────────────────────────────
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

    username = _get_username(bot, author_id)

    bot.replyMessage(
        Message(text=f"🔍 Đang tìm TikTok {content_type}: **{keywords}**..."),
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
    items = items[:total]

    if HAS_MUSIC_STATES:
        user_states[author_id] = {
            'items': items,
            'time_of_search': time.time(),
            'query_msg_id': message_object.msgId if message_object else None,
            'query_cli_msg_id': message_object.cliMsgId if message_object else None,
            'source': 'tiktok'
        }

    image_path = create_tiktok_search_image(items, keywords, content_type)

    if image_path and os.path.exists(image_path):
        try:
            with Image.open(image_path) as img:
                w, h = img.size
            offset = zalo_offset(f"🎵 TikTok Search: {keywords} ({total} kết quả)", "TikTok Search")
            sent_msg = bot.sendLocalImage(
                image_path,
                message=Message(text=f"🎵 TikTok Search: {keywords} ({total} kết quả)"),
                thread_id=thread_id,
                thread_type=thread_type,
                width=w,
                height=h,
            )
            if sent_msg and HAS_MUSIC_STATES and author_id in user_states:
                user_states[author_id]['search_msg'] = sent_msg
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
        Message(text=f"💡 Nhập *ttdl <số> để chọn video (1-{total})"),
        message_object, thread_id, thread_type,
    )
