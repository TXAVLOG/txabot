import json
import os
import re
import tempfile
import threading
import requests
import random
from zlapi.models import Message

KAIROBOT_BASE_URL = os.getenv("KAIROBOT_BASE_URL", "https://kairobot.qzz.io").rstrip("/")
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../txa.json"))

txa = {
    "name": "Auto Download",
    "desc": {
        "autodown": "Bật/tắt tự động tải video TikTok khi phát hiện link"
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
                "Khi da bat, bot gap link TikTok se tu dong tai va gui media."
            ]
        }
    }
}

# Regex tìm link TikTok
TIKTOK_REGEX = re.compile(
    r"https?://(?:www\.|m\.|vm\.|t\.)?tiktok\.com/\S+|https?://vt\.tiktok\.com/\S+",
    re.IGNORECASE
)

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
    response.raise_for_status()
    if isinstance(data, dict) and data.get("success") is False:
        raise RuntimeError(data.get("message") or data.get("error") or "API trả về trạng thái thất bại.")
    return data

def _send_text(bot, thread_id, thread_type, text, reply_to=None):
    if reply_to:
        bot.replyMessage(Message(text=text), reply_to, thread_id=thread_id, thread_type=thread_type)
    else:
        bot.send(Message(text=text), thread_id=thread_id, thread_type=thread_type)

def _send_video(bot, video_url, thread_id, thread_type, caption):
    bot.sendRemoteVideo(
        videoUrl=video_url,
        thumbnailUrl="https://i.imgur.com/f3nK6z5.jpeg",
        duration=0,
        thread_id=thread_id,
        thread_type=thread_type,
        width=1080,
        height=1920,
        message=Message(text=caption)
    )

def _send_image(bot, img_url, thread_id, thread_type, caption):
    path = os.path.join(tempfile.gettempdir(), f"tt_image_{thread_id}_{os.getpid()}.jpeg")
    try:
        img_resp = requests.get(img_url, timeout=15)
        img_resp.raise_for_status()
        with open(path, "wb") as f:
            f.write(img_resp.content)
        bot.sendLocalImage(
            path,
            message=Message(text=caption),
            thread_id=thread_id,
            thread_type=thread_type,
            width=1200,
            height=1200
        )
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

def _try_send_reaction(bot, message_object, thread_id, thread_type, reaction):
    # Get message ID
    message_id = None
    if hasattr(message_object, 'msgId'):
        message_id = message_object.msgId
    elif hasattr(message_object, 'id'):
        message_id = message_object.id
    
    # Only send reaction once per message
    if message_id and message_id in _reacted_message_ids:
        return
        
    try:
        bot.sendReaction(message_object, reaction, thread_id, thread_type)
        if message_id:
            _reacted_message_ids.add(message_id)
            # Keep set from growing too large
            if len(_reacted_message_ids) > 1000:
                _reacted_message_ids.clear()
    except Exception:
        pass

def download_tiktok(bot, message_object, thread_id, thread_type, url):
    """Tải và gửi video/ảnh TikTok về nhóm."""
    try:
        # Gửi reaction chờ
        _try_send_reaction(bot, message_object, thread_id, thread_type, "⏳")
        data = _api_get("/tiktok/download", {"url": url})
        inner = data.get("data", data) or {}

        # 1) Trường hợp có video_url
        video_url = (
            inner.get("video_url")
            or inner.get("url")
            or inner.get("download_url")
        )
        if not video_url and isinstance(inner.get("video"), dict):
            video_url = inner["video"].get("url") or inner["video"].get("play")

        if video_url:
            _send_video(bot, video_url, thread_id, thread_type, "🎬 Video TikTok")
            # Gửi reaction thành công
            _try_send_reaction(bot, message_object, thread_id, thread_type, random.choice(["👍", "❤️", "😆", "😮", "🎉", "🔥", "🤩", "✅"]))
            _try_send_reaction(bot, message_object, thread_id, thread_type, "TBOT OK ✅")
            return

        # 2) Trường hợp là bài đăng dạng ảnh
        images = inner.get("images") or inner.get("medias") or []
        if images:
            for i, img in enumerate(images):
                img_url = img.get("url") if isinstance(img, dict) else img
                if not img_url:
                    continue
                _send_image(bot, img_url, thread_id, thread_type,
                            f"📸 Ảnh TikTok [{i+1}/{len(images)}]")
            # Gửi reaction thành công
            _try_send_reaction(bot, message_object, thread_id, thread_type, random.choice(["👍", "❤️", "😆", "😮", "🎉", "🔥", "🤩", "✅"]))
            _try_send_reaction(bot, message_object, thread_id, thread_type, "TBOT OK ✅")
            return

        # 3) Một số API trả về play/hd_play/no_watermark
        for key in ("play", "hd_play", "no_watermark", "wmplay"):
            if inner.get(key):
                _send_video(bot, inner[key], thread_id, thread_type, "🎬 Video TikTok")
                _try_send_reaction(bot, message_object, thread_id, thread_type, random.choice(["👍", "❤️", "😆", "😮", "🎉", "🔥", "🤩", "✅"]))
                _try_send_reaction(bot, message_object, thread_id, thread_type, "TBOT OK ✅")
                return

        raise RuntimeError("Không tìm thấy tệp phương tiện nào để tải xuống.")
    except Exception as e:
        _send_text(bot, thread_id, thread_type,
                   f"❌ Lỗi tải xuống TikTok: {str(e)}", message_object)
        _try_send_reaction(bot, message_object, thread_id, thread_type, "❌")
        _try_send_reaction(bot, message_object, thread_id, thread_type, "TBOT FAILED ❌")

