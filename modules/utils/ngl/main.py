from datetime import datetime
import os
import random
import threading
import time

import requests
from zlapi.models import Message

from core.bot_sys import get_user_name_by_id, is_admin


MAX_NGL_COUNT = 20


def load_user_agents():
    file_path = os.path.join(os.path.dirname(__file__), "user_agents.txt")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
        ]


USER_AGENTS = load_user_agents()


def ngl_submit(username, count, message):
    success = 0
    failed = 0

    for _ in range(count):
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://ngl.link",
            "referer": f"https://ngl.link/{username}",
            "user-agent": random.choice(USER_AGENTS),
            "x-requested-with": "XMLHttpRequest",
        }
        data = {
            "username": username,
            "question": message,
            "deviceId": "TXABOT-" + str(random.randint(1000000000, 9999999999)),
            "gameSlug": "",
            "referrer": "",
        }

        try:
            response = requests.post(
                "https://ngl.link/api/submit",
                headers=headers,
                data=data,
                timeout=12,
            )
            if response.status_code == 200:
                success += 1
            else:
                failed += 1
        except requests.RequestException:
            failed += 1

        time.sleep(1)

    return success, failed


def handle_ngl_command(message, message_object, thread_id, thread_type, author_id, client):
    if not is_admin(client, author_id):
        client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), message_object, thread_id, thread_type)
        return

    user_name = get_user_name_by_id(client, author_id)
    prefix = getattr(client, "prefix", "!")
    parts = message.strip().split(maxsplit=3)

    if len(parts) < 4:
        client.replyMessage(
            Message(text=(
                f"❌ Sai cú pháp!\n"
                f"➜ Dùng: {prefix}ngl <username> <count> <nội_dung>\n"
                f"➜ Ví dụ: {prefix}ngl userabc 5 Hello từ TXABOT"
            )),
            message_object,
            thread_id,
            thread_type,
        )
        return

    username = parts[1].strip().lstrip("@")
    try:
        count = int(parts[2])
    except ValueError:
        client.replyMessage(Message(text="❌ Count phải là số nguyên dương."), message_object, thread_id, thread_type)
        return

    if count <= 0:
        client.replyMessage(Message(text="❌ Count phải lớn hơn 0."), message_object, thread_id, thread_type)
        return
    if count > MAX_NGL_COUNT:
        client.replyMessage(
            Message(text=f"⚠️ Giới hạn mỗi lần là {MAX_NGL_COUNT} tin. Đã tự giảm count xuống {MAX_NGL_COUNT}."),
            message_object,
            thread_id,
            thread_type,
        )
        count = MAX_NGL_COUNT

    text = parts[3].strip()
    if not text:
        client.replyMessage(Message(text="❌ Nội dung không được để trống."), message_object, thread_id, thread_type)
        return

    client.replyMessage(
        Message(text=f"🚀 Đang gửi {count} tin tới NGL @{username}...\n📝 Nội dung: {text}"),
        message_object,
        thread_id,
        thread_type,
    )

    def worker():
        success, failed = ngl_submit(username, count, text)
        now = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
        result = (
            "✨ [ NGL KẾT QUẢ ] ✨\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Người dùng: {user_name}\n"
            f"🎯 Username đích: @{username}\n"
            f"📨 Tổng gửi: {count}\n"
            f"✅ Thành công: {success}\n"
            f"❌ Thất bại: {failed}\n"
            f"🕒 Thời gian: {now}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━"
        )
        client.sendMessage(Message(text=result), thread_id, thread_type)

    threading.Thread(target=worker, daemon=True).start()


txa = {
    "name": "NGL",
    "desc": "Gửi nội dung tới form NGL theo username.",
    "author": "TXA",
    "command": ["ngl"],
}


def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    handle_ngl_command(message_text, message_object, thread_id, thread_type, author_id, bot)
