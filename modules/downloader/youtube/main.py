# -*- coding: UTF-8 -*-
import os
import sys
import json
import time
import threading
import re
import requests
from io import BytesIO

sys.dont_write_bytecode = True

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from zlapi import ThreadType
from zlapi.models import Message

from modules.utils.ytdlp_downloader import (
    detect_platform, get_platform_label, get_video_info,
    download_video, download_audio, convert_to_m4a,
    check_storage, upload_file, _fmt_size
)

CACHE_PATH = "modules/cache/"
BACKGROUND_PATH = "background/"
os.makedirs(CACHE_PATH, exist_ok=True)

txa = {
    "name": "YouTube Download",
    "desc": {
        "yt": "Tải video/audio từ YouTube",
    },
    "author": "TXA",
    "command": ["yt"],
    "help": {
        "yt": {
            "usage": [
                "{prefix}yt",
                "{prefix}yt <link>",
                "{prefix}yt <link> -a"
            ],
            "examples": [
                "{prefix}yt",
                "{prefix}yt https://youtube.com/watch?v=xxxxx",
                "{prefix}yt https://youtu.be/xxxxx -a",
                "{prefix}yt https://youtube.com/shorts/xxxxx"
            ],
            "notes": [
                "Nếu chi go {prefix}yt khong co link, bot se hien thi huong dan.",
                "Khi them -a, bot se tai audio va gui card thong tin kem file.",
                "Ho tro: youtube shorts, youtube music."
            ]
        }
    }
}

FONT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../font"))
FONT_PATH = os.path.join(FONT_DIR, "SF-Pro.ttf")
FONT_PATH_FALLBACK = os.path.join(FONT_DIR, "arial unicode ms.otf")
EMOJI_FONT_PATH = os.path.join(FONT_DIR, "NotoEmoji-Bold.ttf")

def _get_font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_PATH if os.path.exists(FONT_PATH) else FONT_PATH_FALLBACK, size)
    except:
        return ImageFont.load_default()

def _get_emoji_font(size):
    try:
        return ImageFont.truetype(EMOJI_FONT_PATH, size) if os.path.exists(EMOJI_FONT_PATH) else _get_font(size)
    except:
        return _get_font(size)

def _draw_mixed_text(draw, text, pos, font, emoji_font, fill):
    x, y = pos
    for ch in text:
        if ord(ch) in (0xFE0F, 0xFE0E):
            continue
        f = emoji_font if ch in "❤️🎵🎬🎯👤⏱️📝🔊🎶🎼🎧🔥✅❌" else font
        oy = y - f.size // 6 if f == emoji_font else y
        draw.text((x, oy), ch, font=f, fill=fill)
        try:
            w = draw.textbbox((0, 0), ch, font=f)[2] - draw.textbbox((0, 0), ch, font=f)[0]
            if w == 0 and ch == " ":
                w = f.size // 3
        except:
            w = f.size // 2
        x += w

