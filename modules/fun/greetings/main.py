# -*- coding: UTF-8 -*-
"""
Module: greetings.py
Lệnh: welcome2, goodbye2, chao2, tambiet2
- welcome2 avatar=<url> username=<name> bg=<url> groupname=<name> member=<number> → Tạo ảnh chào mừng V2
- goodbye2 avatar=<url> username=<name> bg=<url> groupname=<name> member=<number> → Tạo ảnh tạm biệt V2
"""

import os
import sys
import requests
import re
import tempfile
from PIL import Image
from zlapi.models import Message

sys.dont_write_bytecode = True

# ─── METADATA ─────────────────────────────────────────────────────────────────
txa = {
    "name": "Greetings Card Generator V2",
    "desc": {
        "welcome2": "Tạo ảnh chào mừng thành viên mới V2",
        "goodbye2": "Tạo ảnh tạm biệt thành viên V2",
        "chao2": "Tạo ảnh chào mừng V2",
        "tambiet2": "Tạo ảnh tạm biệt V2"
    },
    "author": "TXA",
    "command": ["welcome2", "goodbye2", "chao2", "tambiet2"]
}

# ─── CONFIG ───────────────────────────────────────────────────────────────────
API_BASE = "https://apiwebfree.lovable.app/api/greetings2"

# Mặc định tham số theo yêu cầu
DEFAULT_AVATAR = "https://upload.satoru.click/files/fa5173.jpg"
DEFAULT_USERNAME = "Satoru"
DEFAULT_BG = "https://upload.satoru.click/files/4ff52a.jpg"
DEFAULT_GROUPNAME = "Satoru HQ"
DEFAULT_MEMBER = "57"

# ─── API CALLS ────────────────────────────────────────────────────────────────

def _generate_greeting_card(greeting_type, avatar, username, bg, groupname, member):
    """
    Tạo ảnh greeting card qua API.
    greeting_type: 'welcome' hoặc 'goodbye'
    """
    url = API_BASE
    params = {
        "type": greeting_type,
        "avatar": avatar,
        "username": username,
        "bg": bg,
        "groupname": groupname,
        "member": str(member)
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '')
        if 'image' in content_type:
            return response.content, None
        else:
            try:
                json_data = response.json()
                return None, json_data
            except:
                return None, {"error": "Phản hồi không hợp lệ từ API"}
    except Exception as e:
        return None, {"error": str(e)}

# ─── COMMAND HANDLER ──────────────────────────────────────────────────────────

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    parts = message_text.strip().split(None, 1)
    cmd = parts[0].lstrip(prefix).lower() if parts else ""
    arg_text = parts[1].strip() if len(parts) > 1 else ""
    
    # Xác định loại greeting
    if cmd in ["welcome2", "chao2"]:
        greeting_type = "welcome"
    elif cmd in ["goodbye2", "tambiet2"]:
        greeting_type = "goodbye"
    else:
        greeting_type = "welcome"
        
    args = {}
    
    if arg_text:
        # 1. Phân tích dạng đặt tên key=value bằng regex (hỗ trợ khoảng trắng trong value)
        if "=" in arg_text:
            pattern = r'(avatar|username|bg|groupname|member)\s*=\s*(.*?)(?=\s*(?:avatar|username|bg|groupname|member)\s*=|$)'
            matches = re.findall(pattern, arg_text, re.IGNORECASE)
            for k, v in matches:
                args[k.lower().strip()] = v.strip()
                
        # 2. Nếu không tìm thấy bằng regex, thử phân tích dạng vị trí phân tách bằng "|"
        if not args and "|" in arg_text:
            sub_parts = [p.strip() for p in arg_text.split("|")]
            if len(sub_parts) >= 1: args["avatar"] = sub_parts[0]
            if len(sub_parts) >= 2: args["username"] = sub_parts[1]
            if len(sub_parts) >= 3: args["bg"] = sub_parts[2]
            if len(sub_parts) >= 4: args["groupname"] = sub_parts[3]
            if len(sub_parts) >= 5: args["member"] = sub_parts[4]
            
        # 3. Phân tích dạng vị trí mặc định phân tách bằng khoảng trắng
        if not args:
            sub_parts = arg_text.split()
            if len(sub_parts) >= 1: args["avatar"] = sub_parts[0]
            if len(sub_parts) >= 2: args["username"] = sub_parts[1]
            if len(sub_parts) >= 3: args["bg"] = sub_parts[2]
            if len(sub_parts) >= 4: args["groupname"] = sub_parts[3]
            if len(sub_parts) >= 5: args["member"] = sub_parts[4]

    # Nhận các tham số với giá trị mặc định được yêu cầu
    avatar = args.get("avatar") or DEFAULT_AVATAR
    username = args.get("username") or DEFAULT_USERNAME
    
    bg = args.get("bg")
    if not bg:
        try:
            from core.bot_sys import upload_local_bg
            uploaded_bg = upload_local_bg()
            bg = uploaded_bg or DEFAULT_BG
        except Exception as bg_err:
            print(f"[greetings] Lỗi tải ảnh nền ngẫu nhiên: {bg_err}")
            bg = DEFAULT_BG
            
    groupname = args.get("groupname") or DEFAULT_GROUPNAME
    member = args.get("member") or DEFAULT_MEMBER
    
    # Chuẩn hóa member count
    try:
        member = int(member)
    except (ValueError, TypeError):
        member = 57

    # Gửi tin nhắn đang xử lý
    bot.replyMessage(
        Message(text=f"⏳ Đang tạo ảnh {greeting_type} V2…"),
        message_object, thread_id, thread_type
    )
    
    # Gọi API tạo ảnh
    image_data, error = _generate_greeting_card(greeting_type, avatar, username, bg, groupname, member)
    
    if error:
        error_msg = error.get("error", "Lỗi không xác định") if isinstance(error, dict) else str(error)
        bot.replyMessage(
            Message(text=f"❌ Lỗi: {error_msg}"),
            message_object, thread_id, thread_type
        )
        return
        
    if not image_data:
        bot.replyMessage(
            Message(text="❌ Không thể tạo ảnh. Vui lòng thử lại sau."),
            message_object, thread_id, thread_type
        )
        return
        
    # Lưu ảnh vào file tạm
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        tmp_file.write(image_data)
        temp_path = tmp_file.name
        
    try:
        # Gửi ảnh lên Zalo
        with Image.open(temp_path) as img:
            w, h = img.size
            
        bot.sendLocalImage(
            temp_path,
            message=Message(text=f"✅ Ảnh {greeting_type} V2 đã tạo!"),
            thread_id=thread_id,
            thread_type=thread_type,
            width=w,
            height=h,
        )
    except Exception as e:
        bot.replyMessage(
            Message(text=f"❌ Lỗi gửi ảnh: {e}"),
            message_object, thread_id, thread_type
        )
    finally:
        # Xóa file tạm
        try:
            os.remove(temp_path)
        except Exception:
            pass
