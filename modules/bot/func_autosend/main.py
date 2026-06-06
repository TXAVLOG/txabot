from config import prefix
from datetime import datetime, timedelta
import os
import random
import threading
import time
from zlapi.models import *
import pytz
import requests
import json
from core.bot_sys import get_user_name_by_id, read_settings, write_settings, is_admin
from modules.utils.image_sender import ImageSender

# Danh sách thể loại nội dung
CONTENT_TYPES = {
    "vdgirl": {"type": "video", "desc": "Video gái"},
    "vdcos": {"type": "video", "desc": "Video cosplay"},
    "vdanime": {"type": "video", "desc": "Video anime"},
    "vdsexy": {"type": "video", "desc": "Video sexy"},
    "girl": {"type": "image", "desc": "Ảnh gái"},
    "cosplay": {"type": "image", "desc": "Ảnh cosplay"},
    "anime": {"type": "image", "desc": "Ảnh anime"},
    "boy": {"type": "image", "desc": "Ảnh trai"},
    "girlsexy": {"type": "image", "desc": "Ảnh gái sexy"},
    "mixed": {"type": "mixed", "desc": "Trộn lẫn tất cả thể loại"},
}

# Greeting đa dạng hơn
time_greetings = {
    "01:00": [
        "🌙✨ Đêm khuya rồi, ngủ ngon nhé bạn!",
        "🌌💤 Một đêm thật yên bình, chúc bạn ngủ sâu giấc mơ đẹp!",
        "🌃❄️ Giờ này rồi, hãy nghỉ ngơi, chuẩn bị cho ngày mới!",
        "🌜🌠 Trăng dịu dàng, giấc mơ bay, ngủ thật ngon!",
        "✨🌙 Chúc bạn một đêm ngon giấc và mơ đẹp!",
        "🌌💫 Sao lung linh, đêm yên bình, ngủ ngon nha!",
        "🌃🌬️ Khuya tĩnh lặng, hãy thư giãn, nghỉ ngơi!",
        "🌙❄️ Đêm lạnh, chăn ấm, ngủ ngon bạn nhé!",
        "🌠✨ Một đêm thật đẹp, chúc bạn ngủ sâu giấc!",
        "🌜🌌 Đừng thức khuya quá, nghỉ ngơi thôi!"
    ],
    "02:30": [
        "🌙🌌 Đêm khuya, ngủ ngon nhé!",
        "🌃✨ Đêm tĩnh lặng, giấc mơ đẹp!",
        "🌜💤 Gió khuya ru, ngủ sâu giấc!",
        "🌠❄️ Đêm lạnh, chăn ấm, nghỉ ngơi!",
        "✨🌙 Chúc bạn ngủ ngon và mơ đẹp!",
        "🌌💫 Sao lấp lánh, đêm yên bình!",
        "🌃🌬️ Khuya yên bình, thư giãn nhé!",
        "🌙❄️ Đêm sâu thẳm, nghỉ ngơi thôi!"
    ],
    "04:00": [
        "🌃🌙 Đêm khuya, sắp bình minh rồi!",
        "🌜✨ 4 giờ sáng, chuẩn bị cho ngày mới!",
        "🌌💤 Đêm sắp qua, ngủ ngon nhé!",
        "🌠❄️ Bình minh sắp đến, nghỉ ngơi thêm chút!",
        "✨🌙 Đêm cuối, chuẩn bị tinh thần!",
        "🌃💫 Sao sắp tắt, bình minh sắp lên!"
    ],
    "05:30": [
        "🌅☀️ Bình minh đến rồi, chào ngày mới!",
        "☀️✨ Sáng tươi mới, một ngày tốt lành!",
        "🌞💫 5 rưỡi sáng, bắt đầu ngày mới nhé!",
        "🌻❀ Nắng ban mai, năng lượng đầy!",
        "✨🌅 Chúc bạn một ngày thật vui vẻ!",
        "☀️🌬️ Gió mát sáng, bắt đầu thôi!"
    ],
    "07:00": [
        "🌞☀️ Sáng rực rỡ, dậy thôi nào!",
        "☀️✨ 7 giờ sáng, chào buổi sáng!",
        "🌅💫 Một ngày mới, năng lượng mới!",
        "🌻❀ Nắng đẹp, một ngày tốt lành!",
        "✨🌞 Chúc bạn có một ngày hiệu quả!",
        "☀️🌬️ Gió mát, tinh thần sảng khoái!"
    ],
    "08:30": [
        "🌞☕ Sáng hiệu quả, làm việc thôi!",
        "☕✨ 8 rưỡi sáng, uống cafe và làm việc!",
        "🌻💫 Nắng ban mai, năng lượng đầy!",
        "✨🌞 Một buổi sáng thật năng động!",
        "☀️🌬️ Gió mát, làm việc hiệu quả!"
    ],
    "10:06": [
        "🌞⏰ 10 giờ sáng, tiếp tục làm việc!",
        "☀️✨ Nắng rực rỡ, cố lên nào!",
        "🌻💫 Sáng tươi mới, làm thật tốt!",
        "✨🌞 Giữ vững tinh thần nhé!",
        "☕❀ Uống thêm nước, làm việc tiếp!"
    ],
    "11:30": [
        "🌞🍽️ Gần trưa, chuẩn bị ăn nhé!",
        "☀️✨ 11 rưỡi sáng, nghỉ ngơi chút!",
        "🌻💤 Nắng ban trưa, thư giãn thôi!",
        "✨⏰ Trưa yên bình, ăn ngon miệng!",
        "☕❀ Giờ nghỉ trưa, thư giãn nhé!"
    ],
    "13:00": [
        "🌞⏰ 1 giờ chiều, làm việc tiếp!",
        "☀️✨ Nắng chiều, tinh thần sảng khoái!",
        "🌻💫 Chiều tươi mới, cố lên nào!",
        "✨🌞 Một buổi chiều thật hiệu quả!",
        "☕❀ Uống thêm nước, làm việc nhé!"
    ],
    "14:30": [
        "🌞🌻 Chiều lãng mạn, vui vẻ nào!",
        "☀️✨ 2 rưỡi chiều, thư giãn chút!",
        "🌅💫 Nắng chiều, năng lượng đầy!",
        "✨⏰ Chiều rực rỡ, vui vẻ nhé!",
        "☕❀ Gió chiều mát, thư giãn!"
    ],
    "16:00": [
        "🌅✨ Chiều dần trôi, thư giãn nào!",
        "☀️🌻 4 giờ chiều, nghỉ ngơi nhé!",
        "🌞💫 Nắng nhạt dần, thư giãn thôi!",
        "✨⏰ Chiều yên bình, vui vẻ nhé!",
        "☕❀ Giờ chiều, thư giãn chút!"
    ],
    "17:30": [
        "🌅🌞 Hoàng hôn đến, thư giãn nào!",
        "☀️✨ 5 rưỡi chiều, chuẩn bị về!",
        "🌻💤 Nắng chiều tà, thư giãn thôi!",
        "✨⏰ Hoàng hôn đẹp, vui vẻ nhé!",
        "☕❀ Giờ này, thư giãn rồi!"
    ],
    "19:00": [
        "🌙✨ Tối đến, ăn ngon miệng!",
        "🌌💤 7 giờ tối, nghỉ ngơi nhé!",
        "🌜❄️ Tối yên bình, thư giãn thôi!",
        "✨🍽️ Tối đẹp, ăn ngon miệng!",
        "☕🌙 Tối mát mẻ, thư giãn!"
    ],
    "20:30": [
        "🌙✨ Sắp ngủ, thư giãn nhé!",
        "🌌💤 8 rưỡi tối, nghỉ ngơi thôi!",
        "🌜❄️ Tối tĩnh lặng, thư giãn!",
        "✨⏰ Tối dịu dàng, thư giãn!",
        "☕🌙 Gió tối mát, thư giãn!"
    ],
    "22:06": [
        "🌙🌌 Đêm khuya, ngủ ngon nhé!",
        "🌃✨ 10 giờ tối, chuẩn bị ngủ!",
        "🌜💤 Giờ này rồi, ngủ thôi!",
        "✨⏰ Đêm yên bình, ngủ ngon!",
        "☕🌙 Đêm lạnh, ngủ sâu giấc!"
    ],
    "23:30": [
        "🌙✨ Khuya rồi, ngủ thôi!",
        "🌌💤 11 rưỡi tối, ngủ ngon!",
        "🌜❄️ Đêm tĩnh lặng, ngủ sâu!",
        "✨⏰ Giờ này, nghỉ ngơi!",
        "☕🌙 Đêm đẹp, ngủ ngon!"
    ],
    "00:00": [
        "🌙🌌 Nửa đêm, chúc bạn ngủ ngon!",
        "🌃✨ 12 giờ khuya, nghỉ ngơi!",
        "🌜💤 Đêm sâu, ngủ thật sâu!",
        "✨⏰ Nửa đêm, thư giãn!",
        "☕🌙 Đêm đẹp, mơ đẹp nhé!"
    ]
}

vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
image_sender = ImageSender()

def get_content_type_setting(bot, thread_id):
    settings = read_settings(bot.uid)
    if "autosend_content" not in settings:
        settings["autosend_content"] = {}
    return settings["autosend_content"].get(thread_id, "mixed")

def set_content_type_setting(bot, thread_id, content_type):
    settings = read_settings(bot.uid)
    if "autosend_content" not in settings:
        settings["autosend_content"] = {}
    settings["autosend_content"][thread_id] = content_type
    write_settings(bot.uid, settings)

def handle_autosend_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "autosend" not in settings:
        settings["autosend"] = {}
    settings["autosend"][thread_id] = True
    allowed_thread_ids = settings.get("allowed_thread_ids", [])
    if thread_id not in allowed_thread_ids:
        allowed_thread_ids.append(thread_id)
        settings["allowed_thread_ids"] = allowed_thread_ids
    write_settings(bot.uid, settings)
    
    content_type = get_content_type_setting(bot, thread_id)
    content_desc = CONTENT_TYPES[content_type]["desc"]
    
    return (
        f"🚦 Lệnh {prefix}autosend đã được Bật 🚀 trong nhóm này ✅\n"
        f"📂 Thể loại nội dung hiện tại: {content_desc}\n"
        f"⏰ Bot sẽ gửi nội dung theo lịch, không gửi ngay lập tức.\n"
        f"💡 Dùng {prefix}autosend type [tên thể loại] để thay đổi thể loại!"
    )

