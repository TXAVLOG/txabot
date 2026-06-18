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
from core.bot_sys import admin_cao, read_settings, load_qr_session
from zlapi import ZaloAPI

txa = {
    "name": "upcommunity",
    "desc": {
        "upcommunity": "Nâng cấp nhóm Zalo lên Cộng đồng (Community)",
        "upcom": "Nâng cấp nhóm Zalo lên Cộng đồng (Community)",
    },
    "author": "TXA / vandat",
    "command": ["upcommunity", "upcom"],
    "t-per": "s-admin",
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


def _fetch_user_info(client, uid):
    """Fetch tên hiển thị và số điện thoại của user theo UID."""
    name = str(uid)
    phone = ""
    try:
        user_info = client.fetchUserInfo(uid)
        user = user_info.changed_profiles.get(uid) if user_info and getattr(user_info, 'changed_profiles', None) else None
        if user:
            name = getattr(user, 'displayName', '') or getattr(user, 'zaloName', '') or str(uid)
            phone = getattr(user, 'phoneNumber', '') or ''
    except Exception as e:
        print(f"[upcommunity] _fetch_user_info error: {e}")
    return name, phone


def _is_same_account(client_a, uid_a, client_b, uid_b):
    """Kiểm tra 2 client có phải cùng 1 tài khoản Zalo không.
    So sánh bằng UID trước, nếu khác thì so sánh bằng phone number."""
    if str(uid_a) == str(uid_b):
        return True

    try:
        _, phone_a = _fetch_user_info(client_a, uid_a)
        _, phone_b = _fetch_user_info(client_b, uid_b)
        if phone_a and phone_b and phone_a == phone_b:
            print(f"[upcommunity] Same phone number detected: {phone_a}")
            return True
    except Exception as e:
        print(f"[upcommunity] _is_same_account phone check error: {e}")

    return False


def _get_account_description(client, using_qr, qr_client=None):
    """Tạo mô tả tài khoản, nhận ra 2 UID khác nhau nhưng cùng 1 account."""
    bot_uid = client.uid

    if not using_qr or qr_client is None:
        bot_name, _ = _fetch_user_info(client, bot_uid)
        return f"Tài khoản Bot ({bot_name} @{bot_uid})"

    qr_uid = qr_client.uid

    # Cùng 1 UID hoặc cùng sđt -> cùng 1 tài khoản
    if _is_same_account(client, bot_uid, qr_client, qr_uid):
        bot_name, _ = _fetch_user_info(client, bot_uid)
        return f"Cùng 1 tài khoản ({bot_name} @{bot_uid})"

    # Hoàn toàn khác nhau
    bot_name, _ = _fetch_user_info(client, bot_uid)
    qr_name, _ = _fetch_user_info(qr_client, qr_uid)
    return f"Bot: {bot_name} @{bot_uid} | QR: {qr_name} @{qr_uid}"


def _upgrade_community(client, group_id: str) -> dict:
    try:
        result = client.upgradeComunity(group_id)
        return result
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

        # Khởi tạo client nâng cấp: ưu tiên dùng session QR nếu có
        qr_session = load_qr_session()
        active_client = client
        using_qr = False

        if qr_session:
            qr_imei = qr_session.get("imei")
            qr_cookies = qr_session.get("cookies")
            if qr_imei and qr_cookies:
                try:
                    qr_client = ZaloAPI(phone="dummy", password="dummy", imei=qr_imei, session_cookies=qr_cookies, auto_login=True)
                    if qr_client.isLoggedIn():
                        active_client = qr_client
                        using_qr = True
                        print(f"[upcommunity] Using QR session client (UID: {qr_client.uid})")
                    else:
                        print("[upcommunity] QR session loaded but isLoggedIn() is False. Falling back to main bot client.")
                except Exception as qr_err:
                    print(f"[upcommunity] Error initializing QR client: {qr_err}. Falling back to main bot client.")
        else:
            print("[upcommunity] No QR session found. Using main bot client.")

        parts = message.strip().split()
        
        # Kiểm tra gói Zalo Business của Active Client
        biz_pkg = "Thường"
        try:
            active_uid = active_client.uid
            user_info = active_client.fetchUserInfo(active_uid)
            user = user_info.changed_profiles.get(active_uid) if user_info and getattr(user_info, 'changed_profiles', None) else None
            if user:
                biz_val = getattr(user, 'bizPkg', None)
                if biz_val:
                    label_val = None
                    if hasattr(biz_val, 'label'):
                        label_val = biz_val.label
                    elif isinstance(biz_val, dict):
                        label_val = biz_val.get('label')
                    
                    if isinstance(label_val, dict):
                        biz_pkg = label_val.get('VI') or label_val.get('EN') or "Business"
                    elif isinstance(label_val, str):
                        biz_pkg = label_val
                    elif label_val:
                        biz_pkg = str(label_val)
        except Exception as check_err:
            print(f"[upcommunity] check package error: {check_err}")
            biz_pkg = "Lỗi kiểm tra"

        # Nếu người dùng chạy lệnh kiểm tra gói (ví dụ: .upcom check hoặc .upcom biz)
        if len(parts) > 1 and parts[1].lower() in ["check", "biz", "pkg", "package"]:
            account_desc = _get_account_description(client, using_qr, qr_client if using_qr else None)
            reply(
                f"💼 [ZALO BUSINESS CHECK]\n"
                f"🤖 {account_desc}\n"
                f"📦 Gói dịch vụ hiện tại: {biz_pkg}\n\n"
                f"⚠️ Lưu ý về hạn mức cộng đồng:\n"
                f"• Tài khoản Thường: 0 cộng đồng.\n"
                f"• Gói Standard: 1 cộng đồng.\n"
                f"• Gói Pro / Elite: Có hạn mức cao hơn."
            )
            return

        # Nếu không truyền group_id -> dùng thread_id hiện tại (phải trong group)
        if len(parts) > 1:
            target_id = parts[1].strip()
        else:
            if thread_type != ThreadType.GROUP:
                reply(
                    f"⚠️ Vui lòng nhập ID nhóm cần nâng cấp:\n"
                    f"📖 Cú pháp: {client.prefix}upcommunity [group_id]\n"
                    f"💡 Hoặc dùng lệnh trong chính nhóm cần up.\n"
                    f"ℹ️ Hoặc kiểm tra gói: {client.prefix}upcommunity check"
                )
                return
            target_id = str(thread_id)

        account_desc = _get_account_description(client, using_qr, qr_client if using_qr else None)
        reply(
            f"⏳ Đang nâng cấp nhóm [{target_id}] lên Cộng đồng Zalo...\n"
            f"👤 Thực hiện bằng: {account_desc}\n"
            f"💼 Gói Business: {biz_pkg}"
        )

        try:
            result   = _upgrade_community(active_client, target_id)
            err_code = result.get('error_code', result.get('errorCode', -1))
            err_msg  = result.get('error_message', result.get('errorMessage', ''))

            if err_code == 0:
                reply(
                    f"✅ Nâng cấp Cộng đồng thành công!\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏘️ Nhóm đã được nâng cấp lên Cộng đồng\n"
                    f"👥 Mở rộng lên đến 1.000 thành viên\n"
                    f"🔗 Mời tham gia dễ dàng bằng link\n"
                    f"🆔 Group ID: {target_id}\n"
                    f"👤 Thực hiện bằng: {account_desc}"
                )
            else:
                if err_code == 275:
                    err_name, _ = _fetch_user_info(active_client, active_client.uid)
                    if using_qr:
                        friendly_msg = (
                            f"❌ Nâng cấp thất bại!\n"
                            f"⚠️ Tài khoản ({err_name} @{active_client.uid}) không phải là Trưởng nhóm hoặc Phó nhóm của nhóm này.\n"
                            f"➜ Vui lòng cấp quyền quản trị nhóm cho tài khoản này để nâng cấp nhé! 🌸"
                        )
                    else:
                        friendly_msg = (
                            f"❌ Nâng cấp thất bại!\n"
                            f"⚠️ Tài khoản Bot chính ({err_name} @{active_client.uid}) không phải là Trưởng nhóm hoặc Phó nhóm của nhóm này.\n"
                            f"➜ Vui lòng cấp quyền quản trị nhóm cho Bot để nâng cấp nhé! 🌸"
                        )
                elif err_code == 185:
                    friendly_msg = (
                        f"❌ Nâng cấp thất bại!\n"
                        f"⚠️ Tài khoản thực hiện đã đạt giới hạn số lượng Cộng đồng có thể sở hữu (0).\n"
                        f"➜ Vui lòng rời hoặc giải tán các cộng đồng ít hoạt động, hoặc sử dụng tài khoản khác có hạn mức cao hơn để tiếp tục nâng cấp nhé! 🌸"
                    )
                elif "already" in str(err_msg).lower() or "đã là" in str(err_msg).lower():
                    friendly_msg = (
                        f"❌ Nâng cấp thất bại!\n"
                        f"⚠️ Nhóm này thực tế đã là Cộng đồng (Community) rồi nhé! 🌸"
                    )
                elif err_code == 114:
                    friendly_msg = (
                        f"❌ Nâng cấp thất bại!\n"
                        f"⚠️ API báo Tham số không hợp lệ (Mã lỗi #114).\n"
                        f"➜ Nguyên nhân có thể:\n"
                        f"   • Tài khoản chưa là thành viên của nhóm\n"
                        f"   • Tài khoản chưa được cấp quyền Trưởng/Phó nhóm\n"
                        f"   • Chưa đăng ký gói Zalo Business\n"
                        f"   • Đã vượt quá số lượng cộng đồng cho phép\n"
                        f"💡 Hãy kiểm tra lại quyền và gói dịch vụ của tài khoản nhé! 🌸"
                    )
                elif err_code in [-1403, -1]:
                    friendly_msg = (
                        f"❌ Nâng cấp thất bại!\n"
                        f"⚠️ Tài khoản thực hiện không có quyền (không có Key vàng/Business) để nâng cấp cộng đồng.\n"
                        f"➜ Hãy sử dụng một tài khoản QR đã kích hoạt gói Zalo Business nhé! 🌸"
                    )
                elif err_code in [-1008, -2]:
                    friendly_msg = (
                        f"❌ Nâng cấp thất bại!\n"
                        f"⚠️ Tài khoản thực hiện chưa đăng ký gói Zalo Business hoặc hạn mức không đủ.\n"
                        f"➜ Hãy nâng cấp gói Zalo Business cho tài khoản thực hiện trước nhé! 🌸"
                    )
                else:
                    friendly_msg = (
                        f"❌ Nâng cấp thất bại!\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📛 Mã lỗi : {err_code}\n"
                        f"💬 Chi tiết : {err_msg or 'Không xác định hoặc tham số chưa hợp lệ'}\n"
                        f"💡 Hướng dẫn: Vui lòng kiểm tra quyền quản trị của tài khoản thực hiện và gói Zalo Business của họ."
                    )
                reply(friendly_msg)

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
