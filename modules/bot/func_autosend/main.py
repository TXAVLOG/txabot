from config import prefix
from datetime import datetime, timedelta
import os
import random
import threading
import time
from zlapi.models import *
import pytz
import requests
import json
from urllib.parse import urlparse
from PIL import Image
from core.bot_sys import get_user_name_by_id, read_settings, write_settings, is_admin, convert_to_m4a
from modules.utils.image_sender import ImageSender

# Danh sách thể loại nội dung
CONTENT_TYPES = {
    "image": {"type": "random_image", "desc": "Random ảnh"},
    "video": {"type": "random_video", "desc": "Random video"},
    "music": {"type": "music", "desc": "Random nhạc ZingMP3 BXH"},
    "remotevd": {"type": "remote_video", "desc": "Video Local"},
    "vdgirl": {"type": "video", "desc": "Video gái"},
    "vdcos": {"type": "video", "desc": "Video cosplay"},
    "vdanime": {"type": "video", "desc": "Video anime"},
    "girl": {"type": "image", "desc": "Ảnh gái"},
    "cosplay": {"type": "image", "desc": "Ảnh cosplay"},
    "anime": {"type": "image", "desc": "Ảnh anime"},
    "boy": {"type": "image", "desc": "Ảnh trai"},
    "girlsexy": {"type": "image", "desc": "Ảnh gái sexy"},
    "mixed": {"type": "mixed", "desc": "Trộn lẫn tất cả thể loại"},
}

ALLOWED_TYPES = ["image", "video", "music", "remotevd", "mixed"]

VIDEO_CONTENT_TYPES = [name for name, cfg in CONTENT_TYPES.items() if cfg["type"] == "video"]
IMAGE_CONTENT_TYPES = [name for name, cfg in CONTENT_TYPES.items() if cfg["type"] == "image"]
AUTOSEND_TYPE_ALIASES = {
    "anh": "image",
    "ảnh": "image",
    "photo": "image",
    "hinh": "image",
    "hình": "image",
    "vid": "video",
    "vd": "video",
    "nhac": "music",
    "nhạc": "music",
    "zing": "music",
    "mp3": "music",
}

DEFAULT_INTERVAL_MINUTES = 30
REMOTE_VIDEO_LIST_URL = "https://run.mocky.io/v3/c5d65f19-6369-46e9-9a73-68c2d312f1b8"
REMOTE_THUMB_LIST_URL = "https://run.mocky.io/v3/795d39c1-a370-44b8-a2dd-bfd88e41c348"
DEFAULT_VIDEO_THUMB_URL = "https://f66-zpg-r.zdn.vn/jxl/8107149848477004187/d08a4d364d8cf9d2a09d.jxl"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
}

