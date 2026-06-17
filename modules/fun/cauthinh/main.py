import random
import threading
import requests
import os
import json
import re
import time
from datetime import datetime, timedelta
from core.bot_sys import is_admin, read_settings, write_settings
from zlapi.models import Message, Mention

user_contexts = {}
last_message_times = {}
last_gemini_call = {}  # Rate limiting for Gemini API

def _read_gemini_api_key():
    """Read Gemini API key from environment or config file."""
    for key in ("GEMINI_API_KEY", "GEMINI_APIKEY"):
        value = os.getenv(key)
        if value:
            return value.strip()

    try:
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../txa.json"))
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        bot_data = (config.get("data") or [{}])[0]
        for key in ("gemini_api_key", "gemini_apikey", "apikey", "api_key"):
            value = bot_data.get(key)
            if value:
                return str(value).strip()
    except Exception:
        pass
    return ""

THA_THINH_MAU = {
    "Nguyên": "Anh như nguyên tố quý, chỉ cần Nguyên để trái tim anh trọn vẹn.",
    "Tâm": "Anh là đường tròn hoàn hảo, vì có Tâm là trung tâm của trái tim anh.",
    "Hương": "Trái tim anh như cánh đồng, chỉ cần Hương là đủ để thơm ngát cả đời.",
    "Anh": "Siêu anh hùng chỉ trong phim, còn siêu yêu Anh chỉ trong tim em đây.",
    "Duyên": "Anh là sợi dây đỏ, chỉ cần Duyên là đủ để buộc tim anh mãi mãi.",
    "Mai": "Trái tim anh là mùa đông lạnh, chỉ cần Mai là đủ để xuân về rực rỡ.",
    "Lan": "Anh là khu vườn trống, chỉ cần Lan là đủ để tim anh ngập tràn hoa.",
    "Thu": "Mùa thu gió nhẹ thoảng qua, nhưng tim anh chỉ đắm say mỗi Thu thôi.",
    "Bảo": "Trái tim anh là kho báu, và Bảo là viên ngọc quý nhất anh tìm thấy.",
    "Hạnh": "Anh là bầu trời u ám, chỉ cần Hạnh là đủ để tim anh rạng ngời hạnh phúc.",
    "Linh": "Trái tim anh là cỗ máy, chỉ có Linh mới làm nó rung lên từng nhịp.",
    "My": "Anh là cuốn sách trắng, chỉ cần My là đủ để viết nên chuyện tình đẹp.",
    "Kiều": "Trái tim anh là bức tranh, chỉ cần Kiều là nét vẽ hoàn mỹ cuối cùng.",
    "Diễm": "Anh là ngọn lửa nhỏ, chỉ cần Diễm là đủ để tim anh bùng cháy yêu thương.",
    "Vân": "Trái tim anh là bầu trời, chỉ có Vân mới làm nó nhẹ nhàng trôi mãi.",
    "Thảo": "Anh là cánh đồng khô, chỉ cần Thảo là đủ để tim anh xanh mát tình yêu.",
    "Tú": "Trái tim anh là đêm tối, chỉ cần Tú là ngôi sao sáng nhất anh ngắm hoài.",
    "Cẩm": "Anh là tấm vải thô, chỉ cần Cẩm là đủ để tim anh hóa lụa yêu thương.",
    "Ngọc": "Trái tim anh là vỏ sò, chỉ cần Ngọc là viên ngọc sáng nhất bên trong.",
    "Lệ": "Anh là bầu trời khô hạn, chỉ cần Lệ là giọt sương làm tim anh đắm say.",
    "Thuý": "Trái tim anh là mùa hè nóng, chỉ cần Thuý là đủ để mát lành tình yêu.",
    "Quỳnh": "Anh là đêm đen tĩnh lặng, chỉ cần Quỳnh là hoa nở rực rỡ trong tim.",
    "Hải": "Trái tim anh là bờ cát, chỉ cần Hải là sóng cuốn anh vào biển tình.",
    "Bích": "Anh là viên đá thô, chỉ cần Bích là đủ để tim anh hóa ngọc quý.",
    "Hoa": "Trái tim anh là đất khô, chỉ cần Hoa là đủ để nở rộ tình yêu bất tận.",
    "Thùy": "Anh là bến sông vắng, chỉ cần Thùy là sóng vỗ mãi trong tim anh.",
    "Nhung": "Trái tim anh là mùa đông lạnh, chỉ cần Nhung là đủ để ấm áp yêu thương.",
    "Ngân": "Anh là bản nhạc trầm, chỉ cần Ngân là nốt cao làm tim anh rung động.",
    "Shin": "Trái tim anh là bóng tối, chỉ cần Shin là ánh sáng làm anh mê đắm.",
    "Thủy": "Anh là sa mạc khô cằn, chỉ cần Thủy là dòng suối làm tim anh hồi sinh."
}

