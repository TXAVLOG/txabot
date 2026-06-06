from core.bot_sys import admin_cao
from zlapi.models import *

def handle_disbox(bot, thread_id, author_id, thread_type, message_object):
    try:
        if not admin_cao(bot, author_id):
            bot.replyMessage(Message(text="❌ Bạn không phải admin bot!"), 
                            message_object, thread_id=thread_id, 
                            thread_type=thread_type, ttl=100000)
            return
        bot.disperseGroup(thread_id)
        return ""
    except Exception as e:
        return f"❌ Đã xảy ra lỗi khi giải tán nhóm: {str(e)}"

txa = {
    "name": "pro_disbox",
    "desc": "Giải tán nhóm (Chỉ admin cao). Bot sẽ rời và giải tán nhóm. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['disbox']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'disbox': handle_disbox
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
