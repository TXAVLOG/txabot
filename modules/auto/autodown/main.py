import json
import os
import re
import tempfile
import threading
import requests
import random
import time
from urllib.parse import urlparse
from zlapi.models import Message
from zlapi import ThreadType

CACHE_PATH = "modules/cache/"
os.makedirs(CACHE_PATH, exist_ok=True)

txa = {
    "name": "Auto Download",
    "desc": {
        "autodown": "Bat/tat tu dong tai video khi phat hien link YouTube, TikTok, Douyin, Facebook"
    },
    "author": "TXA",
    "command": ["autodown"],
    "help": {
        "autodown": {
            "usage": [
                "{prefix}autodown",
                "{prefix}autodown on",
                "{prefix}autodown off"
            ],
            "examples": [
                "{prefix}autodown",
                "{prefix}autodown on",
                "{prefix}autodown off"
            ],
            "notes": [
                "Bat auto download cho tung nhom rieng biet.",
                "Khi da bat, bot gap link YouTube/TikTok/Douyin/Facebook se tu dong tai va gui media.",
                "Khi bot tat cho nhom, chi admin bot moi co the su dung autodown."
            ]
        }
    }
}

PLATFORM_REGEX = {
    'tiktok': re.compile(
        r'https?://(?:www\.|m\.|vm\.|t\.)?tiktok\.com/\S+|https?://vt\.tiktok\.com/\S+',
        re.IGNORECASE
    ),
    'youtube': re.compile(
        r'(?:https?://)?(?:www\.|m\.)?(?:youtube\.com|youtu\.be)'
        r'(?:/watch\?v=|/embed/|/shorts/|/)([a-zA-Z0-9_-]{11,})',
        re.IGNORECASE
    ),
    'douyin': re.compile(
        r'(?:https?://)?(?:www\.)?(?:douyin\.com|iesdouyin\.com)'
        r'(?:/video/|/share/video/|/)(\d+)',
        re.IGNORECASE
    ),
    'facebook': re.compile(
        r'(?:https?://)?(?:www\.|m\.|mbasic\.)?'
        r'(?:facebook\.com|fb\.watch|fb\.com)'
        r'(?:/(?:watch/?\?v=|reel/|video/|share/|plugins/|(?:[^/]+/videos/)))?'
        r'\S*',
        re.IGNORECASE
    ),
}

PLATFORM_LABELS = {
    'tiktok': 'TikTok',
    'youtube': 'YouTube',
    'douyin': 'Douyin',
    'facebook': 'Facebook',
}

_processed_message_ids = set()
_reacted_message_ids = set()

def detect_platform(url: str):
    for platform, regex in PLATFORM_REGEX.items():
        if regex.search(url):
            return platform
    return None

def extract_urls_from_message(message_text, message_object):
    urls = set()
    url_pattern = re.compile(
        r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s<>"\'()\[\]{}]*',
        re.IGNORECASE
    )
    if message_text:
        for m in url_pattern.finditer(message_text):
            urls.add(m.group(0).rstrip('.,;:!?)'))
    if message_object:
        obj_dict = None
        if hasattr(message_object, '__dict__'):
            obj_dict = vars(message_object)
        elif isinstance(message_object, dict):
            obj_dict = message_object
        if obj_dict:
            def _walk(val, depth=0):
                if depth > 4:
                    return
                if isinstance(val, str):
                    for m in url_pattern.finditer(val):
                        urls.add(m.group(0).rstrip('.,;:!?)'))
                elif isinstance(val, dict):
                    for v in val.values():
                        _walk(v, depth + 1)
                elif isinstance(val, (list, tuple)):
                    for v in val:
                        _walk(v, depth + 1)
            _walk(obj_dict)
    return list(urls)

