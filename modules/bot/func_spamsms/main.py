import time
import subprocess
import os
import json
from zlapi.models import *
import datetime

# File paths
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
BLACKLIST_PATH = os.path.join(MODULE_DIR, 'blacklist.json')
ADMIN_PATH = os.path.join(MODULE_DIR, 'list_admin.json')
DEC_PY_PATH = os.path.join(MODULE_DIR, 'dec.py')

last_sms_time = None
current_processing_number = None
cooldown = 300

txa = {
    "name": "pro_spamsms",
    "desc": "Spam SMS đến số điện thoại (Chỉ dành cho admin). Hỗ trợ blacklist và cooldown. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['sms'],
    "t-per": "admin",
    "help": {
        "sms": {
            "usage": [
                "{prefix}sms <sdt> <so_lan>",
                "{prefix}sms addblacklist <sdt>",
                "{prefix}sms removeblacklist <sdt>",
                "{prefix}sms show"
            ],
            "examples": [
                "{prefix}sms 0901234567 10",
                "{prefix}sms addblacklist 0901234567",
                "{prefix}sms removeblacklist 0901234567",
                "{prefix}sms show"
            ],
            "notes": [
                "Chi admin moi duoc quan ly blacklist.",
                "Nguoi dung thuong chi duoc spam tu 1 den 30 lan."
            ]
        }
    }
}

def is_admin(uid):
    try:
        with open(ADMIN_PATH, 'r', encoding='utf-8') as f:
            admin_list = json.load(f)
        return str(uid) in admin_list
    except Exception as e:
        print(f'Lỗi đọc file list_admin.json: {e}')
        return False

def read_blacklist():
    try:
        with open(BLACKLIST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f) or {}
    except Exception as e:
        print(f'Lỗi đọc file blacklist.json: {e}')
        return {}

def write_blacklist(blacklist):
    try:
        with open(BLACKLIST_PATH, 'w', encoding='utf-8') as f:
            json.dump(blacklist, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f'Lỗi ghi file blacklist.json: {e}')
        return False

