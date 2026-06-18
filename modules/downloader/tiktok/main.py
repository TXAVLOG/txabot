# -*- coding: UTF-8 -*-
"""
Module: tiktok.py
Lệnh: tt, tiktok, ttdl, tksearch, tiktoksearch, downtik, tiktokinfo, in4tiktok
- tt <từ khóa>              → Tìm kiếm video/ảnh TikTok
- tt img <từ khóa>          → Tìm ảnh TikTok
- ttdl <link>               → Tải video TikTok không watermark
- tiktokinfo <username>     → Xem thông tin profile TikTok
"""

from zlapi import ThreadType
import sys
import os
import json
import glob
import random
import tempfile
import requests
import time
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
        "ttmp3": "Tải nhạc/voice từ TikTok",
        "ttaudio": "Tải âm thanh từ TikTok",
        "ttmusic": "Tải nhạc nền từ TikTok"
    },
    "author": "TXA",
    "command": ["tt", "tiktok", "ttdl", "downtik", "tksearch", "tiktoksearch", "tiktokinfo", "in4tiktok", "ttmp3", "ttaudio", "ttmusic"],
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


def _is_emoji(ch):
    import emoji as emoji_mod
    return ch in emoji_mod.EMOJI_DATA


def draw_text_mixed(draw, text, pos, font, emoji_font, fill):
    x, y = pos
    for ch in text:
        if ord(ch) in (0xFE0F, 0xFE0E):
            continue
        f = emoji_font if _is_emoji(ch) else font
        oy = y - f.size // 6 if _is_emoji(ch) else y
        draw.text((x, oy), ch, font=f, fill=fill)
        try:
            w = draw.textbbox((0, 0), ch, font=f)[2] - draw.textbbox((0, 0), ch, font=f)[0]
            if w == 0 and ch == " ":
                w = f.size // 3
        except Exception:
            w = f.size // 2
        x += w + (1 if _is_emoji(ch) else 0)


# ─── TIKTOK SEARCH IMAGE ─────────────────────────────────────────────────────

def _fetch_cover_image(item):
    # 1. If it has images list, use the first image from tiktokcdn
    images = item.get("images")
    if isinstance(images, list) and images:
        for img_url in images:
            if img_url and img_url.startswith("http"):
                try:
                    resp = requests.get(img_url, timeout=8)
                    resp.raise_for_status()
                    return Image.open(BytesIO(resp.content))
                except Exception as e:
                    print(f"Error loading image post cover: {e}")
    
    # 2. If it is a video, extract the thumbnail using ffmpeg from the play URL
    play_url = item.get("playUrl") or item.get("play") or item.get("hdplay") or item.get("video_url_no_watermark")
    if play_url and play_url.startswith("http"):
        try:
            import subprocess
            temp_dir = tempfile.gettempdir()
            temp_out = os.path.join(temp_dir, f"thumb_{random.randint(100000, 999999)}.jpg")
            cmd = ['ffmpeg', '-y', '-ss', '00:00:00', '-i', play_url, '-vframes', '1', '-f', 'image2', temp_out]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            if os.path.exists(temp_out) and os.path.getsize(temp_out) > 0:
                img = Image.open(temp_out)
                img_data = BytesIO()
                img.save(img_data, format="PNG")
                img.close()
                try:
                    os.remove(temp_out)
                except:
                    pass
                img_data.seek(0)
                return Image.open(img_data)
        except Exception as e:
            print(f"ffmpeg extract failed: {e}")
            
    # 3. Fallback: try requesting the cover directly (which might fail with 403)
    cover_url = item.get("coverUrl") or item.get("cover") or ""
    if cover_url and cover_url.startswith("http"):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(cover_url, headers=headers, timeout=8)
            resp.raise_for_status()
            return Image.open(BytesIO(resp.content))
        except Exception as e:
            print(f"Error loading direct cover: {e}")
            
    return None


