import json
import threading
import re
from zlapi.models import *
from core.bot_sys import zalo_len, zalo_offset

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        name = user_info.zaloName or user_info.displayName or ""
        name = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
        return name or "Unknown User"
    except Exception:
        return "Unknown User"

def src(bot, message_object, author_id, thread_id, thread_type, command):
    def src():
        try:
            mention = None
            if message_object.quote:
                quoted_message = message_object.quote
                data = {
                    "ownerId": quoted_message.ownerId,
                    "cliMsgId": quoted_message.cliMsgId,
                    "globalMsgId": quoted_message.globalMsgId,
                    "cliMsgType": quoted_message.cliMsgType,
                    "ts": quoted_message.ts,
                    "msg": quoted_message.msg,
                    "attach": json.loads(quoted_message.attach) if quoted_message.attach else {},
                    "fromD": quoted_message.fromD
                }
                username = get_user_name_by_id(bot, author_id)
                response = f"🚦 @{username} source của bạn đây ✅\n{json.dumps(data, ensure_ascii=False, indent=4)}\n"
                
                if thread_type != ThreadType.USER:
                    offset = zalo_offset(response, f"@{username}")
                    if offset != -1:
                        mention = Mention(uid=author_id, offset=offset + 1, length=zalo_len(username))
            else:
                response = "❌ Vui lòng reply vào một tin nhắn để lấy dữ liệu."

            bot.replyMessage(Message(text=response, mention=mention), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
        except Exception as e:
            print(f"Error: {e}")
            bot.replyMessage(Message(text="🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type)

    thread = threading.Thread(target=src)
    thread.start()

txa = {
    "name": "pro_src",
    "desc": "Xem source code của bot. Hiển thị thông tin về code và repo. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['src']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'src': src
    }
    
    func = dispatch_map.get(cmd)
    if func:
        import inspect
        sig = inspect.signature(func)
        args_map = {
            'bot': bot,
            'client': bot,
            'message_object': message_object,
            'thread_id': thread_id,
            'thread_type': thread_type,
            'author_id': author_id,
            'message': message_text,
            'message_text': message_text,
            'message_lower': message_text.lower()
        }
        args = []
        for param_name in sig.parameters:
            if param_name in args_map:
                args.append(args_map[param_name])
            else:
                args.append(None)
        func(*args)
