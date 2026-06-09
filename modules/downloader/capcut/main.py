import json
import os
import re

import requests
from zlapi.models import Message, MessageStyle, MultiMsgStyle


KAIROBOT_BASE_URL = os.getenv("KAIROBOT_BASE_URL", "https://kairobot.qzz.io").rstrip("/")
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../txa.json"))


txa = {
    "name": "CapCut",
    "desc": {
        "capcut": "Tìm kiếm mẫu CapCut",
        "capcutdl": "Tải video CapCut không logo"
    },
    "author": "TXA",
    "command": ["capcut", "capcutdl"]
}


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
        raise RuntimeError("Thiếu API key KaiRobot. Thêm `kairobot_api_key` vào txa.json hoặc set biến môi trường KAIROBOT_APIKEY.")

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


def _styled_message(text, color="#15a85f"):
    return Message(
        text=text,
        style=MultiMsgStyle([
            MessageStyle(offset=0, length=len(text), style="color", color=color, auto_format=False),
            MessageStyle(offset=0, length=len(text), style="font", size=13, auto_format=False),
            MessageStyle(offset=0, length=len(text), style="bold", auto_format=False),
        ])
    )


def _reply(client, message_object, thread_id, thread_type, text, color="#15a85f"):
    client.replyMessage(_styled_message(text, color), message_object, thread_id, thread_type)


