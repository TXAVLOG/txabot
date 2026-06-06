import requests
import sys
import os
import tempfile

# Thêm thư mục gốc vào sys.path để import được core.utils và zlapi models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from core.utils import send_msg, send_media
from zlapi.models import Message, ThreadType

MODULE_NAME = "tiktok"
COMMAND_PREFIX = "tiktok"
DESCRIPTION = "Tải video TikTok không logo"

def handle_command(client, message, message_object, thread_id, thread_type, author_id, mentions):
    try:
        # Phân tích lệnh: tiktok [link]
        parts = message.strip().split(maxsplit=1)
        if len(parts) < 2:
            send_msg(client, thread_id, thread_type,
                f"📌 Sử dụng: {COMMAND_PREFIX} [link_tiktok]\nVí dụ: {COMMAND_PREFIX} https://vt.tiktok.com/...",
                reply_to=message_object)
            return
        
        video_link = parts[1].strip()
        
        if not video_link.startswith("https://"):
            send_msg(client, thread_id, thread_type, "❌ Link TikTok phải bắt đầu bằng https://", reply_to=message_object)
            return
        
        # Gọi API lấy video
        api_url = f"https://api.sumiproject.net/tiktok?video={video_link}"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_8_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6.6 Mobile/15E148 Safari/604.1"
        }
        
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if "data" not in data or "play" not in data["data"]:
            send_msg(client, thread_id, thread_type, "❌ Không thể lấy được video từ link này", reply_to=message_object)
            return
        
        video_url = data["data"]["play"]
        title = data["data"].get("title", "TikTok video")
        
        # Gửi thông báo và video
        send_msg(client, thread_id, thread_type, f"✅ Đang tải video TikTok...\nTiêu đề: {title}", reply_to=message_object)
        
        # Gửi video (tải xuống rồi gửi vì sendRemoteVideo có thể không ổn định)
        import tempfile
        video_path = tempfile.mktemp(suffix=".mp4")
        r = requests.get(video_url, headers=headers, timeout=60)
        r.raise_for_status()
        with open(video_path, "wb") as f:
            f.write(r.content)
        send_media(client, thread_id, thread_type, video_path, type="video")
        os.remove(video_path)
        
    except Exception as e:
        send_msg(client, thread_id, thread_type, f"❌ Lỗi: {str(e)}", reply_to=message_object)