def _fetch_thumb(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGBA")
    except:
        return None

def _truncate(draw, text, max_w, font):
    if not text:
        return ""
    try:
        w = draw.textbbox((0, 0), text, font=font)[2] - draw.textbbox((0, 0), text, font=font)[0]
        if w <= max_w:
            return text
    except:
        pass
    while text and (draw.textbbox((0, 0), text + "...", font=font)[2] - draw.textbbox((0, 0), text + "...", font=font)[0]) > max_w:
        text = text[:-1]
    return text + "..." if text else ""

def _get_dominant_color(img):
    try:
        small = img.resize((50, 50), Image.Resampling.NEAREST)
        pixels = list(small.getdata())
        r, g, b, c = 0, 0, 0, 0
        for p in pixels:
            if len(p) >= 3:
                r += p[0]; g += p[1]; b += p[2]; c += 1
        if c:
            return (r//c, g//c, b//c)
    except:
        pass
    return (0, 180, 255)

def _create_audio_card(info: dict) -> str:
    try:
        w, h = 1000, 500
        img = Image.new("RGBA", (w, h), (18, 22, 28, 255))
        draw = ImageDraw.Draw(img)

        thumb_url = info.get('thumbnail', '')
        thumb_img = _fetch_thumb(thumb_url) if thumb_url else None
        if thumb_img:
            try:
                bg = ImageOps.fit(thumb_img, (w, h), centering=(0.5, 0.5))
                bg = bg.filter(ImageFilter.GaussianBlur(35))
                img = bg
                draw = ImageDraw.Draw(img)
            except:
                pass

        dom_color = _get_dominant_color(thumb_img) if thumb_img else (0, 180, 255)

        draw.rounded_rectangle([30, 30, w - 30, h - 30], radius=28, fill=(15, 18, 25, 195), outline=(*dom_color, 60), width=2)

        f_large = _get_font(36)
        f_med = _get_font(24)
        f_sml = _get_font(18)
        f_emoji = _get_emoji_font(36)
        f_emoji_s = _get_emoji_font(24)

        cover_size = 280
        cx, cy = 60, 60 + (h - 120 - cover_size) // 2
        if thumb_img:
            try:
                cover = ImageOps.fit(thumb_img, (cover_size, cover_size), centering=(0.5, 0.5))
                mask = Image.new("L", (cover_size, cover_size), 0)
                md = ImageDraw.Draw(mask)
                md.rounded_rectangle([0, 0, cover_size, cover_size], radius=20, fill=255)
                cover.putalpha(mask)
                img.paste(cover, (cx, cy), cover)
            except:
                draw.rounded_rectangle([cx, cy, cx + cover_size, cy + cover_size], radius=20, fill=(30, 35, 45, 255))
        else:
            draw.rounded_rectangle([cx, cy, cx + cover_size, cy + cover_size], radius=20, fill=(30, 35, 45, 255))

        tx = cx + cover_size + 40
        ty = 80

        title = info.get('title', 'Khong co tieu de').strip()
        title = _truncate(draw, title, 580, f_large)
        _draw_mixed_text(draw, f"🎵 {title}", (tx, ty), f_large, f_emoji, (255, 255, 255, 255))

        author = info.get('uploader') or info.get('channel') or info.get('uploader_id', 'Unknown')
        _draw_mixed_text(draw, f"👤 Tác gia: {author}", (tx, ty + 70), f_med, f_emoji_s, (200, 200, 210, 255))

        _draw_mixed_text(draw, "🎯 Nen tang: YouTube", (tx, ty + 120), f_med, f_emoji_s, (200, 200, 210, 255))

        dur = info.get('duration', 0)
        dur_s = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "N/A"
        views = _fmt_size(info.get('view_count', 0))
        stats = f"⏱️ {dur_s}   👁️ {views} luot xem"
        _draw_mixed_text(draw, stats, (tx, ty + 175), f_med, f_emoji_s, dom_color)

        _draw_mixed_text(draw, "🔊 Dang tai audio...", (tx, ty + 230), f_sml, _get_emoji_font(18), (150, 150, 160, 255))

        out = os.path.join(CACHE_PATH, f"yt_audio_{int(time.time())}.png")
        img.convert("RGB").save(out, "JPEG", quality=92)
        return out
    except Exception as e:
        print(f"[YTAudioCard] Error: {e}")
        return ""

def _do_download_audio(bot, url, thread_id, thread_type, message_object, info):
    try:
        img_path = _create_audio_card(info)
        if img_path:
            try:
                with Image.open(img_path) as im:
                    iw, ih = im.size
                bot.sendLocalImage(img_path, message=None, thread_id=thread_id, thread_type=thread_type, width=iw, height=ih)
            except:
                pass
            finally:
                try:
                    os.remove(img_path)
                except:
                    pass

        print(f"[YouTube] Dang tai audio...")
        audio_path = download_audio(url)
        if not audio_path:
            bot.replyMessage(Message(text="❌ Khong the tai audio."), message_object, thread_id, thread_type)
            return

        from core.bot_sys import should_convert_to_m4a as need_convert
        if need_convert(bot, None, thread_type):
            print(f"[YouTube] Dang convert sang m4a...")
            audio_path = convert_to_m4a(audio_path)
            mime = "audio/mp4"
        else:
            mime = "audio/mpeg"

        print(f"[YouTube] Dang upload audio...")
        audio_url = upload_file(audio_path, mime)
        try:
            os.remove(audio_path)
        except:
            pass

        if not audio_url:
            bot.replyMessage(Message(text="❌ Loi upload audio."), message_object, thread_id, thread_type)
            return

        try:
            bot.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
        except:
            pass

        title = info.get('title', '').strip()[:80]
        author = info.get('uploader', '') or info.get('channel', '')
        caption = f"🎵 {title}\n👤 {author}"
        bot.sendRemoteVoice(voiceUrl=audio_url, thread_id=thread_id, thread_type=thread_type, message=Message(text=caption))
        print(f"[YouTube] Da gui audio hoan tat.")
    except Exception as e:
        print(f"[YouTube] Audio download error: {e}")
        bot.replyMessage(Message(text=f"❌ Loi: {e}"), message_object, thread_id, thread_type)

def _do_download_video(bot, url, thread_id, thread_type, message_object):
    try:
        print(f"[YouTube] Dang lay thong tin video...")
        info = get_video_info(url)
        if not info:
            bot.replyMessage(Message(text="❌ Khong the lay thong tin video."), message_object, thread_id, thread_type)
            return

        title = info.get('title', 'Video').strip()[:100]
        dur = info.get('duration', 0)
        dur_s = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "N/A"
        print(f"[YouTube] Video: {title} | {dur_s} | {info.get('uploader', '?')}")

        bot.replyMessage(Message(text=f"⏳ Dang tai video: {title}..."), message_object, thread_id, thread_type)

        out = os.path.join(CACHE_PATH, f"%(title)s_%(id)s.%(ext)s")
        path = download_video(url, out)
        if not path or not os.path.exists(path):
            bot.replyMessage(Message(text="❌ Khong the tai video."), message_object, thread_id, thread_type)
            return

        size = os.path.getsize(path)
        ok, msg = check_storage(size)
        if not ok:
            bot.replyMessage(Message(text=f"❌ Dung luong khong du: {msg}"), message_object, thread_id, thread_type)
            try:
                os.remove(path)
            except:
                pass
            return

        try:
            bot.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
        except:
            pass

        print(f"[YouTube] Dang gui video ({_fmt_size(size)})...")
        caption = f"🎬 {title}\n👤 {info.get('uploader', '')}"
        bot.sendLocalVideo(filePath=path, message=Message(text=caption), thread_id=thread_id, thread_type=thread_type)

        try:
            os.remove(path)
        except:
            pass
        print(f"[YouTube] Da gui video hoan tat.")
    except Exception as e:
        print(f"[YouTube] Video download error: {e}")
        bot.replyMessage(Message(text=f"❌ Loi: {e}"), message_object, thread_id, thread_type)

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, "prefix", ".")
    parts = message_text.strip().split(None, 1)
    cmd = parts[0].lstrip(prefix).lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd != "yt":
        return

    if not arg:
        bot.replyMessage(Message(text=(
            f"🎬 YouTube Download\n"
            f"{'─'*25}\n"
            f"📌 Cach dung:\n"
            f"  {prefix}yt <link>         → Tai video\n"
            f"  {prefix}yt <link> -a      → Tai audio (kem card thong tin)\n"
            f"\n"
            f"📝 Vi du:\n"
            f"  {prefix}yt https://youtube.com/watch?v=xxxxx\n"
            f"  {prefix}yt https://youtu.be/xxxxx -a\n"
            f"  {prefix}yt https://youtube.com/shorts/xxxxx\n"
            f"\n"
            f"💡 Them -a de chi tai audio (nhanh hon, nhe hon)"
        )), message_object, thread_id, thread_type)
        return

    is_audio = re.search(r'\s-a$', arg)
    url = re.sub(r'\s-a$', '', arg).strip()

    platform = detect_platform(url)
    if platform != 'youtube':
        bot.replyMessage(Message(text="❌ Link khong hop le hoac khong phai YouTube."), message_object, thread_id, thread_type)
        return

    print(f"\n[YouTube] >>> Phat hien link: {url} (mode: {'audio' if is_audio else 'video'})")

    def run():
        try:
            info = get_video_info(url)
        except Exception as e:
            print(f"[YouTube] Loi lay info: {e}")
            bot.replyMessage(Message(text=f"❌ Loi: {e}"), message_object, thread_id, thread_type)
            return

        if not info:
            bot.replyMessage(Message(text="❌ Khong the lay thong tin."), message_object, thread_id, thread_type)
            return

        title = info.get('title', '')
        author = info.get('uploader', '')
        dur = info.get('duration', 0)
        dur_s = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "N/A"

        print(f"[YouTube] Info: {title} - {author} - {dur_s}")

        if is_audio:
            _do_download_audio(bot, url, thread_id, thread_type, message_object, info)
        else:
            thumb_url = info.get('thumbnail', '')
            duration = info.get('duration', 0)
            dur_s = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "N/A"
            bot.replyMessage(Message(text=(
                f"🎬 Thong tin video:\n"
                f"📝 {title}\n"
                f"👤 {author}\n"
                f"⏱️ {dur_s} | 👁️ {_fmt_size(info.get('view_count', 0))} luot xem\n"
                f"{'─'*20}\n"
                f"⏳ Dang xu ly..."
            )), message_object, thread_id, thread_type)

            _do_download_video(bot, url, thread_id, thread_type, message_object)

    threading.Thread(target=run, daemon=True).start()
