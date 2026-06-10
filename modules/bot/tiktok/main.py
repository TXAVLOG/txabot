import json
import os
import re
import tempfile

import requests
from zlapi.models import Message


KAIROBOT_BASE_URL = os.getenv("KAIROBOT_BASE_URL", "https://kairobot.qzz.io").rstrip("/")
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../txa.json"))


txa = {
    "name": "TikTok API",
    "desc": {
        "tiktok": "Tải video TikTok",
        "downtik": "Tải video TikTok",
        "tt": "Tải video TikTok",
        "tiktokinfo": "Thông tin kênh TikTok",
        "in4tiktok": "Thông tin kênh TikTok",
        "tiktoksearch": "Tìm kiếm video TikTok"
    },
    "author": "TXA",
    "command": ["tiktok", "downtik", "tt", "tiktokinfo", "in4tiktok", "tiktoksearch"],
    "help": {
        "tiktok": {
            "usage": [
                "{prefix}tiktok <link TikTok>",
                "{prefix}tt <link TikTok>",
                "{prefix}downtik <link TikTok>"
            ],
            "examples": [
                "{prefix}tiktok https://vt.tiktok.com/xxx/",
                "{prefix}tt https://www.tiktok.com/@user/video/123456"
            ],
            "notes": [
                "Ho tro ca link vt.tiktok.com, www.tiktok.com, vm.tiktok.com...",
                "Bot se gui video/anh ve group tu dong."
            ]
        },
        "tiktokinfo": {
            "usage": [
                "{prefix}tiktokinfo <@tiktok_username>",
                "{prefix}in4tiktok <@tiktok_username>"
            ],
            "examples": [
                "{prefix}tiktokinfo @tiktok_user"
            ],
            "notes": [
                "Tra ve thong tin kenh TikTok: ten, bio, so follower, so video...",
                "Dung @username TikTok khong can @zalo user."
            ]
        },
        "tiktoksearch": {
            "usage": [
                "{prefix}tiktoksearch <tu_khoa_tim_kiem>"
            ],
            "examples": [
                "{prefix}tiktoksearch nhac hay nhat"
            ],
            "notes": [
                "Tim kiem video TikTok theo tu khoa.",
                "Tra ve danh sach video lien quan."
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


def _send_text(bot, thread_id, thread_type, text, reply_to=None):
    if reply_to:
        bot.replyMessage(Message(text=text), reply_to, thread_id=thread_id, thread_type=thread_type)
    else:
        bot.send(Message(text=text), thread_id=thread_id, thread_type=thread_type)


def _as_list(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("data", "result", "results", "items", "list", "videos", "aweme_list"):
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
            if isinstance(value, list):
                nested = _find_url(value, preferred)
                if nested:
                    return nested
        for value in obj.values():
            nested = _find_url(value, preferred)
            if nested:
                return nested
    if isinstance(obj, list):
        for item in obj:
            nested = _find_url(item, preferred)
            if nested:
                return nested
    return ""


def _format_number(value):
    try:
        return f"{int(value):,}".replace(",", ".")
    except Exception:
        return str(value or 0)


def _extract_link(message, message_object):
    if isinstance(message, str):
        parts = message.strip().split(maxsplit=1)
        if len(parts) >= 2:
            return parts[1].strip()

    content_obj = getattr(message_object, "content", None)
    if content_obj:
        href = getattr(content_obj, "href", None)
        if href:
            return href
        params = getattr(content_obj, "params", None)
        if params:
            try:
                params_dict = json.loads(params)
                if params_dict.get("href"):
                    return params_dict["href"]
            except Exception:
                pass
    return ""


def _normalize_download(data):
    video_url = _find_url(data, ("video", "video_url", "download_url", "play", "wmplay", "hdplay", "url", "data.video", "data.play"))
    cover_url = _find_url(data, ("cover", "thumbnail", "thumbnail_url", "origin_cover", "dynamic_cover", "data.cover"))
    title = _pick(data, "title", "desc", "description", "data.title", "data.desc", default="TikTok video")
    duration = _pick(data, "duration", "data.duration", default=10)
    width = _pick(data, "width", "data.width", default=1080)
    height = _pick(data, "height", "data.height", default=1920)
    return video_url, cover_url, title, duration, width, height


def _find_tiktok_com_url(obj):
    if isinstance(obj, str) and obj.startswith("http") and "tiktok.com" in obj:
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            res = _find_tiktok_com_url(v)
            if res:
                return res
    if isinstance(obj, list):
        for item in obj:
            res = _find_tiktok_com_url(item)
            if res:
                return res
    return ""


def _get_tiktok_share_url(item):
    # Try to extract video id and author name
    video_id = _pick(item, "id", "video_id", "aweme_id")
    author_id = _pick(item, "author.unique_id", "author.uniqueId", "author.nickname")
    if video_id and author_id:
        return f"https://www.tiktok.com/@{author_id}/video/{video_id}"
        
    # Check if there is an existing share_url or web_url
    for key in ("share_url", "web_url", "url", "link"):
        val = _pick(item, key)
        if isinstance(val, str) and "tiktok.com" in val:
            return val
            
    # Try finding any url containing tiktok.com in the object
    found = _find_tiktok_com_url(item)
    if found:
        return found
        
    # Extract from tikwm play url if possible
    play_url = _find_url(item, ("play", "wmplay", "hdplay", "url"))
    if play_url and "tikwm.com" in play_url:
        match = re.search(r'/play/(\d+)', play_url)
        if match and author_id:
            return f"https://www.tiktok.com/@{author_id}/video/{match.group(1)}"
            
    return play_url or "Không có link"



def _download_via_kairobot(link):
    data = _api_get("/tiktok/download", {"url": link})
    return _normalize_download(data)


def _download_via_tikwm(link):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://tikwm.com",
        "Referer": "https://tikwm.com/"
    }
    response = requests.post("https://tikwm.com/api/", headers=headers, data={"url": link, "hd": "1"}, timeout=30)
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0 or "data" not in data:
        raise RuntimeError("Không thể lấy được video từ link này.")
    item = data["data"]
    return (
        item.get("play") or item.get("hdplay") or item.get("wmplay"),
        item.get("cover") or item.get("origin_cover"),
        item.get("title") or "TikTok video",
        item.get("duration") or 10,
        item.get("width") or 1080,
        item.get("height") or 1920,
    )


def handle_tiktok_download(bot, message_object, author_id, thread_id, thread_type, message):
    link = _extract_link(message, message_object)
    if not link:
        _send_text(bot, thread_id, thread_type, "📌 Sử dụng: tiktok [link_tiktok]\nVí dụ: tiktok https://vt.tiktok.com/...", message_object)
        return
    if not link.startswith("https://"):
        _send_text(bot, thread_id, thread_type, "❌ Link TikTok phải bắt đầu bằng https://", message_object)
        return

    try:
        bot.sendReaction(message_object, "TBOT OK ✅", thread_id, thread_type)
    except Exception:
        pass

    # If user sent a direct mp4 play link instead of a tiktok page url
    if "tiktok.com" not in link and ("tikwm.com/video/media/play" in link or link.endswith(".mp4")):
        try:
            _send_text(bot, thread_id, thread_type, f"✅ Đang gửi video trực tiếp...\nLink: {link}", message_object)
            bot.sendRemoteVideo(
                videoUrl=link,
                thumbnailUrl="https://i.imgur.com/f3nK6z5.jpeg",
                duration=10000,
                thread_id=thread_id,
                thread_type=thread_type,
                width=1080,
                height=1920,
                message=Message(text=f"Tiêu đề: TikTok video\n🔗 Link: {link}")
            )
            try:
                bot.sendReaction(message_object, "TBOT OK ✅", thread_id, thread_type)
            except Exception:
                pass
            return
        except Exception as e:
            try:
                bot.sendReaction(message_object, "TBOT FAILED ❌", thread_id, thread_type)
            except Exception:
                pass
            _send_text(bot, thread_id, thread_type, f"❌ Lỗi khi gửi trực tiếp: {str(e)}", message_object)
            return

    try:
        try:
            video_url, cover_url, title, duration, width, height = _download_via_kairobot(link)
        except Exception as kai_error:
            print(f"[TikTok] KaiRobot download fallback: {kai_error}")
            video_url, cover_url, title, duration, width, height = _download_via_tikwm(link)

        if not video_url:
            _send_text(bot, thread_id, thread_type, "❌ Không thể lấy được video từ link này", message_object)
            return

        _send_text(bot, thread_id, thread_type, f"✅ Đang tải video TikTok...\nTiêu đề: {title}", message_object)
        bot.sendRemoteVideo(
            videoUrl=video_url,
            thumbnailUrl=cover_url or "https://i.imgur.com/f3nK6z5.jpeg",
            duration=int(float(duration or 10)) * 1000,
            thread_id=thread_id,
            thread_type=thread_type,
            width=int(float(width or 1080)),
            height=int(float(height or 1920)),
            message=Message(text=f"Tiêu đề: {title}")
        )
        try:
            bot.sendReaction(message_object, "TBOT OK ✅", thread_id, thread_type)
        except Exception:
            pass
    except Exception as e:
        try:
            bot.sendReaction(message_object, "TBOT FAILED ❌", thread_id, thread_type)
        except Exception:
            pass
        _send_text(bot, thread_id, thread_type, f"❌ Lỗi: {str(e)}", message_object)


def handle_tiktok_profile(bot, message_object, author_id, thread_id, thread_type, message):
    content = (message or "").strip().split(maxsplit=1)
    if len(content) < 2:
        _send_text(bot, thread_id, thread_type, "Vui lòng nhập một id tiktok cần lấy thông tin.\nVí dụ: in4tiktok .nguyenhung07", message_object)
        return
    username = content[1].strip().lstrip("@")
    try:
        data = _api_get("/tiktok/profile", {"username": username})
        profile = data.get("data", data) if isinstance(data, dict) else {}
        uid = _pick(profile, "id", "uid", "user.id", default="Không rõ")
        uname = _pick(profile, "username", "uniqueId", "unique_id", "user.uniqueId", default=username)
        name = _pick(profile, "nickname", "name", "user.nickname", default="Không rõ")
        bio = _pick(profile, "signature", "bio", "desc", "user.signature", default="Không có thông tin tiểu sử")
        avatar = _find_url(profile, ("avatarLarger", "avatar", "avatarMedium", "user.avatarLarger", "user.avatarThumb"))
        heart = _pick(profile, "heartCount", "stats.heartCount", "stats.diggCount", "heart", default=0)
        following = _pick(profile, "followingCount", "stats.followingCount", default=0)
        followers = _pick(profile, "followerCount", "stats.followerCount", default=0)
        videos = _pick(profile, "videoCount", "stats.videoCount", default=0)

        text = (
            f"• Tên: {name}\n"
            f"• Id TikTok: {uid}\n"
            f"• Username TikTok: {uname}\n"
            f"• Tiểu sử: {bio}\n"
            f"• Số follower: {_format_number(followers)}\n"
            f"• Đang follower: {_format_number(following)}\n"
            f"• Số video đã đăng: {_format_number(videos)}\n"
            f"• Tổng số tim TikTok: {_format_number(heart)}"
        )
        if avatar:
            path = os.path.join(tempfile.gettempdir(), f"txa_tiktok_{author_id}.jpeg")
            img = requests.get(avatar, timeout=15)
            img.raise_for_status()
            with open(path, "wb") as f:
                f.write(img.content)
            bot.sendLocalImage(path, message=Message(text=text), thread_id=thread_id, thread_type=thread_type, width=2500, height=2500)
            try:
                os.remove(path)
            except Exception:
                pass
        else:
            _send_text(bot, thread_id, thread_type, text, message_object)
    except Exception as e:
        _send_text(bot, thread_id, thread_type, f"Đã xảy ra lỗi: {str(e)}", message_object)


def handle_tiktok_search(bot, message_object, author_id, thread_id, thread_type, message):
    content = (message or "").strip().split(maxsplit=1)
    if len(content) < 2:
        _send_text(bot, thread_id, thread_type, "Bạn muốn tìm video tiktok?, vui lòng đề cập nội dung rõ ràng hơn để tìm kiếm✨", message_object)
        return
    keyword = content[1].strip()
    try:
        data = _api_get("/tiktok/search", {"keywords": keyword, "count": 10})
        videos = _as_list(data)
        if not videos:
            _send_text(bot, thread_id, thread_type, "Không tìm thấy video tiktok nào với từ khóa bạn yêu cầu.", message_object)
            return
        lines = [f"Tìm thấy {len(videos)} video tiktok với từ khóa `{keyword}`. Dưới đây là các video:", ""]
        for i, item in enumerate(videos[:10], 1):
            title = _pick(item, "title", "desc", "description", default="Không có tiêu đề")
            likes = _pick(item, "digg_count", "like_count", "stats.diggCount", "stats.likeCount", default=0)
            plays = _pick(item, "play_count", "playCount", "stats.playCount", default=0)
            author_name = _pick(item, "author.unique_id", "author.uniqueId", "author.nickname", default="Không có tác giả")
            link = _get_tiktok_share_url(item)
            lines.append(f"[ {i} ]. Tiêu đề: {title}")
            lines.append(f"   - Tác giả: {author_name}")
            lines.append(f"   - Lượt xem: {_format_number(plays)}")
            lines.append(f"   - Lượt thích: {_format_number(likes)}")
            lines.append(f"   - Link: {link}")
            lines.append("")
        text = "\n".join(lines)
        if len(text) > 2500:
            text = text[:2500] + "\n\n... (Bị cắt bớt do độ dài tin nhắn quá dài)"
        _send_text(bot, thread_id, thread_type, text, message_object)
    except Exception as e:
        _send_text(bot, thread_id, thread_type, f"Đã xảy ra lỗi: {str(e)}", message_object)


def txa_command(bot, message_object, author_id, thread_id, thread_type, message):
    cmd = ""
    if isinstance(message, str):
        prefix = getattr(bot, "prefix", ".")
        cmd = message[len(prefix):].split()[0].lower() if message.startswith(prefix) else message.split()[0].lower()

    if cmd in ("tiktokinfo", "in4tiktok"):
        handle_tiktok_profile(bot, message_object, author_id, thread_id, thread_type, message)
    elif cmd == "tiktoksearch":
        handle_tiktok_search(bot, message_object, author_id, thread_id, thread_type, message)
    else:
        handle_tiktok_download(bot, message_object, author_id, thread_id, thread_type, message)
