import os
import random
import time
import threading
from zlapi.models import *
import requests

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        name = user_info.zaloName or user_info.displayName or ""
        name = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
        return name or "Unknown User"
    except Exception:
        return "Unknown User"

def download_and_send_image(image_url, thread_id, thread_type, author_id, client):
    try:

        msg = f"[By: {get_user_name_by_id(client, author_id)}]"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        
        image_response = requests.get(image_url, headers=headers)
        image_response.raise_for_status()
        
        temp_image_path = 'modules/cache/temp_image1.jpeg'
        with open(temp_image_path, 'wb') as f:
            f.write(image_response.content)

        if os.path.exists(temp_image_path):
            client.sendLocalImage(
                temp_image_path,
                thread_id=thread_id,
                message=Message(text=msg),
                thread_type=thread_type,
                width=1200,
                height=1600
            )
            os.remove(temp_image_path)
        else:
            raise Exception("Không thể lưu ảnh")

    except requests.exceptions.RequestException as e:
        error_message = f"Đã xảy ra lỗi khi gọi API: {str(e)}"
        client.sendMessage(error_message, thread_id, thread_type)
    except Exception as e:
        error_message = f"Đã xảy ra lỗi: {str(e)}"
        client.sendMessage(error_message, thread_id, thread_type)

def handle_anhgai_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Use local file instead of github link
        data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data-send")
        image_file = os.path.join(data_dir, "girl.txt")
        
        if os.path.exists(image_file):
            with open(image_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            if urls:
                image_url = random.choice(urls)
            else:
                client.sendMessage("❌ Danh sách ảnh rỗng", thread_id, thread_type)
                return
        else:
            client.sendMessage("❌ Không tìm thấy file ảnh", thread_id, thread_type)
            return
        
        download_and_send_image(image_url, thread_id, thread_type, author_id, client)
        
    except Exception as e:
        error_message = f"Đã xảy ra lỗi: {str(e)}"
        client.sendMessage(error_message, thread_id, thread_type)

txa = {
    "name": "pro_anhgai",
    "desc": "Gửi ảnh gái đẹp ngẫu nhiên vào nhóm. Hỗ trợ nhiều loại ảnh. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['anhgai']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'anhgai': handle_anhgai_command
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
def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'anhgai': handle_anhgai_command
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
