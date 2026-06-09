from zlapi.models import Message, ThreadType
from core.bot_sys import is_admin, admin_cao

txa = {
    "name": "group_link",
    "desc": {
        "link": "Bật/tắt hoặc đổi link nhóm (admin bot/phó nhóm)"
    },
    "author": "TXA",
    "command": ["link"]
}

def is_admin_or_mod(bot, author_id, thread_id, thread_type):
    """Check if user is bot admin or group admin/mod"""
    if is_admin(bot, author_id) or admin_cao(bot, author_id):
        return True
    try:
        group_info = bot.fetchGroupInfo(thread_id)
        if group_info and hasattr(group_info, 'gridInfoMap'):
            grid_info = group_info.gridInfoMap.get(thread_id, {})
            if not grid_info:
                grid_info = group_info.gridInfoMap.get(str(thread_id), {})
            admins = grid_info.get('adminIds', [])
            if author_id in admins:
                return True
    except Exception as e:
        print(f"[ERROR] checking group admin: {e}")
    return False

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')

    if thread_type != ThreadType.GROUP:
        bot.replyMessage(Message(text="❌ Lệnh này chỉ dùng trong nhóm!"), message_object, thread_id, thread_type)
        return

    parts = message_text[len(prefix):].split(None, 2)
    if len(parts) < 2:
        bot.replyMessage(Message(text="❌ Thiếu tham số. Dùng: link on/off/reset"), message_object, thread_id, thread_type)
        return

    sub = parts[1].lower()

    if sub in ["on", "off"]:
        if not is_admin_or_mod(bot, author_id, thread_id, thread_type):
            bot.replyMessage(Message(text="❌ Bạn không phải admin bot/phó nhóm để thực hiện!"), message_object, thread_id, thread_type)
            return

        try:
            add_member_only = 1 if sub == "off" else 0
            bot.changeGroupSetting(thread_id, addMemberOnly=add_member_only)
            status = "🔴 Tắt" if sub == "off" else "🟢 Bật"
            bot.replyMessage(Message(text=f"✅ Đã {status} link tham gia nhóm!"), message_object, thread_id, thread_type)
        except Exception as e:
            print(f"[ERROR] link {sub}: {e}")
            bot.replyMessage(Message(text="❌ Không thể thay đổi cài đặt link nhóm! Đảm bảo bot là admin nhóm!"), message_object, thread_id, thread_type)
        return

    if sub == "reset":
        if not is_admin_or_mod(bot, author_id, thread_id, thread_type):
            bot.replyMessage(Message(text="❌ Bạn không phải admin bot/phó nhóm để thực hiện!"), message_object, thread_id, thread_type)
            return

        try:
            params = {
                "params": bot._encode({
                    "grid": str(thread_id),
                    "imei": bot._imei,
                    "clientLang": "vi"
                }),
                "zpw_ver": 685,
                "zpw_type": 30
            }
            response = bot._post("https://tt-group-wpa.chat.zalo.me/api/group/link/create", params=params)
            data = response.json()
            if data.get("error_code") == 0:
                bot.replyMessage(Message(text="✅ Đã đổi link nhóm thành công! Link cũ sẽ không còn hoạt động."), message_object, thread_id, thread_type)
            else:
                err = data.get("error_message", "Unknown error")
                bot.replyMessage(Message(text=f"❌ Không thể đổi link nhóm: {err}"), message_object, thread_id, thread_type)
        except Exception as e:
            print(f"[ERROR] reset link: {e}")
            bot.replyMessage(Message(text="❌ Không thể đổi link nhóm! Đảm bảo bot là admin nhóm!"), message_object, thread_id, thread_type)
        return

    bot.replyMessage(Message(text="❌ Tham số không hợp lệ. Dùng: link on/off/reset"), message_object, thread_id, thread_type)
