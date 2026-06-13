import sys
import traceback
from zlapi.models import Message

def handle_eval_command(message, message_object, thread_id, thread_type, author_id, bot):
    prefix = getattr(bot, 'prefix', '!')
    code = message[len(prefix) + 4:].strip() # len("eval") is 4
    if not code:
        bot.replyMessage(Message(text="⚠️ Vui lòng cung cấp biểu thức hoặc đoạn mã Python cần thực thi!"), message_object, thread_id, thread_type)
        return
        
    try:
        globals_dict = {
            'bot': bot,
            'client': bot,
            'message_object': message_object,
            'thread_id': thread_id,
            'thread_type': thread_type,
            'author_id': author_id,
            'sys': sys,
            'os': sys.modules['os'],
            'requests': sys.modules.get('requests')
        }
        
        # Thử eval trước
        try:
            result = eval(code, globals_dict)
            response_text = f"✅ Kết quả:\n{result}"
        except SyntaxError:
            # Nếu có lỗi cú pháp (chứa các câu lệnh), thử exec
            import io
            from contextlib import redirect_stdout
            
            f = io.StringIO()
            with redirect_stdout(f):
                exec(code, globals_dict)
            output = f.getvalue()
            response_text = f"✅ Thực thi thành công!\nOutput:\n{output}" if output else "✅ Thực thi thành công (Không có output)."
            
    except Exception as e:
        error_trace = traceback.format_exc()
        response_text = f"❌ Lỗi thực thi:\n{str(e)}\n\nTraceback:\n{error_trace[:500]}"
        
    bot.replyMessage(Message(text=response_text), message_object, thread_id, thread_type)

txa = {
    "name": "eval",
    "desc": "Thực thi code Python động (Chỉ dành cho Super Admin).",
    "author": "TXA",
    "command": ["eval"],
    "t-per": "super-admin"
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    handle_eval_command(message_text, message_object, thread_id, thread_type, author_id, bot)
