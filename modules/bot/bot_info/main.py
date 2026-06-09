from datetime import datetime
from io import BytesIO
import json
import os
import glob
import random
import re
import string
import threading
import time
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import emoji
import requests
from zlapi.models import *
from config import *
from core.bot_sys import (
    is_group_admin_or_creator,
    cleanup_pending_messages,
    handle_welcome_on,
    handle_welcome_off,
    handle_goodbye_on,
    handle_goodbye_off,
)

thread_local = threading.local()

BOT_SUB_COMMANDS = [
    {"name": "Thông tin BOT", "cmd": "{prefix}bot info", "desc": "♨️ Xem thông tin chi tiết về BOT", "oa": False},
    {"name": "Bật/Tắt BOT", "cmd": "{prefix}bot on/off", "desc": "🚀 Bật / 🛑 Tắt BOT trong nhóm", "oa": True},
    {"name": "Dọn dẹp hệ thống", "cmd": "{prefix}bot clean", "desc": "🧹 Dọn dẹp tệp tin rác hệ thống", "oa": False},
    {"name": "Cấu hình quản trị", "cmd": "{prefix}bot setup on/off", "desc": "⚙️ Bật / 🛑 Tắt cấu hình quản trị nhóm", "oa": True},
    {"name": "Nội quy nhóm", "cmd": "{prefix}bot noiquy", "desc": "💢 Xem nội quy nhóm hiện tại", "oa": False},
    {"name": "Lời chào thành viên", "cmd": "{prefix}bot welcome on/off", "desc": "🎊 Bật / 🛑 Tắt lời chào mừng thành viên mới", "oa": True},
    {"name": "Lời tạm biệt", "cmd": "{prefix}bot goodbye on/off", "desc": "👋 Bật / 🛑 Tắt lời chào tạm biệt khi mem rời nhóm", "oa": True},
    {"name": "Anti-Spam", "cmd": "{prefix}bot anti on/off", "desc": "🚦 Bật / 🛑 Tắt tính năng Anti-Spam", "oa": True},
    {"name": "Chặn gửi Link", "cmd": "{prefix}bot link on/off", "desc": "🔗 Bật / 🛑 Tắt chặn gửi liên kết (Link) tự do", "oa": True},
    {"name": "Khóa phát ngôn", "cmd": "{prefix}bot ban @tag", "desc": "😷 Khóa phát ngôn (Mute) người dùng", "oa": False},
    {"name": "Mở khóa phát ngôn", "cmd": "{prefix}bot unban @tag", "desc": "😇 Mở khóa phát ngôn (Unmute) người dùng", "oa": False},
    {"name": "DS bị khóa mõm", "cmd": "{prefix}bot ban list", "desc": "📋 Xem danh sách người dùng bị khóa phát ngôn", "oa": False},
    {"name": "Trục xuất", "cmd": "{prefix}bot kick @tag", "desc": "💪 Trục xuất người dùng khỏi nhóm", "oa": True},
    {"name": "Chặn tham gia", "cmd": "{prefix}bot block @tag", "desc": "🙅 Chặn người dùng tham gia nhóm", "oa": True},
    {"name": "Bỏ chặn", "cmd": "{prefix}bot unblock [UID]", "desc": "🔓 Bỏ chặn người dùng khỏi nhóm (dùng UID)", "oa": True},
    {"name": "DS bị chặn", "cmd": "{prefix}bot block list", "desc": "📋 Xem danh sách người dùng bị chặn", "oa": True},
    {"name": "Thêm từ cấm", "cmd": "{prefix}bot word add [từ]", "desc": "✍️ Thêm từ cấm vào nhóm", "oa": True},
    {"name": "Xóa từ cấm", "cmd": "{prefix}bot word remove [từ]", "desc": "🗑️ Xóa từ cấm khỏi nhóm", "oa": True},
    {"name": "DS từ cấm", "cmd": "{prefix}bot word list", "desc": "📋 Xem danh sách từ ngữ cấm", "oa": True},
    {"name": "Quy định vi phạm", "cmd": "{prefix}bot rule word [lần] [phút]", "desc": "📖 Quy định cấm n lần vi phạm từ ngữ, phạt m phút", "oa": True},
    {"name": "Xem Policy", "cmd": "{prefix}bot policy", "desc": "📋 Xem cấu hình policy và danh sách loại: word/link/sticker/image/flood", "oa": True},
    {"name": "Bật/Tắt Policy", "cmd": "{prefix}bot policy [loại] [on/off]", "desc": "⚙️ Bật / Tắt từng loại policy: word/link/sticker/image/flood", "oa": True},
    {"name": "Cấu hình Policy", "cmd": "{prefix}bot policy [loại] [lần] [phút] [mute/kick/warn]", "desc": "⚙️ Đặt số lần vi phạm, thời gian phạt và hành động cho từng loại", "oa": True},
    {"name": "Quyền từ xa", "cmd": "{prefix}bot remote add/remove/list", "desc": "🌐 Cấp / thu hồi / xem quyền kích hoạt từ xa", "oa": False},
    {"name": "Quản lý Admin", "cmd": "{prefix}bot admin add/remove/list", "desc": "👑 Thêm / xóa / xem danh sách Admin BOT", "oa": False},
    {"name": "Duyệt dùng Bot", "cmd": "{prefix}bot approved add/remove/list", "desc": "👑 Duyệt / hủy duyệt / xem danh sách dùng Bot (Hỗ trợ hẹn giờ)", "oa": False},
    {"name": "Duyệt Kho ảnh", "cmd": "{prefix}duyet <@tag/ID> [thời gian]", "desc": "🌸 Duyệt quyền Kho ảnh cho thành viên (Hỗ trợ hẹn giờ)", "oa": False},
    {"name": "Hủy Kho ảnh", "cmd": "{prefix}unduyet <@tag/ID>", "desc": "🌸 Hủy duyệt quyền Kho ảnh đối với thành viên", "oa": False},
    {"name": "Xóa tin nhắn", "cmd": "{prefix}del @user [count]", "desc": "🗑️ Xóa count tin gần nhất của user được tag; vẫn hỗ trợ reply hoặc xóa tin kề trước", "oa": False},
    {"name": "Tự động duyệt mem", "cmd": "{prefix}bot autoapprove on/off", "desc": "✅ Bật / Tắt tự động duyệt thành viên yêu cầu vào nhóm", "oa": True},
]

txa = {
    "name": "Bot Help & Settings",
    "desc": "Xem hướng dẫn sử dụng và cấu hình cài đặt của Bot",
    "author": "TXA",
    "command": ["bot", "del", "xoa", "delete"]
}

def txa_command(bot, message_object, author_id, thread_id, thread_type, message_text):
    thread_local.bot_uid = bot.uid
    handle_bot_command(bot, message_object, author_id, thread_id, thread_type, message_text)

SETTING_FILE = 'setting.json'
CONFIG_FILE = 'txa.json'


def load_message_log():
    """Đọc thông tin tin nhắn từ file settings.json."""
    try:
        with open(SETTING_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            return settings.get("message_log", {})
    except FileNotFoundError:
        return {}

def save_message_log(message_log):
    
    """Lưu thông tin tin nhắn vào file settings.json."""
    try:
        with open(SETTING_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}


    settings["message_log"] = message_log
    
    with open(SETTING_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)



def get_content_message(message_object):

    if message_object.msgType == 'chat.sticker':
        return ""
    

    content = message_object.content
    

    if isinstance(content, dict) and 'title' in content:
        
        text_to_check = content['title']
    else:
       
        text_to_check = content if isinstance(content, str) else ""
    return text_to_check

def is_url_in_message(message_object):
 
    if message_object.msgType == 'chat.sticker':
        return False
    
  
    content = message_object.content
    
 
    if isinstance(content, dict) and 'title' in content:

        text_to_check = content['title']
    else:
  
        text_to_check = content if isinstance(content, str) else ""
    

    url_regex = re.compile(
        r'http[s]?://' 
        r'(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|' 
        r'(?:%[0-9a-fA-F][0-9a-fA-F]))+'  
    )
   
    if re.search(url_regex, text_to_check):
        return True
    
    return False

def read_settings():
    """Đọc toàn bộ nội dung từ file JSON."""
    bot_uid = getattr(thread_local, 'bot_uid', None)
    if not bot_uid:
        # Fallback tìm kiếm tệp cấu hình thực tế trong thư mục hiện tại
        for f in os.listdir('.'):
            if f.endswith('_setting.json'):
                bot_uid = f.split('_')[0]
                break
    
    filename = f"{bot_uid}_setting.json" if bot_uid else SETTING_FILE
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def write_settings(settings):
    """Ghi toàn bộ nội dung vào file JSON."""
    bot_uid = getattr(thread_local, 'bot_uid', None)
    if not bot_uid:
        for f in os.listdir('.'):
            if f.endswith('_setting.json'):
                bot_uid = f.split('_')[0]
                break
                
    filename = f"{bot_uid}_setting.json" if bot_uid else SETTING_FILE
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(settings, file, ensure_ascii=False, indent=4)

def load_config():
    """Đọc cấu hình từ file JSON và trả về các giá trị cấu hình."""
    try:
        with open(CONFIG_FILE, 'r') as file:
            config = json.load(file)
            imei = config.get('imei')
            session_cookies = config.get('cookies')
            return imei, session_cookies
    except FileNotFoundError:
        print(f"Error: File {CONFIG_FILE} not found.")
        return None, None
    except json.JSONDecodeError:
        print(f"Error: File {CONFIG_FILE} contains invalid JSON.")
        return None, None

def is_admin(author_id):
    settings = read_settings()
    admin_bot = settings.get("admin_bot", [])
    if author_id in admin_bot:
        return True
    else:
        return False

def _get_msg_value(msg, key, default=None):
    if isinstance(msg, dict):
        return msg.get(key, default)
    return getattr(msg, key, default)

def handle_recent_group_delete(bot, message_object, author_id, thread_id, thread_type, parts):
    if thread_type != ThreadType.GROUP:
        return "➜ Lệnh này chỉ khả thi trong nhóm 🤧"

    if not (is_admin(author_id) or is_group_admin_or_creator(bot, author_id, thread_id)):
        return "➜ Lệnh này chỉ khả thi với Admin Bot hoặc quản trị viên nhóm 🤧"

    num_to_delete = 50
    for part in parts[1:]:
        clean_part = part.strip()
        if clean_part.isdigit():
            num_to_delete = int(clean_part)
            break

    if num_to_delete <= 0:
        return "➜ Số lượng tin nhắn cần xóa phải lớn hơn 0 🤧"

    target_uids = {str(uid) for uid in extract_uids_from_mentions(message_object)}

    try:
        group_data = bot.getRecentGroup(thread_id)
        group_msgs = None
        if isinstance(group_data, dict):
            group_msgs = group_data.get("groupMsgs")
        else:
            group_msgs = getattr(group_data, "groupMsgs", None)

        if not group_msgs:
            return "➜ Không có tin nhắn nào để xóa trong recent group 🤧"
    except Exception as e:
        return f"➜ Lỗi khi lấy tin nhắn gần nhất: {e}"

    command_msg_id = str(getattr(message_object, "msgId", ""))
    deleted_count = 0
    failed_count = 0
    scanned_count = 0

    for msg in reversed(group_msgs):
        if deleted_count >= num_to_delete:
            break

        msg_id = _get_msg_value(msg, "msgId")
        cli_msg_id = _get_msg_value(msg, "cliMsgId")
        owner_id = _get_msg_value(msg, "uidFrom")

        if not msg_id or not cli_msg_id:
            continue
        if command_msg_id and str(msg_id) == command_msg_id:
            continue

        owner_id = str(owner_id if owner_id not in (None, "0", 0) else author_id)
        if target_uids and owner_id not in target_uids:
            continue

        scanned_count += 1
        try:
            result = bot.deleteGroupMsg(msg_id, owner_id, cli_msg_id, thread_id)
            status = _get_msg_value(result, "status", 0)
            if status == 0 or str(status) == "0":
                deleted_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"[ERROR] delete recent group msg failed: {e}")
            failed_count += 1

    target_text = " của người được tag" if target_uids else ""
    if scanned_count == 0:
        return f"➜ Không tìm thấy tin nhắn phù hợp{target_text} trong recent group 🤧"

    return (
        f"➜ Đã xóa {deleted_count}/{num_to_delete} tin nhắn{target_text} từ recent group ✅\n"
        f"➜ Không thể xóa: {failed_count} tin"
    )

def handle_bot_admin(bot):
    settings = read_settings()
    admin_bot = settings.get("admin_bot", [])
    if bot.uid not in admin_bot:
        admin_bot.append(bot.uid)
        settings['admin_bot'] = admin_bot
        write_settings(settings)
        print(f"Đã thêm 👑{get_user_name_by_id(bot, bot.uid)} 🆔 {bot.uid} cho lần đầu tiên khởi động vào danh sách Admin 🤖BOT ✅")


def get_allowed_thread_ids():
    """Lấy danh sách các thread ID được phép từ setting.json."""
    settings = read_settings()
    return settings.get('allowed_thread_ids', [])

def bot_on_group(bot, thread_id, by_admin=False):
    try:
        settings = read_settings()
        allowed_thread_ids = settings.get('allowed_thread_ids', [])
        disabled_by_admin = settings.get('disabled_by_admin', [])

        if not by_admin and thread_id in disabled_by_admin:
            return "⚠️ Nhóm này đã bị Admin BOT tắt và khoá tự kích hoạt! Vui lòng liên hệ Admin để được mở lại. 🤧"

        group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]

        if thread_id not in allowed_thread_ids:
            allowed_thread_ids.append(thread_id)
            settings['allowed_thread_ids'] = allowed_thread_ids

        if thread_id in disabled_by_admin:
            disabled_by_admin.remove(thread_id)
            settings['disabled_by_admin'] = disabled_by_admin

        write_settings(settings)

        return f"[🤖BOT {bot.me_name} {bot.version}] đã được bật trong Group: {group.name} - ID: {thread_id}\n➜ Gõ lệnh ➡️ {prefix}help hoặc {prefix}bot để xem danh sách tính năng BOT💡"
    except Exception as e:
        print(f"Error: {e}")
        return "Đã xảy ra lỗi gì đó🤧"

def bot_off_group(bot, thread_id, by_admin=False):
    try:
        settings = read_settings()
        allowed_thread_ids = settings.get('allowed_thread_ids', [])
        disabled_by_admin = settings.get('disabled_by_admin', [])
        group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]

        if thread_id in allowed_thread_ids:
            allowed_thread_ids.remove(thread_id)
            settings['allowed_thread_ids'] = allowed_thread_ids

        if by_admin and thread_id not in disabled_by_admin:
            disabled_by_admin.append(thread_id)
            settings['disabled_by_admin'] = disabled_by_admin

        write_settings(settings)

        if by_admin:
            return f"[🤖BOT {bot.me_name} {bot.version}] đã được tắt và khóa kích hoạt từ xa cho Group: {group.name} - ID: {thread_id} 🛑"
        else:
            return f"[🤖BOT {bot.me_name} {bot.version}] đã được tắt trong Group: {group.name} - ID: {thread_id}\n➜ Chào tạm biệt chúc bạn luôn may mắn🍀"
    except Exception as e:
        print(f"Error: {e}")
        return "Đã xảy ra lỗi gì đó🤧"


def add_forbidden_word(word):
    """Thêm một từ vào danh sách từ ngữ cấm."""
    settings = read_settings()
    forbidden_words = settings.get('forbidden_words', [])
    
    if word not in forbidden_words:
        forbidden_words.append(word)
        settings['forbidden_words'] = forbidden_words
        write_settings(settings)
        return f"➜ Từ '{word}' đã được thêm vào danh sách từ cấm ✅"
    else:
        return f"➜ Từ '{word}' đã tồn tại trong danh sách từ cấm 🤧"

def remove_forbidden_word(word):
    """Xóa một từ khỏi danh sách từ ngữ cấm."""
    settings = read_settings()
    forbidden_words = settings.get('forbidden_words', [])
    
    if word in forbidden_words:
        forbidden_words.remove(word)
        settings['forbidden_words'] = forbidden_words
        write_settings(settings)
        return f"➜ Từ '{word}' đã được xóa khỏi danh sách từ cấm ✅"
    else:
        return f"Từ '{word}' không có trong danh sách từ cấm 🤧"

def is_forbidden_word(word):
    """Kiểm tra xem một từ có nằm trong danh sách từ ngữ cấm hay không."""
    settings = read_settings()
    forbidden_words = settings.get('forbidden_words', [])
    return word in forbidden_words