def handle_autosend_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "autosend" in settings and thread_id in settings["autosend"]:
        settings["autosend"][thread_id] = False
        write_settings(bot.uid, settings)
        return f"🚦 Lệnh {prefix}autosend đã Tắt ⭕️ trong nhóm này ✅"
    return "🚦 Nhóm chưa có thông tin cấu hình autosend để ⭕️ Tắt 🤗"

def handle_autosend_type(bot, thread_id, content_type):
    if content_type not in CONTENT_TYPES:
        type_list = "\n".join([f"• {k}: {v['desc']}" for k, v in CONTENT_TYPES.items()])
        return (
            f"❌ Thể loại '{content_type}' không hợp lệ!\n"
            f"📋 Danh sách thể loại hỗ trợ:\n{type_list}"
        )
    
    set_content_type_setting(bot, thread_id, content_type)
    content_desc = CONTENT_TYPES[content_type]["desc"]
    return f"✅ Đã đổi thể loại nội dung autosend thành: {content_desc}!"

def get_random_content_type():
    types = list(CONTENT_TYPES.keys())
    types.remove("mixed")
    return random.choice(types)

def send_content(bot, thread_id, content_type, message):
    try:
        config = CONTENT_TYPES[content_type]
        
        if config["type"] == "video":
            data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data-send")
            video_file = os.path.join(data_dir, f"{content_type}.txt")
            if os.path.exists(video_file):
                with open(video_file, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                if urls:
                    video_url = random.choice(urls)
                    # Check URL
                    try:
                        video_check = requests.head(video_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                        if video_check.status_code != 200:
                            raise ValueError("URL không hợp lệ")
                    except Exception as e:
                        print(f"❌ Video URL lỗi: {e}")
                        return False
                    
                    thumbnail_url = "https://f66-zpg-r.zdn.vn/jxl/8107149848477004187/d08a4d364d8cf9d2a09d.jxl"
                    duration = '1000000'
                    
                    bot.sendRemoteVideo(
                        video_url,
                        thumbnail_url,
                        duration=duration,
                        message=Message(text=message),
                        thread_id=thread_id,
                        thread_type=ThreadType.GROUP,
                        width=1080,
                        height=1920,
                        ttl=3600000
                    )
                    return True
        
        elif config["type"] == "image":
            error = image_sender.send_image(
                bot=bot,
                thread_id=thread_id,
                thread_type=ThreadType.GROUP,
                type_name=content_type,
                custom_caption=message
            )
            return error is None
        
        elif config["type"] == "mixed":
            random_type = get_random_content_type()
            return send_content(bot, thread_id, random_type, message)
    
    except Exception as e:
        print(f"❌ Lỗi khi gửi nội dung: {e}")
    
    return False

def autosend_task(client):
    last_sent_time = {}
    
    while True:
        try:
            settings = read_settings(client.uid)
            if not settings.get("autosend"):
                time.sleep(30)
                continue
                
            now = datetime.now(vn_tz)
            current_time_str = now.strftime("%H:%M")
            
            if current_time_str in time_greetings:
                greeting = random.choice(time_greetings[current_time_str])
                formatted_message = f"🚦 {greeting}\n⏰ {current_time_str} - Bot: {get_user_name_by_id(client, client.uid)}"
                
                allowed_groups = settings.get("allowed_thread_ids", [])
                for thread_id, enabled in settings["autosend"].items():
                    if not enabled or thread_id not in allowed_groups:
                        continue
                        
                    if thread_id not in last_sent_time or (now - last_sent_time.get(thread_id, now) >= timedelta(minutes=1)):
                        content_type = get_content_type_setting(client, thread_id)
                        success = send_content(client, thread_id, content_type, formatted_message)
                        if success:
                            last_sent_time[thread_id] = now
                            print(f"✅ Đã gửi nội dung đến {thread_id} (type: {content_type})")
                        time.sleep(0.3)
                            
        except Exception as e:
            print(f"❌ Lỗi trong autosend_task: {e}")
            
        time.sleep(30)

def start_autosend_thread(client):
    if not hasattr(client, 'autosend_thread') or not client.autosend_thread.is_alive():
        client.autosend_thread = threading.Thread(target=autosend_task, args=(client,), daemon=True)
        client.autosend_thread.start()

def start_autosend_handle(client, thread_type, message_object, message, thread_id, author_id):
    parts = message.replace(f"{prefix}autosend ", "").strip().lower().split()
    
    if len(parts) == 0:
        response = (
            f"📋 Hướng dẫn sử dụng {prefix}autosend:\n"
            f"• {prefix}autosend on: Bật tính năng\n"
            f"• {prefix}autosend off: Tắt tính năng\n"
            f"• {prefix}autosend type [tên thể loại]: Thay đổi thể loại nội dung\n"
            f"• {prefix}autosend list: Xem danh sách thể loại"
        )
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        return
    
    action = parts[0]
    
    if action == "on":
        if not is_admin(client, author_id):
            client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        response = handle_autosend_on(client, thread_id)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        start_autosend_thread(client)
            
    elif action == "off":
        if not is_admin(client, author_id):
            client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        response = handle_autosend_off(client, thread_id)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
    
    elif action == "type" and len(parts) >= 2:
        if not is_admin(client, author_id):
            client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        content_type = parts[1]
        response = handle_autosend_type(client, thread_id, content_type)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
    
    elif action == "list":
        type_list = "\n".join([f"• {k}: {v['desc']}" for k, v in CONTENT_TYPES.items()])
        response = f"📋 Danh sách thể loại nội dung autosend:\n{type_list}"
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
    
    else:
        response = (
            f"📋 Hướng dẫn sử dụng {prefix}autosend:\n"
            f"• {prefix}autosend on: Bật tính năng\n"
            f"• {prefix}autosend off: Tắt tính năng\n"
            f"• {prefix}autosend type [tên thể loại]: Thay đổi thể loại nội dung\n"
            f"• {prefix}autosend list: Xem danh sách thể loại"
        )
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)

txa = {
    "name": "pro_autosend",
    "desc": "Gửi tin nhắn tự động theo lịch trình. Hỗ trợ nhiều thể loại nội dung.",
    "author": "TXA",
    "command": ['autosend']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'autosend': start_autosend_handle
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