# Greeting đa dạng hơn
time_greetings = {
    "01:00": [
        "🌙✨ Đêm khuya rồi, ngủ ngon nhé bạn!",
        "🌌💤 Một đêm thật yên bình, chúc bạn ngủ sâu giấc mơ đẹp!",
        "🌃❄️ Giờ này rồi, hãy nghỉ ngơi, chuẩn bị cho ngày mới!",
        "🌜🌠 Trăng dịu dàng, giấc mơ bay, ngủ thật ngon!",
        "✨🌙 Chúc bạn một đêm ngon giấc và mơ đẹp!",
        "🌌💫 Sao lung linh, đêm yên bình, ngủ ngon nha!",
        "🌃🌬️ Khuya tĩnh lặng, hãy thư giãn, nghỉ ngơi!",
        "🌙❄️ Đêm lạnh, chăn ấm, ngủ ngon bạn nhé!",
        "🌠✨ Một đêm thật đẹp, chúc bạn ngủ sâu giấc!",
        "🌜🌌 Đừng thức khuya quá, nghỉ ngơi thôi!"
    ],
    "02:30": [
        "🌙🌌 Đêm khuya, ngủ ngon nhé!",
        "🌃✨ Đêm tĩnh lặng, giấc mơ đẹp!",
        "🌜💤 Gió khuya ru, ngủ sâu giấc!",
        "🌠❄️ Đêm lạnh, chăn ấm, nghỉ ngơi!",
        "✨🌙 Chúc bạn ngủ ngon và mơ đẹp!",
        "🌌💫 Sao lấp lánh, đêm yên bình!",
        "🌃🌬️ Khuya yên bình, thư giãn nhé!",
        "🌙❄️ Đêm sâu thẳm, nghỉ ngơi thôi!"
    ],
    "04:00": [
        "🌃🌙 Đêm khuya, sắp bình minh rồi!",
        "🌜✨ 4 giờ sáng, chuẩn bị cho ngày mới!",
        "🌌💤 Đêm sắp qua, ngủ ngon nhé!",
        "🌠❄️ Bình minh sắp đến, nghỉ ngơi thêm chút!",
        "✨🌙 Đêm cuối, chuẩn bị tinh thần!",
        "🌃💫 Sao sắp tắt, bình minh sắp lên!"
    ],
    "05:30": [
        "🌅☀️ Bình minh đến rồi, chào ngày mới!",
        "☀️✨ Sáng tươi mới, một ngày tốt lành!",
        "🌞💫 5 rưỡi sáng, bắt đầu ngày mới nhé!",
        "🌻❀ Nắng ban mai, năng lượng đầy!",
        "✨🌅 Chúc bạn một ngày thật vui vẻ!",
        "☀️🌬️ Gió mát sáng, bắt đầu thôi!"
    ],
    "07:00": [
        "🌞☀️ Sáng rực rỡ, dậy thôi nào!",
        "☀️✨ 7 giờ sáng, chào buổi sáng!",
        "🌅💫 Một ngày mới, năng lượng mới!",
        "🌻❀ Nắng đẹp, một ngày tốt lành!",
        "✨🌞 Chúc bạn có một ngày hiệu quả!",
        "☀️🌬️ Gió mát, tinh thần sảng khoái!"
    ],
    "08:30": [
        "🌞☕ Sáng hiệu quả, làm việc thôi!",
        "☕✨ 8 rưỡi sáng, uống cafe và làm việc!",
        "🌻💫 Nắng ban mai, năng lượng đầy!",
        "✨🌞 Một buổi sáng thật năng động!",
        "☀️🌬️ Gió mát, làm việc hiệu quả!"
    ],
    "10:06": [
        "🌞⏰ 10 giờ sáng, tiếp tục làm việc!",
        "☀️✨ Nắng rực rỡ, cố lên nào!",
        "🌻💫 Sáng tươi mới, làm thật tốt!",
        "✨🌞 Giữ vững tinh thần nhé!",
        "☕❀ Uống thêm nước, làm việc tiếp!"
    ],
    "11:30": [
        "🌞🍽️ Gần trưa, chuẩn bị ăn nhé!",
        "☀️✨ 11 rưỡi sáng, nghỉ ngơi chút!",
        "🌻💤 Nắng ban trưa, thư giãn thôi!",
        "✨⏰ Trưa yên bình, ăn ngon miệng!",
        "☕❀ Giờ nghỉ trưa, thư giãn nhé!"
    ],
    "13:00": [
        "🌞⏰ 1 giờ chiều, làm việc tiếp!",
        "☀️✨ Nắng chiều, tinh thần sảng khoái!",
        "🌻💫 Chiều tươi mới, cố lên nào!",
        "✨🌞 Một buổi chiều thật hiệu quả!",
        "☕❀ Uống thêm nước, làm việc nhé!"
    ],
    "14:30": [
        "🌞🌻 Chiều lãng mạn, vui vẻ nào!",
        "☀️✨ 2 rưỡi chiều, thư giãn chút!",
        "🌅💫 Nắng chiều, năng lượng đầy!",
        "✨⏰ Chiều rực rỡ, vui vẻ nhé!",
        "☕❀ Gió chiều mát, thư giãn!"
    ],
    "16:00": [
        "🌅✨ Chiều dần trôi, thư giãn nào!",
        "☀️🌻 4 giờ chiều, nghỉ ngơi nhé!",
        "🌞💫 Nắng nhạt dần, thư giãn thôi!",
        "✨⏰ Chiều yên bình, vui vẻ nhé!",
        "☕❀ Giờ chiều, thư giãn chút!"
    ],
    "17:30": [
        "🌅🌞 Hoàng hôn đến, thư giãn nào!",
        "☀️✨ 5 rưỡi chiều, chuẩn bị về!",
        "🌻💤 Nắng chiều tà, thư giãn thôi!",
        "✨⏰ Hoàng hôn đẹp, vui vẻ nhé!",
        "☕❀ Giờ này, thư giãn rồi!"
    ],
    "19:00": [
        "🌙✨ Tối đến, ăn ngon miệng!",
        "🌌💤 7 giờ tối, nghỉ ngơi nhé!",
        "🌜❄️ Tối yên bình, thư giãn thôi!",
        "✨🍽️ Tối đẹp, ăn ngon miệng!",
        "☕🌙 Tối mát mẻ, thư giãn!"
    ],
    "20:30": [
        "🌙✨ Sắp ngủ, thư giãn nhé!",
        "🌌💤 8 rưỡi tối, nghỉ ngơi thôi!",
        "🌜❄️ Tối tĩnh lặng, thư giãn!",
        "✨⏰ Tối dịu dàng, thư giãn!",
        "☕🌙 Gió tối mát, thư giãn!"
    ],
    "22:06": [
        "🌙🌌 Đêm khuya, ngủ ngon nhé!",
        "🌃✨ 10 giờ tối, chuẩn bị ngủ!",
        "🌜💤 Giờ này rồi, ngủ thôi!",
        "✨⏰ Đêm yên bình, ngủ ngon!",
        "☕🌙 Đêm lạnh, ngủ sâu giấc!"
    ],
    "23:30": [
        "🌙✨ Khuya rồi, ngủ thôi!",
        "🌌💤 11 rưỡi tối, ngủ ngon!",
        "🌜❄️ Đêm tĩnh lặng, ngủ sâu!",
        "✨⏰ Giờ này, nghỉ ngơi!",
        "☕🌙 Đêm đẹp, ngủ ngon!"
    ],
    "00:00": [
        "🌙🌌 Nửa đêm, chúc bạn ngủ ngon!",
        "🌃✨ 12 giờ khuya, nghỉ ngơi!",
        "🌜💤 Đêm sâu, ngủ thật sâu!",
        "✨⏰ Nửa đêm, thư giãn!",
        "☕🌙 Đêm đẹp, mơ đẹp nhé!"
    ]
}

