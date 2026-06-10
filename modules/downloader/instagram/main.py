import json
import os
import requests
import tempfile
from zlapi.models import Message

KAIROBOT_BASE_URL = os.getenv("KAIROBOT_BASE_URL", "https://kairobot.qzz.io").rstrip("/")
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../txa.json"))

txa = {
    "name": "Instagram",
    "desc": {
        "instagram": "Tải video/ảnh Instagram",
        "ig": "Tải media Instagram",
        "igdl": "Tải media Instagram",
        "iginfo": "Thông tin tài khoản"
    },
    "author": "TXA",
    "command": ["instagram", "ig", "igdl", "iginfo"],
    "help": {
        "ig": {
            "usage": [
                "{prefix}ig <link Instagram>",
                "{prefix}igdl <link Instagram>",
                "{prefix}instagram <link Instagram>"
            ],
            "examples": [
                "{prefix}ig https://www.instagram.com/reel/xxx/",
                "{prefix}igdl https://www.instagram.com/p/xxx/"
            ],
            "notes": [
                "Ho tro ca post, reel, carousel cua Instagram.",
                "Bot se gui media ve group tu dong."
            ]
        },
        "iginfo": {
            "usage": [
                "{prefix}iginfo <@ig_username>"
            ],
            "examples": [
                "{prefix}iginfo @instagram_user"
            ],
            "notes": [
                "Tra ve thong tin tai khoan Instagram: ten, bio, so follower, so post...",
                "Dung @username Instagram khong can @zalo user."
            ]
        }
    }
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

def handle_instagram_download(bot, message_object, thread_id, thread_type, url):
    loading = "🔎 Đang xử lý tải xuống Instagram... Vui lòng đợi trong giây lát ⏳✨"
    _send_text(bot, thread_id, thread_type, loading, message_object)

    try:
        data = _api_get("/instagram/download", {"link": url})
        inner = data.get("data", data)
        
        medias = inner.get("medias") or inner.get("links") or []
        if not medias:
            single_url = inner.get("url") or inner.get("video_url") or inner.get("download_url")
            if single_url:
                medias = [{"url": single_url, "type": "video" if ".mp4" in single_url else "image"}]
                
        if not medias:
            raise RuntimeError("Không tìm thấy tệp phương tiện nào để tải xuống.")

        # Send each media
        for i, media in enumerate(medias):
            media_url = media.get("url") if isinstance(media, dict) else media
            media_type = media.get("type", "image") if isinstance(media, dict) else "image"
            if not media_url:
                continue

            if media_type == "video" or ".mp4" in media_url:
                bot.sendRemoteVideo(
                    videoUrl=media_url,
                    thumbnailUrl="https://i.imgur.com/f3nK6z5.jpeg",
                    duration=0,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=1080,
                    height=1920,
                    message=Message(text=f"🎬 Video Instagram [{i+1}/{len(medias)}]")
                )
            else:
                path = os.path.join(tempfile.gettempdir(), f"ig_image_{i}_{thread_id}.jpeg")
                img_resp = requests.get(media_url, timeout=15)
                img_resp.raise_for_status()
                with open(path, "wb") as f:
                    f.write(img_resp.content)
                bot.sendLocalImage(
                    path, 
                    message=Message(text=f"📸 Ảnh Instagram [{i+1}/{len(medias)}]"), 
                    thread_id=thread_id, 
                    thread_type=thread_type, 
                    width=1200, 
                    height=1200
                )
                try:
                    os.remove(path)
                except:
                    pass
    except Exception as e:
        _send_text(bot, thread_id, thread_type, f"❌ Lỗi tải xuống Instagram: {str(e)}", message_object)

def handle_instagram_info(bot, message_object, thread_id, thread_type, username_or_link):
    _send_text(bot, thread_id, thread_type, "🔎 Đang lấy thông tin Instagram... Vui lòng đợi ⏳", message_object)
    
    link = username_or_link
    if not link.startswith("http"):
        link = f"https://www.instagram.com/{username_or_link.lstrip('@')}/"

    try:
        data = _api_get("/instagram/info", {"link": link})
        inner = data.get("data", data)
        
        fullname = inner.get("full_name") or inner.get("fullName") or "Không rõ"
        username = inner.get("username") or "Không rõ"
        biography = inner.get("biography") or "Không có tiểu sử"
        followers = inner.get("followers") or inner.get("edge_followed_by", {}).get("count", 0)
        following = inner.get("following") or inner.get("edge_follow", {}).get("count", 0)
        posts = inner.get("posts") or inner.get("edge_owner_to_timeline_media", {}).get("count", 0)
        avatar = inner.get("profile_pic_url") or inner.get("avatar")
        
        text = (
            f"📸 THÔNG TIN INSTAGRAM 📸\n"
            f"• Tên đầy đủ: {fullname}\n"
            f"• Username: {username}\n"
            f"• Tiểu sử: {biography}\n"
            f"• Số người theo dõi: {followers:,}\n"
            f"• Đang theo dõi: {following:,}\n"
            f"• Số bài đăng: {posts:,}"
        )
        
        if avatar:
            path = os.path.join(tempfile.gettempdir(), f"ig_avatar_{thread_id}.jpeg")
            img_resp = requests.get(avatar, timeout=15)
            img_resp.raise_for_status()
            with open(path, "wb") as f:
                f.write(img_resp.content)
            bot.sendLocalImage(
                path, 
                message=Message(text=text), 
                thread_id=thread_id, 
                thread_type=thread_type, 
                width=1200, 
                height=1200
            )
            try:
                os.remove(path)
            except:
                pass
        else:
            _send_text(bot, thread_id, thread_type, text, message_object)
    except Exception as e:
        _send_text(bot, thread_id, thread_type, f"❌ Lỗi lấy thông tin Instagram: {str(e)}", message_object)

def txa_command(bot, message_object, author_id, thread_id, thread_type, message):
    parts = (message or "").strip().split(maxsplit=1)
    if len(parts) < 2:
        _send_text(
            bot, 
            thread_id, 
            thread_type, 
            "Bạn muốn sử dụng Instagram?\n"
            "➜ ig/igdl <link Instagram>: tải video, ảnh bài đăng\n"
            "➜ iginfo <username hoặc link>: xem thông tin tài khoản", 
            message_object
        )
        return

    cmd = parts[0].lstrip("!/\\.").lower()
    query = parts[1].strip()

    if cmd == "iginfo":
        handle_instagram_info(bot, message_object, thread_id, thread_type, query)
    elif cmd in ("ig", "igdl"):
        handle_instagram_download(bot, message_object, thread_id, thread_type, query)
    else:
        if "instagram.com/" in query:
            handle_instagram_download(bot, message_object, thread_id, thread_type, query)
        else:
            handle_instagram_info(bot, message_object, thread_id, thread_type, query)
