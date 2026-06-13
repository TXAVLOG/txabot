import time
from core.bot_sys import is_admin
from zlapi.models import *

def handle_leave_group_command(message, message_object, thread_id, thread_type, author_id, client):
    if not is_admin(client, author_id):
        client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), 
                           message_object, thread_id=thread_id, 
                           thread_type=thread_type, ttl=100000)
        return

    try:
        farewell_msg = "🚦Tạm biệt mọi người! Hẹn gặp lại nhé! 👋😊"
        client.replyMessage(Message(text=farewell_msg), 
                           message_object, thread_id=thread_id, 
                           thread_type=thread_type, ttl=120000)
        time.sleep(1)
        client.leaveGroup(thread_id, silent=True)

    except ZaloAPIException as e:
        error_msg = f"❌ Lỗi khi rời nhóm: {str(e)}"
        client.replyMessage(Message(text=error_msg), 
                           message_object, thread_id=thread_id, 
                           thread_type=thread_type, ttl=86400000)
    except Exception as e:
        error_msg = f"❌ Lỗi không xác định: {str(e)}"
        client.replyMessage(Message(text=error_msg), 
                           message_object, thread_id=thread_id, 
                           thread_type=thread_type, ttl=86400000)

txa = {
    "name": "pro_leave",
    "desc": "Bot rời khỏi nhóm (Chỉ admin cao). Gửi lời tạm biệt trước khi rời. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['leave_group'],
    "t-per": "admin"
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'leave_group': handle_leave_group_command
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