def setup_bot_on(bot, thread_id):
   
    group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
  
    admin_ids = group.adminIds.copy()
    if group.creatorId not in admin_ids:
        admin_ids.append(group.creatorId)
    
 
    if bot.uid in admin_ids:
      
        settings = read_settings()
        
      
        if 'group_admins' not in settings:
            settings['group_admins'] = {}
        
        settings['group_admins'][thread_id] = admin_ids
        
      
        write_settings(settings)
        
        return f"[🤖BOT {bot.me_name} {bot.version}]\n➜ Cấu hình thành công nội quy nhóm: {group.name} - ID: {thread_id} ✅\n➜ Hãy nhắn tin một cách văn minh lịch sự! ✨\n➜ Chúc bạn luôn may mắn! 🍀"
    else:
        return f"[🤖BOT {bot.me_name} {bot.version}]\n➜ Cấu hình thất bại  cho nhóm: {group.name} - ID: {thread_id} ⚠️\n➜ Bạn không có quyền quản trị nhóm này! 🤧"


def setup_bot_off(bot,thread_id):
    group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]

    settings = read_settings()


    if 'group_admins' in settings:
     
        if thread_id in settings['group_admins']:
     
            del settings['group_admins'][thread_id]

     
            write_settings(settings)
            
            return f"[🤖BOT {bot.me_name} {bot.version}]\n➜ Đã hủy bỏ thành công cấu hình quản trị cho nhóm: {group.name} - ID: {thread_id} ✅\n➜ Hãy quẫy lên đi! 🤣"
        else:
            return f"[🤖BOT {bot.me_name} {bot.version}]]\n➜ Không tìm thấy cấu hình quản trị cho nhóm: {group.name} - ID: {thread_id} để hủy bỏ! 🤧"
    else:
        return f"[🤖BOT {bot.me_name} {bot.version}]\n➜ Không có thông tin quản trị nào trong cài đặt để hủy bỏ! 🤧"

def check_admin_group(bot,thread_id):
    group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]

    admin_ids = group.adminIds.copy()
    if group.creatorId not in admin_ids:
        admin_ids.append(group.creatorId)
    settings = read_settings()
    if 'group_admins' not in settings:
        settings['group_admins'] = {}
    settings['group_admins'][thread_id] = admin_ids
    

    write_settings(settings)

    if bot.uid in admin_ids:
        return True
    else:
        return False


def get_allow_link_text(thread_id):

    settings = read_settings()


    if 'allow_link' in settings:
      
        return settings['allow_link'].get(thread_id, False)
    else:
      
        return False

user_message_count = {}
user_flood_timestamps = {}
def check_spam(bot, author_id, thread_id, message_object, thread_type):
    settings = read_settings()
    spam_enabled = settings.get('spam_enabled', False)
    
    if isinstance(spam_enabled, bool):
        if spam_enabled:
            settings['spam_enabled'] = {thread_id: True}
        else:
            settings['spam_enabled'] = {}
        write_settings(settings)
    spam_enabled = settings['spam_enabled']

    if not spam_enabled.get(thread_id, False):
        return

    global user_message_count
    now = time.time()

    if thread_id not in user_message_count:
        user_message_count[thread_id] = {}

    if author_id not in user_message_count[thread_id]:
        user_message_count[thread_id][author_id] = []
    user_message_count[thread_id][author_id] = [
        timestamp for timestamp in user_message_count[thread_id][author_id] if now - timestamp <= 1
    ]
    user_message_count[thread_id][author_id].append(now)
    pending_users = bot.viewGroupPending(thread_id)
    if pending_users and pending_users.users:
        if len(user_message_count[thread_id][author_id]) >= 2:
            for user in pending_users.users:
                if user['uid'] == author_id:
                    bot.changeGroupSetting(groupId=thread_id, lockSendMsg=1)
                    bot.handleGroupPending(author_id, thread_id)
                    bot.blockUsersInGroup(author_id, thread_id)
                    bot.dislink(grid=thread_id)
                    time.sleep(10)
                    bot.changeGroupSetting(groupId=thread_id, lockSendMsg=0)
                    return

    if len(user_message_count[thread_id][author_id]) >= 5:
        bot.changeGroupSetting(groupId=thread_id, lockSendMsg=1)
        bot.blockUsersInGroup(author_id, thread_id)
        bot.kickUsersInGroup(author_id, thread_id)
        time.sleep(10)
        bot.changeGroupSetting(groupId=thread_id, lockSendMsg=0)
        bot.spam = True
        return

def handle_check_profanity(bot, author_id, thread_id, message_object, thread_type, message):
    def send_check_profanity_response():
        settings = read_settings()
        admin_ids = settings.get('group_admins', {}).get(thread_id, [])
        if bot.uid not in admin_ids:
            return
        
        skip_bot = settings.get("skip_bot", [])
        if author_id in skip_bot:
            return  
        
        group_info = bot.fetchGroupInfo(groupId=thread_id)
        admin_ids = group_info.gridInfoMap[thread_id]['adminIds']
        creator_id = group_info.gridInfoMap[thread_id]['creatorId']
        
        if author_id in admin_ids or author_id == creator_id:
            return

        muted_users = settings.get('muted_users', [])
        current_time = int(time.time())
        violations = settings.get('violations', {})

        # check if currently muted
        for muted_user in muted_users[:]:
            if muted_user['author_id'] == author_id and muted_user['thread_id'] == thread_id:
                if muted_user['muted_until'] == float('inf') or current_time < muted_user['muted_until']:
                    for _ in range(20):
                        bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
                        time.sleep(0)
                    return
                else:
                    muted_users.remove(muted_user)
                    settings['muted_users'] = muted_users
                    if author_id in violations and thread_id in violations[author_id]:
                        violations[author_id][thread_id]['profanity_count'] = 0
                        for key in list(violations[author_id][thread_id].keys()):
                            if key.endswith('_count'):
                                violations[author_id][thread_id][key] = 0
                    write_settings(settings)
                    response = "➜ 🎉 Bạn đã được phép phát ngôn! Hãy nói chuyện 💬 lịch sự nhé! 😊👍"
                    bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                    return

        content = message_object.content
        message_text = ""
        if isinstance(content, str):
            message_text = str(content)
        elif isinstance(content, dict) and 'title' in content:
            message_text = str(content['title'])

        policies = settings.get("policies", {}).get(thread_id, {})
        violation_type = None
        violation_reason = ""

        # 1. Link policy
        if policies.get("link", {}).get("enabled", False) and is_url_in_message(message_object):
            violation_type = "link"
            violation_reason = "Gửi liên kết (Link)"
        
        # 2. Sticker policy
        elif policies.get("sticker", {}).get("enabled", False) and message_object.msgType == 'chat.sticker':
            violation_type = "sticker"
            violation_reason = "Gửi Sticker"
            
        # 3. Image policy
        elif policies.get("image", {}).get("enabled", False) and message_object.msgType == 'chat.photo':
            violation_type = "image"
            violation_reason = "Gửi Hình ảnh"

        # 4. Word policy
        elif policies.get("word", {}).get("enabled", False):
            forbidden_words = settings.get('forbidden_words', [])
            message_words = message_text.lower().split()
            detected_profanity = any(word in forbidden_words for word in message_words)
            if detected_profanity:
                violation_type = "word"
                violation_reason = f"Từ cấm: '{message_text}'"

        # 5. Flood policy
        elif policies.get("flood", {}).get("enabled", False):
            global user_flood_timestamps
            if 'user_flood_timestamps' not in globals():
                user_flood_timestamps = {}
            if thread_id not in user_flood_timestamps:
                user_flood_timestamps[thread_id] = {}
            if author_id not in user_flood_timestamps[thread_id]:
                user_flood_timestamps[thread_id][author_id] = []
            
            now_time = time.time()
            user_flood_timestamps[thread_id][author_id] = [t for t in user_flood_timestamps[thread_id][author_id] if now_time - t <= 5]
            user_flood_timestamps[thread_id][author_id].append(now_time)
            
            flood_threshold = policies.get("flood", {}).get("threshold", 5)
            if len(user_flood_timestamps[thread_id][author_id]) >= flood_threshold:
                violation_type = "flood"
                violation_reason = f"Spam tin nhắn liên tục"
                user_flood_timestamps[thread_id][author_id] = []

        if violation_type:
            user_violations = violations.setdefault(author_id, {}).setdefault(thread_id, {'profanity_count': 0, 'spam_count': 0, 'penalty_level': 0})
            count_key = f"{violation_type}_count"
            user_violations[count_key] = user_violations.get(count_key, 0) + 1
            violation_count = user_violations[count_key]
            
            p_config = policies.get(violation_type, {})
            threshold = p_config.get("threshold", 3)
            duration = p_config.get("duration", 30)
            action_type = p_config.get("action", "mute")
            
            # Delete violating message immediately
            bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
            
            if violation_count >= threshold:
                user_violations[count_key] = 0
                write_settings(settings)
                
                if action_type == "mute":
                    muted_users.append({
                        'author_id': author_id,
                        'thread_id': thread_id,
                        'reason': violation_reason,
                        'muted_until': current_time + 60 * duration
                    })
                    settings['muted_users'] = muted_users
                    write_settings(settings)
                    response = f"➜ 🚫 Bạn đã vi phạm policy [{violation_reason}] {threshold} lần\n➜ 🤐 Bạn đã bị khóa mõm trong {duration} phút!"
                    bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                    return
                elif action_type == "kick":
                    response = f"➜ ⛔ Bạn đã bị loại khỏi nhóm do vi phạm policy [{violation_reason}] quá {threshold} lần!"
                    bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                    bot.kickUsersInGroup(author_id, thread_id)
                    return
                elif action_type == "warn":
                    response = f"➜ ⚠️ CẢNH BÁO NGHÊM TRỌNG: Bạn đã vi phạm policy [{violation_reason}] {threshold} lần! Hãy dừng ngay lập tức!"
                    bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                    return
            else:
                write_settings(settings)
                response = f"➜ ⚠️ Cảnh báo: Bạn đã vi phạm policy [{violation_reason}] {violation_count}/{threshold} lần!\n➜ 🤐 Nếu tiếp tục vi phạm, bạn sẽ bị xử lý theo cấu hình nhóm!"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                return

        # Fallback to old checks
        spam_thread = threading.Thread(target=check_spam, args=(bot, author_id, thread_id, message_object, thread_type))
        spam_thread.start()

        if get_allow_link_text(thread_id) and is_url_in_message(message_object):
            bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
            return

        forbidden_words = settings.get('forbidden_words', [])
        message_words = message_text.lower().split()
        detected_profanity = any(word in forbidden_words for word in message_words)

        if detected_profanity:
            user_violations = violations.setdefault(author_id, {}).setdefault(thread_id, {'profanity_count': 0, 'spam_count': 0, 'penalty_level': 0})
            user_violations['profanity_count'] += 1
            profanity_count = user_violations['profanity_count']
            penalty_level = user_violations['penalty_level']
            rules = settings.get("rules", {})
            word_rule = rules.get("word", {"threshold": 3, "duration": 30})
            threshold_word = word_rule["threshold"]
            duration_word = word_rule["duration"]

            if penalty_level >= 2:
                response = f"➜ ⛔ Bạn đã bị loại khỏi nhóm do vi phạm nhiều lần\n➜ 💢 Nội dung vi phạm: 🤬 '{message_text}'"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                bot.kickUsersInGroup(author_id, thread_id)
                bot.blockUsersInGroup(author_id, thread_id)
                muted_users = [user for user in muted_users if not (user['author_id'] == author_id and user['thread_id'] == thread_id)]
                settings['muted_users'] = muted_users
                if author_id in violations:
                    violations[author_id].pop(thread_id, None)
                    if not violations[author_id]:
                        violations.pop(author_id, None)
                write_settings(settings)
                return

            if profanity_count >= threshold_word:
                penalty_level += 1
                user_violations['penalty_level'] = penalty_level
                muted_users.append({
                    'author_id': author_id,
                    'thread_id': thread_id,
                    'reason': f'{message_text}',
                    'muted_until': current_time + 60 * duration_word
                })
                settings['muted_users'] = muted_users
                write_settings(settings)
                response = f"➜ 🚫 Bạn đã vi phạm {threshold_word} lần\n➜ 🤐 Bạn đã bị khóa mõm trong {duration_word} phút\n➜ 💢 Nội dung vi phạm: 🤬 '{message_text}'"
                bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                return
            elif profanity_count == threshold_word - 1:
                response = f"➜ ⚠️ Cảnh báo: Bạn đã vi phạm {profanity_count}/{threshold_word} lần\n➜ 🤐 Nếu bạn tiếp tục vi phạm, bạn sẽ bị khóa mõm trong {duration_word} phút\n➜ 💢 Nội dung vi phạm: 🤬 '{message_text}'"
                bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
            else:
                response = f"➜ ⚠️ Bạn đã vi phạm {profanity_count}/{threshold_word} lần!\n➜ 💢 Nội dung vi phạm: 🤬 '{message_text}'"
                bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
            write_settings(settings)

    thread = threading.Thread(target=send_check_profanity_response)
    thread.start()

def get_user_name_by_id(bot,author_id):
    try:
        user = bot.fetchUserInfo(author_id).changed_profiles[author_id].displayName
        return user
    except:
        return "Unknown User"



def print_muted_users_in_group(bot, thread_id):
    settings = read_settings()
    muted_users = settings.get("muted_users", [])
    current_time = int(time.time())
    muted_users_list = []


    for user in muted_users:
        if user['thread_id'] == thread_id:
            author_id = user['author_id']
            user_name = get_user_name_by_id(bot, author_id)
            muted_until = user['muted_until']
            remaining_time = muted_until - current_time
            reason = user['reason']

            if remaining_time > 0:
                minutes_left = remaining_time // 60
                muted_users_list.append({
                    "author_id": author_id,
                    "name": user_name,
                    "minutes_left": minutes_left,
                    "reason": reason
                })


    muted_users_list.sort(key=lambda x: x['minutes_left'])

    if muted_users_list:
        result = "➜ 🚫 Danh sách các thành viên nhóm bị khóa mõm: 🤐\n"
        mentions = []
        for i, user in enumerate(muted_users_list, start=1):
            line = f"{i}. 😷 {user['name']} - ⏳ {user['minutes_left']} phút - ⚠️ Lý do: {user['reason']}"
            result += line + "\n"
            offset = result.rfind(user['name'])
            if offset != -1:
                mentions.append(Mention(uid=user['author_id'], offset=offset, length=len(user['name'])))
        result = result.rstrip()
    else:
        result = "➜ 🎉 Xin chúc mừng!\n➜ Nhóm không có thành viên nào tiêu cực ❤ 🌺 🌻 🌹 🌷 🌼\n➜ Hãy tiếp tục phát huy nhé 🤗"
        mentions = []

    return {"text": result, "mentions": mentions}

def print_blocked_users_in_group(bot, thread_id):
    settings = read_settings()
    blocked_users_group = settings.get("block_user_group", {})


    if thread_id not in blocked_users_group:
        return {"text": "➜ 🎉 Nhóm này không có ai bị block! 🌟", "mentions": []}

    blocked_users = blocked_users_group[thread_id].get('blocked_users', [])
    blocked_users_list = []


    for author_id in blocked_users:
        user_name = get_user_name_by_id(bot, author_id)  
        blocked_users_list.append({
            "author_id": author_id,
            "name": user_name
        })


    blocked_users_list.sort(key=lambda x: x['name'])


    if blocked_users_list:
        result = "➜ 🚫 Danh sách các thành viên bị block khỏi nhóm: 🤧\n"
        mentions = []
        for i, user in enumerate(blocked_users_list, start=1):
            line = f"{i}. 🙅 {user['name']} - {user['author_id']}"
            result += line + "\n"
            offset = result.rfind(user['name'])
            if offset != -1:
                mentions.append(Mention(uid=user['author_id'], offset=offset, length=len(user['name'])))
        result = result.rstrip()
    else:
        result = "➜ 🎉 Nhóm không có ai bị block khỏi nhóm! 🌼"
        mentions = []

    return {"text": result, "mentions": mentions}


