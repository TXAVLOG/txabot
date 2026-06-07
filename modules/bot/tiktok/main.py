import requests
import sys
import os
import tempfile
import re

# Thêm thư mục gốc vào sys.path để import được core.utils và zlapi models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from core.utils import send_msg, send_media
from zlapi.models import Message, ThreadType

txa = {
    "name": "TikTok Downloader",
    "desc": "Tải video TikTok không logo",
    "author": "TXA",
    "command": ["tiktok", "downtik", "tt"]
}

def txa_command(bot, message_object, author_id, thread_id, thread_type, message):
    try:
        video_link = None
        
        # Trường hợp 1: message là string (tin nhắn văn bản đơn giản)
        if isinstance(message, str):
            parts = message.strip().split(maxsplit=1)
            if len(parts) >= 2:
                video_link = parts[1].strip()
        
        # Trường hợp 2: message là đối tượng Message có href/params (tin nhắn rich media)
        content_obj = getattr(message_object, 'content', None)
        if content_obj:
            if not video_link and getattr(content_obj, 'href', None):
                video_link = content_obj.href
            if not video_link and getattr(content_obj, 'params', None):
                import json
                try:
                    params_dict = json.loads(content_obj.params)
                    if 'href' in params_dict:
                        video_link = params_dict['href']
                except:
                    pass
        
        if not video_link:
            send_msg(bot, thread_id, thread_type,
                f"📌 Sử dụng: tiktok [link_tiktok]\nVí dụ: tiktok https://vt.tiktok.com/...",
                reply_to=message_object)
            return
        
        if not video_link.startswith("https://"):
            send_msg(bot, thread_id, thread_type, "❌ Link TikTok phải bắt đầu bằng https://", reply_to=message_object)
            return
        
        # Gửi reaction 👍
        try:
            bot.sendReaction(message_object, "👍", thread_id, thread_type)
        except Exception as react_err:
            print(f"[TikTok] Lỗi gửi reaction: {react_err}")
        
        # Gọi API từ tikwm.com
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://tikwm.com",
            "Referer": "https://tikwm.com/"
        }
        
        # First get the token
        token_url = "https://tikwm.com/api/"
        token_data = {"url": video_link, "hd": "1"}
        response = requests.post(token_url, headers=headers, data=token_data, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != 0 or "data" not in data:
            send_msg(bot, thread_id, thread_type, "❌ Không thể lấy được video từ link này", reply_to=message_object)
            return
        
        video_url = data["data"].get("play")
        if not video_url:
            send_msg(bot, thread_id, thread_type, "❌ Không thể lấy được video từ link này", reply_to=message_object)
            return
            
        title = data["data"].get("title", "TikTok video")
        
        # Gửi thông báo và video
        send_msg(bot, thread_id, thread_type, f"✅ Đang tải video TikTok...\nTiêu đề: {title}", reply_to=message_object)
        
        cover_url = data["data"].get("cover") or "https://f66-zpg-r.zdn.vn/jxl/8107149848477004187/d08a4d364d8cf9d2a09d.jxl"
        duration = data["data"].get("duration") or 10
        width = data["data"].get("width") or 1080
        height = data["data"].get("height") or 1920
        
        bot.sendRemoteVideo(
            videoUrl=video_url,
            thumbnailUrl=cover_url,
            duration=int(duration) * 1000,
            thread_id=thread_id,
            thread_type=thread_type,
            width=int(width),
            height=int(height),
            message=Message(text=f"Tiêu đề: {title}")
        )
        
        # Gửi reaction ❤️ sau khi hoàn thành
        try:
            bot.sendReaction(message_object, "❤️", thread_id, thread_type)
        except Exception as react_err:
            print(f"[TikTok] Lỗi gửi reaction hoàn thành: {react_err}")
        
    except Exception as e:
        # Gửi reaction 😢 nếu lỗi
        try:
            bot.sendReaction(message_object, "😢", thread_id, thread_type)
        except Exception as react_err:
            print(f"[TikTok] Lỗi gửi reaction lỗi: {react_err}")
        send_msg(bot, thread_id, thread_type, f"❌ Lỗi: {str(e)}", reply_to=message_object)
