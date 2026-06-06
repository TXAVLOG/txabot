import json
import threading
from zlapi.models import *

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        return user_info.zaloName or user_info.displayName
    except Exception:
        return "Người Dùng Ẩn Danh"

def src(bot, message_object, author_id, thread_id, thread_type, command):
    def src():
        try:
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
                response = f"🚦 @{get_user_name_by_id(bot, author_id)} source của bạn đây ✅\n{json.dumps(data, ensure_ascii=False, indent=4)}\n"
            else:
                response = "❌ Vui lòng reply vào một tin nhắn để lấy dữ liệu."

            bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
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