def add_users_to_ban_list(bot, author_ids, thread_id, reason):
    settings = read_settings()

    current_time = int(time.time())
    muted_users = settings.get("muted_users", [])
    violations = settings.get("violations", {})
    duration_minutes = settings.get("rules", {}).get("word", {}).get("duration", 30)

    response=""
    for author_id in author_ids:
        user = bot.fetchUserInfo(author_id).changed_profiles[author_id].displayName


        if not any(entry["author_id"] == author_id and entry["thread_id"] == thread_id for entry in muted_users):
            muted_users.append({
                "author_id": author_id,
                "thread_id": thread_id,
                "reason": reason,
                "muted_until": current_time + 60 * duration_minutes
            })


        if author_id not in violations:
            violations[author_id] = {}

        if thread_id not in violations[author_id]:
            violations[author_id][thread_id] = {
                "profanity_count": 0,
                "spam_count": 0,
                "penalty_level": 0
            }

        violations[author_id][thread_id]["profanity_count"] += 1  
        violations[author_id][thread_id]["penalty_level"] += 1 

        response += f"➜ 🚫 {user} đã bị cấm phát ngôn trong {duration_minutes} ⏳ phút\n"
    

    settings['muted_users'] = muted_users
    settings['violations'] = violations
    write_settings(settings)
    return response


def remove_users_from_ban_list(bot, author_ids, thread_id):
    settings = read_settings()

    muted_users = settings.get("muted_users", [])
    violations = settings.get("violations", {})

    response = ""
    for author_id in author_ids:
        user = bot.fetchUserInfo(author_id).changed_profiles[author_id].displayName

  
        initial_count = len(muted_users)
        muted_users = [entry for entry in muted_users if not (entry["author_id"] == author_id and entry["thread_id"] == thread_id)]
        

        removed = False
        if author_id in violations:
            if thread_id in violations[author_id]:
                del violations[author_id][thread_id]

                if not violations[author_id]:
                    del violations[author_id]
                removed = True

   
        if (initial_count != len(muted_users)) or removed:
            response += f"➜ 🎉 Chúc mừng {user} đã được phép phát ngôn 😤\n"
        else:
            response += f"➜ 😲 {user} không có trong danh sách cấm phát ngôn 🤧\n"
    
    
    settings['muted_users'] = muted_users
    settings['violations'] = violations
    write_settings(settings)

    return response

def block_users_from_group(bot, author_ids, thread_id):
    response = ''
    block_user = [] 

   
    settings = read_settings()

 
    if "block_user_group" not in settings:
        settings["block_user_group"] = {}


    if thread_id not in settings["block_user_group"]:
        settings["block_user_group"][thread_id] = {'blocked_users': []}

    for author_id in author_ids:
    
        user = bot.fetchUserInfo(author_id).changed_profiles[author_id].displayName

       
        bot.blockUsersInGroup(author_id, thread_id)  
        block_user.append(user) 

 
        if author_id not in settings["block_user_group"][thread_id]['blocked_users']:
            settings["block_user_group"][thread_id]['blocked_users'].append(author_id)

  
    write_settings(settings)


    if block_user:
        blocked_users_str = ', '.join(block_user)  
        response = f"➜ :v {blocked_users_str} đã bị chặn khỏi nhóm 🤧"
    else:
        response = "➜ Không ai bị chặn khỏi nhóm 🤧"
    
    return response

def unblock_users_from_group(bot, author_ids, thread_id):
    response = ''
    unblocked_users = [] 

 
    settings = read_settings()


    if "block_user_group" in settings and thread_id in settings["block_user_group"]:
        blocked_users = settings["block_user_group"][thread_id]['blocked_users']
        
        for author_id in author_ids:
      
            user = bot.fetchUserInfo(author_id).changed_profiles[author_id].displayName

     
            if author_id in blocked_users:
                bot.unblockUsersInGroup(author_id, thread_id) 
                unblocked_users.append(user)  
                blocked_users.remove(author_id)  

       
        if not blocked_users:
            del settings["block_user_group"][thread_id]
        
       
        write_settings(settings)


    if unblocked_users:
        unblocked_users_str = ', '.join(unblocked_users)  
        response = f"➜ :v {unblocked_users_str} đã được bỏ chặn khỏi nhóm 🎉"
    else:
        response = "➜ Không có ai bị chặn trong nhóm 🤧"
    
    return response

def kick_users_from_group(bot, uids, thread_id):
    response = ""
    for uid in uids:
        try:
        
            bot.kickUsersInGroup(uid, thread_id)
            bot.blockUsersInGroup( uid, thread_id)
     
            user_name = get_user_name_by_id(bot, uid)
         
            response += f"➜ 💪 Đã kick người dùng 😫 {user_name} khỏi nhóm thành công ✅\n"
        except Exception as e:
           
            user_name = get_user_name_by_id(bot, uid)
            response += f"➜ 😲 Không thể kick người dùng 😫 {user_name} khỏi nhóm 🤧\n"
    
    return response

def extract_uids_from_mentions(message_object):
    uids = []
    if message_object.mentions:
      
        uids = [mention['uid'] for mention in message_object.mentions if 'uid' in mention]
    return uids


def add_approved(bot, author_id, mentioned_uids, settings, expiry_time=None, message_object=None, thread_id=None, thread_type=None):
    approved_users = settings.get("approved_users", [])
    response = ""
    for uid in mentioned_uids:
        if author_id not in settings.get("admin_bot", []):
            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
        elif uid not in approved_users:
            approved_users.append(uid)
            
            # Lưu thời gian hết hạn
            approved_expiry = settings.setdefault("approved_users_expiry", {})
            approved_expiry[uid] = expiry_time
            settings["approved_users_expiry"] = approved_expiry
            
            if expiry_time:
                expiry_str = datetime.fromtimestamp(expiry_time).strftime("%H:%M:%S %d/%m/%Y")
                response += f"➜ Đã thêm người dùng ✅ {get_user_name_by_id(bot, uid)} vào danh sách được duyệt đến {expiry_str} ✅\n💡 Bot sẽ tự động thu hồi và thông báo khi hết hạn.\n"
                
                # Tạo Zalo Todo nhắc hẹn nếu có thời hạn
                if message_object and thread_id and thread_type:
                    try:
                        todo_content = f"Hạn dùng TXA Bot của {get_user_name_by_id(bot, uid)}"
                        bot.sendTodo(
                            target_id=uid,
                            content=todo_content,
                            mid=message_object.msgId,
                            author_id=author_id,
                            thread_type=thread_type,
                            thread_id=thread_id if thread_type == ThreadType.GROUP else None,
                            dueDate=int(expiry_time * 1000)
                        )
                    except Exception as todo_err:
                        print(f"[ERROR] Không thể tạo Zalo Todo nhắc hẹn: {todo_err}")
            else:
                response += f"➜ Đã thêm người dùng ✅ {get_user_name_by_id(bot, uid)} vào danh sách được duyệt vô thời hạn ✅\n"
            
            # Gửi tin nhắn riêng (Inbox) báo cho người dùng biết
            try:
                if expiry_time:
                    expiry_str = datetime.fromtimestamp(expiry_time).strftime("%H:%M:%S %d/%m/%Y")
                    inbox_text = f"🎉 Chào bạn, bạn đã được Admin duyệt quyền sử dụng TXA Bot đến {expiry_str}! Hãy trải nghiệm nhé. 🌸"
                else:
                    inbox_text = f"🎉 Chào bạn, bạn đã được Admin duyệt quyền sử dụng TXA Bot vô thời hạn! Hãy trải nghiệm nhé. 🌸"
                bot.send(Message(text=inbox_text), thread_id=uid, thread_type=ThreadType.USER)
            except Exception as e:
                print(f"[ERROR] Không thể gửi tin nhắn riêng cho {uid}: {e}")
                
            # Thực hiện dọn dẹp các tin nhắn chờ duyệt trước đó
            cleanup_pending_messages(bot, uid)
        else:
            # Nếu đã được duyệt từ trước, vẫn cho phép cập nhật lại thời hạn mới
            approved_expiry = settings.setdefault("approved_users_expiry", {})
            approved_expiry[uid] = expiry_time
            settings["approved_users_expiry"] = approved_expiry
            
            if expiry_time:
                expiry_str = datetime.fromtimestamp(expiry_time).strftime("%H:%M:%S %d/%m/%Y")
                response += f"➜ Đã cập nhật hạn duyệt dùng BOT cho người dùng ✅ {get_user_name_by_id(bot, uid)} đến {expiry_str} ✅\n💡 Bot sẽ tự động thu hồi và thông báo khi hết hạn.\n"
                
                # Tạo Zalo Todo nhắc hẹn nếu có thời hạn
                if message_object and thread_id and thread_type:
                    try:
                        todo_content = f"Hạn dùng TXA Bot của {get_user_name_by_id(bot, uid)}"
                        bot.sendTodo(
                            target_id=uid,
                            content=todo_content,
                            mid=message_object.msgId,
                            author_id=author_id,
                            thread_type=thread_type,
                            thread_id=thread_id if thread_type == ThreadType.GROUP else None,
                            dueDate=int(expiry_time * 1000)
                        )
                    except Exception as todo_err:
                        print(f"[ERROR] Không thể tạo Zalo Todo nhắc hẹn: {todo_err}")
                
                try:
                    inbox_text = f"🎉 Chào bạn, Admin đã gia hạn quyền sử dụng TXA Bot của bạn đến {expiry_str}! Hãy tiếp tục trải nghiệm nhé. 🌸"
                    bot.send(Message(text=inbox_text), thread_id=uid, thread_type=ThreadType.USER)
                except Exception as e:
                    print(f"[ERROR] Không thể gửi tin nhắn riêng cho {uid}: {e}")
            else:
                response += f"➜ Người dùng ✅ {get_user_name_by_id(bot, uid)} đã có trong danh sách được duyệt vô thời hạn 🤧\n"

    settings['approved_users'] = approved_users
    write_settings(settings)
    return response

def remove_approved(bot, author_id, mentioned_uids, settings):
    approved_users = settings.get("approved_users", [])
    response = ""
    for uid in mentioned_uids:
        if author_id not in settings.get("admin_bot", []):
            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
        elif uid in approved_users:
            approved_users.remove(uid)
            response += f"➜ Đã xóa người dùng ✅ {get_user_name_by_id(bot, uid)} khỏi danh sách được duyệt ✅\n"
            
            # Xóa lịch sử hết hạn của user
            approved_expiry = settings.get("approved_users_expiry", {})
            approved_expiry.pop(uid, None)
            settings["approved_users_expiry"] = approved_expiry
            
            # Gửi tin nhắn riêng (Inbox) báo cho người dùng bị hủy duyệt biết
            try:
                inbox_text = f"⚠️ Chào bạn, quyền sử dụng TXA Bot của bạn đã bị Admin thu hồi."
                bot.send(Message(text=inbox_text), thread_id=uid, thread_type=ThreadType.USER)
            except Exception as e:
                print(f"[ERROR] Không thể gửi tin nhắn riêng cho {uid}: {e}")
        else:
            response += f"➜ Người dùng ✅ {get_user_name_by_id(bot, uid)} không có trong danh sách được duyệt 🤧\n"

    settings['approved_users'] = approved_users
    write_settings(settings)
    return response

def list_approved(bot, author_id, settings):
    if author_id not in settings.get("admin_bot", []):
        return "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"

    approved_users = settings.get("approved_users", [])
    if not approved_users:
        return "➜ 🎉 Danh sách được duyệt trống! 🌼"

    result = "➜ ✅ Danh sách người dùng được duyệt: 🤖\n"
    for idx, uid in enumerate(approved_users, start=1):
        user_name = get_user_name_by_id(bot, uid)
        result += f"{idx}. ✅ {user_name} - {uid}\n"

    return result

def clean_pycache():
    import shutil
    deleted_dirs = 0
    deleted_files = 0
    
    scan_paths = set()
    scan_paths.add(os.path.abspath("."))
    
    try:
        txabot_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        scan_paths.add(txabot_dir)
        bot_parent_dir = os.path.abspath(os.path.join(txabot_dir, ".."))
        scan_paths.add(bot_parent_dir)
    except Exception as e:
        print(f"Error determining scan paths: {e}")

    for path in scan_paths:
        if not os.path.exists(path):
            continue
        for root, dirs, files in os.walk(path):
            if ".git" in root or ".venv" in root or "node_modules" in root:
                continue
            if "__pycache__" in dirs:
                pycache_path = os.path.join(root, "__pycache__")
                try:
                    shutil.rmtree(pycache_path)
                    deleted_dirs += 1
                except:
                    pass
            for file in files:
                if file.endswith(".pyc") or file.endswith(".pyo"):
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        deleted_files += 1
                    except:
                        pass
    return deleted_dirs, deleted_files

def add_admin(bot, author_id, mentioned_uids, settings):
    admin_bot = settings.get("admin_bot", [])
    response = ""
    for uid in mentioned_uids:
        if author_id not in admin_bot:
            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
        elif uid not in admin_bot:
            admin_bot.append(uid)
            response += f"➜ Đã thêm người dùng 👑 {get_user_name_by_id(bot, uid)} vào danh sách Admin 🤖BOT ✅\n"
        else:
            response += f"➜ Người dùng 👑 {get_user_name_by_id(bot, uid)} đã có trong danh sách Admin 🤖BOT 🤧\n"

    settings['admin_bot'] = admin_bot
    write_settings(settings)
    return response

def remove_admin(bot, author_id, mentioned_uids, settings):
    admin_bot = settings.get("admin_bot", [])
    response = ""
    for uid in mentioned_uids:
        if author_id not in admin_bot:
            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
        elif uid in admin_bot:
            admin_bot.remove(uid)
            response += f"➜ Đã xóa người dùng 👑 {get_user_name_by_id(bot, uid)} khỏi danh sách Admin 🤖BOT ✅\n"
        else:
            response += f"➜ Người dùng 👑 {get_user_name_by_id(bot, uid)} không có trong danh sách Admin 🤖BOT 🤧\n"

    settings['admin_bot'] = admin_bot
    write_settings(settings)
    return response

