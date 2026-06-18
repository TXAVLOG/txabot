# modules/qrlogin.py
# -*- coding: utf-8 -*-
import os
import time
import json
import threading
import traceback
import re
import base64
import requests

from zlapi import ZaloAPI, ThreadType
from zlapi.models import Message
from zlapi._exception import ZaloLoginError

des = {
    'version': "1.0.5",
    'credits': "Kryzis",
    'description': "Tạo QR đăng nhập Zalo",
    'power': "Thành viên"
}

CACHE_DIR = "modules/cache/qrlogin"
os.makedirs(CACHE_DIR, exist_ok=True)

DEFAULT_TTL = 120000
QR_TTL = 100000

def is_admin(author_id, client):
    try:
        with open("asset/seting.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            owner = str(data.get("admin", ""))
            admins = [str(x) for x in data.get("adm", [])]
            return str(author_id) == owner or str(author_id) in admins
    except:
        return False

def login_and_get_session_info(client, thread_id, thread_type):
    temp_client = None
    qr_file_path = os.path.join(CACHE_DIR, f"qr_login_{thread_id}_{int(time.time())}.png")

    try:
        temp_client = ZaloAPI(phone=None, password=None, imei=None, auto_login=False)
        
        client.send(
            Message(text="⏳ Đang tạo QR..."),
            thread_id,
            thread_type,
            ttl=DEFAULT_TTL
        )
        
        def send_qr_to_user(path_to_qr):
            if os.path.exists(path_to_qr):
                client.sendLocalImage(
                    imagePath=path_to_qr,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    message=Message(text="🔐 Quét QR trong 100 giây"),
                    ttl=QR_TTL
                )
        
        temp_client.loginWithQR(
            qr_path=qr_file_path,
            on_qr_generated=send_qr_to_user
        )
        
        if temp_client.isLoggedIn():
            imei = temp_client._state.user_imei
            cookies = temp_client.getSession()
            cookies_str = json.dumps(cookies, indent=2, ensure_ascii=False)
            
            msg = f"✅ Đăng nhập thành công!\n\n🔑 IMEI:\n{imei}\n\n🍪 Cookie:\n{cookies_str}"
            client.send(Message(text=msg), thread_id, thread_type, ttl=DEFAULT_TTL)

    except ZaloLoginError as e:
        if "Het thoi gian cho quet ma QR" in str(e):
            error_msg = "⏰ Hết thời gian, không ai quét QR"
        else:
            error_msg = f"❌ Lỗi: {str(e)[:150]}"
        client.send(Message(text=error_msg), thread_id, thread_type, ttl=DEFAULT_TTL)
        
    except Exception as e:
        client.send(Message(text=f"❌ {str(e)[:150]}"), thread_id, thread_type, ttl=DEFAULT_TTL)

    finally:
        if os.path.exists(qr_file_path):
            try:
                os.remove(qr_file_path)
            except:
                pass

def handle_qrlogin_command(message, message_object, thread_id, thread_type, author_id, client):
    prefix = client.settings.get("prefix", ".")
    
    # Bỏ check admin, cho tất cả thành viên dùng
    # if not is_admin(author_id, client):
    #     client.replyMessage(Message(text="❌ Chỉ admin"), message_object, thread_id, thread_type, ttl=30000)
    #     return

    help_text = f"""📖 QR LOGIN

{prefix}qrlogin - Tạo QR đăng nhập

Sau khi có QR:
1. Mở Zalo > Cài đặt > QR Code
2. Quét mã
3. Bot sẽ gửi IMEI + Cookie"""
    
    client.replyMessage(Message(text=help_text.strip()), message_object, thread_id, thread_type, ttl=30000)

    login_thread = threading.Thread(
        target=login_and_get_session_info,
        args=(client, thread_id, thread_type)
    )
    login_thread.daemon = True
    login_thread.start()

def LIGHT():
    return {
        'qrlogin': handle_qrlogin_command
    }