DEFAULT_SCHEDULE = [
    "00:00", "01:00", "02:30", "04:00", "05:30", "07:00", "08:30", "10:06",
    "11:30", "13:00", "14:30", "16:00", "17:30", "19:00", "20:30", "22:06", "23:30"
]

AUTOSEND_SCHEDULE = time_greetings


def time_str_to_minutes(time_str):
    hour, minute = map(int, time_str.split(":"))
    return hour * 60 + minute


TIME_GREETING_SLOTS = sorted(
    [(time_str_to_minutes(slot), slot, pool) for slot, pool in time_greetings.items()],
    key=lambda entry: entry[0]
)


def get_greeting_slot_for(minutes):
    if not TIME_GREETING_SLOTS:
        return (None, [])

    for slot_minutes, slot_label, pool in reversed(TIME_GREETING_SLOTS):
        if minutes >= slot_minutes:
            return (slot_label, pool)

    last_slot = TIME_GREETING_SLOTS[-1]
    return (last_slot[1], last_slot[2])

vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
image_sender = ImageSender()

def get_or_init_group_schedule_in_dict(settings, thread_id, uid):
    dirty = False
    if "autosend_schedule" not in settings:
        settings["autosend_schedule"] = {}
        dirty = True
    if thread_id not in settings["autosend_schedule"]:
        settings["autosend_schedule"][thread_id] = DEFAULT_SCHEDULE.copy()
        dirty = True
    if dirty:
        write_settings(uid, settings)
    return settings["autosend_schedule"][thread_id]

def get_content_type_setting(bot, thread_id):
    settings = read_settings(bot.uid)
    if "autosend_content" not in settings:
        settings["autosend_content"] = {}
    return settings["autosend_content"].get(thread_id, "vdgirl")

def set_content_type_setting(bot, thread_id, content_type):
    settings = read_settings(bot.uid)
    if "autosend_content" not in settings:
        settings["autosend_content"] = {}
    settings["autosend_content"][thread_id] = content_type
    write_settings(bot.uid, settings)

def handle_autosend_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "autosend" not in settings:
        settings["autosend"] = {}
    settings["autosend"][thread_id] = True
    allowed_thread_ids = settings.get("allowed_thread_ids", [])
    if thread_id not in allowed_thread_ids:
        allowed_thread_ids.append(thread_id)
        settings["allowed_thread_ids"] = allowed_thread_ids
    
    get_or_init_group_schedule_in_dict(settings, thread_id, bot.uid)
    write_settings(bot.uid, settings)
    
    content_type = get_content_type_setting(bot, thread_id)
    content_desc = CONTENT_TYPES[content_type]["desc"]
    
    return (
        f"🚦 Lệnh {prefix}autosend đã được Bật 🚀 trong nhóm này ✅\n"
        f"📂 Thể loại nội dung hiện tại: {content_desc}\n"
        f"⏰ Bot sẽ gửi đúng các khung giờ đã cấu hình.\n"
        f"💡 Dùng {prefix}autosend type image|video|music để chọn nội dung!"
    )