def read_settings(uid):
    settings_file = f"{uid}_setting.json"
    try:
        with open(settings_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def is_admin(bot, author_id):
    settings = read_settings(bot.uid)
    admin_bot = settings.get("admin_bot", [])
    return author_id in admin_bot

def is_bot_on_for_thread(bot, thread_id):
    settings = read_settings(bot.uid)
    allowed = settings.get('allowed_thread_ids', [])
    return thread_id in allowed

def send_reaction_once(bot, message_object, thread_id, thread_type, reaction):
    msg_id = None
    if hasattr(message_object, 'msgId'):
        msg_id = message_object.msgId
    if msg_id and msg_id in _reacted_message_ids:
        return
    try:
        bot.sendReaction(message_object, reaction, thread_id, thread_type)
        if msg_id:
            _reacted_message_ids.add(msg_id)
            if len(_reacted_message_ids) > 1000:
                _reacted_message_ids.clear()
    except Exception as e:
        print(f"[AutoDown] Reaction error: {e}")

def fmt_size(bytes_val):
    if bytes_val >= 1_000_000_000:
        return f"{bytes_val/1_000_000_000:.2f} GB"
    if bytes_val >= 1_000_000:
        return f"{bytes_val/1_000_000:.2f} MB"
    if bytes_val >= 1_000:
        return f"{bytes_val/1_000:.2f} KB"
    return f"{bytes_val} B"

# ─── TIKTOK (uses KaiRobot API) ─────────────────────────────────────────────

KAIROBOT_BASE_URL = os.getenv("KAIROBOT_BASE_URL", "https://kairobot.qzz.io").rstrip("/")
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../txa.json"))

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
    except:
        pass
    return ""

def _api_get(path, params):
    api_key = _read_api_key()
    if not api_key:
        raise RuntimeError("Thieu API key KaiRobot.")
    payload = dict(params)
    payload["apikey"] = api_key
    resp = requests.get(f"{KAIROBOT_BASE_URL}{path}", params=payload, timeout=30)
    data = resp.json() if resp.text else {}
    if resp.status_code == 401:
        raise RuntimeError(data.get("message", "API key khong hop le."))
    resp.raise_for_status()
    if isinstance(data, dict) and data.get("success") is False:
        raise RuntimeError(data.get("message") or data.get("error", "API that bai."))
    return data

def download_tiktok_media(bot, url, thread_id, thread_type, message_object):
    try:
        print(f"[AutoDown-TikTok] Dang goi API lay link: {url}")
        data = _api_get("/tiktok/download", {"url": url})
        inner = data.get("data", data) or {}

        video_url = (inner.get("video_url") or inner.get("url") or inner.get("download_url"))
        if not video_url and isinstance(inner.get("video"), dict):
            video_url = inner["video"].get("url") or inner["video"].get("play")

        if video_url:
            parsed = urlparse(video_url)
            is_img = any(parsed.path.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"])
            if not is_img:
                send_reaction_once(bot, message_object, thread_id, thread_type, "Da")
                print(f"[AutoDown-TikTok] Gui video...")
                bot.sendRemoteVideo(videoUrl=video_url, thumbnailUrl="", duration=0,
                                    thread_id=thread_id, thread_type=thread_type,
                                    width=1080, height=1920, message=Message(text="🎬 TikTok"))
                print(f"[AutoDown-TikTok] Hoan tat.")
                return

        images = inner.get("images") or inner.get("medias") or []
        if images:
            send_reaction_once(bot, message_object, thread_id, thread_type, "Da")
            for i, img_item in enumerate(images):
                img_url = img_item.get("url") if isinstance(img_item, dict) else img_item
                if img_url:
                    try:
                        r = requests.get(img_url, timeout=15)
                        p = os.path.join(tempfile.gettempdir(), f"ttimg_{thread_id}_{i}_{int(time.time())}.jpeg")
                        with open(p, "wb") as f:
                            f.write(r.content)
                        bot.sendLocalImage(p, message=Message(text=f"📸 TikTok [{i+1}/{len(images)}]"),
                                           thread_id=thread_id, thread_type=thread_type)
                        try:
                            os.remove(p)
                        except:
                            pass
                    except:
                        pass
            print(f"[AutoDown-TikTok] Da gui {len(images)} anh.")
            return

        for key in ("play", "hd_play", "no_watermark", "wmplay"):
            if inner.get(key):
                fb_url = inner[key]
                parsed = urlparse(fb_url)
                is_img = any(parsed.path.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"])
                send_reaction_once(bot, message_object, thread_id, thread_type, "Da")
                if is_img:
                    try:
                        r = requests.get(fb_url, timeout=15)
                        p = os.path.join(tempfile.gettempdir(), f"ttimg_{int(time.time())}.jpeg")
                        with open(p, "wb") as f:
                            f.write(r.content)
                        bot.sendLocalImage(p, message=None, thread_id=thread_id, thread_type=thread_type)
                        try:
                            os.remove(p)
                        except:
                            pass
                    except:
                        pass
                else:
                    bot.sendRemoteVideo(videoUrl=fb_url, thumbnailUrl="", duration=0,
                                        thread_id=thread_id, thread_type=thread_type,
                                        width=1080, height=1920, message=Message(text="🎬 TikTok"))
                print(f"[AutoDown-TikTok] Hoan tat.")
                return

        raise RuntimeError("Khong tim thay media.")
    except Exception as e:
        print(f"[AutoDown-TikTok] Loi: {e}")
        try:
            send_reaction_once(bot, message_object, thread_id, thread_type, "❌")
        except:
            pass

# ─── YT-DLP BASED (YouTube, Douyin, Facebook) ────────────────────────────────

from modules.utils.ytdlp_downloader import (
    detect_platform as dl_detect, get_video_info,
    download_video, _progress_hook_factory, _fmt_size
)

def download_with_ytdlp(bot, url, platform, thread_id, thread_type, message_object):
    label = platform.capitalize()
    try:
        print(f"[AutoDown-{label}] Dang lay thong tin: {url}")
        info = get_video_info(url)
        if not info:
            print(f"[AutoDown-{label}] Khong lay duoc info.")
            return
        title = info.get('title', '') or info.get('description', '') or f"Video {label}"
        print(f"[AutoDown-{label}] Info: {title[:60]}")

        send_reaction_once(bot, message_object, thread_id, thread_type, "Da")

        out = os.path.join(CACHE_PATH, f"autodown_{platform}_%(id)s.%(ext)s")
        path = download_video(url, out)
        if not path or not os.path.exists(path):
            print(f"[AutoDown-{label}] Tai that bai.")
            return

        size = os.path.getsize(path)
        free = 0
        try:
            import psutil
            free = psutil.disk_usage(os.path.abspath('.')).free
        except:
            free = size * 2
        if free < size:
            print(f"[AutoDown-{label}] Khong du dung luong. Con {_fmt_size(free)}, can {_fmt_size(size)}")
            try:
                os.remove(path)
            except:
                pass
            return

        print(f"[AutoDown-{label}] Dang gui video ({_fmt_size(size)})...")
        caption = f"🎬 {title[:80]}" if platform != 'douyin' else f"🎵 {title[:80]}"
        bot.sendLocalVideo(filePath=path, message=Message(text=caption),
                           thread_id=thread_id, thread_type=thread_type)

        try:
            os.remove(path)
        except:
            pass
        print(f"[AutoDown-{label}] Hoan tat.")
    except Exception as e:
        print(f"[AutoDown-{label}] Loi: {e}")

# ─── MAIN LISTENER ───────────────────────────────────────────────────────────

def autodown_listener(bot, message_object, author_id, thread_id, thread_type, message_text):
    msg_id = None
    if hasattr(message_object, 'msgId'):
        msg_id = message_object.msgId
    if msg_id and msg_id in _processed_message_ids:
        return

    settings = read_settings(bot.uid)
    enabled_threads = settings.get("autodown_enabled", [])
    if thread_id not in enabled_threads:
        return

    bot_on = is_bot_on_for_thread(bot, thread_id)
    if not bot_on and not is_admin(bot, author_id):
        return

    urls = extract_urls_from_message(message_text, message_object)
    if not urls:
        return

    found_platforms = []
    for url in urls:
        platform = detect_platform(url)
        if platform:
            found_platforms.append((url, platform))
            print(f"[AutoDown] >>> Phat hien link {platform}: {url[:80]}...")

    if not found_platforms:
        return

    if msg_id:
        _processed_message_ids.add(msg_id)
        if len(_processed_message_ids) > 1000:
            _processed_message_ids.clear()

    for url, platform in found_platforms:
        if platform == 'tiktok':
            t = threading.Thread(target=download_tiktok_media,
                                 args=(bot, url, thread_id, thread_type, message_object), daemon=True)
            t.start()
        elif platform in ('youtube', 'douyin', 'facebook'):
            t = threading.Thread(target=download_with_ytdlp,
                                 args=(bot, url, platform, thread_id, thread_type, message_object), daemon=True)
            t.start()

def txa_command(bot, message_object, author_id, thread_id, thread_type, message):
    settings_file = f"{bot.uid}_setting.json"
    try:
        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        settings = {}

    enabled_threads = settings.get("autodown_enabled", [])
    parts = (message or "").strip().split()
    prefix = getattr(bot, "prefix", "")

    stripped_cmd = (parts[0][len(prefix):] if parts and prefix and parts[0].startswith(prefix) else (parts[0] if parts else "")).lower()
    if len(parts) == 1 and stripped_cmd in ("autodown",):
        status = "BAT" if thread_id in enabled_threads else "TAT"
        text = (f"🤖 Auto Download hien dang: {status}\n"
                f"➜ Dung `{prefix}autodown on` de bat\n"
                f"➜ Dung `{prefix}autodown off` de tat\n"
                f"{'─'*20}\n"
                f"💡 Ho tro: YouTube, TikTok, Douyin, Facebook")
        bot.send(Message(text=text), thread_id=thread_id, thread_type=thread_type)
        return

    action = parts[-1].lower()
    if action == "on":
        if thread_id in enabled_threads:
            bot.send(Message(text="✅ Auto download da BAT tu truoc!"), thread_id=thread_id, thread_type=thread_type)
            return
        enabled_threads.append(thread_id)
        settings["autodown_enabled"] = enabled_threads
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        bot.send(Message(text="✅ Da BAT auto download cho nhom nay (YT/TT/DY/FB)."), thread_id=thread_id, thread_type=thread_type)
    elif action == "off":
        if thread_id not in enabled_threads:
            bot.send(Message(text="✅ Auto download da TAT tu truoc!"), thread_id=thread_id, thread_type=thread_type)
            return
        enabled_threads.remove(thread_id)
        settings["autodown_enabled"] = enabled_threads
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        bot.send(Message(text="✅ Da TAT auto download cho nhom nay."), thread_id=thread_id, thread_type=thread_type)
    else:
        bot.send(Message(text="❓ Dung: autodown on / autodown off"), thread_id=thread_id, thread_type=thread_type)
