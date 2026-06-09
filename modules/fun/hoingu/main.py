import json
import os
import random
import requests
from zlapi.models import Message

KAIROBOT_BASE_URL = os.getenv("KAIROBOT_BASE_URL", "https://kairobot.qzz.io").rstrip("/")
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../txa.json"))

txa = {
    "name": "Hỏi Ngu",
    "desc": {
        "hoingu": "Hỏi ngu hại não",
        "dongu": "Hỏi ngu hại não"
    },
    "author": "TXA",
    "command": ["hoingu", "dongu"]
}

# Local list of questions for fallback
FALLBACK_QUESTIONS = [
    "Tại sao gọi là bánh mì trong khi nó không làm từ mì?",
    "Nếu một con mèo rơi từ tầng 10 xuống luôn hạ cánh bằng chân, và một lát bánh mì phết bơ luôn hạ cánh bằng mặt có bơ, chuyện gì xảy ra nếu dán lát bánh mì lên lưng con mèo?",
    "Tại sao nút bấm trên máy tính lại gọi là 'phím'?",
    "Nếu bạn bắn một quả tên lửa vào mặt trời vào ban đêm, nó có bị cháy không?",
    "Tại sao nước biển lại mặn trong khi cá bơi dưới biển thì không mặn?",
    "Tại sao chúng ta nhắm mắt khi ngủ?",
    "Tại sao người ta gọi là rửa tay mà không gọi là giặt tay?",
    "Con gà có trước hay quả trứng có trước?",
    "Tại sao quả táo rớt xuống đất mà bong bóng lại bay lên trời?",
    "Nếu uống thuốc ngủ chung với cà phê thì chúng ta sẽ thức hay ngủ?"
]

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

def _api_get(path, params):
    api_key = _read_api_key()
    if not api_key:
        raise RuntimeError("Thiếu API key KaiRobot.")

    payload = dict(params)
    payload["apikey"] = api_key
    response = requests.get(f"{KAIROBOT_BASE_URL}{path}", params=payload, timeout=20)
    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text}

    if response.status_code == 401:
        msg = data.get("message") if isinstance(data, dict) else None
        raise RuntimeError(msg or "API key KaiRobot không hợp lệ.")
    response.raise_for_status()
    if isinstance(data, dict) and data.get("success") is False:
        raise RuntimeError(data.get("message") or data.get("error") or "API trả về trạng thái thất bại.")
    return data

def handle_hoingu_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Call stupid question API
        data = _api_get("/games/stupid-question", {})
        # If API returns success=true and contains question
        content = data.get("data", {}).get("question") or data.get("question") or data.get("data")
        if not content or content == "Nội dung không có sẵn":
            raise RuntimeError("API không trả về câu hỏi hợp lệ")
    except Exception as e:
        print(f"[Hỏi Ngu] Lỗi API: {e}. Sử dụng danh sách dự phòng...")
        content = random.choice(FALLBACK_QUESTIONS)

    client.replyMessage(
        Message(text=f"🤔 Câu hỏi hại não:\n> {content}"),
        message_object,
        thread_id,
        thread_type,
        ttl=120000
    )

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    handle_hoingu_command(message_text, message_object, thread_id, thread_type, author_id, bot)
