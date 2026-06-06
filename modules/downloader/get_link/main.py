import json
import urllib
from zlapi.models import *

last_sent_image_url = None  

def handle_getlink_command(message, message_object, thread_id, thread_type, author_id, client):
    global last_sent_image_url
    msg_obj = message_object

    if msg_obj.msgType == "chat.photo":
        img_url = msg_obj.content.href.replace("\\/", "/")
        img_url = urllib.parse.unquote(img_url)
        last_sent_image_url = img_url
        send_image_link(img_url, thread_id, thread_type, client)

    elif msg_obj.quote:
        attach = msg_obj.quote.attach
        if attach:
            try:
                attach_data = json.loads(attach)
            except json.JSONDecodeError as e:
                print(f"Lỗi khi phân tích JSON: {str(e)}")
                return

            image_url = attach_data.get('hdUrl') or attach_data.get('href')
            if image_url:
                send_image_link(image_url, thread_id, thread_type, client)
            else:
                send_error_message(thread_id, thread_type, client)
        else:
            send_error_message(thread_id, thread_type, client)
    else:
        send_error_message(thread_id, thread_type, client)

def send_image_link(image_url, thread_id, thread_type, client):
    if image_url:
        message_to_send = Message(text=f"{image_url}")
        
        if hasattr(client, 'send'):
            client.send(message_to_send, thread_id, thread_type)
        else:
            print("Client không hỗ trợ gửi tin nhắn.")

def send_error_message(thread_id, thread_type, client):
    error_message = Message(text="➜ getlink: 🔗 Lấy link trong tin nhắn\n💞 Ví dụ: Reply getlink vào tin nhắn để lấy link media ✅")
    
    if hasattr(client, 'send'):
        client.send(error_message, thread_id, thread_type)
    else:
        print("Client không hỗ trợ gửi tin nhắn.")

txa = {
    "name": "pro_getlink",
    "desc": "Lấy link media từ tin nhắn. Reply vào tin nhắn để lấy link ảnh/video. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['getlink']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'getlink': handle_getlink_command
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
