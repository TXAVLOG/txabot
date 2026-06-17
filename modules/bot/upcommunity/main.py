"""
Module: upcommunity
Nâng cấp nhóm Zalo lên Cộng đồng (Community) bằng API trực tiếp.
Chỉ dành cho high_level_admins của bot chính.
"""

import time
import json
import requests
import threading
import traceback
from zlapi.models import Message, ThreadType
from core.bot_sys import admin_cao, read_settings

txa = {
    "name": "upcommunity",
    "desc": {
        "upcommunity": "Nâng cấp nhóm Zalo lên Cộng đồng (Community)",
        "upcom": "Nâng cấp nhóm Zalo lên Cộng đồng (Community)",
    },
    "author": "TXA / vandat",
    "command": ["upcommunity", "upcom"],
}


def _get_cookies(client) -> dict:
    """Lấy cookies từ session của zlapi client."""
    try:
        session = getattr(client, '_state', None)
        if session:
            inner = getattr(session, '_session', None)
            if inner and hasattr(inner, 'cookies'):
                return dict(inner.cookies)

        session = getattr(client, 'session', None)
        if session and hasattr(session, 'cookies'):
            return dict(session.cookies)

        session = getattr(client, '_session', None)
        if session and hasattr(session, 'cookies'):
            return dict(session.cookies)

    except Exception as e:
        print(f"[upcommunity] _get_cookies error: {e}")
    return {}


def _upgrade_community(client, group_id: str) -> dict:
    bot_uid = getattr(client, 'uid', None) or getattr(client, '_uid', None)
    settings = read_settings(bot_uid)
    bot_config = next((b for b in settings.get('data', []) if b.get('is_main_bot')), None)
    cookies = bot_config.get('session_cookies', {}) if bot_config else {}
    imei    = bot_config.get('imei', '') if bot_config else ''

    headers = {
        "User-Agent"  : "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/91.0.4472.120 Mobile Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin"      : "https://chat.zalo.me",
        "Referer"     : "https://chat.zalo.me/",
    }

    params = {
        "zpw_ver" : 645,
        "zpw_type": 30,
    }

    ts = int(time.time() * 1000)
    data = {
        "params": json.dumps({
            "grid": str(group_id),
            "imei": imei,
            "ts"  : ts,
        }, separators=(',', ':')),
    }

    try:
        res = requests.post(
            "https://tt-group-wpa.chat.zalo.me/api/group/upgrade/community",
            params=params, data=data, headers=headers, cookies=cookies, timeout=15,
        )
        return res.json()
    except Exception as e:
        return {"error_code": -1, "error_message": str(e)}

def handle_upcommunity_command(message, message_object, thread_id, thread_type, author_id, client):
    def run():
        def reply(text):
            try:
                client.replyMessage(
                    Message(text=text),
                    message_object, thread_id, thread_type,
                    ttl=120000
                )
            except Exception as e:
                print(f"[upcommunity] reply error: {e}")

        # Chỉ high_level_admins của bot chính mới dùng được
        if not admin_cao(client, author_id):
            reply("⚠️ Lệnh này chỉ dành cho Admin cấp cao nhất của Bot!")
            return

        parts = message.strip().split()
        # Nếu không truyền group_id → dùng thread_id hiện tại (phải trong group)
        if len(parts) > 1:
            target_id = parts[1].strip()
        else:
            if thread_type != ThreadType.GROUP:
                reply(
                    f"⚠️ Vui lòng nhập ID nhóm cần nâng cấp:\n"
                    f"📖 Cú pháp: {client.prefix}upcommunity [group_id]\n"
                    f"💡 Hoặc dùng lệnh trong chính nhóm cần up."
                )
                return
            target_id = str(thread_id)

        reply(f"⏳ Đang nâng cấp nhóm [{target_id}] lên Cộng đồng Zalo...")

        try:
            result   = _upgrade_community(client, target_id)
            err_code = result.get('error_code', result.get('errorCode', -1))
            err_msg  = result.get('error_message', result.get('errorMessage', ''))

            if err_code == 0:
                reply(
                    "✅ Nâng cấp Cộng đồng thành công!\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "🏘️ Nhóm đã được nâng cấp lên Cộng đồng\n"
                    "👥 Mở rộng lên đến 1.000 thành viên\n"
                    "🔗 Mời tham gia dễ dàng bằng link\n"
                    f"🆔 Group ID: {target_id}"
                )
            else:
                reply(
                    f"❌ Nâng cấp thất bại!\n"
                    f"📛 Error code : {err_code}\n"
                    f"💬 Message    : {err_msg or 'Không xác định'}\n"
                    f"📄 Raw: {result}"
                )

        except Exception as e:
            print(f"[upcommunity] error: {e}")
            traceback.print_exc()
            reply(f"❌ Lỗi không mong muốn: {e}")

    threading.Thread(target=run, daemon=True).start()


def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    import inspect
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()

    dispatch_map = {
        'upcommunity': handle_upcommunity_command,
        'upcom'      : handle_upcommunity_command,
    }

    func = dispatch_map.get(cmd)
    if func:
        sig = inspect.signature(func)
        args_map = {
            'bot'           : bot,
            'client'        : bot,
            'message_object': message_object,
            'thread_id'     : thread_id,
            'thread_type'   : thread_type,
            'author_id'     : author_id,
            'message'       : message_text,
            'message_text'  : message_text,
        }
        args = [args_map.get(p, None) for p in sig.parameters]
        func(*args)