def handle_autosend_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "autosend" in settings and thread_id in settings["autosend"]:
        settings["autosend"][thread_id] = False
        write_settings(bot.uid, settings)
        return f"🚦 Lệnh {prefix}autosend đã Tắt ⭕️ trong nhóm này ✅"
    return "🚦 Nhóm chưa có thông tin cấu hình autosend để ⭕️ Tắt 🤗"

def handle_autosend_type(bot, thread_id, content_type):
    content_type = normalize_content_type(content_type)
    if content_type not in ALLOWED_TYPES:
        type_list = "\n".join([f"• {k}: {CONTENT_TYPES[k]['desc']}" for k in ALLOWED_TYPES])
        return (
            f"❌ Thể loại '{content_type}' không hợp lệ!\n"
            f"📋 Danh sách thể loại hỗ trợ:\n{type_list}"
        )
    
    set_content_type_setting(bot, thread_id, content_type)
    content_desc = CONTENT_TYPES[content_type]["desc"]
    return f"✅ Đã đổi thể loại nội dung autosend thành: {content_desc}!"

def get_autosend_interval(bot, thread_id):
    settings = read_settings(bot.uid)
    intervals = settings.get("autosend_interval", {})
    try:
        interval = int(intervals.get(thread_id, DEFAULT_INTERVAL_MINUTES))
    except (TypeError, ValueError):
        interval = DEFAULT_INTERVAL_MINUTES
    return max(1, interval)

def set_autosend_interval(bot, thread_id, minutes):
    settings = read_settings(bot.uid)
    settings.setdefault("autosend_interval", {})
    settings["autosend_interval"][thread_id] = max(1, int(minutes))
    write_settings(bot.uid, settings)
    return f"✅ Đã đổi chu kỳ autosend thành {max(1, int(minutes))} phút!"

def get_random_content_type():
    types = ["image", "video", "music"]
    return random.choice(types)

def normalize_content_type(content_type):
    return AUTOSEND_TYPE_ALIASES.get(content_type, content_type)

def normalize_url(raw_url):
    if raw_url is None:
        return ""
    url = str(raw_url).strip().strip('"').strip("'").strip()
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("www."):
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return url

def extract_urls(data):
    urls = []
    if isinstance(data, str):
        url = normalize_url(data)
        if url:
            urls.append(url)
    elif isinstance(data, list):
        for item in data:
            urls.extend(extract_urls(item))
    elif isinstance(data, dict):
        for key in ("url", "href", "link", "video", "videoUrl", "video_url", "thumb", "thumbnail", "thumbnailUrl"):
            if key in data:
                urls.extend(extract_urls(data[key]))
        for key in ("data", "items", "videos", "results"):
            if key in data:
                urls.extend(extract_urls(data[key]))
    return list(dict.fromkeys(urls))

def read_url_file(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return [url for url in (normalize_url(line) for line in f) if url]

def get_json_with_ssl_fallback(url):
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=12)
    except requests.exceptions.SSLError as ssl_error:
        print(f"⚠️ SSL verify lỗi khi tải remote list, thử lại verify=False: {ssl_error}")
        requests.packages.urllib3.disable_warnings()
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=12, verify=False)
    response.raise_for_status()
    return response.json()

def url_is_reachable(url):
    try:
        response = requests.head(url, headers=REQUEST_HEADERS, timeout=5, allow_redirects=True)
        if 200 <= response.status_code < 400:
            return True
        if response.status_code in (401, 403, 405):
            return True
    except requests.RequestException:
        pass

    try:
        headers = dict(REQUEST_HEADERS)
        headers["Range"] = "bytes=0-0"
        response = requests.get(url, headers=headers, timeout=7, stream=True, allow_redirects=True)
        try:
            if 200 <= response.status_code < 400 or response.status_code in (401, 403):
                return True
            return False
        finally:
            response.close()
    except requests.RequestException:
        return True

def choose_reachable_url(urls):
    candidates = [url for url in urls if normalize_url(url)]
    random.shuffle(candidates)
    for url in candidates:
        if url_is_reachable(url):
            return url
    return candidates[0] if candidates else ""

