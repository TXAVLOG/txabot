# -*- coding: UTF-8 -*-
import os
import sys
import time
import threading
import re
from io import BytesIO

sys.dont_write_bytecode = True

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from zlapi import ThreadType
from zlapi.models import Message

from modules.utils.ytdlp_downloader import (
    detect_platform, get_video_info, download_video, download_audio,
    convert_to_m4a, check_storage, upload_file, _fmt_size
)

CACHE_PATH = "modules/cache/"
BACKGROUND_PATH = "background/"
os.makedirs(CACHE_PATH, exist_ok=True)

txa = {
    "name": "Douyin Download",
    "desc": {
        "dy": "Tai video/audio tu Douyin (khong watermark)",
        "douyin": "Tai video/audio tu Douyin (khong watermark)",
    },
    "author": "TXA",
    "command": ["dy", "douyin"],
    "help": {
        "dy": {
            "usage": [
                "{prefix}dy <link>",
                "{prefix}dy <link> -a"
            ],
            "examples": [
                "{prefix}dy https://douyin.com/video/xxxxx",
                "{prefix}dy https://www.iesdouyin.com/share/video/xxxxx/ -a"
            ],
            "notes": [
                "Tu dong tai video chat luong cao, khong watermark.",
                "Them -a de tai audio.",
                "Tu dong phat hien link Douyin."
            ]
        }
    }
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, "prefix", ".")
    parts = message_text.strip().split(None, 1)
    cmd = parts[0].lstrip(prefix).lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd not in ("dy", "douyin"):
        return

    if not arg:
        bot.replyMessage(Message(text=(
            f"🎵 Douyin Download\n"
            f"{'─'*25}\n"
            f"📌 Cach dung:\n"
            f"  {prefix}dy <link>         → Tai video (khong watermark)\n"
            f"  {prefix}dy <link> -a      → Tai audio\n"
            f"\n"
            f"📝 Vi du:\n"
            f"  {prefix}dy https://douyin.com/video/xxxxx\n"
            f"  {prefix}dy https://www.iesdouyin.com/share/video/xxxxx/"
        )), message_object, thread_id, thread_type)
        return

    is_audio = re.search(r'\s-a$', arg)
    url = re.sub(r'\s-a$', '', arg).strip()

    platform = detect_platform(url)
    if platform != 'douyin':
        bot.replyMessage(Message(text="❌ Link khong hop le hoac khong phai Douyin."), message_object, thread_id, thread_type)
        return

    print(f"\n[Douyin] >>> Phat hien link: {url} (mode: {'audio' if is_audio else 'video'})")

    def run():
        try:
            print(f"[Douyin] Dang lay thong tin video...")
            info = get_video_info(url)
        except Exception as e:
            print(f"[Douyin] Loi: {e}")
            bot.replyMessage(Message(text=f"❌ Loi lay thong tin: {e}"), message_object, thread_id, thread_type)
            return

        if not info:
            bot.replyMessage(Message(text="❌ Khong the lay thong tin video."), message_object, thread_id, thread_type)
            return

        title = info.get('title', '').strip() or info.get('description', '').strip() or "Video Douyin"
        author = info.get('uploader', '') or info.get('channel', '') or ''
        dur = info.get('duration', 0)
        dur_s = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "N/A"
        print(f"[Douyin] Info: {title} - {author} - {dur_s}")

        if is_audio:
            bot.replyMessage(Message(text=f"⏳ Dang tai audio: {title}..."), message_object, thread_id, thread_type)
            try:
                audio_path = download_audio(url)
                if not audio_path:
                    bot.replyMessage(Message(text="❌ Khong the tai audio."), message_object, thread_id, thread_type)
                    return

                from core.bot_sys import should_convert_to_m4a as need_convert
                if need_convert(bot, None, thread_type):
                    print(f"[Douyin] Dang convert sang m4a...")
                    audio_path = convert_to_m4a(audio_path)
                    mime = "audio/mp4"
                else:
                    mime = "audio/mpeg"

                print(f"[Douyin] Dang upload audio...")
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

                caption = f"🎵 {title[:80]}\n👤 {author}" if author else f"🎵 {title[:80]}"
                bot.sendRemoteVoice(voiceUrl=audio_url, thread_id=thread_id, thread_type=thread_type, message=Message(text=caption))
                print(f"[Douyin] Da gui audio hoan tat.")
            except Exception as e:
                print(f"[Douyin] Audio error: {e}")
                bot.replyMessage(Message(text=f"❌ Loi: {e}"), message_object, thread_id, thread_type)
            return

        bot.replyMessage(Message(text=(
            f"🎵 Thong tin Douyin:\n"
            f"📝 {title}\n"
            f"{'─'*20}\n"
            f"⏳ Dang xu ly..."
        )), message_object, thread_id, thread_type)

        try:
            out = os.path.join(CACHE_PATH, f"douyin_%(id)s_%(title)s.%(ext)s")
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

            print(f"[Douyin] Dang gui video ({_fmt_size(size)})...")
            caption = f"🎵 {title[:80]}"
            if author:
                caption += f"\n👤 {author}"
            bot.sendLocalVideo(filePath=path, message=Message(text=caption), thread_id=thread_id, thread_type=thread_type)

            try:
                os.remove(path)
            except:
                pass
            print(f"[Douyin] Da gui video hoan tat.")
        except Exception as e:
            print(f"[Douyin] Video error: {e}")
            bot.replyMessage(Message(text=f"❌ Loi: {e}"), message_object, thread_id, thread_type)

    threading.Thread(target=run, daemon=True).start()