def generate_tha_thinh(ten):
    ten = ten.capitalize()
    if ten in THA_THINH_MAU:
        return THA_THINH_MAU[ten]
    else:
        templates = [
            f"Người ta cần lý do để thích ai đó, còn anh gặp {ten} là thích luôn rồi.",
            f"Nếu trái tim có mật khẩu thì chắc {ten} là dãy số duy nhất mở được tim anh.",
            f"Anh từng nghĩ mình ổn một mình, cho tới khi gặp {ten}.",
            f"Thời tiết hôm nay thế nào anh không biết, nhưng nhìn thấy {ten} là tim anh nắng rồi.",
            f"Người khác mang đến cảm xúc, còn {ten} mang đến cảm giác muốn ở cạnh thật lâu.",
            f"Anh không giỏi thả thính, nhưng đứng trước {ten} thì câu nào cũng thành lời tỏ tình.",
            f"Có hàng nghìn cái tên đẹp, nhưng với anh {ten} vẫn là cái tên làm tim rung động nhất.",
            f"Nếu được chọn lại từ đầu, anh vẫn muốn gặp {ten} sớm hơn một chút.",
            f"Anh không tin yêu từ cái nhìn đầu tiên, cho tới khi nhìn thấy {ten}.",
            f"Trên bản đồ có rất nhiều nơi để đến, còn trong tim anh chỉ có chỗ dành cho {ten}."
        ]
        return random.choice(templates)

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        name = user_info.zaloName or user_info.displayName or ""
        name = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
        return name or "Unknown User"
    except Exception:
        return "Unknown User"

