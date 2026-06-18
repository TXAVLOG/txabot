import os
import json
import requests
import re
from datetime import datetime
from zlapi.models import Message, MultiMsgStyle, MessageStyle

des = {
    'version': '1.0.0',
    'credits': 'Yuta Bot',
    'description': 'Lấy tài khoản Liên Quân Mobile ngẫu nhiên',
    'power': 'Thành viên'
}

FONT_SIZE = "9"
CACHE_DIR = "modules/cache/lqacc"
os.makedirs(CACHE_DIR, exist_ok=True)

def _sty(text, color="#e8eaf6"):
    h = len(text.split("\n")[0]) + 1
    return MultiMsgStyle([
        MessageStyle(offset=0, length=len(text), style="font", size=FONT_SIZE, auto_format=False),
        MessageStyle(offset=0, length=h, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=h, style="bold", auto_format=False),
    ])

def get_lq_accounts(count=1):
    """Lấy tài khoản Liên Quân từ API"""
    try:
        url = f"https://apiwebfree.lovable.app/api/lq-acc?count={count}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('accounts'):
                return data['accounts'], data.get('total_available', 0)
        return None, 0
    except Exception as e:
        print(f"[LQACC] Lỗi API: {e}")
        return None, 0

def handle_lqacc_command(message, message_object, thread_id, thread_type, author_id, client):
    prefix = client.settings.get("prefix", ".")
    
    cmd = message.strip()
    if cmd.startswith(prefix):
        cmd = cmd[len(prefix):].strip()
    
    if not cmd.startswith("lqacc"):
        return
    
    content = cmd[5:].strip()
    
    # Lấy số lượng (mặc định 1, tối đa 5)
    count = 1
    if content.isdigit():
        count = min(int(content), 5)
        if count < 1:
            count = 1
    
    # Thông báo đang lấy
    if count == 1:
        client.replyMessage(
            Message(text="🎮 Đang lấy tài khoản Liên Quân...", style=_sty("🎮 Đang lấy...", "#F7B503")),
            message_object, thread_id, thread_type, ttl=10000
        )
    else:
        client.replyMessage(
            Message(text=f"🎮 Đang lấy {count} tài khoản Liên Quân...", style=_sty(f"🎮 Đang lấy {count} tk...", "#F7B503")),
            message_object, thread_id, thread_type, ttl=10000
        )
    
    # Lấy tài khoản
    accounts, total = get_lq_accounts(count)
    
    if not accounts:
        client.replyMessage(
            Message(text="❌ Không thể lấy tài khoản!\n💡 Thử lại sau.", style=_sty("❌ Lỗi!", "#DB342E")),
            message_object, thread_id, thread_type, ttl=30000
        )
        return
    
    # Format kết quả
    if count == 1:
        acc = accounts[0]
        msg = f"""
🎮 TÀI KHOẢN LIÊN QUÂN
━━━━━━━━━━━━━━━━━━━━━━
👤 Username: {acc['username']}
🔑 Password: {acc['password']}
━━━━━━━━━━━━━━━━━━━━━━
📊 Còn lại: {total} tài khoản
💡 Dùng: {prefix}lqacc <số> để lấy nhiều
        """
        client.replyMessage(
            Message(text=msg.strip(), style=_sty(msg, "#15A85F")),
            message_object, thread_id, thread_type, ttl=60000
        )
    else:
        lines = [f"🎮 DANH SÁCH {len(accounts)} TÀI KHOẢN LIÊN QUÂN", "━━━━━━━━━━━━━━━━━━━━━━"]
        for i, acc in enumerate(accounts, 1):
            lines.append(f"{i}. 👤 {acc['username']}")
            lines.append(f"   🔑 {acc['password']}")
            lines.append("")
        lines.append(f"📊 Còn lại: {total} tài khoản")
        lines.append(f"💡 Dùng: {prefix}lqacc <số> để lấy nhiều")
        
        client.replyMessage(
            Message(text="\n".join(lines), style=_sty("\n".join(lines), "#e8eaf6")),
            message_object, thread_id, thread_type, ttl=60000
        )

def LIGHT():
    return {"lqacc": handle_lqacc_command}