def send_fallback_video_content(bot, thread_id, message, excluded_type=None):
    fallback_types = [t for t in VIDEO_CONTENT_TYPES if t != excluded_type]
    random.shuffle(fallback_types)
    for fallback_type in fallback_types:
        print(f"⏩ Thử fallback autosend video '{fallback_type}'.")
        if send_content(bot, thread_id, fallback_type, message, allow_fallback=False):
            return True
    return False

def send_chart_music_content(bot, thread_id, message):
    try:
        from modules.music.nhac_zingmp3.main import (
            request_zing,
            create_single_song_image,
            upload_to_uguu,
            delete_file,
            CACHE_PATH,
        )
    except Exception as e:
        print(f"❌ Không import được module ZingMP3: {e}")
        return False

    chart_res = request_zing("/api/v2/page/get/chart-home")
    items = (((chart_res or {}).get("data") or {}).get("RTChart") or {}).get("items", [])[:10]
    if not items:
        print("❌ BXH ZingMP3 rỗng hoặc không lấy được.")
        return False

    random.shuffle(items)
    for item in items:
        encode_id = item.get("encodeId")
        if not encode_id:
            continue

        stream_res = request_zing("/api/v2/song/get/streaming", {"id": encode_id})
        stream_data = (stream_res or {}).get("data") or {}
        stream_url = stream_data.get("128") or stream_data.get("320")
        if not stream_url or stream_url == "VIP":
            continue

        song = (
            encode_id,
            item.get("title", "Unknown"),
            item.get("thumbnailM") or item.get("thumbnail", ""),
            item.get("listen", 0),
            item.get("like", 0),
            0,
            item.get("artistsNames", "Unknown Artist"),
        )
        song_image_path = create_single_song_image(song)
        temp_file = os.path.join(CACHE_PATH, f"autosend_{encode_id}.mp3")

        try:
            audio = requests.get(stream_url, headers=REQUEST_HEADERS, timeout=20)
            audio.raise_for_status()
            with open(temp_file, "wb") as f:
                f.write(audio.content)


            m4a_file = convert_to_m4a(temp_file)
            upload_url = upload_to_uguu(m4a_file)
            if m4a_file != temp_file:
                delete_file(m4a_file)

            if not upload_url:
                continue

            caption = message
            if song_image_path and os.path.exists(song_image_path):
                with Image.open(song_image_path) as img:
                    width, height = img.size
                bot.sendLocalImage(
                    song_image_path,
                    thread_id=thread_id,
                    thread_type=ThreadType.GROUP,
                    width=width,
                    height=height,
                    message=Message(text=caption),
                    ttl=600000,
                )
            else:
                bot.send(Message(text=caption), thread_id, ThreadType.GROUP, ttl=600000)

            bot.sendRemoteVoice(
                voiceUrl=upload_url,
                thread_id=thread_id,
                thread_type=ThreadType.GROUP,
                ttl=600000,
            )
            return True
        except Exception as e:
            print(f"❌ Gửi autosend music lỗi với {encode_id}: {e}")
        finally:
            delete_file(temp_file)
            if song_image_path:
                delete_file(song_image_path)

    return False

