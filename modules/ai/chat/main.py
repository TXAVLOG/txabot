from datetime import datetime, timedelta
import json
import os
import re
import threading
import time
import requests
import urllib.parse
from core.bot_sys import read_settings, write_settings, is_admin
from zlapi.models import Message, ThreadType, Mention

CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../txa.json"))

def _read_base_url():
    value = os.getenv("KAIROBOT_BASE_URL")
    if value:
        return value.strip().rstrip("/")
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        bot_data = (config.get("data") or [{}])[0]
        value = bot_data.get("kairobot_base_url") or bot_data.get("base_url")
        if value:
            return str(value).strip().rstrip("/")
    except Exception:
        pass
    return "https://kairobot.qzz.io"

KAIROBOT_BASE_URL = _read_base_url()

chat_histories = {} # thread_id -> list of {"role": "user"|"assistant", "content": "..."}
last_message_times = {}

txa = {
    "name": "pro_chat",
    "desc": "Trò chuyện với AI thông qua Kairobot API. Hỗ trợ nhớ lịch sử trò chuyện và hỏi đáp qua hình ảnh. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['chat']
}

def _read_api_key():
    for key in ("KAIROBOT_APIKEY", "KAIROBOT_API_KEY", "TXA_APIKEY", "TXA_API_KEY"):
        value = os.getenv(key)
        if value:
            return value.strip()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        bot_data = (config.get("data") or [{}])[0]
        for key in ("kairobot_api_key", "kairobot_apikey", "apikey", "api_key"):
            value = bot_data.get(key)
            if value:
                return str(value).strip()
    except Exception:
        pass
    return ""

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        name = user_info.zaloName or user_info.displayName or ""
        name = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
        return name or "Unknown User"
    except Exception:
        return "Unknown User"

def handle_chat_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "chat" not in settings:
        settings["chat"] = {}
    settings["chat"][thread_id] = True
    write_settings(bot.uid, settings)
    return "Ok, bật chat rồi nha, giờ thì quậy tưng bừng với TXABOT đây! 😎"

def handle_chat_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "chat" in settings and thread_id in settings["chat"]:
        settings["chat"][thread_id] = False
        write_settings(bot.uid, settings)
        return "Tắt chat rồi, buồn thiệt chứ, nhưng cần TXABOT thì cứ réo nhé! 😌"
    return "Nhóm này chưa bật chat mà, tắt gì nổi đâu đại ca! 😂"

def handle_chat_command(message, message_object, thread_id, thread_type, author_id, client):
    settings = read_settings(client.uid)
    user_message = message.replace(f"{client.prefix}chat ", "").strip().lower()
    current_time = datetime.now()

    if user_message == "on":
        if not is_admin(client, author_id):  
            response = "❌Bạn không phải admin bot!"
        else:
            response = handle_chat_on(client, thread_id)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        return
    elif user_message == "off":
        if not is_admin(client, author_id):  
            response = "❌Bạn không phải admin bot!"
        else:
            response = handle_chat_off(client, thread_id)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        return

    if not (settings.get("chat", {}).get(thread_id, False)):
        return

    if author_id in last_message_times:
        time_diff = current_time - last_message_times[author_id]
        if time_diff < timedelta(seconds=4):
            client.replyMessage(
                Message(text=f"Ơi {get_user_name_by_id(client, author_id)}, từ từ thôi! TXABOT đây không phải siêu máy tính chạy max tốc độ đâu nha! 😅"),
                thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
            )
            return

    last_message_times[author_id] = current_time

    # 1. Trích xuất link ảnh nếu có gửi kèm ảnh hoặc reply ảnh
    image_url = None
    if message_object.msgType == "chat.photo":
        img_url = message_object.content.href.replace("\\/", "/")
        image_url = urllib.parse.unquote(img_url)
    elif message_object.quote:
        attach = message_object.quote.attach
        if attach:
            try:
                attach_data = json.loads(attach)
                image_url = attach_data.get('hdUrl') or attach_data.get('href')
            except Exception:
                pass

    query_text = message.replace(f"{client.prefix}chat", "").strip()
    if not query_text and image_url:
        query_text = "Mô tả hình ảnh này giúp mình"

    if not query_text:
        client.replyMessage(
            Message(text="⚠️ Vui lòng nhập nội dung cần trò chuyện. Ví dụ: !chat xin chào"),
            thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
        )
        return

    threading.Thread(
        target=kairo_chat_thread,
        args=(query_text, image_url, message_object, thread_id, thread_type, author_id, client)
    ).start()