# Store processed message IDs to avoid duplicates
_processed_message_ids = set()
# Store messages we've already reacted to
_reacted_message_ids = set()

def _extract_all_links(message_text, message_object):
    """Extract link từ cả message_text và message_object (embed, etc.)"""
    links = set()
    # 1) Lấy từ message_text
    if message_text:
        links.update(TIKTOK_REGEX.findall(message_text))
    # 2) Lấy từ message_object: title, desc, hay bất cứ trường nào chứa text
    if message_object:
        # Kiểm tra dict nếu có
        if hasattr(message_object, '__dict__'):
            obj_dict = vars(message_object)
            # Duyệt qua các giá trị trong dict
            for k, v in obj_dict.items():
                if isinstance(v, str):
                    links.update(TIKTOK_REGEX.findall(v))
                elif isinstance(v, dict):
                    for sk, sv in v.items():
                        if isinstance(sv, str):
                            links.update(TIKTOK_REGEX.findall(sv))
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str):
                            links.update(TIKTOK_REGEX.findall(item))
    # Trả về danh sách unique links
    return list(links)

def _read_settings(uid):
    """Đọc settings đúng cách dùng từ core.bot_sys"""
    settings_file = f"{uid}_setting.json"
    try:
        with open(settings_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def autodown_listener(bot, message_object, author_id, thread_id, thread_type, message_text):
    """Listener chính được gọi từ txa.py"""
    # Get message ID to avoid duplicates
    message_id = None
    if hasattr(message_object, 'msgId'):
        message_id = message_object.msgId
    elif hasattr(message_object, 'id'):
        message_id = message_object.id
    
    # If we have a message ID and we've already processed it, skip
    if message_id and message_id in _processed_message_ids:
        return
    
    # Đọc settings
    settings = _read_settings(bot.uid)
    enabled_threads = settings.get("autodown_enabled", [])

    # Kiểm tra xem thread hiện tại có enable không
    if thread_id not in enabled_threads:
        return

    # Extract link
    links = _extract_all_links(message_text, message_object)
    if not links:
        return
    
    # Mark this message as processed if we have an ID
    if message_id:
        _processed_message_ids.add(message_id)
        # Keep the set from growing too large (clean up old entries after 1000 messages)
        if len(_processed_message_ids) > 1000:
            # Remove oldest half of the set
            _processed_message_ids.clear()

    # Tải từng link (dùng thread để không block)
    for link in links:
        threading.Thread(
            target=download_tiktok,
            args=(bot, message_object, thread_id, thread_type, link),
            daemon=True
        ).start()

def txa_command(bot, message_object, author_id, thread_id, thread_type, message):
    """
    Lệnh autodown dùng để bật/tắt cờ autodown cho thread hiện tại.
    Khi bật, mọi tin nhắn chứa link TikTok sẽ được bot tự tải.
    """
    settings_file = f"{bot.uid}_setting.json"
    try:
        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        settings = {}

    enabled_threads = settings.get("autodown_enabled", [])
    parts = (message or "").strip().split()
    prefix = getattr(bot, "prefix", "")

    # Nếu chỉ gọi lệnh không kèm on/off -> hiển thị trạng thái
    stripped_cmd = (parts[0][len(prefix):] if parts and prefix and parts[0].startswith(prefix) else (parts[0] if parts else "")).lower()
    if len(parts) == 1 and stripped_cmd in ("autodown",):
        status = "BẬT" if thread_id in enabled_threads else "TẮT"
        _send_text(
            bot, thread_id, thread_type,
            f"🤖 Auto Download hiện đang: {status}\n"
            f"➜ Dùng `{prefix}autodown on` để bật\n"
            f"➜ Dùng `{prefix}autodown off` để tắt"
        )
        return

    action = parts[-1].lower()
    if action == "on":
        if thread_id in enabled_threads:
            # Đã bật rồi
            _send_text(bot, thread_id, thread_type, "✅ Auto download TikTok đã BẬT từ trước rồi cho nhóm này!")
            return
        enabled_threads.append(thread_id)
        settings["autodown_enabled"] = enabled_threads
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        _send_text(bot, thread_id, thread_type, "✅ Đã BẬT auto download TikTok cho nhóm này.")
    elif action == "off":
        if thread_id not in enabled_threads:
            _send_text(bot, thread_id, thread_type, "✅ Auto download TikTok đã TẮT từ trước rồi cho nhóm này!")
            return
        enabled_threads.remove(thread_id)
        settings["autodown_enabled"] = enabled_threads
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        _send_text(bot, thread_id, thread_type, "✅ Đã TẮT auto download TikTok cho nhóm này.")
    else:
        _send_text(bot, thread_id, thread_type, "❓ Dùng: autodown on / autodown off")
