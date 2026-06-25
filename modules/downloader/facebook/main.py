# -*- coding: UTF-8 -*-
import os
import sys
import time
import threading
import re

sys.dont_write_bytecode = True

from zlapi import ThreadType
from zlapi.models import Message

from modules.utils.ytdlp_downloader import (
    detect_platform, get_video_info, download_video, download_audio,
    convert_to_m4a, check_storage, upload_file, _fmt_size
)

CACHE_PATH = "modules/cache/"
os.makedirs(CACHE_PATH, exist_ok=True)

txa = {
    "name": "Facebook Download",
    "desc": {
        "fb": "Tai video tu Facebook (FHD, khong logo)",
        "facebook": "Tai video tu Facebook (FHD, khong logo)",
    },
    "author": "TXA",
    "command": ["fb", "facebook"],
    "help": {
        "fb": {
            "usage": [
                "{prefix}fb <link>",
                "{prefix}fb <link> -a"
            ],
            "examples": [
                "{prefix}fb https://facebook.com/watch/?v=xxxxx",
                "{prefix}fb https://fb.watch/xxxxx/",
                "{prefix}fb https://www.facebook.com/reel/xxxxx"
            ],
            "notes": [
                "Tai video chat luong cao nhat co the.",
                "Ho tro Facebook Watch, Reel, video tuong.",
                "Facebook audio khong ho tro."
            ]
        }
    }
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, "prefix", ".")
    parts = message_text.strip().split(None, 1)
    cmd = parts[0].lstrip(prefix).lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd not in ("fb", "facebook"):
        return

    if not arg:
        bot.replyMessage(Message(text=(
            f"📘 Facebook Download\n"
            f"{'─'*25}\n"
            f"📌 Cach dung:\n"
            f"  {prefix}fb <link>         → Tai video\n"
            f"\n"
            f"📝 Vi du:\n"
            f"  {prefix}fb https://facebook.com/watch/?v=xxxxx\n"
            f"  {prefix}fb https://fb.watch/xxxxx/\n"
            f"  {prefix}fb https://www.facebook.com/reel/xxxxx"
        )), message_object, thread_id, thread_type)
        return

    is_audio = re.search(r'\s-a$', arg)
    url = re.sub(r'\s-a$', '', arg).strip()

    platform = detect_platform(url)
    if platform != 'facebook':
        bot.replyMessage(Message(text="❌ Link khong hop le hoac khong phai Facebook."), message_object, thread_id, thread_type)
        return

    if is_audio:
        bot.replyMessage(Message(text="❌ Facebook khong ho tro tai audio."), message_object, thread_id, thread_type)
        return

    print(f"\n[Facebook] >>> Phat hien link: {url}")

    def run():
        try:
            print(f"[Facebook] Dang lay thong tin video...")
            info = get_video_info(url)
        except Exception as e:
            print(f"[Facebook] Loi: {e}")
            bot.replyMessage(Message(text=f"❌ Loi lay thong tin: {e}"), message_object, thread_id, thread_type)
            return

        if not info:
            bot.replyMessage(Message(text="❌ Khong the lay thong tin video."), message_object, thread_id, thread_type)
            return

        title = info.get('title', '').strip() or info.get('description', '').strip() or "Video Facebook"
        author = info.get('uploader', '') or info.get('channel', '') or ''
        dur = info.get('duration', 0)
        dur_s = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "N/A"
        print(f"[Facebook] Info: {title} - {author} - {dur_s}")

        bot.replyMessage(Message(text=(
            f"📘 Thong tin video:\n"
            f"📝 {title}\n"
            f"{'─'*20}\n"
            f"⏳ Dang xu ly..."
        )), message_object, thread_id, thread_type)

        try:
            out = os.path.join(CACHE_PATH, f"fb_%(id)s_%(title)s.%(ext)s")
            path = download_video(url, out)
            if not path or not os.path.exists(path):
                bot.replyMessage(Message(text="❌ Khong the tai video Facebook."), message_object, thread_id, thread_type)
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

            print(f"[Facebook] Dang gui video ({_fmt_size(size)})...")
            caption = f"📘 {title[:80]}"
            if author:
                caption += f"\n👤 {author}"
            bot.sendLocalVideo(filePath=path, message=Message(text=caption), thread_id=thread_id, thread_type=thread_type)

            try:
                os.remove(path)
            except:
                pass
            print(f"[Facebook] Da gui video hoan tat.")
        except Exception as e:
            print(f"[Facebook] Video error: {e}")
            bot.replyMessage(Message(text=f"❌ Loi: {e}"), message_object, thread_id, thread_type)

    threading.Thread(target=run, daemon=True).start()