def gemini_scrip(context_prompt, message_object, thread_id, thread_type, author_id, client):
    # Check API key
    api_key = _read_gemini_api_key()
    if not api_key:
        text_to_use = message_object.text if message_object.text else "bạn"
        words = text_to_use.split() if text_to_use else ["bạn"]
        tha_thinh_message = generate_tha_thinh(words[-1])
        client.replyMessage(
            Message(text=f"⚠️ Chưa cấu hình gemini_api_key trong txa.json!\n{tha_thinh_message}"),
            thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
        )
        return

    # Rate limiting - wait at least 2 seconds between API calls
    current_time = datetime.now()
    if author_id in last_gemini_call:
        time_diff = current_time - last_gemini_call[author_id]
        if time_diff < timedelta(seconds=2):
            time.sleep(2 - time_diff.total_seconds())
    last_gemini_call[author_id] = current_time

    headers = {'Content-Type': 'application/json'}
    params = {'key': api_key}
    json_data = {'contents': [{'parts': [{'text': context_prompt}]}]}

    try:
        response = requests.post(
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent',
            params=params, headers=headers, json=json_data,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            candidate = result['candidates'][0]
            content = candidate.get('content', {}).get('parts', [])
            if content and 'text' in content[0]:
                response_text = content[0]['text'].replace('*', '')
                if "tên trường" in response_text.lower() or not response_text.strip():
                    text_to_use = message_object.text if message_object.text else "bạn"
                    words = text_to_use.split() if text_to_use else ["bạn"]
                    response_text = generate_tha_thinh(words[-1])
                client.replyMessage(
                    Message(text=response_text),
                    thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
                )
                if author_id not in user_contexts:
                    user_contexts[author_id] = {'chat_history': []}
                user_contexts[author_id]['chat_history'][-1]['bot'] = response_text
                return
        text_to_use = message_object.text if message_object.text else "bạn"
        words = text_to_use.split() if text_to_use else ["bạn"]
        tha_thinh_message = generate_tha_thinh(words[-1])
        client.replyMessage(
            Message(text=tha_thinh_message),
            thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
        )
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        # Handle case where message_object.text is None
        text_to_use = message_object.text if message_object.text else "bạn"
        words = text_to_use.split() if text_to_use else ["bạn"]
        tha_thinh_message = generate_tha_thinh(words[-1])
        client.replyMessage(
            Message(text=tha_thinh_message),
            thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
        )

def handle_love_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "love" not in settings:
        settings["love"] = {}
    settings["love"][thread_id] = True
    write_settings(bot.uid, settings)
    return f"🚦Lệnh {bot.prefix}love đã được Bật 🚀 trong nhóm này ✅"

def handle_love_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "love" in settings and thread_id in settings["love"]:
        settings["love"][thread_id] = False
        write_settings(bot.uid, settings)
        return f"🚦Lệnh {bot.prefix}love đã Tắt ⭕️ trong nhóm này ✅"
    return "🚦Nhóm chưa có thông tin cấu hình love để ⭕️ Tắt 🤗"

def handle_tha_thinh_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        settings = read_settings(client.uid)
    
        cmd = message.strip()[len(client.prefix):].split()[0].lower()
        user_message = message.replace(f"{client.prefix}{cmd} ", "") if f"{client.prefix}{cmd} " in message else ""
        user_message = user_message.strip().lower()

        if user_message == "on":
            if not is_admin(client, author_id):  
                    response = "❌Bạn không phải admin bot!"
            else:
                response = handle_love_on(client, thread_id)
            client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        elif user_message == "off":
            if not is_admin(client, author_id):  
                response = "❌Bạn không phải admin bot!"
            else:
                response = handle_love_off(client, thread_id)
            client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        
        if not (settings.get("love", {}).get(thread_id, False)):
            return
        
        if not user_message:
            client.send(
                Message(text=f"Vui lòng chỉ nhập tên 1 chữ để thả thính. Ví dụ: '{client.prefix}{cmd} Shin' hoặc '{client.prefix}{cmd} Thủy'"),
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=15000
            )
            return

        parts = user_message.split()
        if len(parts) != 1:
            client.send(
                Message(text=f"Vui lòng chỉ nhập tên 1 chữ để thả thính. Ví dụ: '{client.prefix}{cmd} Shin' hoặc '{client.prefix}{cmd} Thủy'"),
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=15000
            )
            return

        ten = parts[0].strip()
        if ' ' in ten or not ten.isalpha():
            client.send(
                Message(text="Tên phải là 1 chữ cái duy nhất"),
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=15000
            )
            return

        tha_thinh_message = generate_tha_thinh(ten)
        mention_text = f"@{ten}"
        mention = Mention(author_id, length=len(mention_text), offset=0)
        user_message = f"{mention_text}, {tha_thinh_message}"

        current_time = datetime.now()
        if author_id in last_message_times:
            time_diff = current_time - last_message_times[author_id]
            if time_diff < timedelta(seconds=5):
                client.send(
                    Message(text="Vui lòng chờ 5 giây trước khi thả thính tiếp!"),
                    thread_id=thread_id,
                    thread_type=thread_type,
                    ttl=15000
                )
                return

        last_message_times[author_id] = current_time

        if author_id not in user_contexts:
            user_contexts[author_id] = {'chat_history': []}
        user_contexts[author_id]['chat_history'].append({'user': user_message, 'bot': ''})

        context_prompt = f"""
Hãy tạo 1 câu thả thính bằng tiếng Việt.

Yêu cầu:
- Dưới 30 từ.
- Cực tự nhiên.
- Văn phong Gen Z.
- Không dùng mô típ bài toán, chìa khóa, cánh cửa, đường tròn.
- Không triết lý.
- Không hỏi thêm thông tin.
- Không emoji.
- Phải lồng tên "{ten}" vào câu.
- Nghe như người thật đang tán tỉnh.

Chỉ trả về duy nhất câu thả thính.
"""

        threading.Thread(target=gemini_scrip, args=(context_prompt, message_object, thread_id, thread_type, author_id, client)).start()

    except Exception as e:
        print(f"Lỗi khi xử lý lệnh thả thính: {str(e)}")
        tha_thinh_message = generate_tha_thinh(user_message)
        client.send(
            Message(text=f"@{user_message}, {tha_thinh_message}"),
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=15000
        )

txa = {
    "name": "pro_thinh",
    "desc": {
        "tha_thinh": "Thả thính đối phương",
        "thathinh": "Thả thính đối phương",
        "love": "Thả thính/Xem độ hợp"
    },
    "author": "TXA",
    "command": ['tha_thinh', 'thathinh', 'love']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'tha_thinh': handle_tha_thinh_command,
        'thathinh': handle_tha_thinh_command,
        'love': handle_tha_thinh_command
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
