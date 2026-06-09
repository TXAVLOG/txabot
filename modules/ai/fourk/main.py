import json
import os
import time
import requests
import urllib.parse
import threading
from core.bot_sys import read_settings, write_settings, is_admin
from zlapi.models import Message, ThreadType

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

txa = {
    "name": "pro_4k",
    "desc": "Tăng chất lượng hình ảnh lên 4K bằng Kairobot AI. Hỗ trợ reply ảnh, gửi kèm ảnh hoặc nhập link ảnh.",
    "author": "TXA",
    "command": ['4k']
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

def download_image(url, save_path, timeout=20):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
    }
    response = requests.get(url, headers=headers, timeout=timeout, stream=True)
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return True

def handle_4k_command(message, message_object, thread_id, thread_type, author_id, client):
    msg_obj = message_object
    image_url = None

    # 1. Trích xuất ảnh trực tiếp từ tin nhắn
    if msg_obj.msgType == "chat.photo":
        img_url = msg_obj.content.href.replace("\\/", "/")
        image_url = urllib.parse.unquote(img_url)

    # 2. Trích xuất ảnh từ tin nhắn reply/quote
    elif msg_obj.quote:
        attach = msg_obj.quote.attach
        if attach:
            try:
                attach_data = json.loads(attach)
                image_url = attach_data.get('hdUrl') or attach_data.get('href')
            except Exception:
                pass

    # 3. Trích xuất ảnh từ tham số link truyền vào lệnh
    if not image_url:
        parts = message.split()
        if len(parts) > 1:
            url_candidate = parts[1].strip()
            if url_candidate.startswith("http://") or url_candidate.startswith("https://"):
                image_url = url_candidate

    if not image_url:
        client.replyMessage(
            Message(text="⚠️ Vui lòng phản hồi (reply) lệnh 4k vào một ảnh, hoặc gửi kèm ảnh với lệnh 4k, hoặc nhập link ảnh dạng: !4k <link_ảnh>"),
            message_object, thread_id, thread_type
        )
        return

    # Chạy xử lý trong luồng riêng biệt
    threading.Thread(
        target=kairo_4k_thread,
        args=(image_url, message_object, thread_id, thread_type, client)
    ).start()

def kairo_4k_thread(image_url, message_object, thread_id, thread_type, client):
    api_key = _read_api_key()
    if not api_key:
        client.replyMessage(
            Message(text="❌ Lỗi: Admin chưa cấu hình `kairobot_api_key` trong file txa.json."),
            message_object, thread_id, thread_type
        )
        return

    # Thông báo bắt đầu xử lý
    progress_msg = client.replyMessage(
        Message(text="✨ Đang xử lý tăng chất lượng ảnh lên 4K... Vui lòng đợi trong giây lát! 🚀"),
        message_object, thread_id, thread_type
    )

    api_url = f"{KAIROBOT_BASE_URL}/ai/4k"
    params = {
        "url": image_url,
        "version": "v2", # Mặc định dùng v2 ổn định nhất
        "apikey": api_key
    }

    try:
        response = requests.get(api_url, params=params, timeout=40)
        response.raise_for_status()
        res_data = response.json()

        if res_data.get("success") and "data" in res_data:
            upscaled_url = res_data["data"].get("url")
            if upscaled_url:
                # Tạo thư mục temp nếu chưa có
                temp_dir = "temp"
                os.makedirs(temp_dir, exist_ok=True)
                temp_file = os.path.join(temp_dir, f"4k_{int(time.time())}.jpg")

                try:
                    # Tải ảnh nâng cấp về cục bộ
                    download_image(upscaled_url, temp_file)
                    
                    # Gửi lại ảnh nét cho group chat
                    client.sendLocalImage(
                        temp_file,
                        thread_id=thread_id,
                        thread_type=thread_type,
                        message=Message(text="✅ Ảnh của bạn đã được nâng cấp lên 4K thành công! ✨"),
                        ttl=300000 # Hết hạn tự xóa sau 5 phút để dọn dẹp bộ nhớ chat
                    )
                finally:
                    # Dọn dẹp tệp tạm
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except Exception:
                            pass
                
                # Thu hồi tin nhắn trạng thái chờ
                if progress_msg:
                    try:
                        p_msg_id = progress_msg.get('msgId') or progress_msg.get('messageId')
                        p_cli_msg_id = progress_msg.get('cliMsgId') or progress_msg.get('clientMsgId')
                        if p_msg_id and p_cli_msg_id:
                            client.deleteGroupMsg(p_msg_id, client.uid, p_cli_msg_id, thread_id)
                    except Exception:
                        pass
                return

        # Nếu thất bại
        err_msg = res_data.get("message") or "Không thể xử lý ảnh vào lúc này."
        client.replyMessage(
            Message(text=f"❌ Thất bại: {err_msg}"),
            message_object, thread_id, thread_type
        )

    except Exception as e:
        client.replyMessage(
            Message(text=f"❌ Gặp lỗi trong quá trình xử lý ảnh: {str(e)}"),
            message_object, thread_id, thread_type
        )

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        '4k': handle_4k_command
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
