# -*- coding: utf-8 -*-
import os
import re
import requests
from datetime import datetime
from zlapi.models import Message, MultiMsgStyle, MessageStyle

txa = {
    "name": "capweb",
    "desc": {
        "capweb": "Chụp ảnh màn hình website"
    },
    "author": "Yuta Bot",
    "command": ["capweb"],
    "t-per": "all"
}

FONT_SIZE = "9"
CACHE_DIR = "modules/cache/capweb"
os.makedirs(CACHE_DIR, exist_ok=True)

def _sty(text, color="#e8eaf6"):
    h = len(text.split("\n")[0]) + 1
    return MultiMsgStyle([
        MessageStyle(offset=0, length=len(text), style="font", size=FONT_SIZE, auto_format=False),
        MessageStyle(offset=0, length=h, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=h, style="bold", auto_format=False),
    ])

def is_valid_url(url):
    pattern = re.compile(
        r'^https?://' 
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return pattern.match(url) is not None

def capture_screenshot(url, output_path):
    try:
        apis = [
            f"https://image.thum.io/get/width/1280/crop/800/noanimate/{url}",
            f"https://mini.s-shot.ru/1280x720/JPEG/?{url}",
            f"https://www.pagepeeker.com/v1/thumbs.php?size=m&url={url}",
        ]
        
        for api_url in apis:
            try:
                print(f"[CAPWEB] Thử API: {api_url[:50]}...")
                response = requests.get(api_url, timeout=30)
                if response.status_code == 200 and len(response.content) > 5000:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    print(f"[CAPWEB] Thành công! Size: {len(response.content)} bytes")
                    return True
            except Exception as e:
                print(f"[CAPWEB] API lỗi: {e}")
                continue
        return False
    except Exception as e:
        print(f"[CAPWEB] Lỗi: {e}")
        return False

def txa_command(client, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(client, "prefix", ".")
    parts = message_text.strip().split(None, 1)
    
    if len(parts) < 2:
        help_text = f"""
📸 CHỤP ẢNH MÀN HÌNH WEBSITE

Cách dùng: {prefix}capweb <url>

Ví dụ:
{prefix}capweb google.com
{prefix}capweb facebook.com
{prefix}capweb youtube.com

⚠️ Có thể mất 10-20 giây để xử lý
        """
        client.replyMessage(
            Message(text=help_text.strip(), style=_sty(help_text, "#00BFFF")),
            message_object, thread_id, thread_type, ttl=60000
        )
        return
        
    content = parts[1].strip()
    url = content
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    if not is_valid_url(url):
        client.replyMessage(
            Message(text="❌ URL không hợp lệ!\nVD: google.com", style=_sty("❌ URL không hợp lệ!", "#DB342E")),
            message_object, thread_id, thread_type, ttl=30000
        )
        return

    client.replyMessage(
        Message(text=f"📸 Đang chụp ảnh {url}...\n⏱️ Có thể mất 10-20 giây", style=_sty(f"📸 Đang chụp...", "#F7B503")),
        message_object, thread_id, thread_type, ttl=20000
    )
    
    filename = f"screenshot_{int(datetime.now().timestamp())}.jpg"
    filepath = os.path.join(CACHE_DIR, filename)
    
    try:
        success = capture_screenshot(url, filepath)
        if not success or not os.path.exists(filepath) or os.path.getsize(filepath) < 5000:
            raise Exception("Không thể chụp ảnh website này")
            
        client.sendLocalImage(
            filepath,
            thread_id=thread_id,
            thread_type=thread_type,
            message=Message(text=f"📸 Ảnh chụp: {url}"),
            ttl=120000
        )
    except Exception as e:
        client.replyMessage(
            Message(text=f"❌ Lỗi: {str(e)[:100]}\n💡 Thử website khác hoặc kiểm tra URL", style=_sty("❌ Lỗi!", "#DB342E")),
            message_object, thread_id, thread_type, ttl=30000
        )
    finally:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