def handle_bot_command(bot, message_object, author_id, thread_id, thread_type, command):
    def send_bot_response():
        try:
            parts = command.split()
            response = ""
            
            # Check if this is a command help lookup
            prefix = getattr(bot, 'prefix', '!')
            trigger_word = parts[0][len(prefix):].lower() if parts[0].startswith(prefix) else parts[0].lower()

            if trigger_word in ("del", "xoa", "delete"):
                response = handle_recent_group_delete(bot, message_object, author_id, thread_id, thread_type, parts)
            
            elif trigger_word == "help" and len(parts) > 1:
                import modules.txacommand as txacommand
                target_cmd = parts[1].lower().strip()
                if target_cmd.startswith(prefix):
                    target_cmd = target_cmd[len(prefix):]
                
                if target_cmd in txacommand.loaded_commands:
                    cmd_info = txacommand.loaded_commands[target_cmd]
                    aliases = cmd_info['command']
                    if isinstance(aliases, list):
                        alias_str = ", ".join([f"{prefix}{c}" for c in aliases])
                    else:
                        alias_str = f"{prefix}{aliases}"
                    
                    label1 = f"📖 HƯỚNG DẪN SỬ DỤNG LỆNH: {prefix}{target_cmd.upper()}\n"
                    label2 = "➜ ❖ Tên chức năng: "
                    line2 = f"{label2}{cmd_info['name']}\n"
                    label3 = "➜ ❖ Phím tắt: "
                    line3 = f"{label3}{alias_str}\n"
                    label4 = "➜ ❖ Mô tả: "
                    line4 = f"{label4}{cmd_info['desc'] if cmd_info['desc'] else 'Chưa có mô tả chi tiết.'}\n"
                    label5 = "➜ 👨‍💻 Tác giả: "
                    line5 = f"{label5}{cmd_info['author']}"
                    
                    full_text = label1 + line2 + line3 + line4 + line5
                    
                    offset1 = 0
                    len1 = len(label1)
                    
                    offset2 = len1
                    len2 = len(line2)
                    
                    offset3 = offset2 + len2
                    len3 = len(line3)
                    
                    offset4 = offset3 + len3
                    len4 = len(line4)
                    
                    offset5 = offset4 + len4
                    len5 = len(line5)
                    
                    styles_list = [
                        # Header: Bold + Italic + Pink Neon
                        MessageStyle(offset=offset1, length=len1, style="bold", auto_format=False),
                        MessageStyle(offset=offset1, length=len1, style="italic", auto_format=False),
                        MessageStyle(offset=offset1, length=len1, style="color", color="ff4081", auto_format=False),
                        
                        # Line 2 label: Bold
                        MessageStyle(offset=offset2, length=len(label2), style="bold", auto_format=False),
                        # Line 2 value: Cyan Neon
                        MessageStyle(offset=offset2 + len(label2), length=len2 - len(label2), style="color", color="00e5ff", auto_format=False),
                        
                        # Line 3 label: Bold
                        MessageStyle(offset=offset3, length=len(label3), style="bold", auto_format=False),
                        # Line 3 value: Yellow Neon
                        MessageStyle(offset=offset3 + len(label3), length=len3 - len(label3), style="color", color="ffeb3b", auto_format=False),
                        
                        # Line 4 label: Bold
                        MessageStyle(offset=offset4, length=len(label4), style="bold", auto_format=False),
                        # Line 4 value: Green Neon
                        MessageStyle(offset=offset4 + len(label4), length=len4 - len(label4), style="color", color="00e676", auto_format=False),
                        
                        # Line 5 label: Bold
                        MessageStyle(offset=offset5, length=len(label5), style="bold", auto_format=False),
                        # Line 5 value: Purple Neon
                        MessageStyle(offset=offset5 + len(label5), length=len5 - len(label5), style="color", color="aa00ff", auto_format=False)
                    ]
                    multi_style = MultiMsgStyle(styles_list)
                    
                    bot.replyMessage(
                        Message(
                            text=full_text,
                            style=multi_style
                        ),
                        message_object,
                        thread_id,
                        thread_type,
                        ttl=60000
                    )
                    response = None
                else:
                    response = f"➜ Không tìm thấy hướng dẫn cho lệnh '{prefix}{target_cmd}' 🤧"
            
            elif len(parts) == 1:
                # Gửi help menu dạng ảnh giống !menu
                def generate_help_image():
                    try:
                        BACKGROUND_PATH = "background/"
                        CACHE_PATH = "modules/cache/"
                        
                        images_bg = glob.glob(BACKGROUND_PATH + "*.jpg") + glob.glob(BACKGROUND_PATH + "*.png") + glob.glob(BACKGROUND_PATH + "*.jpeg")
                        if not images_bg:
                            return None
                        
                        image_path = random.choice(images_bg)
                        size = (1920, 1400)
                        bg_image = Image.open(image_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
                        bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=12))
                        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
                        draw = ImageDraw.Draw(overlay)
                        
                        box_color = (10, 10, 15, 200)
                        box_x1, box_y1 = 60, 40
                        box_x2, box_y2 = size[0] - 60, size[1] - 40
                        draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=40, fill=box_color)
                        
                        font_path = "font/arial unicode ms.otf"
                        font_bold_path = "font/arial unicode ms bold.otf"
                        emoji_font_path = "font/NotoEmoji-Bold.ttf"
                        
                        try:
                            font_header = ImageFont.truetype(font_bold_path, 56)
                            font_title = ImageFont.truetype(font_bold_path, 34)
                            font_cmd = ImageFont.truetype(font_path, 28)
                            font_desc = ImageFont.truetype(font_path, 24)
                            font_emoji = ImageFont.truetype(emoji_font_path, 32)
                            font_footer = ImageFont.truetype(font_path, 24)
                        except:
                            font_header = ImageFont.load_default()
                            font_title = font_cmd = font_desc = font_emoji = font_footer = font_header

                        def _emoji_tokens(text):
                            tokens = []
                            i = 0
                            while i < len(text):
                                token = text[i]
                                i += 1
                                while i < len(text) and text[i] in ("\ufe0f", "\ufe0e", "\u20e3"):
                                    token += text[i]
                                    i += 1
                                while i < len(text) and text[i] == "\u200d":
                                    token += text[i]
                                    i += 1
                                    if i < len(text):
                                        token += text[i]
                                        i += 1
                                    while i < len(text) and text[i] in ("\ufe0f", "\ufe0e", "\u20e3"):
                                        token += text[i]
                                        i += 1
                                tokens.append(token)
                            return tokens

                        def _is_emoji_token(token):
                            return (
                                token in emoji.EMOJI_DATA
                                or "\ufe0f" in token
                                or "\u200d" in token
                                or any(ch in emoji.EMOJI_DATA or ord(ch) > 0xFFFF for ch in token)
                            )

                        def _text_width(text, font):
                            try:
                                return draw.textlength(text, font=font)
                            except Exception:
                                bbox = draw.textbbox((0, 0), text, font=font)
                                return bbox[2] - bbox[0]

                        def _mixed_text_width(text, text_font, icon_font, spacing=1):
                            total = 0
                            for token in _emoji_tokens(text):
                                current_font = icon_font if _is_emoji_token(token) else text_font
                                total += _text_width(token, current_font) + spacing
                            return max(0, total - spacing)

                        def _draw_mixed_text(text, pos, text_font, icon_font, fill, spacing=1):
                            x, y = pos
                            for token in _emoji_tokens(text):
                                is_icon = _is_emoji_token(token)
                                current_font = icon_font if is_icon else text_font
                                oy = y - max(0, current_font.size // 8) if is_icon else y
                                draw.text((x, oy), token, fill=fill, font=current_font)
                                x += _text_width(token, current_font) + spacing
                            return x

                        def _draw_mixed_text_centered(text, y, text_font, icon_font, fill, spacing=1):
                            x = (size[0] - _mixed_text_width(text, text_font, icon_font, spacing)) // 2
                            _draw_mixed_text(text, (x, y), text_font, icon_font, fill, spacing)
                        
                        # Header
                        header_text = "📖 HƯỚNG DẪN SỬ DỤNG TXABOT"
                        _draw_mixed_text_centered(header_text, 68, font_header, ImageFont.truetype(emoji_font_path, 48) if os.path.exists(emoji_font_path) else font_header, (0, 229, 255, 255), spacing=2)
                        
                        # Subtitle
                        sub_text = f"Prefix: {prefix}  |  Gõ {prefix}help [tên_lệnh] để xem chi tiết"
                        sub_bbox = draw.textbbox((0, 0), sub_text, font=font_desc)
                        sub_w = sub_bbox[2] - sub_bbox[0]
                        draw.text(((size[0] - sub_w) // 2, 135), sub_text, fill=(255, 235, 59, 200), font=font_desc)
                        
                        # Separator line
                        draw.line([(120, 175), (size[0] - 120, 175)], fill=(255, 64, 129, 150), width=2)
                        
                        # Chia lệnh thành 2 cột
                        col1_items = []
                        col2_items = []
                        
                        for i, sub_cmd in enumerate(BOT_SUB_COMMANDS):
                            cmd_str = sub_cmd["cmd"].format(prefix=prefix)
                            name_str = sub_cmd.get("name", "")
                            desc_str = sub_cmd["desc"]
                            oa_tag = " (OA)" if sub_cmd["oa"] else ""
                            item = {"name": name_str, "cmd": cmd_str, "desc": f"{desc_str}{oa_tag}"}
                            if i < len(BOT_SUB_COMMANDS) // 2 + 1:
                                col1_items.append(item)
                            else:
                                col2_items.append(item)
                        
                        # Tính scale dựa trên số lệnh
                        max_items = max(len(col1_items), len(col2_items))
                        available_height = box_y2 - 220 - 80  # Trừ header + footer
                        item_height = 90
                        needed_height = max_items * item_height
                        scale = min(1.0, available_height / needed_height) if needed_height > 0 else 1.0
                        scale = max(0.70, scale)
                        
                        scaled_item_h = int(item_height * scale)
                        scaled_cmd_font_size = max(18, int(28 * scale))
                        scaled_desc_font_size = max(16, int(24 * scale))
                        desc_offset = max(34, int(scaled_item_h * 0.52))
                        
                        try:
                            s_font_cmd = ImageFont.truetype(font_path, scaled_cmd_font_size)
                            s_font_desc = ImageFont.truetype(font_path, scaled_desc_font_size)
                            s_font_emoji = ImageFont.truetype(emoji_font_path, max(18, scaled_desc_font_size + 3))
                        except:
                            s_font_cmd = font_cmd
                            s_font_desc = font_desc
                            s_font_emoji = font_emoji
                        
                        # Neon colors cho lệnh
                        neon_colors = [
                            (0, 229, 255),   # Cyan
                            (255, 64, 129),  # Pink
                            (0, 230, 118),   # Green
                            (255, 235, 59),  # Yellow
                            (170, 0, 255),   # Purple
                            (255, 145, 0),   # Orange
                            (0, 176, 255),   # Light Blue
                            (233, 30, 99),   # Rose
                        ]
                        
                        def draw_column(items, x_start, y_start):
                            y = y_start
                            for idx, item in enumerate(items):
                                color = neon_colors[idx % len(neon_colors)]
                                # Bullet + Full Name
                                full_text = f"➜ {item['name']}"
                                _draw_mixed_text(full_text, (x_start, y), s_font_cmd, s_font_emoji, (255, 255, 255, 220))
                                # Command
                                draw.text((x_start + 30, y + desc_offset - 14), item["cmd"], fill=(*color, 255), font=s_font_cmd)
                                # Description below command
                                _draw_mixed_text(item["desc"], (x_start + 35, y + desc_offset + 10), s_font_desc, s_font_emoji, (200, 200, 200, 180))
                                y += scaled_item_h
                            return y
                        
                        col_width = (box_x2 - box_x1 - 80) // 2
                        y_start = 200
                        
                        draw_column(col1_items, box_x1 + 40, y_start)
                        draw_column(col2_items, box_x1 + 40 + col_width, y_start)
                        
                        # Footer
                        footer_y = box_y2 - 55
                        draw.line([(120, footer_y - 15), (size[0] - 120, footer_y - 15)], fill=(255, 64, 129, 100), width=1)
                        footer_text = f"🤖 TXA Bot v{bot.version} | 💡 Hiện tại đang miễn phí, sau này sẽ có tính phí dịch vụ!"
                        try:
                            ft_w = _mixed_text_width(footer_text, font_footer, font_emoji)
                        except:
                            ft_w = 600
                        _draw_mixed_text(footer_text, ((size[0] - ft_w) // 2, footer_y), font_footer, font_emoji, (150, 150, 150, 200))
                        
                        # Compose
                        result = Image.alpha_composite(bg_image, overlay)
                        result = result.convert("RGB")
                        
                        output_path = os.path.join(CACHE_PATH, "bot_help.png")
                        result.save(output_path, quality=92)
                        return output_path
                    except Exception as e:
                        print(f"[ERROR] generate_help_image: {e}")
                        return None
                
                help_image_path = generate_help_image()
                
                user_name = get_user_name_by_id(bot, author_id)
                caption_line1 = f"{user_name}\n"
                caption_line2 = f"📖 HƯỚNG DẪN SỬ DỤNG TXA BOT ⚙️\n"
                caption_line3 = f"➜ Prefix: {prefix}  |  Gõ {prefix}help [tên_lệnh] để xem chi tiết\n"
                caption_line4 = f"💡 Gõ {prefix}menu để xem menu phím tắt đầy đủ 🚀"
                caption_text = caption_line1 + caption_line2 + caption_line3 + caption_line4
                
                if help_image_path and os.path.exists(help_image_path):
                    try:
                        bot.sendLocalImage(
                            imagePath=help_image_path,
                            thread_id=thread_id,
                            thread_type=thread_type,
                            width=1920,
                            height=1400,
                            message=Message(text=caption_text),
                            ttl=60000
                        )
                    except Exception as e:
                        print(f"[ERROR] sendLocalImage help: {e}")
                        bot.replyMessage(Message(text=caption_text), message_object, thread_id, thread_type, ttl=60000)
                    
                    try:
                        os.remove(help_image_path)
                    except:
                        pass
                else:
                    # Fallback text nếu không sinh được ảnh
                    response = f"{user_name}\n🎉 Chào mừng đến với 🤖BOT! ⚙️\n"
                    for sub_cmd in BOT_SUB_COMMANDS:
                        cmd_str = sub_cmd["cmd"].format(prefix=prefix)
                        oa_suffix = " (OA)" if sub_cmd["oa"] else ""
                        response += f"   ➜ {cmd_str}: {sub_cmd['desc']}{oa_suffix}\n"
                    response += f"🤖 BOT {get_user_name_by_id(bot, bot.uid)} luôn sẵn sàng phục vụ bạn! 🌸\n"
                    response += f"💡 Mẹo: Để xem toàn bộ danh sách tính năng & phím tắt của BOT, hãy gõ: {prefix}menu 🚀"
                
                # === GỬI ẢNH HƯỚNG DẪN DEMO ===
                def generate_guide_image(title, guide_lines, filename):
                    try:
                        BACKGROUND_PATH = "background/"
                        CACHE_PATH = "modules/cache/"

                        images_bg = glob.glob(BACKGROUND_PATH + "*.jpg") + glob.glob(BACKGROUND_PATH + "*.png") + glob.glob(BACKGROUND_PATH + "*.jpeg")
                        if not images_bg:
                            return None

                        # ── Font ──────────────────────────────────────────────────
                        font_path      = "font/arial unicode ms.otf"
                        font_bold_path = "font/arial unicode ms bold.otf"
                        font_emoji_path = "font/NotoEmoji-Bold.ttf"

                        def _fnt(path, size):
                            try:
                                return ImageFont.truetype(path, size)
                            except Exception:
                                return ImageFont.load_default()

                        f_title   = _fnt(font_bold_path,  38)
                        f_section = _fnt(font_bold_path,  26)
                        f_text    = _fnt(font_path,       22)
                        f_example = _fnt(font_path,       20)
                        f_note    = _fnt(font_path,       19)
                        f_emoji_t = _fnt(font_emoji_path, 36)
                        f_emoji_s = _fnt(font_emoji_path, 26)
                        f_emoji_x = _fnt(font_emoji_path, 20)

                        # ── Row-height map ────────────────────────────────────────
                        def row_h(line):
                            if   line.startswith("##"):  return 52   # section header
                            elif line.startswith("!!"):  return 34   # command
                            elif line.startswith(">>"):  return 32   # example
                            elif line == "---":          return 22   # divider
                            else:                        return 30   # plain / note

                        # ── Calculate total height ────────────────────────────────
                        PADDING_TOP    = 130   # title + divider
                        PADDING_BOTTOM = 40
                        SIDE_PAD       = 55
                        total_content_h = sum(row_h(l) for l in guide_lines)
                        H = max(600, PADDING_TOP + total_content_h + PADDING_BOTTOM + 20)
                        W = 1100

                        # ── Background ────────────────────────────────────────────
                        image_path = random.choice(images_bg)
                        bg = Image.open(image_path).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)
                        bg = bg.filter(ImageFilter.GaussianBlur(radius=14))

                        ov   = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                        draw = ImageDraw.Draw(ov)

                        # Glass card
                        draw.rounded_rectangle(
                            [(30, 20), (W - 30, H - 20)],
                            radius=28, fill=(8, 10, 18, 215),
                            outline=(255, 255, 255, 20), width=1
                        )

                        # ── Helper: draw mixed emoji+text ─────────────────────────
                        def emoji_tokens(text_str):
                            tokens = []
                            i = 0
                            while i < len(text_str):
                                token = text_str[i]
                                i += 1
                                while i < len(text_str) and text_str[i] in ("\ufe0f", "\ufe0e", "\u20e3"):
                                    token += text_str[i]
                                    i += 1
                                while i < len(text_str) and text_str[i] == "\u200d":
                                    token += text_str[i]
                                    i += 1
                                    if i < len(text_str):
                                        token += text_str[i]
                                        i += 1
                                    while i < len(text_str) and text_str[i] in ("\ufe0f", "\ufe0e", "\u20e3"):
                                        token += text_str[i]
                                        i += 1
                                tokens.append(token)
                            return tokens

                        def is_emoji_token(token):
                            return (
                                token in emoji.EMOJI_DATA
                                or "\ufe0f" in token
                                or "\u200d" in token
                                or any(ch in emoji.EMOJI_DATA or ord(ch) > 0xFFFF for ch in token)
                            )

                        def draw_mixed(text_str, pos, base_font, emoji_f, fill_color):
                            cx, cy = pos
                            for token in emoji_tokens(text_str):
                                is_e = is_emoji_token(token)
                                sf = emoji_f if is_e else base_font
                                oy   = cy - sf.size // 6 if is_e else cy
                                draw.text((cx, oy), token, fill=fill_color, font=sf)
                                try:
                                    cx += sf.getlength(token)
                                except Exception:
                                    cw = draw.textbbox((0, 0), token, font=sf)[2]
                                    cx += cw if cw > 0 else sf.size // 2

                        def line_w(text_str, base_font, emoji_f):
                            w = 0
                            for token in emoji_tokens(text_str):
                                sf = emoji_f if is_emoji_token(token) else base_font
                                try:
                                    w += sf.getlength(token)
                                except Exception:
                                    cw = draw.textbbox((0, 0), token, font=sf)[2]
                                    w += cw if cw > 0 else sf.size // 2
                            return w

                        # ── Title ─────────────────────────────────────────────────
                        tw = line_w(title, f_title, f_emoji_t)
                        draw_mixed(title, ((W - tw) // 2, 42), f_title, f_emoji_t, (0, 229, 255, 255))
                        draw.line([(SIDE_PAD, 100), (W - SIDE_PAD, 100)], fill=(255, 64, 129, 140), width=2)

                        # ── Body ──────────────────────────────────────────────────
                        y = PADDING_TOP
                        neon_section = (255, 64, 129, 255)
                        neon_cmd     = (0, 230, 118, 255)
                        white_text   = (215, 215, 220, 230)
                        example_col  = (255, 235, 59, 210)
                        note_col     = (180, 200, 230, 200)

                        for line in guide_lines:
                            if line.startswith("##"):
                                # Section header — with subtle bg strip
                                strip_h = 38
                                draw.rounded_rectangle(
                                    [(SIDE_PAD - 10, y - 4), (W - SIDE_PAD + 10, y + strip_h - 4)],
                                    radius=8, fill=(255, 64, 129, 18)
                                )
                                draw_mixed(line[2:].strip(), (SIDE_PAD, y), f_section, f_emoji_s, neon_section)
                                y += 52

                            elif line.startswith("!!"):
                                draw_mixed(line[2:].strip(), (SIDE_PAD + 20, y), f_text, f_emoji_x, neon_cmd)
                                y += 34

                            elif line.startswith(">>"):
                                example_str = f"💡 Ví dụ: {line[2:].strip()}"
                                draw_mixed(example_str, (SIDE_PAD + 20, y), f_example, f_emoji_x, example_col)
                                y += 32

                            elif line == "---":
                                draw.line([(SIDE_PAD, y + 8), (W - SIDE_PAD, y + 8)],
                                          fill=(100, 105, 120, 90), width=1)
                                y += 22

                            else:
                                # Plain text / note (starts with 📌 etc.)
                                draw_mixed(line, (SIDE_PAD, y), f_note, f_emoji_x, note_col)
                                y += 30

                        # ── Compose ───────────────────────────────────────────────
                        result = Image.alpha_composite(bg, ov)
                        output_path = os.path.join(CACHE_PATH, filename)
                        result.convert("RGB").save(output_path, quality=93)
                        return output_path

                    except Exception as e:
                        print(f"[ERROR] generate_guide_image {filename}: {e}")
                        import traceback; traceback.print_exc()
                        return None
                
                # Ảnh 1: Hướng dẫn Duyệt quyền
                duyet_guide = [
                    "## 🔑 DUYỆT QUYỀN SỬ DỤNG BOT",
                    f"!!{prefix}bot approved add @tag  → Duyệt dùng Bot vô thời hạn",
                    f"!!{prefix}bot approved add @tag 60  → Duyệt dùng Bot trong 60 giây",
                    f"!!{prefix}bot approved add @tag 10:30:00 06/06/2026  → Duyệt đến mốc giờ",
                    f"!!{prefix}bot approved remove @tag  → Thu hồi quyền dùng Bot",
                    f"!!{prefix}bot approved list  → Xem danh sách đã duyệt",
                    f">>Admin gõ: {prefix}bot approved add 123456789 120",
                    "---",
                    "## 🌸 DUYỆT QUYỀN KHO ẢNH",
                    f"!!{prefix}duyet @tag  → Duyệt quyền Kho ảnh vô thời hạn",
                    f"!!{prefix}duyet @tag 300  → Duyệt Kho ảnh trong 5 phút",
                    f"!!{prefix}duyet @tag 23:59:00 31/12/2026  → Duyệt đến cuối năm",
                    f"!!{prefix}unduyet @tag  → Thu hồi quyền Kho ảnh",
                    f">>Admin gõ: {prefix}duyet @XuânAnh 3600",
                    "---",
                    "📌 Bot tự động thu hồi và thông báo inbox khi hết hạn quyền",
                    "📌 Hỗ trợ nhập UID trực tiếp thay vì @tag",
                    "📌 Admin được dùng mọi lệnh mà không cần duyệt",
                ]
                
                # Ảnh 2: Hướng dẫn Xóa tin nhắn
                del_guide = [
                    "## 🗑️ CÁCH 1: REPLY ĐỂ XÓA",
                    "Phản hồi (Reply) tin nhắn muốn xóa",
                    f"rồi gõ {prefix}del hoặc {prefix}xoa",
                    "→ Bot xóa tin nhắn được reply + lệnh Admin",
                    f">>Reply tin nhắn A → gõ {prefix}del",
                    "---",
                    "## 🗑️ CÁCH 2: TAG + COUNT ĐỂ XÓA",
                    f"Gõ {prefix}del @Tên_Thành_Viên [số_lượng]",
                    "→ Count là số tin gần nhất của user được tag cần xóa",
                    "→ Bot lấy recent group, lọc UID user rồi xóa đủ count tin",
                    f">>{prefix}del @XuânAnh 5",
                    f">>{prefix}xoa @XuânAnh 10",
                    "---",
                    "## 🗑️ CÁCH 3: XÓA TIN KỀ TRƯỚC",
                    f"Chỉ cần gõ {prefix}del (không reply, không tag)",
                    "→ Bot xóa tin nhắn kề trước tin lệnh",
                    f">>{prefix}del",
                    "---",
                    "📌 Chỉ Admin Bot hoặc Quản trị viên nhóm mới dùng được",
                    "📌 Nếu không nhập count khi tag, mặc định xóa 1 tin gần nhất",
                    "📌 Nếu người thường gõ, Bot báo lỗi rồi tự xóa sau 5s",
                    f"📌 Hỗ trợ: {prefix}del, {prefix}xoa, {prefix}delete",
                ]
                
                time.sleep(0.5)
                
                guide1_path = generate_guide_image("📖 HƯỚNG DẪN DUYỆT QUYỀN", duyet_guide, "guide_duyet.png")
                if guide1_path and os.path.exists(guide1_path):
                    try:
                        bot.sendLocalImage(
                            imagePath=guide1_path,
                            thread_id=thread_id,
                            thread_type=thread_type,
                            width=1200,
                            height=900,
                            message=Message(text=f"📖 Hướng dẫn Duyệt quyền sử dụng Bot & Kho ảnh\n➜ Gõ {prefix}help duyet hoặc {prefix}help unduyet để xem thêm."),
                            ttl=60000
                        )
                        os.remove(guide1_path)
                    except Exception as e:
                        print(f"[ERROR] send guide duyet: {e}")
                
                time.sleep(0.3)
                
                guide2_path = generate_guide_image("📖 HƯỚNG DẪN XÓA TIN NHẮN", del_guide, "guide_del.png")
                if guide2_path and os.path.exists(guide2_path):
                    try:
                        bot.sendLocalImage(
                            imagePath=guide2_path,
                            thread_id=thread_id,
                            thread_type=thread_type,
                            width=1200,
                            height=900,
                            message=Message(text=f"📖 Hướng dẫn Xóa tin nhắn trong nhóm\n➜ Gõ {prefix}help del để xem thêm."),
                            ttl=60000
                        )
                        os.remove(guide2_path)
                    except Exception as e:
                        print(f"[ERROR] send guide del: {e}")
                
                response = None

            else:
                action = parts[1].lower()

                if action == 'on':
                    target_id = parts[2].strip() if len(parts) > 2 else thread_id
                    is_remote = (target_id != thread_id)
                    is_bot_adm = is_admin(author_id)
                    is_grp_adm = is_group_admin_or_creator(bot, author_id, target_id)
                    
                    if not (is_bot_adm or is_grp_adm):
                        response = "➜ Lệnh này chỉ khả thi với chủ nhân hoặc admin nhóm 🤧"
                    elif is_remote and thread_type != ThreadType.GROUP:
                        if is_grp_adm and not is_bot_adm:
                            settings = read_settings()
                            remote_allowed_users = settings.get("remote_allowed_users", [])
                            if author_id not in remote_allowed_users:
                                response = "⚠️ Tài khoản của bạn cần được Admin BOT cấp quyền để kích hoạt từ xa cho nhóm này. Vui lòng liên hệ Admin BOT! 🤧"
                            else:
                                response = bot_on_group(bot, target_id, by_admin=is_bot_adm)
                        else:
                            response = bot_on_group(bot, target_id, by_admin=is_bot_adm)
                    elif not is_remote and thread_type != ThreadType.GROUP:
                        response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                    else:
                        response = bot_on_group(bot, target_id, by_admin=is_bot_adm)
                elif action == 'off':
                    target_id = parts[2].strip() if len(parts) > 2 else thread_id
                    is_remote = (target_id != thread_id)
                    is_bot_adm = is_admin(author_id)
                    is_grp_adm = is_group_admin_or_creator(bot, author_id, target_id)
                    
                    if not (is_bot_adm or is_grp_adm):
                        response = "➜ Lệnh này chỉ khả thi với chủ nhân hoặc admin nhóm 🤧"
                    elif is_remote and thread_type != ThreadType.GROUP:
                        if is_grp_adm and not is_bot_adm:
                            settings = read_settings()
                            remote_allowed_users = settings.get("remote_allowed_users", [])
                            if author_id not in remote_allowed_users:
                                response = "⚠️ Tài khoản của bạn cần được Admin BOT cấp quyền để kích hoạt từ xa cho nhóm này. Vui lòng liên hệ Admin BOT! 🤧"
                            else:
                                response = bot_off_group(bot, target_id, by_admin=is_bot_adm)
                        else:
                            response = bot_off_group(bot, target_id, by_admin=is_bot_adm)
                    elif not is_remote and thread_type != ThreadType.GROUP:
                        response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                    else:
                        response = bot_off_group(bot, target_id, by_admin=is_bot_adm)
                elif action == 'remote':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [list/add/remove] sau lệnh: {prefix}bot remote 🤧\n➜ Ví dụ: {prefix}bot remote list hoặc {prefix}bot remote add @tag hoặc {prefix}bot remote remove @tag ✅"
                    else:
                        settings = read_settings()
                        remote_allowed_users = settings.get("remote_allowed_users", [])
                        sub_action = parts[2].lower()
                        if sub_action == 'add':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {prefix}bot remote add 🤧\n➜ Ví dụ: {prefix}bot remote add @tag ✅"
                            else:
                                if not is_admin(author_id):
                                    response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                                else:
                                    mentioned_uids = extract_uids_from_mentions(message_object)
                                    response = ""
                                    for uid in mentioned_uids:
                                        if uid not in remote_allowed_users:
                                            remote_allowed_users.append(uid)
                                            response += f"➜ Đã cấp quyền kích hoạt từ xa cho 👑 {get_user_name_by_id(bot, uid)} ✅\n"
                                        else:
                                            response += f"➜ 👑 {get_user_name_by_id(bot, uid)} đã có quyền từ trước 🤧\n"
                                    settings['remote_allowed_users'] = remote_allowed_users
                                    write_settings(settings)
                        elif sub_action == 'remove':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {prefix}bot remote remove 🤧\n➜ Ví dụ: {prefix}bot remote remove @tag ✅"
                            else:
                                if not is_admin(author_id):
                                    response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                                else:
                                    mentioned_uids = extract_uids_from_mentions(message_object)
                                    response = ""
                                    for uid in mentioned_uids:
                                        if uid in remote_allowed_users:
                                            remote_allowed_users.remove(uid)
                                            response += f"➜ Đã thu hồi quyền kích hoạt từ xa của 👑 {get_user_name_by_id(bot, uid)} ✅\n"
                                        else:
                                            response += f"➜ 👑 {get_user_name_by_id(bot, uid)} không có quyền kích hoạt từ xa 🤧\n"
                                    settings['remote_allowed_users'] = remote_allowed_users
                                    write_settings(settings)
                        elif sub_action == 'list':
                            if remote_allowed_users:
                                response = "➜ 🌐 Danh sách được cấp quyền kích hoạt từ xa 👑\n"
                                for idx, uid in enumerate(remote_allowed_users, start=1):
                                    response += f"      ➜ {idx}. 👑 {get_user_name_by_id(bot, uid)}\n"
                            else:
                                response = "➜ Chưa có ai được cấp quyền kích hoạt từ xa 🤧"
                        else:
                            response = f"➜ Lệnh {prefix}bot remote {sub_action} không được hỗ trợ 🤧"
                elif action == 'info':
                    import modules.txacommand as txacommand
                    total_commands = len(txacommand.loaded_commands)
                    response = (
                        f"➜ 💻 Phiên bản: {bot.version}\n"
                        f"➜ 📅 Ngày cập nhật: {bot.date_update}\n"
                        f"➜ 👨‍💻 Tác giả: {bot.me_name} (TXA)\n"
                        f"➜ 📖 Cách dùng: Lệnh [{prefix}bot/help]\n"
                        f"➜ ⏳ Thời gian chờ: 1 giây\n"
                        f"➜ 🗃️ Tổng lệnh: {total_commands} 🍬 public 🌏 BOT(11), 🌀 Facebook(6), ⬇️ Downloader(1) , 💬 Chat AI(1), 🩴 Zép Lào(9), 🧙‍♂️ Bói bói Jocker(1), 📢 Tin tức(4), 🎮 Game(1),🔑 Key API ZL(1), 🌌 Tính năng ẩn(...)"
                    )
                elif action == 'approved':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [list/add/remove] sau lệnh: {prefix}bot approved 🤧\n➜ Ví dụ: {prefix}bot approved list hoặc {prefix}bot approved add @username hoặc {prefix}bot approved remove @username ✅"
                    else:
                        settings = read_settings()
                        sub_action = parts[2].lower()
                        if sub_action == 'add':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag hoặc nhập UID sau lệnh: {prefix}bot approved add 🤧\n➜ Ví dụ: {prefix}bot approved add @username hoặc {prefix}bot approved add 123456 ✅"
                            else:
                                uids = extract_uids_from_mentions(message_object)
                                if not uids and len(parts) >= 4:
                                    raw_uid = parts[3].strip()
                                    if raw_uid.startswith('@'):
                                        raw_uid = raw_uid[1:]
                                    if raw_uid.isdigit():
                                        uids = [raw_uid]
                                if not uids:
                                    response = "⚠️ ID người dùng không hợp lệ! Vui lòng nhập UID dạng số hoặc tag người dùng."
                                else:
                                    message_text = command
                                    # Lấy time_arg
                                    time_arg = ""
                                    if message_object.mentions:
                                        mention = message_object.mentions[0]
                                        offset = mention['offset']
                                        length = mention['length']
                                        time_arg = message_text[offset + length:].strip()
                                    else:
                                        if len(parts) >= 5:
                                            time_arg = " ".join(parts[4:])
                                            
                                    from core.bot_sys import parse_expiration_time
                                    expiry_time = None
                                    if time_arg:
                                        expiry_time = parse_expiration_time(time_arg)
                                        if not expiry_time:
                                            response = "⚠️ Định dạng thời gian không hợp lệ! Vui lòng nhập số giây (ví dụ: 60) hoặc ngày giờ (ví dụ: 10:30:00 06/06/2026)."
                                            uids = [] # Huỷ thực thi duyệt
                                            
                                    if uids:
                                        response = add_approved(bot, author_id, uids, settings, expiry_time, message_object, thread_id, thread_type)
                        elif sub_action == 'remove':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag hoặc nhập UID sau lệnh: {prefix}bot approved remove 🤧\n➜ Ví dụ: {prefix}bot approved remove @username hoặc {prefix}bot approved remove 123456 ✅"
                            else:
                                uids = extract_uids_from_mentions(message_object)
                                if not uids and len(parts) >= 4:
                                    raw_uid = parts[3].strip()
                                    if raw_uid.startswith('@'):
                                        raw_uid = raw_uid[1:]
                                    if raw_uid.isdigit():
                                        uids = [raw_uid]
                                if not uids:
                                    response = "⚠️ ID người dùng không hợp lệ! Vui lòng nhập UID dạng số hoặc tag người dùng."
                                else:
                                    response = remove_approved(bot, author_id, uids, settings)
                        elif sub_action == 'list':
                            if not is_admin(author_id):
                                response = '➜ Lệnh này chỉ khả thi với chủ nhân 🤧'
                            else:
                                response = list_approved(bot, author_id, settings)
                        else:
                            response = f"➜ Lệnh {prefix}bot approved {sub_action} không được hỗ trợ 🤧"

                elif action == 'clean':
                    if not is_admin(author_id):
                        response = "❌Bạn không phải admin bot!"
                    else:
                        deleted_dirs, deleted_files = clean_pycache()
                        response = f"🧹 Đã dọn dẹp hệ thống thành công!\n➜ Xóa {deleted_dirs} thư mục __pycache__\n➜ Xóa {deleted_files} tệp .pyc/.pyo"

                elif action == 'admin':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [list/add/remove] sau lệnh: {prefix}bot admin 🤧\n➜ Ví dụ: {prefix}bot admin list hoặc {prefix}bot admin add @TXA hoặc {prefix}bot admin remove @TXA ✅"
                    else:
                        settings = read_settings()
                        admin_bot = settings.get("admin_bot", [])  
                        sub_action = parts[2].lower()
                        if sub_action == 'add':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {prefix}bot admin add 🤧\n➜ Ví dụ: {prefix}bot admin add @TXA ✅"
                            else:
                                if author_id not in admin_bot:
                                    response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                                else:
                                    mentioned_uids = extract_uids_from_mentions(message_object)
                                    response = add_admin(bot, author_id, mentioned_uids, settings)
                        elif sub_action == 'remove':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {prefix}bot admin remove 🤧\n➜ Ví dụ: {prefix}bot admin remove @TXA ✅"
                            else:
                                if author_id not in admin_bot:
                                    response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                                else:
                                    mentioned_uids = extract_uids_from_mentions(message_object)
                                    response = remove_admin(bot, author_id, mentioned_uids, settings)
                        elif sub_action == 'list':
                            if admin_bot:
                                response = "➜ 🛡️ Danh sách Admin BOT 👑\n"
                                for idx, uid in enumerate(admin_bot, start=1):
                                    response += f"      ➜ {idx}. 👑 {get_user_name_by_id(bot, uid)}\n"
                            else:
                                response = "➜ Không có Admin BOT nào trong danh sách 🤧"
                        else:
                            response = f"➜ Lệnh {prefix}bot admin {sub_action} không được hỗ trợ 🤧"


                elif action == 'setup':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {prefix}bot setup 🤧\n➜ Ví dụ: {prefix}bot setup on hoặc {prefix}bot setup off ✅"
                    else:
                        setup_action = parts[2].lower()
                        if setup_action == 'on':
                            if not is_admin(author_id):
                                response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                response = setup_bot_on(bot, thread_id)
                        elif setup_action == 'off':
                            if not is_admin(author_id):
                                response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                response = setup_bot_off(bot,thread_id)
                        else:
                            response = f"➜ Lệnh {prefix}bot setup {setup_action} không được hỗ trợ 🤧"
                elif action == 'link':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {prefix}bot link 🤧\n➜ Ví dụ: {prefix}bot link on hoặc {prefix}bot link off ✅"
                    else:
                        link_action = parts[2].lower()
                        if not is_admin(author_id):
                            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                        elif thread_type != ThreadType.GROUP:
                            response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                        else:
                            settings = read_settings()

                            if 'allow_link' not in settings:
                                settings['allow_link'] = {}

                            
                            if link_action == 'on':
                                settings['allow_link'][thread_id] = True
                                response = "➜ Tùy chọn cho phép gởi link 🔗 đã được bật 🟢 cho nhóm này ✅"
                            elif link_action == 'off':
                                settings['allow_link'][thread_id] = False
                                response = "➜ Tùy chọn cho phép gởi link 🔗 đã được tắt 🔴 cho nhóm này ✅"
                            else:
                                response = f"➜ Lệnh {prefix}bot link {link_action} không được hỗ trợ 🤧"
                        write_settings(settings)
                elif action == 'word':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [add/remove/list] sau lệnh: {prefix}bot word 🤧\n➜ Ví dụ: {prefix}bot word list hoặc {prefix}bot word add [từ khóa] ✅"
                    else:
                        sub_action = parts[2].lower()
                        if sub_action == 'list':
                            settings = read_settings()
                            forbidden_words = settings.get('forbidden_words', [])
                            if forbidden_words:
                                response = "➜ 🚫 Danh sách từ cấm hiện tại:\n"
                                for idx, w in enumerate(forbidden_words, start=1):
                                    response += f"      ➜ {idx}. {w}\n"
                            else:
                                response = "➜ Không có từ cấm nào trong danh sách 🤧"
                        elif len(parts) < 4:
                            response = f"➜ Vui lòng nhập [từ khóa] sau lệnh: {prefix}bot word {sub_action} 🤧\n➜ Ví dụ: {prefix}bot word {sub_action} [từ cấm] ✅"
                        else:
                            if not is_admin(author_id):
                                response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                word = ' '.join(parts[3:]) 
                                if sub_action == 'add':
                                    response = add_forbidden_word(word)
                                elif sub_action == 'remove':
                                    response = remove_forbidden_word(word)
                                else:
                                    response = f"➜ Lệnh [{prefix}bot word {sub_action}] không được hỗ trợ 🤧\n➜ Ví dụ: {prefix}bot word add [từ khóa] hoặc {prefix}bot word remove [từ khóa] ✅"
                elif action == 'noiquy':
                    settings = read_settings()
                    rules=settings.get("rules", {})
                    word_rule = rules.get("word", {"threshold": 3, "duration": 30})
                    threshold_word = word_rule["threshold"]
                    duration_word = word_rule["duration"]
                    group_admins = settings.get('group_admins', {})
                    admins = group_admins.get(thread_id, [])
                    group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
                    if admins:
                        response = (
                            f"➜ 💢 Nội quy 🤖BOT {bot.me_name} được áp dụng cho nhóm: {group.name} - ID: {thread_id} ✅\n"
                            f"➜ 🚫 Cấm sử dụng các từ ngữ thô tục 🤬 trong nhóm\n"
                            f"➜ 💢 Vi phạm {threshold_word} lần sẽ bị 😷 khóa mõm {duration_word} phút\n"
                            f"➜ ⚠️ Nếu tái phạm 2 lần sẽ bị 💪 kick khỏi nhóm 🤧"
                        )
                    else:
                        response = (
                            f"➜ 💢 Nội quy không áp dụng cho nhóm: {group.name} - ID: {thread_id} 💔\n➜ Lý do: 🤖BOT {bot.me_name} chưa được setup hoặc BOT không có quyền cầm key quản trị nhóm 🤧"
                        )
                elif action == 'ban':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập list hoặc ban @tag tên sau lệnh: {prefix}bot 🤧\n➜ Ví dụ: {prefix}bot list hoặc {prefix}bot ban @TXA ✅"
                    else:
                        s_action = parts[2].lower()
                        # Show current ban/muted list
                        if s_action == 'list':
                            result = print_muted_users_in_group(bot, thread_id)
                            if result.get('mentions'):
                                bot.replyMessage(Message(text=result['text'], mention=MultiMention(result['mentions'])), message_object, thread_id, thread_type)
                            else:
                                bot.replyMessage(Message(text=result['text']), message_object, thread_id, thread_type)
                            return
                        # Otherwise treat as ban command (must tag users)
                        else:
                            if not is_admin(author_id):
                                response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            elif check_admin_group(bot, thread_id) == False:
                                response = "➜ Lệnh này không khả thi do 🤖BOT không có quyền cầm 🔑 key nhóm 🤧"
                            else:
                                uids = extract_uids_from_mentions(message_object)
                                if not uids:
                                    response = f"➜ Vui lòng tag người dùng để cấm: {prefix}bot ban @user ✅"
                                else:
                                    response = add_users_to_ban_list(bot, uids, thread_id, "Quản trị viên cấm")

                elif action == 'unban':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập @tag tên sau lệnh: {prefix}bot unban 🤧\n➜ Ví dụ: {prefix}bot unban @TXA ✅"
                    else:
                        if not is_admin(author_id):
                            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                        elif thread_type != ThreadType.GROUP:
                            response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                        else:
                            
                            uids = extract_uids_from_mentions(message_object)
                            response = remove_users_from_ban_list(bot, uids, thread_id)

                elif action in ('spam', 'anti'):
                    if not is_admin(author_id):
                        response = "❌Bạn không phải admin bot!"
                    elif len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {prefix}bot anti 🤧\n➜ Ví dụ: {prefix}bot anti on hoặc {prefix}bot anti off ✅"
                    else:
                        spam_action = parts[2].lower()
                        settings = read_settings()

                        if 'spam_enabled' not in settings:
                            settings['spam_enabled'] = {}

                        if spam_action == 'on':
                            settings['spam_enabled'][thread_id] = True  
                            response = f"Anti-Spam đã bật ✅\n"
                        elif spam_action == 'off':
                            settings['spam_enabled'][thread_id] = False  
                            response = f"Anti-Spam đã tắt ⭕️\n"
                        else:
                            response = f"➜ Lệnh {prefix}bot anti {spam_action} không hợp lệ 🤧"
                        
                        write_settings(settings)
                
                elif action == 'welcome':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {prefix}bot welcome 🤧\n➜ Ví dụ: {prefix}bot welcome on hoặc {prefix}bot welcome off ✅"
                    else:
                        settings = read_settings()
                        setup_action = parts[2].lower()
                        if setup_action == 'on':
                            if not is_admin(author_id):
                                response = "❌Bạn không phải admin bot!"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                response = handle_welcome_on(bot, thread_id)
                        elif setup_action == 'off':
                            if not is_admin(author_id):
                                response = "❌Bạn không phải admin bot!"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                response = handle_welcome_off(bot, thread_id)
                        else:
                            response = f"➜ Lệnh {prefix}bot welcome {setup_action} không được hỗ trợ 🤧"

                elif action == 'goodbye':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {prefix}bot goodbye 🤧\n➜ Ví dụ: {prefix}bot goodbye on hoặc {prefix}bot goodbye off ✅"
                    else:
                        setup_action = parts[2].lower()
                        if setup_action == 'on':
                            if not is_admin(author_id):
                                response = "❌Bạn không phải admin bot!"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                response = handle_goodbye_on(bot, thread_id)
                        elif setup_action == 'off':
                            if not is_admin(author_id):
                                response = "❌Bạn không phải admin bot!"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                response = handle_goodbye_off(bot, thread_id)
                        else:
                            response = f"➜ Lệnh {prefix}bot goodbye {setup_action} không được hỗ trợ 🤧"

                elif action == 'autoapprove':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {prefix}bot autoapprove 🤧\n➜ Ví dụ: {prefix}bot autoapprove on hoặc {prefix}bot autoapprove off ✅"
                    else:
                        setup_action = parts[2].lower()
                        if setup_action == 'on':
                            if not is_admin(author_id):
                                response = "❌Bạn không phải admin bot!"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                settings = read_settings()
                                if 'auto_approve_members' not in settings:
                                    settings['auto_approve_members'] = {}
                                settings['auto_approve_members'][thread_id] = True
                                write_settings(settings)
                                response = "✅ Tự động duyệt thành viên yêu cầu vào nhóm đã được BẬT ✅"
                        elif setup_action == 'off':
                            if not is_admin(author_id):
                                response = "❌Bạn không phải admin bot!"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                settings = read_settings()
                                if 'auto_approve_members' not in settings:
                                    settings['auto_approve_members'] = {}
                                settings['auto_approve_members'][thread_id] = False
                                write_settings(settings)
                                response = "⭕ Tự động duyệt thành viên yêu cầu vào nhóm đã được TẮT ⭕"
                        else:
                            response = f"➜ Lệnh {prefix}bot autoapprove {setup_action} không được hỗ trợ 🤧"

                elif action == 'block':
                      
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập @tag tên sau lệnh: {prefix}bot block 🤧\n➜ Ví dụ: {prefix}bot block @TXA ✅"
                    else:
                        s_action = parts[2]  
                      
                        if s_action == 'list':
                            result = print_blocked_users_in_group(bot, thread_id)
                            if result['mentions']:
                                bot.replyMessage(Message(text=result['text'], mention=MultiMention(result['mentions'])), message_object, thread_id, thread_type)
                            else:
                                bot.replyMessage(Message(text=result['text']), message_object, thread_id, thread_type)
                            return
                        else:
                         
                            if not is_admin(author_id):
                                response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            elif check_admin_group(bot,thread_id)==False:
                                response = "➜ Lệnh này không khả thi do 🤖BOT không có quyền cầm 🔑 key nhóm 🤧"
                            else:
                              
                                uids = extract_uids_from_mentions(message_object)
                                response = block_users_from_group(bot, uids, thread_id)

                elif action == 'unblock':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập UID sau lệnh: {prefix}bot unblock 🤧\n➜ Ví dụ: {prefix}bot unblock 8421834556970988033, 842183455697098804... ✅"
                    else:
                        if not is_admin(author_id):
                            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                        elif thread_type != ThreadType.GROUP:
                            response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                        else:
                           
                            ids_str = parts[2]  
                            print(f"Chuỗi UIDs: {ids_str}")

                            uids = [uid.strip() for uid in ids_str.split(',') if uid.strip()]
                            print(f"Danh sách UIDs: {uids}")

                            
                            if uids:
                              
                                response = unblock_users_from_group(bot, uids, thread_id)
                            else:
                                response = "➜ Không có UID nào hợp lệ để bỏ chặn 🤧"

                elif action == 'kick':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập @tag tên sau lệnh: {prefix}bot kick 🤧\n➜ Ví dụ: {prefix}bot kick @TXA ✅"
                    else:
                        if not is_admin(author_id):
                            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                        elif thread_type != ThreadType.GROUP:
                            response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                        elif check_admin_group(bot,thread_id)==False:
                                response = "➜ Lệnh này không khả thi do 🤖BOT không có quyền cầm 🔑 key nhóm 🤧"
                        else:
                            uids = extract_uids_from_mentions(message_object)
                            response = kick_users_from_group(bot, uids, thread_id)

                elif action == 'rule':
                    if len(parts) < 5:
                        response = f"➜ Vui lòng nhập word [n lần] [m phút] sau lệnh: {prefix}bot rule 🤧\n➜ Ví dụ: {prefix}bot rule word 3 30 ✅"
                    else:
                        rule_type = parts[2].lower()
                        try:
                            threshold = int(parts[3])
                            duration = int(parts[4])
                        except ValueError:
                            response = "➜ Số lần và phút phạt phải là số nguyên 🤧"
                        else:
                            settings = read_settings()
                            if rule_type not in ["word", "spam"]:
                                response = f"➜ Lệnh {prefix}bot rule {rule_type} không được hỗ trợ 🤧\n➜ Ví dụ: {prefix}bot rule word 3 30✅"
                            else:
                                if not is_admin(author_id):
                                    response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                                elif thread_type != ThreadType.GROUP:
                                    response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                                else:
                                    settings.setdefault("rules", {})
                                    settings["rules"][rule_type] = {
                                        "threshold": threshold,
                                        "duration": duration
                                    }
                                    write_settings(settings)
                                    response = f"➜ 🔄 Đã cập nhật nội quy cho {rule_type}: Nếu vi phạm {threshold} lần sẽ bị phạt {duration} phút ✅"

                elif action == 'policy':
                    if not is_admin(author_id):
                        response = "❌Bạn không phải admin bot!"
                    elif thread_type != ThreadType.GROUP:
                        response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                    elif len(parts) < 3:
                        # Show current policy config
                        settings = read_settings()
                        policies = settings.get("policies", {})
                        group_policies = policies.get(thread_id, {})
                        
                        policy_types = {
                            "word": "🔤 Từ cấm",
                            "link": "🔗 Gửi link",
                            "sticker": "🎨 Spam sticker",
                            "image": "🖼️ Spam ảnh",
                            "flood": "💬 Spam tin nhắn"
                        }
                        
                        response = f"📋 Cấu hình Policy nhóm:\n"
                        for p_type, p_name in policy_types.items():
                            p_config = group_policies.get(p_type, {})
                            enabled = p_config.get("enabled", False)
                            threshold = p_config.get("threshold", 3)
                            duration = p_config.get("duration", 30)
                            action_type = p_config.get("action", "mute")
                            status = "✅ BẬT" if enabled else "⭕ TẮT"
                            
                            action_text = {"mute": "😷 Khóa mõm", "kick": "💪 Kick", "warn": "⚠️ Cảnh báo"}.get(action_type, "😷 Khóa mõm")
                            response += f"   {p_name}: {status}\n"
                            if enabled:
                                response += f"      Vi phạm {threshold} lần → {action_text} {duration}p\n"
                        
                        response += (
                            f"\n📖 HƯỚNG DẪN CẤU HÌNH POLICY\n"
                            f"1️⃣ Các loại vi phạm (Loại):\n"
                            f"   • word (Từ cấm), link (Gửi link), sticker (Spam sticker)\n"
                            f"   • image (Spam ảnh), flood (Spam tin nhắn)\n"
                            f"2️⃣ Bật/Tắt nhanh:\n"
                            f"   ➜ {prefix}bot policy [loại] [on/off]\n"
                            f"   VD: {prefix}bot policy link on\n"
                            f"3️⃣ Cài đặt chi tiết hình phạt:\n"
                            f"   ➜ {prefix}bot policy [loại] [lần] [phút] [hành_động]\n"
                            f"   Loại: word / link / sticker / image / flood\n"
                            f"   Hành động: mute (Khóa mõm) / kick (Trục xuất) / warn (Cảnh báo)\n"
                            f"   • mute: xóa nội dung vi phạm và khóa mõm trong [phút]\n"
                            f"   • kick: xóa nội dung vi phạm và kick khi đủ [lần]\n"
                            f"   • warn: cảnh báo khi đủ [lần], không khóa mõm\n"
                            f"   VD: {prefix}bot policy word 3 60 mute\n"
                            f"   VD: {prefix}bot policy link 2 30 kick"
                        )
                    else:
                        policy_type = parts[2].lower()
                        valid_policies = ["word", "link", "sticker", "image", "flood"]
                        
                        if policy_type not in valid_policies:
                            response = f"➜ Loại policy không hợp lệ 🤧\n➜ Chọn: {', '.join(valid_policies)}"
                        elif len(parts) == 4 and parts[3].lower() in ('on', 'off'):
                            # Toggle on/off
                            settings = read_settings()
                            settings.setdefault("policies", {})
                            settings["policies"].setdefault(thread_id, {})
                            settings["policies"][thread_id].setdefault(policy_type, {"threshold": 3, "duration": 30, "action": "mute"})
                            
                            if parts[3].lower() == 'on':
                                settings["policies"][thread_id][policy_type]["enabled"] = True
                                response = f"✅ Policy [{policy_type}] đã BẬT cho nhóm này"
                            else:
                                settings["policies"][thread_id][policy_type]["enabled"] = False
                                response = f"⭕ Policy [{policy_type}] đã TẮT cho nhóm này"
                            
                            write_settings(settings)
                        elif len(parts) >= 5:
                            try:
                                threshold = int(parts[3])
                                duration = int(parts[4])
                                action_type = parts[5].lower() if len(parts) > 5 else "mute"
                                
                                if action_type not in ["mute", "kick", "warn"]:
                                    response = f"➜ Hành động không hợp lệ 🤧 Chọn: mute/kick/warn"
                                else:
                                    settings = read_settings()
                                    settings.setdefault("policies", {})
                                    settings["policies"].setdefault(thread_id, {})
                                    settings["policies"][thread_id][policy_type] = {
                                        "enabled": True,
                                        "threshold": threshold,
                                        "duration": duration,
                                        "action": action_type
                                    }
                                    write_settings(settings)
                                    
                                    action_text = {"mute": "😷 Khóa mõm", "kick": "💪 Kick", "warn": "⚠️ Cảnh báo"}.get(action_type, "😷 Khóa mõm")
                                    response = f"✅ Policy [{policy_type}] đã cập nhật:\n   Vi phạm {threshold} lần → {action_text} {duration} phút"
                            except ValueError:
                                response = "➜ Số lần và phút phạt phải là số nguyên 🤧"
                        else:
                            response = f"➜ Cú pháp: {prefix}bot policy {policy_type} [on/off] hoặc {prefix}bot policy {policy_type} [lần] [phút] [mute/kick/warn]"
                else:
                    bot.replyMessage(Message(text=f"➜ Lệnh [{prefix}bot {action}] không được hỗ trợ 🤧"), message_object, thread_id=thread_id, thread_type=thread_type)
            
            if response:
                if len(parts) == 1:
                    temp_image_path = create_menu1_image({"response": response}, 1, bot, author_id)
                    bot.sendLocalImage(
                        temp_image_path, thread_id=thread_id, thread_type=thread_type,
                        message=Message(text=response), height=350, width=980, ttl=60000
                    )
                    os.remove(temp_image_path)
                else:
                    bot.replyMessage(Message(text=response),message_object, thread_id=thread_id, thread_type=thread_type,ttl=9000)
        
        except Exception as e:
            print(f"Error: {e}")
            bot.replyMessage(Message(text="➜ 🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type)

    thread = threading.Thread(target=send_bot_response)
    thread.start()

def create_menu1_image(command_names, page, bot, author_id):
    
    avatar_url = None

    if author_id:
        user_info = bot.fetchUserInfo(author_id)
        avatar_url = user_info.changed_profiles.get(author_id).avatar

    start_index = (page - 1) * 10
    end_index = start_index + 10
    current_page_commands = list(command_names.items())[start_index:end_index]

    
    numbered_commands = [f"⭐ {i + start_index + 1}. {name} - {desc}" for i, (name, desc) in enumerate(current_page_commands)]

    
    background_dir = "background"
    background_files = [os.path.join(background_dir, f) for f in os.listdir(background_dir) if f.endswith(('.png', '.jpg'))]
    background_path = random.choice(background_files)
    image = Image.open(background_path).convert("RGBA")
    image = image.resize((1280, 500))

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    rect_x0 = (1280 - 1100) // 2
    rect_y0 = (500 - 300) // 2
    rect_x1 = rect_x0 + 1100
    rect_y1 = rect_y0 + 300

    radius = 50
    draw.rounded_rectangle([rect_x0, rect_y0, rect_x1, rect_y1], radius=radius, fill=(255, 255, 255, 200))
    overlay = Image.alpha_composite(image, overlay)
    if avatar_url:
        try:
            avatar_response = requests.get(avatar_url)
            avatar_image = Image.open(BytesIO(avatar_response.content)).convert("RGBA").resize((100, 100))

            gradient_size = 110
            gradient_colors = create_gradient_colors(7)
            gradient_overlay = Image.new("RGBA", (gradient_size, gradient_size), (0, 0, 0, 0))
            gradient_draw = ImageDraw.Draw(gradient_overlay)

            for i, color in enumerate(gradient_colors):
                radius = gradient_size // 2 - i
                gradient_draw.ellipse(
                    (i, i, gradient_size - i, gradient_size - i),
                    outline=color,
                    width=1
                )

            mask = Image.new("L", avatar_image.size, 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 100, 100), fill=255)
            gradient_overlay.paste(avatar_image, (5, 5), mask)

            overlay.paste(gradient_overlay, (rect_x0 + 20, rect_y0 + 100), gradient_overlay)
        except Exception:
            pass
    

    text_hi = f"Hi {user_info.changed_profiles[author_id].displayName}!" if author_id in user_info.changed_profiles else "Hi Người dùng!"
    text_welcome = f"   Hi, {user_info.changed_profiles[author_id].displayName}, Tôi có thể giúp gì cho bạn?"
    bot_name = getattr(bot, "me_name", "bin")
    bot_version = getattr(bot, "version", "1.0.0")
    bot_update = getattr(bot, "date_update", datetime.now().strftime("%d-%m-%y"))
    text_bot_info = f"🤖 Bot: {bot_name} 💻 version {bot_version} 🗓️ update {bot_update}"
    text_bot_ready = f"♥️ Bot sẵn sàng phục vụ tình iu :3"
    font_paci = "font/Kai.ttf"
    font_emoji = "font/NotoEmoji-Bold.ttf"
    draw = ImageDraw.Draw(overlay)

    font_hi = ImageFont.truetype(font_paci, size=50) if os.path.exists(font_paci) else ImageFont.load_default()
    font_welcome = ImageFont.truetype(font_paci, size=35) if os.path.exists(font_paci) else ImageFont.load_default()
    font_bot_info = ImageFont.truetype(font_emoji, size=25) if os.path.exists(font_emoji) else ImageFont.load_default()

    x_hi = rect_x0 + (1100 - draw.textbbox((0, 0), text_hi, font=font_hi)[2]) // 2

    y_hi = rect_y0 + 10

    gradient_colors_hi = interpolate_colors(create_gradient_colors(5), len(text_hi), 1)
    for i, char in enumerate(text_hi):
        draw.text((x_hi, y_hi), char, font=font_hi, fill=gradient_colors_hi[i])
        try:
            x_hi += font_hi.getlength(char)
        except AttributeError:
            x_hi += draw.textbbox((0, 0), char, font=font_hi)[2]

    x_welcome = (1200 - draw.textbbox((0, 0), text_welcome, font=font_welcome)[2]) // 2
    y_welcome = y_hi + 60

    gradient_colors_welcome = interpolate_colors(create_gradient_colors(5), len(text_welcome), 1)
    for i, char in enumerate(text_welcome):
        draw.text((x_welcome, y_welcome), char, font=font_welcome, fill=gradient_colors_welcome[i])
        try:
            x_welcome += font_welcome.getlength(char)
        except AttributeError:
            x_welcome += draw.textbbox((0, 0), char, font=font_welcome)[2]

    x_bot_info = rect_x0 + (1100 - draw.textbbox((0, 0), text_bot_info, font=font_welcome)[2]) // 2

    y_bot_info = rect_y1 - 60

    gradient_colors_bot_info = interpolate_colors(create_gradient_colors(7), len(text_bot_info), 1)
    current_x = x_bot_info

    for i, char in enumerate(text_bot_info):
        if char in "🤖💻🗓️🎊":
            current_font = font_bot_info
        else:
            current_font = font_welcome

        draw.text((current_x, y_bot_info), char, font=current_font, fill=gradient_colors_bot_info[i])
        try:
            char_width = current_font.getlength(char)
        except AttributeError:
            char_width = draw.textbbox((0, 0), char, font=current_font)[2]
        current_x += char_width

    y_bot_ready = y_bot_info - 80
    gradient_colors_bot_ready = interpolate_colors(create_gradient_colors(5), len(text_bot_ready), 1)
    current_x_bot_ready = (1200 - draw.textbbox((0, 0), text_bot_ready, font=font_welcome)[2]) // 2

    for i, char in enumerate(text_bot_ready):
        if char in "♥️:3🤗🎉🎊":
            current_font = font_bot_info
        else:
            current_font = font_welcome
        draw.text((current_x_bot_ready, y_bot_ready), char, font=current_font, fill=gradient_colors_bot_ready[i])
        try:
            char_width = current_font.getlength(char)
        except AttributeError:
            char_width = draw.textbbox((0, 0), char, font=current_font)[2]
        current_x_bot_ready += char_width

    overlay = Image.alpha_composite(image, overlay)
    temp_image_path = "temp_image.png"
    overlay.save(temp_image_path)

    return temp_image_path

def create_gradient_colors(num_colors):
    return [(random.randint(100, 175), random.randint(100, 180), random.randint(100, 170)) for _ in range(num_colors)]

def interpolate_colors(colors, text_length, change_every):
    gradient = []
    num_segments = len(colors) - 1
    steps_per_segment = (text_length // change_every) + 1
    for i in range(num_segments):
        for j in range(steps_per_segment):
            if len(gradient) < text_length:
                ratio = j / steps_per_segment
                interpolated_color = (
                    int(colors[i][0] * (1 - ratio) + colors[i + 1][0] * ratio),
                    int(colors[i][1] * (1 - ratio) + colors[i + 1][1] * ratio),
                    int(colors[i][2] * (1 - ratio) + colors[i + 1][2] * ratio)
                )
                gradient.append(interpolated_color)
    while len(gradient) < text_length:
        gradient.append(colors[-1])
    return gradient[:text_length]

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        return user_info.zaloName or user_info.displayName
    except Exception as e:
        return "Unknown User"
    
font_path_emoji = os.path.join("font/NotoEmoji-Bold.ttf")
font_path_arial = os.path.join("font/arial unicode ms.otf")

def create_gradient_colors(num_colors: int) -> List[Tuple[int, int, int]]:
    return [(random.randint(30, 255), random.randint(30, 255), random.randint(30, 255)) for _ in range(num_colors)]

def interpolate_colors(colors: List[Tuple[int, int, int]], text_length: int, change_every: int) -> List[Tuple[int, int, int]]:
    gradient = []
    num_segments = len(colors) - 1
    steps_per_segment = max((text_length // change_every) + 1, 1)

    for i in range(num_segments):
        for j in range(steps_per_segment):
            if len(gradient) < text_length:
                ratio = j / steps_per_segment
                interpolated_color = (
                    int(colors[i][0] * (1 - ratio) + colors[i + 1][0] * ratio),
                    int(colors[i][1] * (1 - ratio) + colors[i + 1][1] * ratio),
                    int(colors[i][2] * (1 - ratio) + colors[i + 1][2] * ratio)
                )
                gradient.append(interpolated_color)

    while len(gradient) < text_length:
        gradient.append(colors[-1])

    return gradient[:text_length]

def is_emoji(character: str) -> bool:
    return character in emoji.EMOJI_DATA

def create_text(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, 
                emoji_font: ImageFont.FreeTypeFont, text_position: Tuple[int, int], 
                gradient_colors: List[Tuple[int, int, int]]):
    gradient = interpolate_colors(gradient_colors, text_length=len(text), change_every=4)
    current_x = text_position[0]

    for i, char in enumerate(text):
        color = tuple(gradient[i])
        try:
            selected_font = emoji_font if is_emoji(char) and emoji_font else font
            draw.text((current_x, text_position[1]), char, fill=color, font=selected_font)
            try:
                text_width = selected_font.getlength(char)
            except AttributeError:
                text_bbox = draw.textbbox((0, 0), char, font=selected_font)
                text_width = text_bbox[2] - text_bbox[0]
                if text_width == 0 and char == " ":
                    text_width = selected_font.size // 3
            current_x += text_width
        except Exception as e:
            print(f"Lỗi khi vẽ ký tự '{char}': {e}. Bỏ qua ký tự này.")
            continue

def draw_gradient_border(draw: ImageDraw.Draw, center_x: int, center_y: int, 
                        radius: int, border_thickness: int, 
                        gradient_colors: List[Tuple[int, int, int]]):
    num_segments = 80
    gradient = interpolate_colors(gradient_colors, num_segments, change_every=10)

    for i in range(num_segments):
        start_angle = i * (360 / num_segments)
        end_angle = (i + 1) * (360 / num_segments)
        color = tuple(gradient[i])
        draw.arc(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            start=start_angle, end=end_angle, fill=color, width=border_thickness
        )

def load_image_from_url(url: str) -> Image.Image:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert('RGBA')
    except Exception as e:
        print(f"Lỗi khi tải ảnh từ URL {url}: {e}")
        return Image.new('RGBA', (100, 100), (0, 0, 0, 0))

def generate_short_filename(length: int = 10) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def load_random_background(background_dir: str = "background") -> Image.Image:
    if not os.path.exists(background_dir):
        print(f"Error: Background folder '{background_dir}' does not exist.")
        return None
    background_files = [os.path.join(background_dir, f) for f in os.listdir(background_dir) 
                       if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not background_files:
        print(f"Error: No valid image files found in '{background_dir}'")
        return None
    background_path = random.choice(background_files)
    try:
        return Image.open(background_path).convert("RGBA")
    except Exception as e:
        print(f"Error loading image {background_path}: {e}")
        return None

def create_default_background(width: int, height: int) -> Image.Image:
    return Image.new('RGBA', (width, height), (0, 100, 0, 255))

def create_default_avatar(name: str) -> Image.Image:
    avatar = Image.new('RGBA', (170, 170), (200, 200, 200, 255))
    draw = ImageDraw.Draw(avatar)
    draw.ellipse((0, 0, 170, 170), fill=(100, 100, 255, 255))
    initials = (name[:2].upper() if name else "??")
    font = ImageFont.truetype(font_path_arial, 60)
    text_bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    draw.text(
        ((170 - text_width) // 2, (170 - text_height) // 2),
        initials,
        font=font,
        fill=(255, 255, 255, 255)
    )
    return avatar

def create_banner(bot, uid: str, thread_id: str, group_name: str = None, 
                 avatar_url: str = None, event_type: str = None, 
                 event_data = None, background_dir: str = "background") -> str:
    try:
        settings = read_settings()
        if not settings.get("welcome", {}).get(thread_id, False):
            return None
            
        member_info = bot.fetchUserInfo(uid).changed_profiles.get(uid)
        if not member_info:
            print(f"[ERROR] Không tìm thấy thông tin user {uid}")
            return None
            
        avatar_url = member_info.avatar if not avatar_url else avatar_url
        user_name = getattr(member_info, 'zaloName', f"User{uid}")

        group_info = bot.group_info_cache.get(thread_id, {})
        group_name = group_info.get('name', "Nhóm không xác định") if not group_name else group_name
        total_members = group_info.get('total_member', 0)
        thread_type = ThreadType.GROUP

        ow_name = ""
        ow_avatar_url = ""
        if event_data and hasattr(event_data, 'sourceId'):
            try:
                ow_info = bot.fetchUserInfo(event_data.sourceId).changed_profiles.get(event_data.sourceId)
                ow_name = getattr(ow_info, 'zaloName', f"Admin{event_data.sourceId}") if ow_info else "Quản trị viên"
                ow_avatar_url = ow_info.avatar if ow_info else ""
            except Exception as e:
                print(f"[WARNING] Lỗi khi lấy thông tin admin: {e}")
                ow_name = "Quản trị viên"

        event_config = {
            GroupEventType.JOIN: {
                'main_text': f'Chào mừng, {user_name} 💜',
                'group_name_text': group_name,
                'credit_text': f"Được duyệt bởi {ow_name}" if ow_name else "Đã được duyệt vào nhóm",
                'msg': f"🎉 Chào mừng {user_name} đã được duyệt vào nhóm" + (f" bởi {ow_name}! 🚀" if ow_name else "! 🚀"),
                'mention': Mention(uid=uid, offset=12, length=len(user_name))
            },
            GroupEventType.LEAVE: {
                'main_text': f'Tạm biệt, {user_name} 💔',
                'group_name_text': "Cộng Đồng",
                'credit_text': "Đã rời khỏi nhóm",
                'msg': f'💔 {user_name}',
                'mention': None
            },
            GroupEventType.ADD_ADMIN: {
                'main_text': f'Chúc mừng, {user_name}',
                'group_name_text': "Cộng Đồng",
                'credit_text': f"bổ nhiệm làm phó nhóm🔑",
                'msg': f'🎉 {user_name}',
                'mention': None
            },
            GroupEventType.REMOVE_ADMIN: {
                'main_text': f'Rất tiếc, {user_name}',
                'group_name_text': "Cộng Đồng",
                'credit_text': f"Đã bị xóa vai trò nhóm❌",
                'msg': f'⚠️ {user_name}',
                'mention': None
            },
            GroupEventType.REMOVE_MEMBER: {
                'main_text': f'Nhây này, {user_name}',
                'group_name_text': "Cộng Đồng",
                'credit_text': f"Đã bị kick khỏi nhóm🚫",
                'msg': f'🚫 {user_name}',
                'mention': None
            },
            GroupEventType.JOIN_REQUEST: {
                'main_text': f'Yêu cầu tham gia ✋',
                'group_name_text': "Cộng Đồng",
                'credit_text': f"{user_name}",
                'msg': f'✋ {user_name}',
                'mention': None
            }
        }

        config = event_config.get(event_type)
        if not config:
            print(f"[ERROR] Sự kiện {event_type} không được hỗ trợ")
            return None
        
        banner_width, banner_height = 980, 350
        
        try:
            background = load_random_background(background_dir) or create_default_background(banner_width, banner_height)
            background = background.resize((banner_width, banner_height), Image.LANCZOS)
            background_blurred = background.filter(ImageFilter.GaussianBlur(radius=5))
        except Exception as e:
            print(f"[ERROR] Lỗi background: {e}")
            background = create_default_background(banner_width, banner_height)
            background_blurred = background

        overlay = Image.new("RGBA", (banner_width, banner_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        glass_color = (
            random.randint(30, 80),
            random.randint(30, 80), 
            random.randint(30, 80),
            random.randint(170, 220)
        )
        
        rect_margin = 60
        rect_x0, rect_y0 = rect_margin, 30
        rect_x1, rect_y1 = banner_width - rect_margin, banner_height - 30
        draw.rounded_rectangle([rect_x0, rect_y0, rect_x1, rect_y1], radius=30, fill=glass_color)

        member_circle_radius = 25
        member_circle_x = rect_x1 - member_circle_radius - 20 
        member_circle_y = rect_y0 + member_circle_radius + 15
        
        circle_border_color = (
            random.randint(100, 255),
            random.randint(100, 255),
            random.randint(100, 255),
            255 
        )
        
        draw.ellipse(
            [member_circle_x - member_circle_radius, 
             member_circle_y - member_circle_radius,
             member_circle_x + member_circle_radius, 
             member_circle_y + member_circle_radius],
            outline=circle_border_color,
            width=6
        )
        
        member_font = ImageFont.truetype(font_path_arial, 20)
        member_count_text = str(total_members)
        member_bbox = draw.textbbox((0, 0), member_count_text, font=member_font)
        member_text_width = member_bbox[2] - member_bbox[0]
        member_text_height = member_bbox[3] - member_bbox[1]
        
        member_text_x = member_circle_x - (member_text_width // 2)
        member_text_y = member_circle_y - (member_text_height // 2 + 10)
        draw.text(
            (member_text_x, member_text_y),
            member_count_text,
            font=member_font,
            fill=(255, 255, 255, 255)
        )

        banner = Image.alpha_composite(background_blurred, overlay)

        try:
            avatar = load_image_from_url(avatar_url) or create_default_avatar(user_name)
            avatar_size = 135
            mask = Image.new('L', (avatar_size, avatar_size), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            
            avatar = avatar.resize((avatar_size, avatar_size), Image.LANCZOS)
            avatar_x = rect_x0 + 25
            avatar_y = rect_y1 - avatar_size - 70
            banner.paste(avatar, (avatar_x, avatar_y), mask)
            
            border_size = 4
            border = Image.new('RGBA', (avatar_size + border_size*2, avatar_size + border_size*2), (255, 255, 255, 255))
            border_mask = Image.new('L', (avatar_size + border_size*2, avatar_size + border_size*2), 0)
            border_draw = ImageDraw.Draw(border_mask)
            border_draw.ellipse((0, 0, avatar_size + border_size*2, avatar_size + border_size*2), fill=255)
            banner.paste(border, (avatar_x - border_size, avatar_y - border_size), border_mask)
            banner.paste(avatar, (avatar_x, avatar_y), mask)
        except Exception as e:
            print(f"[WARNING] Lỗi avatar người dùng: {e}")

        if ow_avatar_url:
            try:
                ow_avatar = load_image_from_url(ow_avatar_url) or create_default_avatar(ow_name)
                ow_avatar = ow_avatar.resize((avatar_size, avatar_size), Image.LANCZOS)
                ow_avatar_x = rect_x1 - avatar_size - 25
                ow_avatar_y = avatar_y
                banner.paste(ow_avatar, (ow_avatar_x, ow_avatar_y), mask)
                
                banner.paste(border, (ow_avatar_x - border_size, ow_avatar_y - border_size), border_mask)
                banner.paste(ow_avatar, (ow_avatar_x, ow_avatar_y), mask)
            except Exception as e:
                print(f"[WARNING] Lỗi avatar người thực hiện: {e}")

        draw = ImageDraw.Draw(banner)
        
        def get_vibrant_color():
            colors = [
                (255, 90, 90), (90, 255, 90), (90, 90, 255),
                (255, 255, 90), (255, 90, 255), (90, 255, 255)
            ]
            return random.choice(colors)
        
        font_main = ImageFont.truetype(font_path_arial, 50)
        main_text = config['main_text']
        main_bbox = draw.textbbox((0, 0), main_text, font=font_main)
        main_width = main_bbox[2] - main_bbox[0]
        main_x = rect_x0 + (rect_x1 - rect_x0 - main_width) // 2
        main_y = rect_y0 + 10
        draw.text((main_x, main_y), main_text, font=font_main, fill=get_vibrant_color())

        font_group = ImageFont.truetype(font_path_arial, 48)
        group_text = config['group_name_text']
        group_bbox = draw.textbbox((0, 0), group_text, font=font_group)
        group_width = group_bbox[2] - group_bbox[0]
        group_x = rect_x0 + (rect_x1 - rect_x0 - group_width) // 2
        group_y = main_y + main_bbox[3] + 15
        max_width = rect_x1 - rect_x0 - 20
        if group_width > max_width:
            while group_bbox[2] - group_bbox[0] > max_width and len(group_text) > 0:
                group_text = group_text[:-1]
                group_bbox = draw.textbbox((0, 0), group_text + "...", font=font_group)
            group_text += "..."
        draw.text((group_x, group_y), group_text, font=font_group, fill=get_vibrant_color())

        font_credit = ImageFont.truetype(font_path_arial, 38)
        credit_text = config['credit_text']
        credit_bbox = draw.textbbox((0, 0), credit_text, font=font_credit)
        credit_width = credit_bbox[2] - credit_bbox[0]
        credit_x = rect_x0 + (rect_x1 - rect_x0 - credit_width) // 2
        credit_y = group_y + group_bbox[3] + 15
        draw.text((credit_x, credit_y), credit_text, font=font_credit, fill=(255, 255, 255))

        time_text = f"📅 {time.strftime('%d/%m/%Y')}  ⏰ {time.strftime('%H:%M:%S')}    🔑 Executed by {ow_name}" if ow_name else f"📅 {time.strftime('%d/%m/%Y')}     ⏰ {time.strftime('%H:%M:%S')}"
        font_footer = ImageFont.truetype(font_path_arial, 22)
        footer_bbox = draw.textbbox((0, 0), time_text, font=font_footer)
        footer_x = rect_x0 + (rect_x1 - rect_x0 - footer_bbox[2]) // 2 + 20
        footer_y = rect_y1 - footer_bbox[3] - 15
        draw.text((footer_x, footer_y), time_text, font=font_footer, fill=(220, 220, 220))

        file_name = f"banner_{int(time.time())}.jpg"
        try:
            banner.convert('RGB').save(file_name, quality=95)
            if event_type:
                bot.sendMultiLocalImage(
                    [file_name],
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=banner_width,
                    height=banner_height,
                    message=Message(text=config['msg'], mention=config.get('mention')),
                    ttl=60000 * 60
                )
        except Exception as e:
            print(f"[ERROR] Lỗi khi lưu/gửi banner: {e}")
            return None
        finally:
            try:
                delete_file(file_name)
            except:
                pass

        return file_name

    except Exception as e:
        print(f"[CRITICAL] Lỗi nghiêm trọng: {str(e)}")
        return None

def delete_file(file_path: str):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Đã xóa tệp: {file_path}")
    except Exception as e:
        print(f"Lỗi khi xóa tệp: {e}")

def load_emoji_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        if os.path.exists(font_path_emoji):
            return ImageFont.truetype(font_path_emoji, size)
        if os.name == 'nt':
            return ImageFont.truetype("seguiemj.ttf", size)
        elif os.path.exists("/System/Library/Fonts/Apple Color font/Emoji.ttc"):
            return ImageFont.truetype("/System/Library/Fonts/Apple Color font/Emoji.ttc", size)
    except Exception:
        return None

def handle_event(client, event_data, event_type):
    try:
        if not hasattr(event_data, 'groupId'):
            print(f"Dữ liệu sự kiện không có groupId: {event_data}")
            return

        thread_id = event_data.groupId
        thread_type = ThreadType.GROUP
        
        settings = read_settings()
        
        # Xử lý tự động duyệt thành viên yêu cầu vào nhóm
        if event_type == GroupEventType.JOIN_REQUEST:
            auto_approve = settings.get("auto_approve_members", {}).get(thread_id, False)
            if auto_approve:
                try:
                    # Kiểm tra nhóm có bật yêu cầu duyệt không
                    group_info = client.fetchGroupInfo(thread_id)
                    # Nếu group có pendingApprove hoặc viewGroupPending trả về kết quả thì nhóm đang bật duyệt
                    pending = client.viewGroupPending(thread_id)
                    if pending and hasattr(pending, 'users') and pending.users:
                        for member in event_data.updateMembers:
                            member_id = member['id']
                            try:
                                client.handleGroupPending(member_id, thread_id, isApprove=True)
                                print(f"✅ Auto-approved member {member_id} for group {thread_id}")
                            except Exception as approve_err:
                                print(f"❌ Lỗi auto-approve member {member_id}: {approve_err}")
                except Exception as check_err:
                    print(f"❌ Lỗi kiểm tra pending group {thread_id}: {check_err}")
            return
        
        if not settings.get("welcome", {}).get(thread_id, False):
            return
            
        group_info = client.fetchGroupInfo(thread_id)
        group_name = group_info.gridInfoMap.get(str(thread_id), {}).get('name', 'nhóm')
        total_member = group_info.gridInfoMap[str(thread_id)]['totalMember']

        client.group_info_cache[thread_id] = {
            "name": group_name,
            "member_list": group_info.gridInfoMap[str(thread_id)]['memVerList'],
            "total_member": total_member
        }

        for member in event_data.updateMembers:
            member_id = member['id']
            member_name = member['dName']
            user_info = client.fetchUserInfo(member_id)
            avatar_url = user_info.changed_profiles[member_id].avatar

            create_banner(
                client, 
                member_id, 
                thread_id, 
                group_name=group_name, 
                avatar_url=avatar_url, 
                event_type=event_type, 
                event_data=event_data
            )

    except Exception as e:
        print(f"Lỗi khi xử lý event {event_type}: {e}")

def get_allow_welcome(bot, thread_id: str) -> bool:
    settings = read_settings()
    return settings.get("welcome", {}).get(thread_id, False)

def initialize_group_info(bot, allowed_thread_ids: List[str]):
    for thread_id in allowed_thread_ids:
        group_info = bot.fetchGroupInfo(thread_id).gridInfoMap.get(thread_id, None)
        if group_info:
            bot.group_info_cache[thread_id] = {
                "name": group_info['name'],
                "member_list": group_info['memVerList'],
                "total_member": group_info['totalMember']
            }
        else:
            print(f"Bỏ qua nhóm {thread_id}")

def check_member_changes(bot, thread_id: str) -> Tuple[set, set]:
    current_group_info = bot.fetchGroupInfo(thread_id).gridInfoMap.get(thread_id, None)
    cached_group_info = bot.group_info_cache.get(thread_id, None)

    if not cached_group_info or not current_group_info:
        return set(), set()

    old_members = set([member.split('_')[0] for member in cached_group_info["member_list"]])
    new_members = set([member.split('_')[0] for member in current_group_info['memVerList']])

    joined_members = new_members - old_members
    left_members = old_members - new_members

    bot.group_info_cache[thread_id] = {
        "name": current_group_info['name'],
        "member_list": current_group_info['memVerList'],
        "total_member": current_group_info['totalMember']
    }

    return joined_members, left_members

def handle_group_member(bot, message_object, author_id: str, thread_id: str, thread_type: str):
    if not get_allow_welcome(bot, thread_id):
        return
        
    current_group_info = bot.fetchGroupInfo(thread_id).gridInfoMap.get(thread_id, None)
    cached_group_info = bot.group_info_cache.get(thread_id, None)

    if not cached_group_info or not current_group_info:
        print(f"Không có thông tin nhóm cho thread_id {thread_id}")
        return

    old_members = set([member.split('_')[0] for member in cached_group_info["member_list"]])
    new_members = set([member.split('_')[0] for member in current_group_info['memVerList']])

    joined_members = new_members - old_members
    left_members = old_members - new_members

    for member_id in joined_members:
        banner = create_banner(bot, member_id, thread_id, event_type=GroupEventType.JOIN, 
                             event_data=type('Event', (), {'sourceId': author_id or bot.uid})())
        if banner and os.path.exists(banner):
            try:
                user_name = bot.fetchUserInfo(member_id).changed_profiles[member_id].zaloName
                bot.sendLocalImage(
                    banner,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=980,
                    height=350,
                    message=Message(
                        text=f"🚦 {user_name}",
                        mention=Mention(uid=member_id, length=len(user_name), offset=3)
                    ),
                    ttl=86400000
                )
                delete_file(banner)
            except Exception as e:
                print(f"Lỗi khi gửi banner cho {member_id} (JOIN): {e}")
                if os.path.exists(banner):
                    delete_file(banner)

    for member_id in left_members:
        banner = create_banner(bot, member_id, thread_id, event_type=GroupEventType.LEAVE, 
                             event_data=type('Event', (), {'sourceId': author_id or bot.uid})())
        if banner and os.path.exists(banner):
            try:
                bot.sendLocalImage(
                    banner,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=980,
                    height=350,
                    ttl=86400000
                )
                delete_file(banner)
            except Exception as e:
                print(f"Lỗi khi gửi banner cho {member_id} (LEAVE): {e}")
                if os.path.exists(banner):
                    delete_file(banner)

    bot.group_info_cache[thread_id] = {
        "name": current_group_info['name'],
        "member_list": current_group_info['memVerList'],
        "total_member": current_group_info['totalMember']
    }

def start_member_check_thread(bot, allowed_thread_ids: List[str]):
    def check_members_loop():
        while True:
            for thread_id in allowed_thread_ids:
                if not get_allow_welcome(bot, thread_id):
                    continue
                handle_group_member(bot, None, None, thread_id, ThreadType.GROUP)
            time.sleep(2)

    thread = threading.Thread(target=check_members_loop, daemon=True)
    thread.start()
