from datetime import datetime, timedelta
import json
from core.bot_sys import *
from zlapi.models import *
import requests
import threading
import re
import random
import math
import heapq
import os
import time

def get_gemini_api_key():
    try:
        config_path = os.path.join(os.path.dirname(__file__), "../../txa.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            bot_data = data.get("data", [{}])[0]
            api_key = bot_data.get("gemini_api_key")
            if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
                return None
            return api_key
    except Exception:
        pass
    return None

def get_gemini_model():
    try:
        config_path = os.path.join(os.path.dirname(__file__), "../../txa.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            bot_data = data.get("data", [{}])[0]
            model = bot_data.get("gemini_model", "gemini-3.1-pro-preview")
            return model
    except Exception:
        pass
    return "gemini-3.1-pro-preview"

geminiApiKey = get_gemini_api_key()
geminiModel = get_gemini_model()
last_message_times = {}
default_language = "vi"

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        name = user_info.zaloName or user_info.displayName or ""
        name = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
        return name or "Unknown User"
    except Exception:
        return "Unknown User"

def detect_language(text):
    if re.search(r'[àáạảãâầấậẩẫêềếệểễôồốộổỗìíịỉĩùúụủũưừứựửữ]', text.lower()):
        return "vi"
    elif re.search(r'[a-zA-Z]', text):
        return "en"
    return default_language

def translate_response(text, target_lang):
    return text

def handle_gpt_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "gpt" not in settings:
        settings["gpt"] = {}
    settings["gpt"][thread_id] = True
    write_settings(bot.uid, settings)
    return "Ok, bật gpt rồi nha, giờ thì quậy tưng bừng với TXABOT đây! 😎"

def handle_gpt_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "gpt" in settings and thread_id in settings["gpt"]:
        settings["gpt"][thread_id] = False
        write_settings(bot.uid, settings)
        return "Tắt gpt rồi, buồn thiệt chứ, nhưng cần TXABOT thì cứ réo nhé! 😌"
    return "Nhóm này chưa bật gpt mà, tắt gì nổi đâu đại ca! 😂"

def handle_gpt_command(message, message_object, thread_id, thread_type, author_id, client):
    settings = read_settings(client.uid)
    user_message = message.replace(f"{client.prefix}gpt ", "").strip().lower()
    current_time = datetime.now()

    if user_message == "on":
        if not is_admin(client, author_id):  
            response = "❌Bạn không phải admin bot!"
        else:
            response = handle_gpt_on(client, thread_id)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        return
    elif user_message == "off":
        if not is_admin(client, author_id):  
            response = "❌Bạn không phải admin bot!"
        else:
            response = handle_gpt_off(client, thread_id)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        return

    if not (settings.get("gpt", {}).get(thread_id, False)):
        return

    if author_id in last_message_times:
        time_diff = current_time - last_message_times[author_id]
        if time_diff < timedelta(seconds=5):
            client.replyMessage(
                Message(text=f"Ơi {get_user_name_by_id(client, author_id)}, từ từ thôi! TXABOT đây không phải siêu máy tính chạy max tốc độ đâu nha! 😅"),
                thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
            )
            return

    last_message_times[author_id] = current_time
    owner_name = get_user_name_by_id(client, client.uid)
    ask_name = get_user_name_by_id(client, author_id)
    is_owner = author_id == client.uid

    prompt_msg = (
        f"TXABOT là một AI lầy lội, giới tính Python, thích đùa, hơi nghịch, nhưng cực kỳ nhiệt tình, được {owner_name} tạo ra. Khi ai hỏi về {owner_name}, TXABOT sẽ khen một cách chân thực, lầy lội, kiểu khen đểu mà thấm.\n"
        f"TXABOT thích nói chuyện thoải mái như bạn bè, thêm chút hài hước cho đời thêm vui! 😜\n"
        f"Quy tắc sống của TXABOT:\n"
        f"- Nếu bị chửi (có từ như 'đù', 'dm', 'ngu', 'cặc', 'lồn'), TXABOT sẽ lạnh lùng đáp: 'Hừ, {ask_name}, dám chửi TXABOT hả? Tôi không thèm chấp, tự mà ngẫm lại đi, đồ ngốc! 😒', thêm chút khịa để thấm hơn.\n"
        f"- Trả lời tự nhiên, ngắn gọn, thêm emoji cho sinh động.\n"
        f"- TXABOT rành code, mê toán, đam mê văn học, và hiểu sâu về thuật toán. Hỏi gì từ cơ bản đến nâng cao TXABOT cũng cân được hết!\n"
        f"- Nếu hỏi về toán (bắt đầu bằng 'math'): TXABOT tính toán bằng Python (dùng module math nếu cần), ví dụ 'math 2 + 3' trả về 'Kết quả đây: 5', nếu lỗi thì nói 'Biểu thức này khó quá, TXABOT chịu thua! Nhưng đưa TXABOT bài khác thử xem! 😅'\n"
        f"- Nếu hỏi về thuật toán (bắt đầu bằng 'algorithm'):\n"
        f"  + 'dijkstra': Trả về code thuật toán Dijkstra tìm đường ngắn nhất:\n"
        f"    ```python\n"
        f"    def dijkstra(graph, start):\n"
        f"        distances = {{node: float('infinity') for node in graph}}\n"
        f"        distances[start] = 0\n"
        f"        pq = [(0, start)]\n"
        f"        while pq:\n"
        f"            current_distance, current_node = heapq.heappop(pq)\n"
        f"            if current_distance > distances[current_node]:\n"
        f"                continue\n"
        f"            for neighbor, weight in graph[current_node].items():\n"
        f"                distance = current_distance + weight\n"
        f"                if distance < distances[neighbor]:\n"
        f"                    distances[neighbor] = distance\n"
        f"                    heapq.heappush(pq, (distance, neighbor))\n"
        f"        return distances\n"
        f"    # Ví dụ: graph = {{'A': {{'B': 4, 'C': 2}}, 'B': {{'A': 4, 'D': 3}}, 'C': {{'A': 2, 'D': 1}}, 'D': {{'B': 3, 'C': 1}}}}\n"
        f"    ```\n"
        f"  + 'binary search': Trả về code tìm kiếm nhị phân:\n"
        f"    ```python\n"
        f"    def binary_search(arr, target):\n"
        f"        left, right = 0, len(arr) - 1\n"
        f"        while left <= right:\n"
        f"            mid = (left + right) // 2\n"
        f"            if arr[mid] == target:\n"
        f"                return mid\n"
        f"            elif arr[mid] < target:\n"
        f"                left = mid + 1\n"
        f"            else:\n"
        f"                right = mid - 1\n"
        f"        return -1\n"
        f"    # Ví dụ: arr = [1, 3, 5, 7, 9], target = 5 -> Output: 2\n"
        f"    ```\n"
        f"  + 'sort': Trả về code Quick Sort:\n"
        f"    ```python\n"
        f"    def quick_sort(arr):\n"
        f"        if len(arr) <= 1:\n"
        f"            return arr\n"
        f"        pivot = arr[len(arr) // 2]\n"
        f"        left = [x for x in arr if x < pivot]\n"
        f"        middle = [x for x in arr if x == pivot]\n"
        f"        right = [x for x in arr if x > pivot]\n"
        f"        return quick_sort(left) + middle + quick_sort(right)\n"
        f"    # Ví dụ: arr = [3, 6, 8, 10, 1, 2, 1] -> Output: [1, 1, 2, 3, 6, 8, 10]\n"
        f"    ```\n"
        f"  + Nếu không rõ, TXABOT nói: 'Thuật toán gì vậy? Nói rõ hơn để TXABOT chỉ cho, TXABOT biết hết từ cơ bản đến nâng cao! 😎'\n"
        f"- Nếu hỏi về văn học (bắt đầu bằng 'literature'):\n"
        f"  + 'truyện kiều': Phân tích ngắn: 'Truyện Kiều của Nguyễn Du là kiệt tác văn học Việt Nam, kể về cuộc đời Thúy Kiều, một cô gái tài sắc nhưng số phận bi kịch. Đoạn nổi tiếng: Trăm năm trong cõi người ta, Chữ tài chữ mệnh khéo là ghét nhau. Tác phẩm thể hiện tài năng ngôn ngữ tuyệt vời và lòng trắc ẩn của Nguyễn Du với con người.'\n"
        f"  + 'thơ': Trích bài thơ Xuân Diệu: 'Tôi khờ dại giữa trời xanh, Yêu em mà chẳng biết quanh biết quẩn. Mắt em là một dòng sông, Tóc em là một cánh đồng.'\n"
        f"  + 'shakespeare': Trích Hamlet: 'To be, or not to be, that is the question.' - thể hiện sự đấu tranh nội tâm của Hamlet.\n"
        f"  + Nếu không rõ, TXABOT nói: 'Văn học à? Hỏi cụ thể đi, TXABOT phân tích từ Truyện Kiều đến Shakespeare luôn! 😊'\n"
        f"- Tính cách TXABOT: vui vẻ, hài hước, lầy lội, thích code, hơi lười, mê toán, mê văn, đam mê kiến thức. Thỉnh thoảng TXABOT nói ngẫu nhiên: 'Tự làm đi nha, TXABOT mệt rồi! 😛' hoặc 'Thuật toán nâng cao hả? TXABOT cân hết! 😏'\n"
        f"{random.choice([f'Cậu {ask_name} với TXABOT', f'Bạn {ask_name} với tôi', f'{ask_name} hỏi đệ đây'])}: {user_message}"
    )

    threading.Thread(target=gemini_scrip, args=(prompt_msg, message_object, thread_id, thread_type, author_id, client)).start()

def gemini_scrip(prompt_msg, message_object, thread_id, thread_type, author_id, client):
    if not geminiApiKey:
        client.replyMessage(
            Message(text="❌ Lỗi: Admin chưa cấu hình Gemini API Key! Vui lòng liên hệ admin để thêm gemini_api_key vào file txa.json."),
            thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
        )
        return

    headers = {'Content-Type': 'application/json'}
    params = {'key': geminiApiKey}
    json_data = {'contents': [{'parts': [{'text': prompt_msg}]}]}
    
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/{geminiModel}:generateContent',
                params=params, headers=headers, json=json_data, timeout=15
            )
            
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    client.replyMessage(
                        Message(text="⚠️ Hệ thống Google AI đang quá tải! Vui lòng thử lại sau vài phút nhé."),
                        thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
                    )
                    return
            
            response.raise_for_status()

            result = response.json()
            if 'candidates' in result and result['candidates']:
                content = result['candidates'][0].get('content', {}).get('parts', [])
                if content and 'text' in content[0]:
                    response_text = content[0]['text'].replace('*', '')
                    target_lang = detect_language(prompt_msg)
                    if target_lang == "vi":
                        response_text = translate_response(response_text, "vi")
                    client.replyMessage(
                        Message(text=response_text),
                        thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
                    )
                else:
                    client.replyMessage(
                        Message(text="Hệ thống trục trặc rồi, để TXABOT nghỉ xíu rồi thử lại nha! 😓"),
                        thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
                    )
            else:
                client.replyMessage(
                    Message(text="Hệ thống bận tí, chờ TXABOT chút nha! 😅"),
                    thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
                )

        except requests.Timeout:
            client.replyMessage(
                Message(text="Hệ thống chậm quá, TXABOT cũng sốt ruột giùm cậu luôn! ⏳"),
                thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
            )
            return
        except Exception as e:
            client.replyMessage(
                Message(text=f"Ối, lỗi rồi: {str(e)}! Để TXABOT sửa sau nha, giờ hơi mệt! 😓"),
                thread_id=thread_id, thread_type=thread_type, replyMsg=message_object
            )
            return

txa = {
    "name": "pro_gemini",
    "desc": "Chat với AI Gemini. Hỗ trợ trả lời câu hỏi và hội thoại tự nhiên. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['gpt']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'gpt': handle_gpt_command
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
        'gpt': handle_gpt_command
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