def send_content(bot, thread_id, content_type, message, allow_fallback=True):
    try:
        content_type = normalize_content_type(content_type)
        config = CONTENT_TYPES[content_type]
        
        if config["type"] == "remote_video":
            try:
                video_urls = extract_urls(get_json_with_ssl_fallback(REMOTE_VIDEO_LIST_URL))
                if not video_urls:
                    raise ValueError("Danh sách video trống")

                try:
                    thumb_urls = extract_urls(get_json_with_ssl_fallback(REMOTE_THUMB_LIST_URL))
                except Exception as thumb_error:
                    print(f"⚠️ Không tải được thumbnail remote, dùng thumb mặc định: {thumb_error}")
                    thumb_urls = []
                thumbnail_url = choose_reachable_url(thumb_urls) or DEFAULT_VIDEO_THUMB_URL
                video_url = choose_reachable_url(video_urls)
                if not video_url:
                    raise ValueError("Không tìm thấy video URL hợp lệ")

                bot.sendRemoteVideo(
                    video_url,
                    thumbnail_url,
                    duration='1000',
                    message=Message(text=message) if message else None,
                    thread_id=thread_id,
                    thread_type=ThreadType.GROUP,
                    width=1080,
                    height=1920,
                    ttl=3600000
                )
                return True
            except Exception as e:
                print(f"❌ Không tải được video remote ({type(e).__name__}): {e}")
                if allow_fallback:
                    set_content_type_setting(bot, thread_id, "vdgirl")
                    print("⏩ Nguồn remotevd lỗi, đã chuyển cấu hình autosend của nhóm sang 'vdgirl'.")
                return send_fallback_video_content(bot, thread_id, message) if allow_fallback else False

        if config["type"] == "video":
            data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data-send")
            video_file = os.path.join(data_dir, f"{content_type}.txt")
            urls = read_url_file(video_file)
            if urls:
                video_url = choose_reachable_url(urls)
                if not video_url:
                    print(f"❌ Không tìm thấy URL video hợp lệ trong {video_file}")
                    return send_fallback_video_content(bot, thread_id, message, excluded_type=content_type) if allow_fallback else False
                    
                bot.sendRemoteVideo(
                    video_url,
                    DEFAULT_VIDEO_THUMB_URL,
                    duration='1000000',
                    message=Message(text=message),
                    thread_id=thread_id,
                    thread_type=ThreadType.GROUP,
                    width=1080,
                    height=1920,
                    ttl=3600000
                )
                return True
            print(f"❌ File video trống hoặc không có URL hợp lệ: {video_file}")
            return send_fallback_video_content(bot, thread_id, message, excluded_type=content_type) if allow_fallback else False
        
        elif config["type"] == "random_video":
            return send_content(bot, thread_id, random.choice(VIDEO_CONTENT_TYPES), message, allow_fallback=allow_fallback)

        elif config["type"] == "image":
            error = image_sender.send_image(
                bot=bot,
                thread_id=thread_id,
                thread_type=ThreadType.GROUP,
                type_name=content_type,
                custom_caption=message
            )
            return error is None

        elif config["type"] == "random_image":
            return send_content(bot, thread_id, random.choice(IMAGE_CONTENT_TYPES), message, allow_fallback=allow_fallback)

        elif config["type"] == "music":
            return send_chart_music_content(bot, thread_id, message)
        
        elif config["type"] == "mixed":
            random_type = get_random_content_type()
            return send_content(bot, thread_id, random_type, message, allow_fallback=allow_fallback)
    
    except Exception as e:
        print(f"❌ Lỗi khi gửi nội dung: {e}")
    
    return False

def autosend_task(client):
    sent_slots = set()
    
    while True:
        try:
            settings = read_settings(client.uid)
            if not settings.get("autosend"):
                time.sleep(30)
                continue
                
            now = datetime.now(vn_tz)
            current_time_str = now.strftime("%H:%M")
            allowed_groups = settings.get("allowed_thread_ids", [])
            
            # Build set of all active schedule hours across all enabled groups
            active_schedules = set()
            for thread_id, enabled in settings.get("autosend", {}).items():
                if enabled and thread_id in allowed_groups:
                    group_sched = get_or_init_group_schedule_in_dict(settings, thread_id, client.uid)
                    active_schedules.update(group_sched)
            
            if current_time_str not in active_schedules:
                time.sleep(30)
                continue

            bot_name = get_user_name_by_id(client, client.uid)

            for thread_id, enabled in settings.get("autosend", {}).items():
                if not enabled or thread_id not in allowed_groups:
                    continue

                group_sched = get_or_init_group_schedule_in_dict(settings, thread_id, client.uid)
                if current_time_str not in group_sched:
                    continue

                sent_key = (thread_id, now.strftime("%Y-%m-%d"), current_time_str)
                if sent_key in sent_slots:
                    continue

                # Choose greeting pool using closest preceding slot
                minutes = time_str_to_minutes(current_time_str)
                slot_label, greeting_pool = get_greeting_slot_for(minutes)
                if not greeting_pool:
                    greeting_pool = ["Chúc bạn một ngày vui vẻ và tràn đầy năng lượng!"]
                greeting = random.choice(greeting_pool)

                print(f"🕒 Autosend đến đúng khung giờ: {current_time_str} cho nhóm {thread_id}")
                formatted_message = f"> Send task ({current_time_str}) <\n\n{greeting}\n\nSend by (@{bot_name} - TXA Bot ✨)"

                content_type = get_content_type_setting(client, thread_id)
                success = send_content(client, thread_id, content_type, formatted_message)
                if success:
                    sent_slots.add(sent_key)
                    print(f"✅ Đã gửi nội dung đến {thread_id} (type: {content_type}, slot: {current_time_str})")
                time.sleep(0.3)
                            
        except Exception as e:
            print(f"❌ Lỗi trong autosend_task: {e}")
            
        time.sleep(30)

