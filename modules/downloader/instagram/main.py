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
    
    # Handle 400 Bad Request
    if response.status_code == 400:
        # Check both direct message and success flag
        msg = data.get("message") if isinstance(data, dict) else None
        if not msg and isinstance(data, dict) and data.get("success") is False:
            msg = "API không thể xử lý link này."
        
        # Clean up error message if it contains technical details
        if msg:
            # Remove technical terms but keep user-friendly parts
            if "Failed to get media ID" in msg:
                msg = "Không thể lấy media từ link này. Link có thể bị giới hạn hoặc không công khai."
            elif "Error downloading Instagram media" in msg:
                msg = "Không thể tải xuống từ link Instagram này."
            elif "Failed to get profile ID" in msg:
                msg = "Không thể lấy thông tin profile. Tài khoản có thể bị giới hạn hoặc không tồn tại."
            elif "Maximum number of redirects exceeded" in msg:
                msg = "Không thể truy cập profile do quá nhiều chuyển hướng. Tài khoản có thể bị giới hạn."
            elif "redirects exceeded" in msg.lower():
                msg = "Không thể truy cập profile. Tài khoản có thể bị giới hạn hoặc private."
        
        raise RuntimeError(msg or "Link Instagram không hợp lệ. Vui lòng kiểm tra lại.")
    
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        # Hide URL from error message
        error_msg = str(e)
        if "http" in error_msg.lower() or "instagram.com" in error_msg.lower():
            raise RuntimeError("Không thể xử lý link này. Link có thể không hợp lệ hoặc đã bị giới hạn bởi Instagram.")
        raise
    
    if isinstance(data, dict) and data.get("success") is False:
        msg = data.get("message") or data.get("error") or "API trả về trạng thái thất bại."
        # Clean up technical error messages
        if "Failed to get media ID" in msg:
            msg = "Không thể lấy media từ link này. Link có thể bị giới hạn hoặc không công khai."
        elif "Error downloading Instagram media" in msg:
            msg = "Không thể tải xuống từ link Instagram này."
        elif "Failed to get profile ID" in msg:
            msg = "Không thể lấy thông tin profile. Tài khoản có thể bị giới hạn hoặc không tồn tại."
        elif "Maximum number of redirects exceeded" in msg:
            msg = "Không thể truy cập profile do quá nhiều chuyển hướng. Tài khoản có thể bị giới hạn."
        elif "redirects exceeded" in msg.lower():
            msg = "Không thể truy cập profile. Tài khoản có thể bị giới hạn hoặc private."
        raise RuntimeError(msg)
    return data

def _send_text(bot, thread_id, thread_type, text, reply_to=None, ttl=None):
    if reply_to:
        msg = bot.replyMessage(Message(text=text), reply_to, thread_id=thread_id, thread_type=thread_type, ttl=ttl)
    else:
        msg = bot.send(Message(text=text), thread_id=thread_id, thread_type=thread_type, ttl=ttl)
    return msg  # Return message object to potentially delete later

def handle_instagram_download(bot, message_object, thread_id, thread_type, url):
    # Validate Instagram URL
    if not url or "instagram.com" not in url.lower():
        _send_text(bot, thread_id, thread_type, "❌ Link không hợp lệ. Vui lòng cung cấp link Instagram hợp lệ.", message_object)
        return
    
    # Check if URL contains required Instagram patterns
    if not any(pattern in url.lower() for pattern in ['/p/', '/reel/', '/tv/']):
        _send_text(bot, thread_id, thread_type, "❌ Link không phải là bài đăng Instagram (post/reel/tv). Vui lòng dùng link bài đăng hợp lệ.", message_object)
        return
    
    # Send loading message with short TTL (30 seconds) only after validation passes
    loading_msg = _send_text(bot, thread_id, thread_type, "🔎 Đang xử lý tải xuống Instagram... Vui lòng đợi trong giây lát ⏳✨", message_object, ttl=30000)

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
        
        # Delete loading message after success
        try:
            if loading_msg:
                bot.deleteMessage(loading_msg)
        except:
            pass
            
    except Exception as e:
        # Hide URL in error message
        error_msg = str(e)
        if "http" in error_msg.lower() or "instagram.com" in error_msg.lower():
            error_msg = "Không thể tải xuống từ link này. Link có thể không hợp lệ hoặc đã bị giới hạn."
        _send_text(bot, thread_id, thread_type, f"❌ Lỗi tải xuống Instagram: {error_msg}", message_object)
        
        # Delete loading message after error
        try:
            if loading_msg:
                bot.deleteMessage(loading_msg)
        except:
            pass

def handle_instagram_info(bot, message_object, thread_id, thread_type, username_or_link):
    # Send loading message
    loading_msg = _send_text(bot, thread_id, thread_type, "🔎 Đang lấy thông tin Instagram... Vui lòng đợi ⏳", message_object, ttl=60000)
    
    link = username_or_link
    if not link.startswith("http"):
        link = f"https://www.instagram.com/{username_or_link.lstrip('@')}/"
    
    # Check if it's a post/reel link, not a profile
    if '/p/' in link or '/reel/' in link:
        _send_text(bot, thread_id, thread_type, "❌ Link này là bài đăng Instagram, không phải profile. Vui lòng dùng lệnh ig/igdl để tải xuống.", message_object)
        try:
            if loading_msg:
                bot.deleteMessage(loading_msg)
        except:
            pass
        return

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
        
        # Delete loading message after success
        try:
            if loading_msg:
                bot.deleteMessage(loading_msg)
        except:
            pass
            
    except Exception as e:
        # Hide URL in error message and clean up technical details
        error_msg = str(e)
        if "http" in error_msg.lower() or "instagram.com" in error_msg.lower():
            error_msg = "Không thể lấy thông tin từ link này. Link có thể không hợp lệ hoặc đã bị giới hạn."
        
        # Clean up specific API error messages
        if "Maximum number of redirects exceeded" in error_msg or "redirects exceeded" in error_msg.lower():
            error_msg = "Không thể truy cập profile. Tài khoản Instagram có thể bị giới hạn hoặc private."
        elif "Failed to get profile ID" in error_msg:
            error_msg = "Không thể lấy thông tin profile. Tài khoản có thể bị giới hạn hoặc không tồn tại."
        
        _send_text(bot, thread_id, thread_type, f"❌ Lỗi lấy thông tin Instagram: {error_msg}", message_object)
        
        # Delete loading message after error
        try:
            if loading_msg:
                bot.deleteMessage(loading_msg)
        except:
            pass

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
