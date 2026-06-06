import os
import requests
from deep_translator import GoogleTranslator
from core.bot_sys import read_settings, write_settings
from zlapi.models import Message

CACHE_DIR = 'modules/cache'
os.makedirs(CACHE_DIR, exist_ok=True)

def handle_dich_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "dich" not in settings:
        settings["dich"] = {}
    settings["dich"][thread_id] = True
    write_settings(bot.uid, settings)
    return f"🚦Lệnh {bot.prefix}dich đã được Bật 🚀 trong nhóm này ✅"

def handle_dich_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "dich" in settings and thread_id in settings["dich"]:
        settings["dich"][thread_id] = False
        write_settings(bot.uid, settings)
        return f"🚦Lệnh {bot.prefix}dich đã Tắt ⭕️ trong nhóm này ✅"
    return "🚦Nhóm chưa có thông tin cấu hình dich để ⭕️ Tắt 🤗"

def handle_translate_command(message, message_object, thread_id, thread_type, author_id, client):
    message_text = message_object.get('content', '').strip()
    settings = read_settings(client.uid)
    user_message = message.replace(f"{client.prefix}dich ", "").strip().lower()
    if user_message == "on":
        response = handle_dich_on(client, thread_id)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        return
    elif user_message == "off":
        response = handle_dich_off(client, thread_id)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        return
    
    if not (settings.get("dich", {}).get(thread_id, False)):
        return
    if not message_text or len(message_text.split(maxsplit=1)) < 2:
        response = Message(text="Vui lòng nhập văn bản cần dịch sau lệnh.")
        client.replyMessage(response, message_object, thread_id, thread_type)
        return

    # Tách phần văn bản cần dịch
    _, text_to_translate = message_text.split(maxsplit=1)

    try:
        # Dịch văn bản sang tiếng Việt
        translator = GoogleTranslator(source='auto', target='vi')
        translated = translator.translate(text_to_translate)
        
        # Định dạng phản hồi
        response_text = f"Tiếng Việt:\n{translated}"
        response = Message(text=response_text)
        client.replyMessage(response, message_object, thread_id, thread_type)
        
    except Exception as e:
        # Xử lý lỗi và gửi thông báo
        error_message = f"Lỗi khi dịch: {str(e)}"
        response = Message(text=error_message)
        client.replyMessage(response, message_object, thread_id, thread_type)

def upload_to_catbox(file_path):
    """
    Upload file lên Catbox từ đường dẫn cục bộ.
    
    Args:
        file_path (str): Đường dẫn đến file cần upload
    
    Returns:
        str: URL của file trên Catbox nếu thành công, None nếu thất bại
    """
    if not os.path.exists(file_path):
        print(f"Lỗi: File không tồn tại tại {file_path}")
        return None

    try:
        with open(file_path, 'rb') as file:
            response = requests.post(
                'https://catbox.moe/user/api.php',
                data={'reqtype': 'fileupload', 'userhash': ''},
                files={'fileToUpload': (os.path.basename(file_path), file)},
                timeout=30
            )
            response.raise_for_status()
            
            catbox_url = response.text.strip()
            if catbox_url.startswith('http'):
                return catbox_url
            else:
                print(f"Lỗi: URL trả về không hợp lệ - {catbox_url}")
                return None
                
    except requests.exceptions.RequestException as e:
        print(f"Lỗi upload Catbox: {str(e)}")
        return None
    except Exception as e:
        print(f"Lỗi không xác định khi upload: {str(e)}")
        return None

txa = {
    "name": "pro_dich",
    "desc": "Dịch văn bản sang nhiều ngôn ngữ khác nhau. Hỗ trợ dịch nhanh và chính xác. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['translate']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'translate': handle_translate_command
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