def handle_sms_command(message, message_object, thread_id, thread_type, author_id, bot):
    global last_sms_time, current_processing_number
    
    parts = message.split()
    
    if len(parts) < 2:
        bot.replyMessage(Message(text=f'❌ Vui lòng dùng đúng cú pháp:\n➤ {bot.prefix}sms <sdt> <số lần>\n➤ {bot.prefix}sms addblacklist <sdt>\n➤ {bot.prefix}sms removeblacklist <sdt>\n➤ {bot.prefix}sms show'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Xử lý lệnh addblacklist
    if parts[1].lower() == 'addblacklist' and len(parts) == 3:
        if not is_admin(author_id):
            bot.replyMessage(Message(text='❌ Chỉ admin mới có thể thêm số vào blacklist!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
            return

        sdt = parts[2]
        if len(sdt) != 10 or not sdt.isdigit() or not sdt.startswith('0'):
            bot.replyMessage(Message(text='❌ Số điện thoại phải là 10 số và bắt đầu bằng 0!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
            return

        blacklist = read_blacklist()
        if sdt in blacklist:
            bot.replyMessage(Message(text=f'❌ Số {sdt} đã có trong blacklist!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
            return

        blacklist[sdt] = True
        if write_blacklist(blacklist):
            bot.replyMessage(Message(text=f'✅ Đã thêm số {sdt} vào blacklist.'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        else:
            bot.replyMessage(Message(text=f'❌ Lỗi khi thêm số {sdt} vào blacklist!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Xử lý lệnh removeblacklist
    if parts[1].lower() == 'removeblacklist' and len(parts) == 3:
        if not is_admin(author_id):
            bot.replyMessage(Message(text='❌ Chỉ admin mới có thể xóa số khỏi blacklist!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
            return

        sdt = parts[2]
        if len(sdt) != 10 or not sdt.isdigit() or not sdt.startswith('0'):
            bot.replyMessage(Message(text='❌ Số điện thoại phải là 10 số và bắt đầu bằng 0!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
            return

        blacklist = read_blacklist()
        if sdt not in blacklist:
            bot.replyMessage(Message(text=f'❌ Số {sdt} không có trong blacklist!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
            return

        del blacklist[sdt]
        if write_blacklist(blacklist):
            bot.replyMessage(Message(text=f'✅ Đã xóa số {sdt} khỏi blacklist.'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        else:
            bot.replyMessage(Message(text=f'❌ Lỗi khi xóa số {sdt} khỏi blacklist!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Xử lý lệnh show
    if parts[1].lower() == 'show' and len(parts) == 2:
        if not is_admin(author_id):
            bot.replyMessage(Message(text='❌ Chỉ admin mới có thể xem danh sách blacklist!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
            return

        blacklist = read_blacklist()
        numbers = list(blacklist.keys())
        if len(numbers) == 0:
            bot.replyMessage(Message(text='📋 Danh sách blacklist trống.'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
            return

        msg = '📋 Danh sách blacklist:\n' + '\n'.join([f'{i+1}. {num}' for i, num in enumerate(numbers)])
        bot.replyMessage(Message(text=msg), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Xử lý spam
    if len(parts) != 3:
        bot.replyMessage(Message(text=f'❌ Vui lòng nhập sdt và số lần vào sau lệnh {bot.prefix}sms\nVí dụ: {bot.prefix}sms 090***567 10'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    sdt = parts[1]
    try:
        count = int(parts[2])
    except ValueError:
        bot.replyMessage(Message(text='❌ Số lần spam phải là số!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    is_admin_user = is_admin(author_id)
    blacklist = read_blacklist()
    
    if sdt in blacklist:
        try:
            bot.deleteMessage(message_object, thread_id, thread_type)
        except:
            pass
        bot.replyMessage(Message(text=f'❌ Số {sdt[:5]}xxxxx nằm trong blacklist, không thể spam!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    if len(sdt) != 10 or not sdt.startswith('0') or not sdt.isdigit():
        bot.replyMessage(Message(text='❌ Số điện thoại không hợp lệ. Phải có đúng 10 chữ số và bắt đầu bằng 0!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    if not is_admin_user and (count <= 0 or count > 30):
        bot.replyMessage(Message(text='❌ Số lần spam phải là số dương từ 1 đến 30 thôi!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    if count <= 0:
        bot.replyMessage(Message(text='❌ Số lần spam phải là số dương!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    current_time = datetime.datetime.now()
    if current_processing_number:
        bot.replyMessage(Message(text=f"🚦 Vui lòng đợi số {current_processing_number} xử lý xong!"), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    if last_sms_time and (current_time - last_sms_time).total_seconds() < cooldown:
        remaining_time = cooldown - int((current_time - last_sms_time).total_seconds())
        remaining_minutes = remaining_time // 60
        remaining_seconds = remaining_time % 60
        if random.random() > 0.3:
            bot.sendReaction(message_object, "⏱️", thread_id, thread_type)
        bot.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
        return

    current_processing_number = sdt
    bot.replyMessage(Message(text=f'Đang tiến hành spam\nSDT: {sdt}\nSố Lần: {count}\nCreate by: TXA'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
    
    last_sms_time = current_time
    
    # Chạy script Python dec.py
    try:
        process = subprocess.Popen(['python', DEC_PY_PATH, sdt, str(count)], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  text=True)
        process.wait()
        
        success_msg = f'📲 Đã gửi xong {count} request spam SMS'
        bot.replyMessage(Message(text=success_msg), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
    except Exception as e:
        print(f'Lỗi khi chạy dec.py: {e}')
        bot.replyMessage(Message(text='❌ Lỗi khi thực hiện spam SMS!'), message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000)
    
    current_processing_number = None
    last_sms_time = datetime.datetime.now()

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'sms': handle_sms_command
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
