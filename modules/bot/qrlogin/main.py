# -*- coding: utf-8 -*-
import threading
from zlapi.models import Message, ThreadType
from core import bot_sys

txa = {
    "name": "qrlogin",
    "desc": {
        "qrlogin": "Tạo mã QR đăng nhập Zalo để lưu session"
    },
    "author": "TXA",
    "command": ["qrlogin"]
}

def handle_qrlogin_command(message, message_object, thread_id, thread_type, author_id, client):
    threading.Thread(
        target=bot_sys.login_and_get_session_info,
        args=(client, thread_id, thread_type),
        daemon=True
    ).start()

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()

    if cmd == "qrlogin":
        handle_qrlogin_command(message_text, message_object, thread_id, thread_type, author_id, bot)
