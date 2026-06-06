from zlapi.models import Message, ThreadType
from core.bot_sys import is_admin

txa = {
    "name": "group_lock",
    "desc": "Khóa/mở khóa nhóm: chỉ admin/phó nhóm mới có thể chat khi khóa (dùng API Zalo thật)!",
    "author": "TXA",
    "command": ["lockgroup", "unlockgroup", "lock"]
}

def is_admin_or_mod(bot, author_id, thread_id, thread_type):
    """Check if user is bot admin or group admin/mod"""
    if is_admin(bot, author_id):
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
    
    # Check if thread is GROUP
    if thread_type != ThreadType.GROUP:
        bot.replyMessage(Message(text="❌ Lệnh này chỉ dùng trong nhóm!"), message_object, thread_id, thread_type)
        return
    
    cmd = message_text[len(prefix):].split()[0].lower()
    
    # Handle lock/unlock commands
    if cmd in ["lockgroup", "lock"]:
        if not is_admin_or_mod(bot, author_id, thread_id, thread_type):
            bot.replyMessage(Message(text="❌ Bạn không phải admin bot/phó nhóm để khóa nhóm!"), message_object, thread_id, thread_type)
            return
        
        try:
            bot.changeGroupSetting(thread_id, lockSendMsg=1)
            bot.replyMessage(Message(text="✅ Nhóm đã được khóa! Chỉ admin/phó nhóm có thể gửi tin nhắn!"), message_object, thread_id, thread_type)
        except Exception as e:
            print(f"[ERROR] locking group: {e}")
            bot.replyMessage(Message(text="❌ Không thể khóa nhóm! Đảm bảo bot là admin nhóm!"), message_object, thread_id, thread_type)
        return
    
    if cmd == "unlockgroup":
        if not is_admin_or_mod(bot, author_id, thread_id, thread_type):
            bot.replyMessage(Message(text="❌ Bạn không phải admin bot/phó nhóm để mở khóa nhóm!"), message_object, thread_id, thread_type)
            return
        
        try:
            bot.changeGroupSetting(thread_id, lockSendMsg=0)
            bot.replyMessage(Message(text="✅ Nhóm đã được mở khóa! Mọi người có thể chat bình thường!"), message_object, thread_id, thread_type)
        except Exception as e:
            print(f"[ERROR] unlocking group: {e}")
            bot.replyMessage(Message(text="❌ Không thể mở khóa nhóm! Đảm bảo bot là admin nhóm!"), message_object, thread_id, thread_type)
        return