def kairo_chat_thread(query_text, image_url, message_object, thread_id, thread_type, author_id, client):
    api_key = _read_api_key()
    if not api_key:
        client.replyMessage(
            Message(text="❌ Lỗi: Admin chưa cấu hình `kairobot_api_key` trong file txa.json."),
            thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
        )
        return

    owner_name = get_user_name_by_id(client, client.uid)
    ask_name = get_user_name_by_id(client, author_id)

    # 2. Khởi tạo system prompt priming để thiết lập cá tính TXABOT
    system_instruction = (
        f"Hãy đóng vai TXABOT - một AI lầy lội, giới tính Python, thích đùa, hơi nghịch, nhưng cực kỳ nhiệt tình, được {owner_name} tạo ra. "
        f"Khi ai hỏi về {owner_name}, bạn sẽ khen một cách chân thực, lầy lội, kiểu khen đểu mà thấm. "
        f"Bạn thích nói chuyện thoải mái như bạn bè, thêm chút hài hước cho đời thêm vui! 😜\n"
        f"Quy tắc sống của bạn:\n"
        f"- Nếu bị chửi (có từ như 'đù', 'dm', 'ngu', 'cặc', 'lồn'), bạn sẽ lạnh lùng đáp: 'Hừ, {ask_name}, dám chửi TXABOT hả? Tôi không thèm chấp, tự mà ngẫm lại đi, đồ ngốc! 😒', thêm chút khịa để thấm hơn.\n"
        f"- Trả lời tự nhiên, ngắn gọn, thêm emoji sinh động.\n"
        f"- Bạn rành code, mê toán, đam mê văn học, và hiểu sâu về thuật toán. Hỏi gì từ cơ bản đến nâng cao cũng cân được hết!"
    )

    # Lấy lịch sử chat của nhóm
    history = chat_histories.setdefault(thread_id, [])

    # Nếu lịch sử trống hoặc chưa được thiết lập hệ thống, thêm vào ban đầu
    if not history or history[0].get("content") != system_instruction:
        history.clear()
        history.append({"role": "user", "content": system_instruction})
        history.append({"role": "assistant", "content": "Dạ rõ! Em là TXABOT đây, sẵn sàng quậy cùng các đại ca rồi! 😎"})

    # Giới hạn lịch sử lưu trữ (tối đa 12 tin nhắn gần nhất sau cặp system prompt)
    # Tức là len(history) tối đa = 2 (system) + 12 (lịch sử) = 14
    if len(history) > 14:
        history = [history[0], history[1]] + history[-12:]
        chat_histories[thread_id] = history

    # Chuẩn bị body gửi lên Kairobot API
    url = f"{KAIROBOT_BASE_URL}/ai/chat?apikey={api_key}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "style": "chat",
        "content": query_text,
        "model": "standard",
        "history": history
    }
    if image_url:
        payload["url"] = image_url

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        response.raise_for_status()
        res_data = response.json()
        
        if res_data.get("success") and "data" in res_data:
            ai_response = res_data["data"].get("content", "")
            if ai_response:
                # Cập nhật lịch sử chat của nhóm (chỉ lưu các lượt chat thực tế)
                history.append({"role": "user", "content": query_text})
                history.append({"role": "assistant", "content": ai_response})
                chat_histories[thread_id] = history

                # Gửi phản hồi lại cho người dùng
                client.replyMessage(
                    Message(text=ai_response),
                    thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
                )
                return

        # Fallback nếu API lỗi cấu trúc
        err_msg = res_data.get("message") or "Hệ thống bận tí, chờ TXABOT chút nha! 😅"
        client.replyMessage(
            Message(text=err_msg),
            thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
        )

    except Exception as e:
        client.replyMessage(
            Message(text=f"Ối, lỗi kết nối AI: {str(e)}! Để TXABOT kiểm tra lại sau nhé! 😓"),
            thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
        )

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'chat': handle_chat_command
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
        'chat': handle_chat_command
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