def start_autosend_thread(client):
    if not hasattr(client, 'autosend_thread') or not client.autosend_thread.is_alive():
        client.autosend_thread = threading.Thread(target=autosend_task, args=(client,), daemon=True)
        client.autosend_thread.start()

def start_autosend_handle(client, thread_type, message_object, message, thread_id, author_id):
    parts = message.strip().lower().split()
    if parts and parts[0] in (f"{prefix}autosend", "autosend"):
        parts = parts[1:]
    
    if len(parts) == 0:
        response = (
            f"📋 Hướng dẫn sử dụng {prefix}autosend:\n"
            f"• {prefix}autosend on: Bật tính năng\n"
            f"• {prefix}autosend off: Tắt tính năng\n"
            f"• {prefix}autosend <thể_loại>: Đổi sang thể loại gửi (ví dụ: {prefix}autosend mixed)\n"
            f"• {prefix}autosend addtime <giờ1> <giờ2>...: Thêm khung giờ gửi\n"
            f"• {prefix}autosend deltime <giờ1> <giờ2>...: Xóa khung giờ gửi\n"
            f"• {prefix}autosend now: Gửi thử ngay\n"
            f"• {prefix}autosend list: Xem cấu hình nhóm, thể loại và khung giờ"
        )
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        return
    
    action = parts[0]
    normalized_action = normalize_content_type(action)
    
    if action == "on":
        if not is_admin(client, author_id):
            client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        response = handle_autosend_on(client, thread_id)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        start_autosend_thread(client)
            
    elif action == "off":
        if not is_admin(client, author_id):
            client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        response = handle_autosend_off(client, thread_id)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
    
    elif action == "type" and len(parts) >= 2:
        if not is_admin(client, author_id):
            client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        content_type = parts[1]
        response = handle_autosend_type(client, thread_id, content_type)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)

    elif action in ("addtime", "deltime") and len(parts) >= 2:
        if not is_admin(client, author_id):
            client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
            
        time_args = " ".join(parts[1:])
        import re
        time_tokens = re.split(r'[\s,]+', time_args)
        time_tokens = [t.strip() for t in time_tokens if t.strip()]
        
        valid_times = []
        invalid_times = []
        for token in time_tokens:
            match = re.match(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$', token)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))
                valid_times.append(f"{hour:02d}:{minute:02d}")
            else:
                invalid_times.append(token)
                
        if invalid_times:
            client.replyMessage(Message(text=f"❌ Khung giờ không hợp lệ: {', '.join(invalid_times)}\nVui lòng nhập đúng định dạng HH:MM (ví dụ: 12:00, 08:30)"), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
            
        if not valid_times:
            client.replyMessage(Message(text="❌ Vui lòng cung cấp ít nhất một khung giờ gửi!"), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
            
        settings = read_settings(client.uid)
        group_sched = get_or_init_group_schedule_in_dict(settings, thread_id, client.uid)
        
        if action == "addtime":
            added = []
            already_exists = []
            for t in valid_times:
                if t not in group_sched:
                    group_sched.append(t)
                    added.append(t)
                else:
                    already_exists.append(t)
            group_sched.sort()
            settings.setdefault("autosend_schedule", {})[thread_id] = group_sched
            write_settings(client.uid, settings)
            
            msg = ""
            if added:
                msg += f"✅ Đã thêm khung giờ gửi: {', '.join(added)}\n"
            if already_exists:
                msg += f"⚠️ Khung giờ đã tồn tại trước đó: {', '.join(already_exists)}\n"
            msg += f"⏰ Danh sách khung giờ hiện tại: {', '.join(group_sched)}"
            client.replyMessage(Message(text=msg), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            
        else:  # deltime
            removed = []
            not_found = []
            for t in valid_times:
                if t in group_sched:
                    group_sched.remove(t)
                    removed.append(t)
                else:
                    not_found.append(t)
            group_sched.sort()
            settings.setdefault("autosend_schedule", {})[thread_id] = group_sched
            write_settings(client.uid, settings)
            
            msg = ""
            if removed:
                msg += f"✅ Đã xóa khung giờ gửi: {', '.join(removed)}\n"
            if not_found:
                msg += f"⚠️ Khung giờ không có trong danh sách: {', '.join(not_found)}\n"
            msg += f"⏰ Danh sách khung giờ hiện tại: {', '.join(group_sched)}"
            client.replyMessage(Message(text=msg), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)

    elif action == "interval" and len(parts) >= 2:
        if not is_admin(client, author_id):
            client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        response = "⚠️ Autosend hiện gửi theo khung giờ cố định, không dùng interval nữa."
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)

    elif action == "now":
        if not is_admin(client, author_id):
            client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        content_type = get_content_type_setting(client, thread_id)
        bot_name = get_user_name_by_id(client, client.uid)
        
        current_time_str = datetime.now(vn_tz).strftime("%H:%M")
        minutes = time_str_to_minutes(current_time_str)
        slot_label, greeting_pool = get_greeting_slot_for(minutes)
        if not greeting_pool:
            greeting_pool = ["Chúc bạn một ngày vui vẻ và tràn đầy năng lượng!"]
        greeting = random.choice(greeting_pool)
        
        message_now = f"> Send task ({current_time_str}) <\n\n{greeting}\n\nSend by (@{bot_name} - TXA Bot ✨)"
        success = send_content(client, thread_id, content_type, message_now)
        response = "✅ Đã gửi thử autosend!" if success else "❌ Không gửi thử được autosend, kiểm tra nguồn media/type."
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
    
    elif action == "list":
        settings = read_settings(client.uid)
        autosend_enabled = settings.get("autosend", {}).get(thread_id, False)
        status_str = "Đang bật ✅" if autosend_enabled else "Đang tắt ❌"
        
        current_type = get_content_type_setting(client, thread_id)
        current_desc = CONTENT_TYPES.get(current_type, {}).get("desc", "Không rõ")
        
        group_sched = get_or_init_group_schedule_in_dict(settings, thread_id, client.uid)
        slot_list = ", ".join(sorted(group_sched))
        
        categories_str = "\n".join([f"• {k}: {CONTENT_TYPES[k]['desc']}" for k in ALLOWED_TYPES])
        
        response = (
            f"⚙️ CẤU HÌNH AUTOSEND CỦA NHÓM:\n"
            f"• Trạng thái: {status_str}\n"
            f"• Thể loại gửi hiện tại: {current_type} ({current_desc})\n\n"
            f"⏰ Khung giờ gửi ({len(group_sched)}):\n{slot_list}\n\n"
            f"📋 Danh sách thể loại nội dung hỗ trợ:\n{categories_str}\n\n"
            f"💡 Hướng dẫn Admin:\n"
            f"• {prefix}autosend <thể_loại>: Đổi thể loại gửi\n"
            f"• {prefix}autosend addtime <giờ1> <giờ2>...: Thêm khung giờ\n"
            f"• {prefix}autosend deltime <giờ1> <giờ2>...: Xóa khung giờ"
        )
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        
    elif normalized_action in ALLOWED_TYPES:
        if not is_admin(client, author_id):
            client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        response = handle_autosend_type(client, thread_id, normalized_action)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
    
    else:
        response = (
            f"📋 Hướng dẫn sử dụng {prefix}autosend:\n"
            f"• {prefix}autosend on: Bật tính năng\n"
            f"• {prefix}autosend off: Tắt tính năng\n"
            f"• {prefix}autosend <image|video|music|remotevd|mixed>: Đổi sang thể loại gửi (ví dụ: {prefix}autosend mixed)\n"
            f"• {prefix}autosend addtime <giờ1> <giờ2>...: Thêm khung giờ gửi\n"
            f"• {prefix}autosend deltime <giờ1> <giờ2>...: Xóa khung giờ gửi\n"
            f"• {prefix}autosend now: Gửi thử ngay\n"
            f"• {prefix}autosend list: Xem cấu hình nhóm, thể loại và khung giờ"
        )
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)

txa = {
    "name": "pro_autosend",
    "desc": "Gửi tin nhắn tự động theo lịch trình. Hỗ trợ nhiều thể loại nội dung.",
    "author": "TXA",
    "command": ['autosend']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'autosend': start_autosend_handle
    }
    
    func = dispatch_map.get(cmd)
    if func:
        import inspect
        sig = inspect.signature(func)
        args_map = {
            'bot': bot,
            'client': bot,
            'message_object': message_object,
            'thread_id': thread_id,
            'thread_type': thread_type,
            'author_id': author_id,
            'message': message_text,
            'message_text': message_text,
            'message_lower': message_text.lower()
        }
        args = []
        for param_name in sig.parameters:
            if param_name in args_map:
                args.append(args_map[param_name])
            else:
                args.append(None)
        func(*args)