def _get_avatar_image(item):
    author_obj = item.get("author")
    avatar_url = ""
    if isinstance(author_obj, dict):
        avatar_url = author_obj.get("avatarUrl") or author_obj.get("avatar") or ""
    else:
        avatar_url = item.get("avatarUrl") or item.get("avatar") or ""
        
    if avatar_url and avatar_url.startswith("http") and "tikwm.com" not in avatar_url:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            resp = requests.get(avatar_url, headers=headers, timeout=5)
            resp.raise_for_status()
            return Image.open(BytesIO(resp.content))
        except Exception:
            pass
            
    # Draw a premium default initial avatar
    size = 120
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size, size], fill=(40, 45, 55, 255), outline=(255, 255, 255, 30), width=2)
    draw.ellipse([size//3, size//5, size - size//3, size//2], fill=(170, 180, 195, 255))
    draw.chord([size//5, size//2 + 5, size - size//5, size - size//10], start=180, end=360, fill=(170, 180, 195, 255))
    return img


def create_tiktok_search_image(items, keywords, content_type="video"):
    try:
        width, height = 1200, 720
        # Background
        img = Image.new("RGBA", (width, height), (17, 20, 23, 255))
        draw = ImageDraw.Draw(img)
        
        # Load background from background/ if exists
        bg_path = None
        if os.path.exists(BACKGROUND_PATH):
            imgs = [os.path.join(BACKGROUND_PATH, f) for f in os.listdir(BACKGROUND_PATH)
                    if f.lower().endswith((".png", ".jpg", ".jpeg"))]
            if imgs:
                bg_path = random.choice(imgs)
                
        if bg_path:
            try:
                bg = Image.open(bg_path).convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)
                bg = bg.filter(ImageFilter.GaussianBlur(radius=25))
                img = bg
                draw = ImageDraw.Draw(img)
            except Exception:
                pass
                
        # Draw grid stripes
        for x in range(0, width, 120):
            draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 5), width=1)
        for y in range(0, height, 120):
            draw.line([(0, y), (width, y)], fill=(255, 255, 255, 5), width=1)

        # Glassmorphism container card
        draw.rounded_rectangle([30, 30, width - 30, height - 30], radius=32, fill=(18, 22, 28, 180), outline=(255, 255, 255, 20), width=1)
        
        # Fonts
        base_dir = os.path.dirname(os.path.abspath(__file__))
        font_dir = os.path.abspath(os.path.join(base_dir, "../../../font"))
        
        sf_pro_bold = os.path.join(font_dir, "SF-Pro.ttf")
        font_path = sf_pro_bold if os.path.exists(sf_pro_bold) else os.path.join(font_dir, "arial unicode ms.otf")
        emoji_font_path = os.path.join(font_dir, "NotoEmoji-Bold.ttf")
        
        font_large = ImageFont.truetype(font_path, 32)
        font_bold = ImageFont.truetype(font_path, 20)
        font_medium = ImageFont.truetype(font_path, 16)
        font_small = ImageFont.truetype(font_path, 14)
        
        f_emoji_large = ImageFont.truetype(emoji_font_path, 32) if os.path.exists(emoji_font_path) else font_large
        f_emoji_bold = ImageFont.truetype(emoji_font_path, 20) if os.path.exists(emoji_font_path) else font_bold
        f_emoji_med = ImageFont.truetype(emoji_font_path, 16) if os.path.exists(emoji_font_path) else font_medium
        f_emoji_sm = ImageFont.truetype(emoji_font_path, 14) if os.path.exists(emoji_font_path) else font_small

        # Draw Left Panel (Item 1 Cover)
        cover_size = 340
        cx0, cy0 = 60, 60
        cx1, cy1 = cx0 + cover_size, cy0 + cover_size
        
        # Get first item details
        first_item = items[0] if items else {}
        first_title = (first_item.get("title") or first_item.get("desc") or "Video TikTok").strip()
        first_author_obj = first_item.get("author")
        if isinstance(first_author_obj, dict):
            first_author = first_author_obj.get("unique_id") or first_author_obj.get("nickname") or "User"
        else:
            first_author = first_item.get("nickname") or first_item.get("unique_id") or "User"
            
        first_stats_obj = first_item.get("stats")
        if isinstance(first_stats_obj, dict):
            first_likes = _format_number(first_stats_obj.get("digg_count") or first_stats_obj.get("diggCount") or 0)
            first_plays = _format_number(first_stats_obj.get("play_count") or first_stats_obj.get("playCount") or 0)
        else:
            first_likes = _format_number(first_item.get("digg_count") or first_item.get("diggCount") or 0)
            first_plays = _format_number(first_item.get("play_count") or first_item.get("play_count") or 0)
            
        first_stats = f"❤️ {first_likes}  •  🎬 {first_plays} lượt xem"
        
        cover_img = _fetch_cover_image(first_item)
        has_first_cover = False
        if cover_img:
            try:
                cover_img = cover_img.convert("RGBA")
                cover_img = ImageOps.fit(cover_img, (cover_size, cover_size), centering=(0.5, 0.5))
                mask = Image.new("L", (cover_size, cover_size), 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.rounded_rectangle([0, 0, cover_size, cover_size], radius=24, fill=255)
                cover_img.putalpha(mask)
                img.paste(cover_img, (cx0, cy0), cover_img)
                has_first_cover = True
            except Exception as e:
                print(f"Error loading first cover: {e}")
                
        if not has_first_cover:
            # Draw placeholder cover
            draw.rounded_rectangle([cx0, cy0, cx1, cy1], radius=24, fill=(30, 35, 45, 255), outline=(255, 255, 255, 10), width=1)
            
        # Draw texts under cover
        if len(first_title) > 28:
            first_title = first_title[:25] + "..."
        draw_text_mixed(draw, first_title, (cx0 + 10, cy1 + 25), font_large, f_emoji_large, (255, 255, 255, 255))
        draw_text_mixed(draw, f"@{first_author}", (cx0 + 10, cy1 + 75), font_medium, f_emoji_med, (170, 180, 195, 255))
        draw_text_mixed(draw, first_stats, (cx0 + 10, cy1 + 110), font_small, f_emoji_sm, (0, 240, 255, 255))

        # Right Panel Layout
        col1_x = 440
        col2_x = 810
        item_w = 330
        item_h = 102
        y_start = 60
        y_space = 14
        
        # Parallel extraction of thumbnails to speed up
        import concurrent.futures
        def fetch_thumb_wrapped(item):
            return _fetch_cover_image(item)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            thumbs_imgs = list(executor.map(fetch_thumb_wrapped, items[1:]))

        for idx in range(1, len(items)):
            col = 0 if idx <= 5 else 1
            row = (idx - 1) % 5
            
            x = col1_x if col == 0 else col2_x
            y = y_start + row * (item_h + y_space)
            
            # Card background
            draw.rounded_rectangle([x, y, x + item_w, y + item_h], radius=16, fill=(25, 28, 32, 160), outline=(255, 255, 255, 15), width=1)
            
            # Thumbnail size
            thumb_size = 76
            tx = x + 12
            ty = y + 13
            
            item = items[idx]
            title = (item.get("title") or item.get("desc") or f"Video TikTok {idx + 1}").strip()
            
            item_author_obj = item.get("author")
            if isinstance(item_author_obj, dict):
                author = item_author_obj.get("unique_id") or item_author_obj.get("nickname") or "User"
            else:
                author = item.get("nickname") or item.get("unique_id") or "User"
                
            item_stats_obj = item.get("stats")
            if isinstance(item_stats_obj, dict):
                likes_val = _format_number(item_stats_obj.get("digg_count") or item_stats_obj.get("diggCount") or 0)
            else:
                likes_val = _format_number(item.get("digg_count") or item.get("diggCount") or 0)
                
            thumb_img = thumbs_imgs[idx - 1]
            has_thumb = False
            if thumb_img:
                try:
                    thumb_img = thumb_img.convert("RGBA")
                    thumb_img = ImageOps.fit(thumb_img, (thumb_size, thumb_size), centering=(0.5, 0.5))
                    mask = Image.new("L", (thumb_size, thumb_size), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.rounded_rectangle([0, 0, thumb_size, thumb_size], radius=12, fill=255)
                    thumb_img.putalpha(mask)
                    img.paste(thumb_img, (tx, ty), thumb_img)
                    has_thumb = True
                except Exception as e:
                    print(f"Error parsing thumbnail {idx}: {e}")
                    
            if not has_thumb:
                draw.rounded_rectangle([tx, ty, tx + thumb_size, ty + thumb_size], radius=12, fill=(40, 45, 55, 255))
                
            if len(title) > 20:
                title = title[:18] + "..."
                
            # Text layout inside the card
            draw_text_mixed(draw, title, (x + 104, y + 20), font_bold, f_emoji_bold, (255, 255, 255, 255))
            draw_text_mixed(draw, f"@{author} | {likes_val} likes", (x + 104, y + 54), font_small, f_emoji_sm, (170, 180, 195, 255))
            
            # Index Number
            num_str = str(idx + 1)
            draw.text((x + item_w - 36, y + 36), num_str, font=font_bold, fill=(255, 255, 255, 60))
            
        file_path = os.path.join(CACHE_PATH, f"tt_search_{hash(keywords) & 0xFFFFFF:06x}.png")
        img.convert("RGB").save(file_path, format="JPEG", quality=95, optimize=True)
        return file_path
    except Exception as e:
        print(f"[TikTok] Error creating search image: {e}")
        return None


def create_tiktok_download_image(data):
    try:
        width, height = 1200, 420
        img = Image.new("RGBA", (width, height), (17, 20, 23, 255))
        draw = ImageDraw.Draw(img)
        
        # Load background and blur
        cover_img = _fetch_cover_image(data)
        if cover_img:
            try:
                bg = cover_img.convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)
                bg = bg.filter(ImageFilter.GaussianBlur(radius=25))
                img = bg
                draw = ImageDraw.Draw(img)
            except Exception as e:
                print(f"Error generating background: {e}")
                
        # Draw glass card overlay
        draw.rounded_rectangle([40, 40, width - 40, height - 40], radius=24, fill=(18, 22, 28, 180), outline=(255, 255, 255, 20), width=1)
        
        # Fonts
        base_dir = os.path.dirname(os.path.abspath(__file__))
        font_dir = os.path.abspath(os.path.join(base_dir, "../../../font"))
        sf_pro_bold = os.path.join(font_dir, "SF-Pro.ttf")
        font_path = sf_pro_bold if os.path.exists(sf_pro_bold) else os.path.join(font_dir, "arial unicode ms.otf")
        emoji_font_path = os.path.join(font_dir, "NotoEmoji-Bold.ttf")
        
        f_large = ImageFont.truetype(font_path, 36)
        f_medium = ImageFont.truetype(font_path, 22)
        f_small = ImageFont.truetype(font_path, 16)
        f_emoji = ImageFont.truetype(emoji_font_path, 36) if os.path.exists(emoji_font_path) else f_large
        f_emoji_sm = ImageFont.truetype(emoji_font_path, 22) if os.path.exists(emoji_font_path) else f_medium
        
        # Left: Cover photo
        cover_size = 300
        cx0, cy0 = 60, 60
        cx1, cy1 = cx0 + cover_size, cy0 + cover_size
        
        has_cover = False
        if cover_img:
            try:
                cover = cover_img.convert("RGBA")
                cover = ImageOps.fit(cover, (cover_size, cover_size), centering=(0.5, 0.5))
                mask = Image.new("L", (cover_size, cover_size), 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.rounded_rectangle([0, 0, cover_size, cover_size], radius=18, fill=255)
                cover.putalpha(mask)
                img.paste(cover, (cx0, cy0), cover)
                has_cover = True
            except Exception as e:
                print(f"Error loading download cover: {e}")
                
        if not has_cover:
            draw.rounded_rectangle([cx0, cy0, cx1, cy1], radius=18, fill=(30, 35, 45, 255), outline=(255, 255, 255, 10), width=1)
            
        # Right: Texts
        tx = cx1 + 40
        ty = 80
        
        title = (data.get("title") or data.get("desc") or "Video TikTok").strip()
        author_data = data.get("author")
        if isinstance(author_data, dict):
            author = author_data.get("unique_id") or author_data.get("nickname") or "User"
        else:
            author = data.get("author") or data.get("nickname") or data.get("unique_id") or "User"
            
        likes = _format_number(data.get("digg_count") or data.get("diggCount") or data.get("like_count") or 0)
        plays = _format_number(data.get("play_count") or data.get("playCount") or 0)
        dur = data.get("duration") or 0
        dur_s = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "N/A"
        
        # Truncate title
        if len(title) > 40:
            title = title[:37] + "..."
            
        draw_text_mixed(draw, f"🎵 {title}", (tx, ty), f_large, f_emoji, (255, 255, 255, 255))
        draw_text_mixed(draw, f"👤 Tác giả: @{author}", (tx, ty + 70), f_medium, f_emoji_sm, (170, 180, 195, 255))
        draw_text_mixed(draw, "🎯 Nền tảng: TikTok", (tx, ty + 120), f_medium, f_emoji_sm, (170, 180, 195, 255))
        
        stats_str = f"⏱️ {dur_s}   ❤️ {likes}   🎬 {plays} lượt xem"
        draw_text_mixed(draw, stats_str, (tx, ty + 170), f_medium, f_emoji_sm, (0, 240, 255, 255))
        
        file_path = os.path.join(CACHE_PATH, f"tt_dl_{int(time.time())}.png")
        img.convert("RGB").save(file_path, format="JPEG", quality=95, optimize=True)
        return file_path
    except Exception as e:
        print(f"[TikTok] Error creating download image: {e}")
        return None


# ─── TEXT CARDS (fallback) ───────────────────────────────────────────────────

def _build_download_card(data: dict) -> str:
    title = (data.get("title") or data.get("desc") or "").strip()
    title = title[:100] + "…" if len(title) > 100 else title
    author_data = data.get("author")
    if isinstance(author_data, dict):
        author = author_data.get("unique_id") or author_data.get("nickname") or "User"
    else:
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

def _search_tiktok(keywords: str, content_type: str = "video", count: int = 11, cursor: int = 0):
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

def _convert_mp3_to_m4a(mp3_path):
    m4a_path = mp3_path.rsplit('.', 1)[0] + '.m4a'
    try:
        if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) < 1024:
            return mp3_path
        cmd = ['ffmpeg', '-y', '-threads', '0', '-i', mp3_path, '-vn', '-sn', '-dn', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', m4a_path]
        import subprocess
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(m4a_path) and os.path.getsize(m4a_path) > 0:
            return m4a_path
    except Exception as e:
        print(f"Error converting to m4a: {e}")
    return mp3_path


def send_tiktok_media(bot, video_url, is_voice_only, thread_id, thread_type, message_object):
    from zlapi.models import Message
    try:
        print(f"\n[TikTok] >>> Bắt đầu xử lý tải xuống: {video_url}")
        print(f"[TikTok] Chế độ tải: {'Chỉ lấy nhạc (Voice Only)' if is_voice_only else 'Tải video đầy đủ'}")
        
        status_msg = "⏳ Đang tải nhạc/voice từ TikTok…" if is_voice_only else "⏳ Đang tải video TikTok…"
        loading_msg = bot.replyMessage(Message(text=status_msg), message_object, thread_id, thread_type)
        
        print(f"[TikTok] Đang yêu cầu API lấy link tải...")
        try:
            data = _download_tiktok(video_url)
            print(f"[TikTok] Lấy siêu dữ liệu video thành công.")
        except Exception as e:
            print(f"[TikTok] Lỗi gọi API: {e}")
            bot.replyMessage(Message(text=f"❌ Lỗi tải TikTok: {e}"), message_object, thread_id, thread_type)
            return

        inner = data.get("data") if isinstance(data, dict) else data
        if not inner:
            print(f"[TikTok] Thất bại: API không trả về dữ liệu 'data'.")
            bot.replyMessage(Message(text="❌ Không thể lấy dữ liệu từ link TikTok này."), message_object, thread_id, thread_type)
            return
            
        title = (inner.get("title") or inner.get("desc") or "").strip()
        author_data = inner.get("author")
        if isinstance(author_data, dict):
            author = author_data.get("unique_id") or author_data.get("nickname") or "User"
        else:
            author = inner.get("author") or inner.get("nickname") or inner.get("unique_id") or "?"
            
        if is_voice_only:
            music_data = inner.get("music")
            audio_url = None
            if isinstance(music_data, dict):
                audio_url = music_data.get("play") or music_data.get("url") or music_data.get("playUrl")
            if not audio_url:
                audio_url = inner.get("musicUrl") or inner.get("music_url")
                
            if not audio_url:
                print(f"[TikTok] Thất bại: Không tìm thấy link âm thanh (audio_url).")
                bot.replyMessage(Message(text="❌ Không tìm thấy âm thanh của video này."), message_object, thread_id, thread_type)
                return
                
            try:
                print(f"[TikTok] Đang kết nối tải file âm thanh: {audio_url}")
                r_audio = requests.get(audio_url, stream=True, timeout=20)
                r_audio.raise_for_status()
                total_size = int(r_audio.headers.get('content-length', 0))
                
                temp_dir = tempfile.gettempdir()
                temp_file = os.path.join(temp_dir, f"tiktok_voice_{int(time.time())}.mp3")
                
                downloaded = 0
                with open(temp_file, "wb") as f:
                    for chunk in r_audio.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                print(f"\r[TikTok] Tiến trình tải nhạc: {percent:.1f}% ({downloaded}/{total_size} bytes)", end="", flush=True)
                            else:
                                print(f"\r[TikTok] Tiến trình tải nhạc: {downloaded} bytes", end="", flush=True)
                print("\n[TikTok] Đã tải xong file âm thanh gốc.")
                    
                from core.bot_sys import should_convert_to_m4a, upload_file
                if should_convert_to_m4a(bot, author_id=None, thread_type=thread_type):
                    print(f"[TikTok] Đang chuyển đổi định dạng MP3 -> M4A...")
                    audio_file = _convert_mp3_to_m4a(temp_file)
                else:
                    audio_file = temp_file
                    
                print(f"[TikTok] Đang tải file âm thanh lên server trung gian...")
                upload_url = upload_file(audio_file, "audio/mp4" if audio_file.endswith(".m4a") else "audio/mpeg")
                
                try:
                    os.remove(temp_file)
                    if audio_file != temp_file:
                        os.remove(audio_file)
                except:
                    pass
                    
                if not upload_url:
                    print(f"[TikTok] Thất bại: Lỗi tải file lên server trung gian.")
                    bot.replyMessage(Message(text="❌ Lỗi tải âm thanh lên server trung gian."), message_object, thread_id, thread_type)
                    return
                    
                if loading_msg:
                    try:
                        if thread_type == ThreadType.GROUP:
                            bot.deleteGroupMsg(loading_msg.msgId, bot.uid, loading_msg.cliMsgId, thread_id)
                        else:
                            bot.undoMessage(loading_msg.msgId, loading_msg.cliMsgId, thread_id, thread_type)
                    except:
                        pass
                        
                print(f"[TikTok] Đang gửi Voice Message qua Zalo...")
                bot.sendRemoteVoice(voiceUrl=upload_url, thread_id=thread_id, thread_type=thread_type)
                bot.replyMessage(Message(text=f"🔊 Tải nhạc từ @{author} thành công!\n📝 {title}"), message_object, thread_id, thread_type)
                print(f"[TikTok] Gửi voice hoàn tất thành công!")
            except Exception as e:
                print(f"[TikTok] Lỗi trong quá trình tải/gửi voice: {e}")
                bot.replyMessage(Message(text=f"❌ Lỗi tải âm thanh: {e}"), message_object, thread_id, thread_type)
        else:
            video_dl = (
                inner.get("video_url_no_watermark")
                or inner.get("video")
                or inner.get("url")
                or inner.get("play")
                or inner.get("hdplay")
            )
            
            if not video_dl:
                print(f"[TikTok] Thất bại: Không lấy được link tải video không watermark.")
                bot.replyMessage(Message(text="❌ Không lấy được link tải video không watermark."), message_object, thread_id, thread_type)
                return
                
            print(f"[TikTok] Đang vẽ Card tải xuống...")
            img_path = create_tiktok_download_image(inner)
            if img_path and os.path.exists(img_path):
                try:
                    with Image.open(img_path) as img_ref:
                        w, h = img_ref.size
                    print(f"[TikTok] Đang gửi Card hình ảnh...")
                    bot.sendLocalImage(
                        img_path,
                        message=None,
                        thread_id=thread_id,
                        thread_type=thread_type,
                        width=w,
                        height=h,
                    )
                except Exception as err:
                    print(f"[TikTok] Lỗi gửi Card hình ảnh: {err}")
                    card = _build_download_card(inner)
                    bot.replyMessage(Message(text=card), message_object, thread_id, thread_type)
                finally:
                    try:
                        os.remove(img_path)
                    except:
                        pass
            else:
                print(f"[TikTok] Vẽ Card thất bại, fallback sang Card text.")
                card = _build_download_card(inner)
                bot.replyMessage(Message(text=card), message_object, thread_id, thread_type)
            
            if loading_msg:
                try:
                    if thread_type == ThreadType.GROUP:
                        bot.deleteGroupMsg(loading_msg.msgId, bot.uid, loading_msg.cliMsgId, thread_id)
                    else:
                        bot.undoMessage(loading_msg.msgId, loading_msg.cliMsgId, thread_id, thread_type)
                except:
                    pass
                    
            try:
                print(f"[TikTok] Đang tải video về local: {video_dl}")
                dl_msg = bot.replyMessage(Message(text="⏳ Bot đang tải video về máy chủ..."), message_object, thread_id, thread_type)
                
                r_video = requests.get(video_dl, stream=True, timeout=60)
                r_video.raise_for_status()
                total_size = int(r_video.headers.get('content-length', 0))
                
                temp_dir = tempfile.gettempdir()
                temp_video = os.path.join(temp_dir, f"tiktok_video_{int(time.time())}.mp4")
                
                downloaded = 0
                with open(temp_video, "wb") as f:
                    for chunk in r_video.iter_content(chunk_size=16384):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                print(f"\r[TikTok] Tiến trình tải video: {percent:.1f}% ({downloaded}/{total_size} bytes)", end="", flush=True)
                            else:
                                print(f"\r[TikTok] Tiến trình tải video: {downloaded} bytes", end="", flush=True)
                print("\n[TikTok] Đã tải xong video về local.")
                
                if dl_msg:
                    try:
                        if thread_type == ThreadType.GROUP:
                            bot.deleteGroupMsg(dl_msg.msgId, bot.uid, dl_msg.cliMsgId, thread_id)
                        else:
                            bot.undoMessage(dl_msg.msgId, dl_msg.cliMsgId, thread_id, thread_type)
                    except:
                        pass
                
                print(f"[TikTok] Đang gửi video local qua Zalo...")
                bot.replyMessage(Message(text="✅ Đã tải xong! Đang gửi video qua Zalo..."), message_object, thread_id, thread_type)
                
                caption = f"🎵 {title}\n👤 @{author}"
                bot.sendLocalVideo(
                    filePath=temp_video,
                    message=Message(text=caption),
                    thread_id=thread_id,
                    thread_type=thread_type,
                )
                print(f"[TikTok] Gửi video local hoàn tất!")
                
                try:
                    os.remove(temp_video)
                except:
                    pass
            except Exception as e:
                print(f"[TikTok] Lỗi tải/gửi video local: {e}")
                bot.replyMessage(
                    Message(text=f"⚠️ Không gửi được video trực tiếp.\n🔗 Link tải: {video_dl}"),
                    message_object, thread_id, thread_type,
                )
    except Exception as e:
        print(f"[TikTok] Lỗi ngoài dự kiến: {e}")
        bot.replyMessage(Message(text=f"❌ Đã xảy ra lỗi: {e}"), message_object, thread_id, thread_type)


# ─── COMMAND HANDLER ──────────────────────────────────────────────────────────

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    from zlapi.models import Message, ThreadType
    from core.bot_sys import USER_MUSIC_STATES
    user_states = USER_MUSIC_STATES

    prefix = getattr(bot, "prefix", ".")
    parts = message_text.strip().split(None, 1)
    cmd = parts[0].lstrip(prefix).lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    if not _read_api_key():
        bot.replyMessage(
            Message(text="⚠️ Chưa cấu hình kairobot_api_key trong txa.json!"),
            message_object, thread_id, thread_type,
        )
        return

    # ── SELECTION HANDLING (ZingMP3-like) ──────────────────────────────────
    is_direct_selection = cmd.isdigit() and author_id in user_states and user_states[author_id].get('source') == 'tiktok'
    is_command_selection = cmd in ("tt", "tiktok", "ttmp3", "ttaudio", "ttmusic") and arg.isdigit() and author_id in user_states and user_states[author_id].get('source') == 'tiktok'

    if is_direct_selection or is_command_selection:
        selected_number = cmd if is_direct_selection else arg
        state = user_states[author_id]
        
        if time.time() - state.get('time_of_search', 0) > 180:
            bot.replyMessage(Message(text="⚠️ Hết thời gian lựa chọn kết quả tìm kiếm TikTok."), message_object, thread_id, thread_type)
            return

        items = state.get("items", [])
        idx = int(selected_number) - 1
        if idx < 0 or idx >= len(items):
            bot.replyMessage(Message(text=f"❌ Số thứ tự không hợp lệ: {selected_number}"), message_object, thread_id, thread_type)
            return

        search_msg = state.get('search_msg')
        if search_msg and hasattr(search_msg, 'msgId') and hasattr(search_msg, 'cliMsgId'):
            try:
                bot.undoMessage(search_msg.msgId, search_msg.cliMsgId, thread_id, thread_type)
            except Exception as e:
                print(f"[TikTok] Recall search image error: {e}")

        query_msg_id = state.get('query_msg_id')
        query_cli_msg_id = state.get('query_cli_msg_id')
        if thread_type == ThreadType.GROUP and query_msg_id and query_cli_msg_id:
            try:
                bot.deleteGroupMsg(query_msg_id, author_id, query_cli_msg_id, thread_id)
            except Exception as e:
                print(f"[TikTok] Delete search query msg error: {e}")

        if thread_type == ThreadType.GROUP and message_object and hasattr(message_object, 'msgId') and hasattr(message_object, 'cliMsgId'):
            try:
                bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
            except Exception as e:
                print(f"[TikTok] Delete selection msg error: {e}")

        selected_item = items[idx]
        if author_id in user_states:
            del user_states[author_id]

        video_id = selected_item.get("id")
        author_obj = selected_item.get("author")
        if isinstance(author_obj, dict):
            unique_id = author_obj.get("unique_id") or "user"
        else:
            unique_id = selected_item.get("unique_id") or "user"
            
        video_url = f"https://www.tiktok.com/@{unique_id}/video/{video_id}"
        is_voice_only = state.get("is_voice_only", False)
        
        def run_selection_download():
            send_tiktok_media(bot, video_url, is_voice_only, thread_id, thread_type, message_object)
            
        import threading
        threading.Thread(target=run_selection_download, daemon=True).start()
        return

    # ── HELP ──────────────────────────────────────────────────────────────
    if not arg and cmd in ("tiktok", "tt", "tksearch", "tiktoksearch", "ttmp3", "ttaudio", "ttmusic"):
        bot.replyMessage(
            Message(text=(
                "🎵 TikTok Search & Download\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📌 Lệnh:\n"
                f"  {prefix}tt <từ khóa>           → Tìm kiếm & Chọn tải video\n"
                f"  {prefix}ttmp3 <từ khóa>        → Tìm kiếm & Chọn tải nhạc/voice\n"
                f"  {prefix}ttdl <link>            → Tải video no-WM bằng link\n"
                f"  {prefix}ttmp3 <link>           → Tải âm thanh từ link TikTok\n"
                f"  {prefix}tiktokinfo <username>  → Xem profile"
            )),
            message_object, thread_id, thread_type,
        )
        return

    # ── PROFILE ───────────────────────────────────────────────────────────
    if cmd in ("tiktokinfo", "in4tiktok"):
        if not arg:
            bot.replyMessage(
                Message(text=f"🎵 Dùng: {prefix}tiktokinfo <username>\nVí dụ: {prefix}tiktokinfo @nguyenhung07"),
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

    # ── DOWNLOAD DIRECT LINK (Video or Voice) ─────────────────────────────
    if cmd in ("ttdl", "downtik", "ttmp3", "ttaudio", "ttmusic") and arg.startswith("http"):
        is_voice_only = cmd in ("ttmp3", "ttaudio", "ttmusic")
        
        def run_direct_download():
            send_tiktok_media(bot, arg, is_voice_only, thread_id, thread_type, message_object)
            
        import threading
        threading.Thread(target=run_direct_download, daemon=True).start()
        return

    # ── SEARCH & CHOOSE (ZingMP3-style) ───────────────────────────────────
    is_voice_search = cmd in ("ttmp3", "ttaudio", "ttmusic")
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

    search_type_str = "nhạc/voice" if is_voice_search else f"TikTok {content_type}"
    bot.replyMessage(
        Message(text=f"🔍 Đang tìm {search_type_str}: {keywords}…"),
        message_object, thread_id, thread_type,
    )

    try:
        resp = _search_tiktok(keywords, content_type, count=11)
    except Exception as e:
        bot.replyMessage(
            Message(text=f"❌ Lỗi tìm kiếm: {e}"),
            message_object, thread_id, thread_type,
        )
        return

    items = _normalize_items(resp)

    if not items:
        bot.replyMessage(
            Message(text=f"😔 Không tìm thấy kết quả cho: {keywords}"),
            message_object, thread_id, thread_type,
        )
        return

    total = min(len(items), 11)
    
    # Save selection state
    user_states[author_id] = {
        "source": "tiktok",
        "items": items[:total],
        "time_of_search": time.time(),
        "query_msg_id": getattr(message_object, "msgId", None),
        "query_cli_msg_id": getattr(message_object, "cliMsgId", None),
        "search_msg": None,
        "is_voice_only": is_voice_search
    }

    image_path = create_tiktok_search_image(items[:total], keywords, content_type)

    if image_path and os.path.exists(image_path):
        try:
            with Image.open(image_path) as img:
                w, h = img.size
            
            search_title = f"🎵 TikTok Music Search: {keywords}" if is_voice_search else f"🎬 TikTok Video Search: {keywords}"
            sent_msg = bot.sendLocalImage(
                image_path,
                message=Message(text=f"{search_title}\n👉 Chọn bằng cách gõ từ số 1 đến {total}"),
                thread_id=thread_id,
                thread_type=thread_type,
                width=w,
                height=h,
            )
            
            # Save sent image message object so we can recall it upon selection
            if sent_msg and author_id in user_states:
                user_states[author_id]["search_msg"] = sent_msg
                
        except Exception as err:
            print("Error sending search image:", err)
            bot.replyMessage(
                Message(text=f"🎵 Tìm thấy {total} kết quả TikTok. Gửi số từ 1 đến {total} để tải."),
                message_object, thread_id, thread_type,
            )
        finally:
            try:
                os.remove(image_path)
            except Exception:
                pass
    else:
        bot.replyMessage(
            Message(text=f"🎵 Tìm thấy {total} kết quả TikTok. Gửi số từ 1 đến {total} để tải."),
            message_object, thread_id, thread_type,
        )