def _as_list(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("data", "result", "results", "items", "list", "videos", "templates"):
        value = data.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _as_list(value)
            if nested:
                return nested
    return []


def _pick(obj, *keys, default=""):
    if not isinstance(obj, dict):
        return default
    for key in keys:
        value = obj
        ok = True
        for part in key.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                ok = False
                break
        if ok and value not in (None, ""):
            return value
    return default


def _find_url(obj, preferred=()):
    if isinstance(obj, str) and obj.startswith("http"):
        return obj
    if isinstance(obj, dict):
        for key in preferred:
            value = _pick(obj, key)
            if isinstance(value, str) and value.startswith("http"):
                return value
        for key, value in obj.items():
            if isinstance(value, str) and value.startswith("http"):
                return value
            nested = _find_url(value, preferred)
            if nested:
                return nested
    if isinstance(obj, list):
        for item in obj:
            nested = _find_url(item, preferred)
            if nested:
                return nested
    return ""


def _find_capcut_web_url(obj):
    if isinstance(obj, str) and obj.startswith("http") and "capcut.com" in obj and "v16-cc" not in obj:
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            res = _find_capcut_web_url(v)
            if res:
                return res
    if isinstance(obj, list):
        for item in obj:
            res = _find_capcut_web_url(item)
            if res:
                return res
    return ""


def _get_capcut_share_url(video):
    # Try to get share_url or template_url
    for key in ("share_url", "template_url", "web_url"):
        val = _pick(video, key)
        if isinstance(val, str) and "capcut.com" in val and "v16-cc" not in val:
            return val
            
    # Try to find template_id or id
    template_id = _pick(video, "id", "template_id", "templateId", "item_id")
    if template_id and str(template_id).isdigit():
        return f"https://www.capcut.com/template-detail/{template_id}"
        
    # Search recursively for a capcut web url (not CDN)
    found = _find_capcut_web_url(video)
    if found:
        return found
        
    # Fallback to direct cdn url or any url
    return _find_url(video, ("video_url", "url", "link"))



def _is_capcut_url(text):
    return bool(re.search(r"https?://\S*(capcut\.com|capcut)", text, re.I))


def _format_number(value):
    try:
        return f"{int(value):,}".replace(",", ".")
    except Exception:
        return str(value or 0)


def _search_capcut(client, message_object, thread_id, thread_type, keyword):
    data = _api_get("/capcut/search", {"query": keyword, "type": 1})
    videos = _as_list(data)
    if not videos:
        _reply(client, message_object, thread_id, thread_type, "Không tìm thấy video capcut nào với từ khóa bạn yêu cầu.", "#ff4081")
        return

    gui = f"Tìm thấy {len(videos)} video capcut với từ khóa `{keyword}`. Dưới đây là các video:\n\n"
    for i, video in enumerate(videos[:10], 1):
        title = _pick(video, "title", "name", "desc", "description", default="Không có tiêu đề")
        views = _pick(video, "play_amount", "playCount", "views", "stats.playCount", default=0)
        likes = _pick(video, "like_count", "likeCount", "likes", "stats.likeCount", default=0)
        video_url = _get_capcut_share_url(video)

        gui += (
            f"[ {i} ]. Tiêu đề: {title}\n"
            f"   - Lượt xem: {views}\n"
            f"   - Lượt thích: {likes}\n"
            f"   - Link: {video_url}\n\n"
        )

    max_length = 2000
    if len(gui) > max_length:
        gui = gui[:max_length] + "\n\n... (Bị cắt bớt do độ dài tin nhắn quá dài)"
    _reply(client, message_object, thread_id, thread_type, gui)


def _download_capcut(client, message_object, thread_id, thread_type, url):
    if "capcut.com" not in url and url.endswith(".mp4"):
        loading = "🔎 đang gửi video capcut để gửi lên..vui lòng chờ trong giây lát🚦✨"
        client.send(Message(text=loading), thread_id=thread_id, thread_type=thread_type, ttl=250000)
        client.sendRemoteVideo(
            videoUrl=url,
            thumbnailUrl="https://i.imgur.com/f3nK6z5.jpeg",
            duration=0,
            thread_id=thread_id,
            thread_type=thread_type,
            width=1080,
            height=1920,
            message=Message(text=f"🎬 video capcut của bạn đây! 🎶\n🔗 Link: {url}")
        )
        return

    video_url = None
    thumb_url = None
    title = "video capcut"
    duration = 0
    width = 1080
    height = 1920

    try:
        data = _api_get("/capcut/download", {"url": url})
        video_url = _find_url(data, ("video", "video_url", "download_url", "url", "play", "data.video", "data.url"))
        thumb_url = _find_url(data, ("thumbnail", "thumbnail_url", "cover", "thumb", "data.thumbnail", "data.cover"))
        title = _pick(data, "title", "data.title", "name", "data.name", default="video capcut")
        duration = _pick(data, "duration", "data.duration", default=0)
        width = _pick(data, "width", "data.width", default=1080)
        height = _pick(data, "height", "data.height", default=1920)
    except Exception as e:
        print(f"[CapCut] KaiRobot download failed: {e}. Trying /medias/down-aio fallback...")
        try:
            fallback_data = _api_get("/medias/down-aio", {"url": url, "version": "v1"})
            inner = fallback_data.get("data", fallback_data)
            medias = inner.get("medias", [])
            for media in medias:
                if media.get("type") == "video":
                    video_url = media.get("url")
                    break
            title = inner.get("title", "video capcut")
            thumb_url = inner.get("thumbnail") or "https://i.imgur.com/f3nK6z5.jpeg"
        except Exception as fb_err:
            raise RuntimeError(f"Không thể tải video từ link này (Lỗi: {e} | Fallback: {fb_err})")

    if not video_url:
        raise RuntimeError("API không trả về link video CapCut.")

    loading = "🔎 đang tải video capcut để gửi lên..vui lòng chờ trong giây lát🚦✨"
    client.send(Message(text=loading), thread_id=thread_id, thread_type=thread_type, ttl=250000)
    success = f"🎬 video capcut của bạn đây! 🎶\n✨ Tiêu đề: {title}\n🔗 Link gốc: {url}"
    client.sendRemoteVideo(
        videoUrl=video_url,
        thumbnailUrl=thumb_url or "https://i.imgur.com/f3nK6z5.jpeg",
        duration=int(float(duration or 0)),
        thread_id=thread_id,
        thread_type=thread_type,
        width=int(float(width or 1080)),
        height=int(float(height or 1920)),
        message=Message(text=success)
    )
    client.send(Message(text="tải thành công video capcut, ghi capcut <từ khóa> để tìm tiếp✨"), thread_id=thread_id, thread_type=thread_type)


def handle_capcut_command(message, message_object, thread_id, thread_type, author_id, client):
    content = (message or "").strip().split(maxsplit=1)
    if len(content) < 2:
        _reply(
            client,
            message_object,
            thread_id,
            thread_type,
            "Bạn muốn tìm hoặc tải video capcut?\n"
            "➜ capcut <từ khóa>: tìm video capcut\n"
            "➜ capcutdl <link capcut>: tải video capcut✨",
            "#ff4081"
        )
        return

    query = content[1].strip()
    cmd = content[0].lstrip("!/\\.").lower()
    try:
        if cmd == "capcutdl" or _is_capcut_url(query):
            _download_capcut(client, message_object, thread_id, thread_type, query)
        else:
            _search_capcut(client, message_object, thread_id, thread_type, query)
    except Exception as e:
        _reply(client, message_object, thread_id, thread_type, f"Đã xảy ra lỗi: {str(e)}", "#ff4081")


def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    handle_capcut_command(message_text, message_object, thread_id, thread_type, author_id, bot)
