
import colorsys
from datetime import datetime, timedelta
import difflib
import glob
import importlib
from io import BytesIO
import os
import platform
import random
import re
import string
import sys
from threading import Thread
import threading
import time
from typing import List, Optional, Tuple
import emoji
import psutil
import pytz
import requests
from zlapi.models import *
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BACKGROUND_PATH = "background/"
CACHE_PATH = "modules/cache/"
OUTPUT_IMAGE_PATH = os.path.join(CACHE_PATH, "bot.png")
SETTING_FILE = 'setting.json'
LOG_FILE = 'logs.json'
MUTED_MESSAGES_FILE = 'muted_messages.json'

def read_settings(uid):
    data_file_path = os.path.join(f"{uid}_{SETTING_FILE}")
    try:
        with open(data_file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def write_settings(uid, settings):
    data_file_path = os.path.join(f"{uid}_{SETTING_FILE}")
    with open(data_file_path, 'w', encoding='utf-8') as file:
        json.dump(settings, file, ensure_ascii=False, indent=4)

def load_message_log(uid):
    log_file_path = os.path.join(f"{uid}_{LOG_FILE}")
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            return settings.get("message_log", {})
    except FileNotFoundError:
        return {}

def save_message_log(uid, message_log):
    log_file_path = os.path.join(f"{uid}_{LOG_FILE}")
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}
    settings["message_log"] = message_log
    with open(log_file_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

def save_muted_message(uid, author_id, thread_id, message_content):
    muted_file_path = os.path.join(f"{uid}_{MUTED_MESSAGES_FILE}")
    try:
        with open(muted_file_path, 'r', encoding='utf-8') as file:
            muted_messages = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        muted_messages = {}

    if thread_id not in muted_messages:
        muted_messages[thread_id] = {}
    if author_id not in muted_messages[thread_id]:
        muted_messages[thread_id][author_id] = []

    muted_messages[thread_id][author_id].append(message_content)

    with open(muted_file_path, 'w', encoding='utf-8') as file:
        json.dump(muted_messages, file, ensure_ascii=False, indent=4)

def ban_user_from_commands(bot, author_id, mentioned_uids):
    settings = read_settings(bot.uid)
    admin_bot = settings.get("admin_bot", [])
    response = ""

    if author_id not in admin_bot:
        return "❌Bạn không phải admin bot!"

    banned_users = settings.get("banned_users", [])

    for uid in mentioned_uids:
        if uid not in banned_users:
            banned_users.append(uid)
            user_name = get_user_name_by_id(bot, uid)
            response += f"➜ Người dùng 👤 {user_name} đã bị cấm sử dụng các lệnh BOT 🤖\n"
        else:
            user_name = get_user_name_by_id(bot, uid)
            response += f"➜ Người dùng 👤 {user_name} đã bị cấm trước đó 🤧\n"

    settings["banned_users"] = banned_users
    write_settings(bot.uid, settings)
    return response

def unban_user_from_commands(bot, author_id, mentioned_uids):
    settings = read_settings(bot.uid)
    admin_bot = settings.get("admin_bot", [])
    response = ""

    if author_id not in admin_bot:
        return "❌Bạn không phải admin bot!"

    banned_users = settings.get("banned_users", [])

    for uid in mentioned_uids:
        if uid in banned_users:
            banned_users.remove(uid)
            user_name = get_user_name_by_id(bot, uid)
            response += f"➜ Người dùng 👤 {user_name} đã được gỡ cấm sử dụng các lệnh BOT 🤖\n"
        else:
            user_name = get_user_name_by_id(bot, uid)
            response += f"➜ Người dùng 👤 {user_name} không có trong danh sách cấm 🤧\n"

    settings["banned_users"] = banned_users
    write_settings(bot.uid, settings)
    return response

def list_banned_users(bot):
    settings = read_settings(bot.uid)
    banned_users = settings.get("banned_users", [])
    if not banned_users:
        return "➜ Không có người dùng nào bị cấm sử dụng các lệnh BOT 🤖"
    
    response = "➜ Danh sách người dùng bị cấm sử dụng các lệnh BOT 🤖:\n"
    for uid in banned_users:
        user_name = get_user_name_by_id(bot, uid)
        response += f"👤 {user_name}\n"
    return response

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
    
    return bool(re.search(url_regex, text_to_check))

def is_admin(bot, author_id):
    settings = read_settings(bot.uid)
    admin_bot = settings.get("admin_bot", [])
    return author_id in admin_bot

def is_group_admin_or_creator(bot, author_id, thread_id):
    try:
        group_info = bot.fetchGroupInfo(groupId=thread_id)
        if group_info and thread_id in group_info.gridInfoMap:
            group_data = group_info.gridInfoMap[thread_id]
            admin_ids = group_data.get('adminIds', [])
            creator_id = group_data.get('creatorId', '')
            return author_id in admin_ids or author_id == creator_id
    except Exception as e:
        print(f"[ERROR] is_group_admin_or_creator error: {e}")
    return False

def admin_cao(bot, author_id):
    settings = read_settings(bot.uid)
    high_level_admins = settings.get("high_level_admins", [])
    return author_id in high_level_admins

def handle_bot_admin(bot):
    settings = read_settings(bot.uid)
    admin_bot = settings.get("admin_bot", [])
    high_level_admins = settings.get("high_level_admins", [])

    if bot.uid not in admin_bot:
        admin_bot.append(bot.uid)
        settings['admin_bot'] = admin_bot
        write_settings(bot.uid, settings)
        print(f"Đã thêm 👑{get_user_name_by_id(bot, bot.uid)} 🆔 {bot.uid} cho lần đầu tiên khởi động vào danh sách Admin 🤖BOT ✅")

    if bot.uid not in high_level_admins:
        high_level_admins.append(bot.uid)
        settings['high_level_admins'] = high_level_admins
        write_settings(bot.uid, settings)
        print(f"Đã thêm 👑{get_user_name_by_id(bot, bot.uid)} 🆔 {bot.uid} vào danh sách Admin cấp cao 🤖BOT ✅")

def get_allowed_thread_ids(bot):
    settings = read_settings(bot.uid)
    return settings.get('allowed_thread_ids', [])

def bot_on_group(bot, thread_id, by_admin=False):
    try:
        settings = read_settings(bot.uid)
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

        write_settings(bot.uid, settings)

        return f"[🤖BOT {bot.me_name} {bot.version}] đã được bật trong Group: {group.name} - ID: {thread_id}\n➜ Gõ lệnh ➡️ {bot.prefix}help hoặc {bot.prefix}bot để xem danh sách tính năng BOT💡"
    except Exception as e:
        print(f"Error: {e}")
        return "Đã xảy ra lỗi gì đó🤧"

def bot_off_group(bot, thread_id, by_admin=False):
    try:
        settings = read_settings(bot.uid)
        allowed_thread_ids = settings.get('allowed_thread_ids', [])
        disabled_by_admin = settings.get('disabled_by_admin', [])
        group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]

        if thread_id in allowed_thread_ids:
            allowed_thread_ids.remove(thread_id)
            settings['allowed_thread_ids'] = allowed_thread_ids

        if by_admin and thread_id not in disabled_by_admin:
            disabled_by_admin.append(thread_id)
            settings['disabled_by_admin'] = disabled_by_admin

        write_settings(bot.uid, settings)

        if by_admin:
            return f"[🤖BOT {bot.me_name} {bot.version}] đã được tắt và khóa kích hoạt từ xa cho Group: {group.name} - ID: {thread_id} 🛑"
        else:
            return f"[🤖BOT {bot.me_name} {bot.version}] đã được tắt trong Group: {group.name} - ID: {thread_id}\n➜ Chào tạm biệt chúc bạn luôn may mắn🍀"
    except Exception as e:
        print(f"Error: {e}")
        return "Đã xảy ra lỗi gì đó🤧"

def add_forbidden_word(bot, author_id, word):
    if not is_admin(bot, author_id):
        return "❌Bạn không phải admin bot!"
    
    settings = read_settings(bot.uid)
    forbidden_words = settings.get('forbidden_words', [])
    
    if word not in forbidden_words:
        forbidden_words.append(word)
        settings['forbidden_words'] = forbidden_words
        write_settings(bot.uid, settings)
        return f"➜ Từ '{word}' đã được thêm vào danh sách từ cấm ✅"
    else:
        return f"➜ Từ '{word}' đã tồn tại trong danh sách từ cấm 🤧"

def remove_forbidden_word(bot, author_id, word):
    if not is_admin(bot, author_id):
        return "❌Bạn không phải admin bot!"
    
    settings = read_settings(bot.uid)
    forbidden_words = settings.get('forbidden_words', [])
    
    if word in forbidden_words:
        forbidden_words.remove(word)
        settings['forbidden_words'] = forbidden_words
        write_settings(bot.uid, settings)
        return f"➜ Từ '{word}' đã được xóa khỏi danh sách từ cấm ✅"
    else:
        return f"Từ '{word}' không có trong danh sách từ cấm 🤧"

def is_forbidden_word(bot, word):
    settings = read_settings(bot.uid)
    forbidden_words = settings.get('forbidden_words', [])
    return word in forbidden_words

def setup_bot_on(bot, thread_id):
    group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
    admin_ids = group.adminIds.copy()
    if group.creatorId not in admin_ids:
        admin_ids.append(group.creatorId)
    
    if bot.uid in admin_ids:
        settings = read_settings(bot.uid)
        
        if 'group_admins' not in settings:
            settings['group_admins'] = {}
        
        settings['group_admins'][thread_id] = admin_ids
        write_settings(bot.uid, settings)
        
        return f"[🤖BOT {bot.me_name} {bot.version}]\n➜ Cấu hình thành công nội quy nhóm: {group.name} - ID: {thread_id} ✅\n➜ Hãy nhắn tin một cách văn minh lịch sự! ✨\n➜ Chúc bạn luôn may mắn! 🍀"
    else:
        return f"[🤖BOT {bot.me_name} {bot.version}]\n➜ Cấu hình thất bại cho nhóm: {group.name} - ID: {thread_id} ⚠️\n➜ Bạn không có quyền quản trị nhóm này! 🤧"
        
def handle_undo_message(bot, message_object, thread_id, thread_type):
    settings = read_settings(bot.uid)
    undo_enabled = settings.get('undo_enabled', {}).get(thread_id, True)

    # Nếu chưa bật tính năng undo → bỏ qua
    if not undo_enabled:
        return

    if message_object.msgType != 'chat.undo':
        return

    cli_msg_id = str(message_object.content.get('cliMsgId', ''))
    if not cli_msg_id:
        return

    # Đọc dữ liệu undo từ file
    try:
        with open('undo.json', 'r', encoding='utf-8') as f:
            undo_data = json.load(f)
    except:
        undo_data = []

    data = next((msg for msg in undo_data if msg.get('cliMsgId') == cli_msg_id), None)
    if not data:
        return

    uid_from = message_object.uidFrom
    mention = Mention(uid_from, offset=0, length=1)
    formatted_time = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime())
    content = data.get("content", {})
    msg_type = data.get("msgType", "")

    if msg_type == "chat.text":
        text = content.get("text", "")
        bot.replyMessage(
            Message(text=f"@ Vừa thu hồi tin nhắn:\n{text}\n🕒 {formatted_time}", mention=mention),
            message_object, thread_id, thread_type
        )

    elif msg_type == "chat.image" and "href" in content:
        bot.sendRemoteImage(content["href"], thumbnailUrl=content.get("thumb"), thread_id=thread_id, thread_type=thread_type)
        bot.replyMessage(
            Message(text=f"@ Vừa thu hồi ảnh\n🕒 {formatted_time}", mention=mention),
            message_object, thread_id, thread_type
        )

    elif msg_type == "chat.video" and "href" in content:
        params = json.loads(content.get("params", "{}"))
        bot.sendRemoteVideo(
            videoUrl=content["href"],
            thumbnailUrl=content.get("thumb"),
            duration=params.get("duration", ""),
            width=params.get("video_width", ""),
            height=params.get("video_height", ""),
            thread_id=thread_id, thread_type=thread_type
        )
        bot.replyMessage(
            Message(text=f"@ Vừa thu hồi video\n🕒 {formatted_time}", mention=mention),
            message_object, thread_id, thread_type
        )

    elif msg_type == "chat.voice" and "href" in content:
        bot.sendRemoteVoice(content["href"], thread_id=thread_id, thread_type=thread_type)
        bot.replyMessage(
            Message(text=f"@ Vừa thu hồi voice\n🕒 {formatted_time}", mention=mention),
            message_object, thread_id, thread_type
        )

    elif msg_type == "chat.file" and "href" in content:
        file_name = content.get("fileName", "file")
        bot.sendRemoteFile(content["href"], filename=file_name, thread_id=thread_id, thread_type=thread_type)
        bot.replyMessage(
            Message(text=f"@ Vừa thu hồi file: {file_name}\n🕒 {formatted_time}", mention=mention),
            message_object, thread_id, thread_type
        )

    elif msg_type == "chat.sticker":
        catId = data.get('catId')
        msgId = data.get('id')
        bot.sendSticker(msgId, catId, thread_id, thread_type)
        bot.replyMessage(
            Message(text=f"@ Vừa thu hồi sticker\n🕒 {formatted_time}", mention=mention),
            message_object, thread_id, thread_type
        )

    else:
        bot.replyMessage(
            Message(text=f"@ Vừa thu hồi một loại tin nhắn không xác định\n🕒 {formatted_time}", mention=mention),
            message_object, thread_id, thread_type
        )

def setup_bot_off(bot, thread_id):
    group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
    settings = read_settings(bot.uid)

    if 'group_admins' in settings and thread_id in settings['group_admins']:
        del settings['group_admins'][thread_id]
        write_settings(bot.uid, settings)
        return f"[🤖BOT {bot.me_name} {bot.version}]\n➜ Đã hủy bỏ thành công cấu hình quản trị cho nhóm: {group.name} - ID: {thread_id} ✅\n➜ Hãy quẫy lên đi! 🤣"
    else:
        return f"[🤖BOT {bot.me_name} {bot.version}]\n➜ Không tìm thấy cấu hình quản trị cho nhóm: {group.name} - ID: {thread_id} để hủy bỏ! 🤧"

def check_admin_group(bot, thread_id):
    group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
    admin_ids = group.adminIds.copy()
    if group.creatorId not in admin_ids:
        admin_ids.append(group.creatorId)
    settings = read_settings(bot.uid)
    if 'group_admins' not in settings:
        settings['group_admins'] = {}
    settings['group_admins'][thread_id] = admin_ids
    write_settings(bot.uid, settings)
    return bot.uid in admin_ids

def get_allow_link_status(bot, thread_id):
    settings = read_settings(bot.uid)
    return settings.get('allow_link', {}).get(thread_id, False)

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        return user_info.zaloName or user_info.displayName
    except Exception:
        return "Unknown User"

polls_created = {}

def is_spamming(bot, author_id, thread_id):
    max_messages = 4 
    time_window = 2
    min_interval = 0.5
    message_log = load_message_log(bot.uid)
    key = f"{thread_id}_{author_id}"
    current_time = time.time()
    if key in message_log:
        user_data = message_log[key]
        last_message_time = user_data['last_message_time']
        message_times = user_data['message_times']
        if current_time - last_message_time < min_interval:
            recent_messages = [t for t in message_times if current_time - t <= min_interval]
            if len(recent_messages) >= 6:
                return True  
        message_times = [t for t in message_times if current_time - t <= time_window]
        message_times.append(current_time)
        message_log[key] = {
            'last_message_time': current_time,
            'message_times': message_times
        }
        if len(message_times) > max_messages:
            return True  
    else:
        message_log[key] = {
            'last_message_time': current_time,
            'message_times': [current_time]
        }
    save_message_log(bot.uid, message_log)
    return False 

user_message_count = {}
user_flood_timestamps = {}
def check_spam(bot, author_id, thread_id, message_object, thread_type):
    settings = read_settings(bot.uid)
    spam_enabled = settings.get('spam_enabled', False)
    
    if isinstance(spam_enabled, bool):
        if spam_enabled:
            settings['spam_enabled'] = {thread_id: True}
        else:
            settings['spam_enabled'] = {}
        write_settings(bot.uid, settings)
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

def safe_delete_message(bot, message_object, user_author_id, thread_id):
    def delete_message():
        max_retries = 20
        retries = 0
        while retries < max_retries:
            result = bot.deleteGroupMsg(message_object.msgId, user_author_id, message_object.cliMsgId, thread_id)
            if "error_code" not in result:
                print(f"➜ Xóa tin nhắn lần {retries} thành công:", result)
                return
            retries += 1
            time.sleep(0.8)
        print(f"➜ Thất bại khi xóa tin nhắn sau {retries} lần thử")
        return

    save_muted_message(bot.uid, user_author_id, thread_id, message_object.content)

    delete_thread = threading.Thread(target=delete_message)
    delete_thread.start()

def handle_check_profanity(bot, author_id, thread_id, message_object, thread_type, message):
    def send_check_profanity_response():
        settings = read_settings(bot.uid)
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
                        safe_delete_message(bot, message_object, author_id, thread_id)
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
                    write_settings(bot.uid, settings)
                    response = "➜ 🎉 Bạn đã được phép phát ngôn! Hãy nói chuyện 💬 lịch sự nhé! 😊👍"
                    bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                    try:
                        group_name = "nhóm"
                        if group_info and thread_id in group_info.gridInfoMap:
                            group_name = group_info.gridInfoMap[thread_id].get('name', 'nhóm')
                        pm_text = f"🎉 Bạn đã được mở mõm (cho phép phát ngôn) trong nhóm '{group_name}'! Hãy nói chuyện văn minh lịch sự nhé! 😊👍"
                        bot.send(Message(text=pm_text), thread_id=author_id, thread_type=ThreadType.USER)
                    except Exception as e:
                        print(f"[WARNING] Không thể gửi tin nhắn riêng mở cấm cho {author_id}: {e}")
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
            now_time = time.time()
            if 'user_flood_timestamps' not in globals():
                user_flood_timestamps = {}
            if thread_id not in user_flood_timestamps:
                user_flood_timestamps[thread_id] = {}
            if author_id not in user_flood_timestamps[thread_id]:
                user_flood_timestamps[thread_id][author_id] = []
            
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
                write_settings(bot.uid, settings)
                
                if action_type == "mute":
                    muted_users.append({
                        'author_id': author_id,
                        'thread_id': thread_id,
                        'reason': violation_reason,
                        'muted_until': current_time + 60 * duration
                    })
                    settings['muted_users'] = muted_users
                    write_settings(bot.uid, settings)
                    response = f"➜ 🚫 Bạn đã vi phạm policy [{violation_reason}] {threshold} lần\n➜ 🤐 Bạn đã bị khóa mõm trong {duration} phút!"
                    bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                    try:
                        group_name = "nhóm"
                        if group_info and thread_id in group_info.gridInfoMap:
                            group_name = group_info.gridInfoMap[thread_id].get('name', 'nhóm')
                        pm_text = f"🤐 Bạn đã bị khóa mõm trong nhóm '{group_name}' trong {duration} phút vì vi phạm chính sách: {violation_reason}."
                        bot.send(Message(text=pm_text), thread_id=author_id, thread_type=ThreadType.USER)
                    except Exception as e:
                        print(f"[WARNING] Không thể gửi tin nhắn riêng cấm cho {author_id}: {e}")
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
                write_settings(bot.uid, settings)
                response = f"➜ ⚠️ Cảnh báo: Bạn đã vi phạm policy [{violation_reason}] {violation_count}/{threshold} lần!\n➜ 🤐 Nếu tiếp tục vi phạm, bạn sẽ bị xử lý theo cấu hình nhóm!"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                return

        # Fallback to old checks
        spam_thread = threading.Thread(target=check_spam, args=(bot, author_id, thread_id, message_object, thread_type))
        spam_thread.start()

        if get_allow_link_status(bot, thread_id) and is_url_in_message(message_object):
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
                write_settings(bot.uid, settings)
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
                write_settings(bot.uid, settings)
                response = f"➜ 🚫 Bạn đã vi phạm {threshold_word} lần\n➜ 🤐 Bạn đã bị khóa mõm trong {duration_word} phút\n➜ 💢 Nội dung vi phạm: 🤬 '{message_text}'"
                bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                try:
                    group_name = "nhóm"
                    if group_info and thread_id in group_info.gridInfoMap:
                        group_name = group_info.gridInfoMap[thread_id].get('name', 'nhóm')
                    pm_text = f"🤐 Bạn đã bị khóa mõm trong nhóm '{group_name}' trong {duration_word} phút vì sử dụng từ ngữ thô tục: '{message_text}'."
                    bot.send(Message(text=pm_text), thread_id=author_id, thread_type=ThreadType.USER)
                except Exception as e:
                    print(f"[WARNING] Không thể gửi tin nhắn riêng cấm từ ngữ cho {author_id}: {e}")
                return
            elif profanity_count == threshold_word - 1:
                response = f"➜ ⚠️ Cảnh báo: Bạn đã vi phạm {profanity_count}/{threshold_word} lần\n➜ 🤐 Nếu bạn tiếp tục vi phạm, bạn sẽ bị khóa mõm trong {duration_word} phút\n➜ 💢 Nội dung vi phạm: 🤬 '{message_text}'"
                bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
            else:
                response = f"➜ ⚠️ Bạn đã vi phạm {profanity_count}/{threshold_word} lần!\n➜ 💢 Nội dung vi phạm: 🤬 '{message_text}'"
                bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
            write_settings(bot.uid, settings)

        doodle_enabled = settings.get('doodle_enabled', True)
        if message_object.msgType == 'chat.doodle' and not doodle_enabled:
            bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
            
        undo_enabled = settings.get('undo_enabled', {}).get(thread_id, True)
        if message_object.msgType == 'chat.undo ' and not doodle_enabled:
            bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
        
        voice_enabled = settings.get('voice_enabled', True)
        if message_object.msgType == 'chat.voice' and not voice_enabled:
            bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)

        chat_enabled = settings.get('chat_enabled', True)
        if not chat_enabled and (message_object.content is None or not isinstance(message_object.content, str)) and message_object.msgType != 'webchat':
            bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)

        image_enabled = settings.get('image_enabled', True)
        if message_object.msgType == 'chat.photo' and not image_enabled:
            bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)

        card_enabled = settings.get('card_enabled', True)
        if message_object.msgType == 'chat.recommended' and not card_enabled:
            bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)

        file_enabled = settings.get('file_enabled', True)
        if message_object.msgType == 'share.file' and not file_enabled:
            bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)

        sticker_enabled = settings.get('sticker_enabled', True)
        if message_object.msgType == 'chat.sticker' and not sticker_enabled:
            bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)

        gif_enabled = settings.get('gif_enabled', True)
        if message_object.msgType == 'chat.gif' and not gif_enabled:
            bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)

        video_enabled = settings.get('video_enabled', True)
        if message_object.msgType == 'chat.video.msg' and not video_enabled:
            bot.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)

        anti_poll_enabled = settings.get('anti_poll', True)
        if anti_poll_enabled and message_object.msgType == 'group.poll':
            if thread_id not in polls_created:
                polls_created[thread_id] = {}
            user_polls = polls_created[thread_id].get(author_id, [])
            user_polls.append(current_time)
            polls_created[thread_id][author_id] = user_polls
            user_polls = [poll_time for poll_time in user_polls if current_time - poll_time <= 300]
            if len(user_polls) > 3:
                response = "➜ ⛔ Bạn đã bị kick vì spam tạo quá nhiều cuộc khảo sát trong nhóm."
                bot.kickUsersInGroup(author_id, thread_id)
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                return
            polls_created[thread_id][author_id] = user_polls

    thread = Thread(target=send_check_profanity_response)
    thread.start()

def print_muted_users_in_group(bot, thread_id):
    settings = read_settings(bot.uid)
    muted_users = settings.get("muted_users", [])
    current_time = int(time.time())
    muted_users_list = []

    for user in muted_users:
        if user['thread_id'] == thread_id:
            author_id = user['author_id']
            user_name = get_user_name_by_id(bot, author_id)
            muted_until = user['muted_until']
            reason = user.get('reason', 'Không rõ lý do')

            if muted_until == float('inf'):
                minutes_left = 'Vô hạn'
            else:
                remaining_time = muted_until - current_time
                if remaining_time > 0:
                    minutes_left = remaining_time // 60
                else:
                    continue

            muted_users_list.append({
                "author_id": author_id,
                "name": user_name,
                "minutes_left": minutes_left,
                "reason": reason
            })

    muted_users_list.sort(key=lambda x: float('inf') if x['minutes_left'] == 'Vô hạn' else x['minutes_left'])

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
        result = (
            "➜ 🎉 Xin chúc mừng!\n"
            "➜ Nhóm không có thành viên nào tiêu cực ❤ 🌺 🌻 🌹 🌷 🌼\n"
            "➜ Hãy tiếp tục phát huy nhé 🤗"
        )
        mentions = []

    return {"text": result, "mentions": mentions}

def ban_users_permanently(bot, uids, thread_id):
    settings = read_settings(bot.uid)
    muted_users = settings.get('muted_users', [])

    group_name = "nhóm"
    try:
        group_info = bot.fetchGroupInfo(groupId=thread_id)
        if group_info and thread_id in group_info.gridInfoMap:
            group_name = group_info.gridInfoMap[thread_id].get('name', 'nhóm')
    except Exception:
        pass

    for uid in uids:
        user_name = get_user_name_by_id(bot, uid)
        muted_users.append({
            'author_id': uid,
            'thread_id': thread_id,
            'name': user_name,
            'reason': 'Quản trị viên cấm Vĩnh Viễn',
            'muted_until': float('inf')
        })
        try:
            pm_text = f"🤐 Bạn đã bị khóa mõm Vĩnh Viễn trong nhóm '{group_name}' bởi Quản trị viên."
            bot.send(Message(text=pm_text), thread_id=uid, thread_type=ThreadType.USER)
        except Exception as e:
            print(f"[WARNING] Không thể gửi tin nhắn riêng cấm vĩnh viễn cho {uid}: {e}")

    settings['muted_users'] = muted_users
    write_settings(bot.uid, settings)

    usernames = [get_user_name_by_id(bot, uid) for uid in uids]
    return f"➜ 😷 Người dùng {', '.join(usernames)} đã bị cấm phát ngôn vĩnh viễn do quản trị viên!"

def print_blocked_users_in_group(bot, thread_id):
    settings = read_settings(bot.uid)
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
    settings = read_settings(bot.uid)
    current_time = int(time.time())
    muted_users = settings.get("muted_users", [])
    violations = settings.get("violations", {})
    duration_minutes = settings.get("rules", {}).get("word", {}).get("duration", 30)

    group_name = "nhóm"
    try:
        group_info = bot.fetchGroupInfo(groupId=thread_id)
        if group_info and thread_id in group_info.gridInfoMap:
            group_name = group_info.gridInfoMap[thread_id].get('name', 'nhóm')
    except Exception:
        pass

    response = ""
    for author_id in author_ids:
        user = bot.fetchUserInfo(author_id).changed_profiles[author_id].displayName

        if not any(entry["author_id"] == author_id and entry["thread_id"] == thread_id for entry in muted_users):
            muted_users.append({
                "author_id": author_id,
                "thread_id": thread_id,
                "reason": reason,
                "muted_until": current_time + 60 * duration_minutes
            })
            
            try:
                pm_text = f"🤐 Bạn đã bị khóa mõm trong nhóm '{group_name}' bởi Quản trị viên trong {duration_minutes} phút. Lý do: {reason}."
                bot.send(Message(text=pm_text), thread_id=author_id, thread_type=ThreadType.USER)
            except Exception as e:
                print(f"[WARNING] Không thể gửi tin nhắn riêng cấm thủ công cho {author_id}: {e}")

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
    write_settings(bot.uid, settings)
    return response

def remove_users_from_ban_list(bot, author_ids, thread_id):
    settings = read_settings(bot.uid)
    muted_users = settings.get("muted_users", [])
    violations = settings.get("violations", {})
    response = ""

    group_name = "nhóm"
    try:
        group_info = bot.fetchGroupInfo(groupId=thread_id)
        if group_info and thread_id in group_info.gridInfoMap:
            group_name = group_info.gridInfoMap[thread_id].get('name', 'nhóm')
    except Exception:
        pass

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

        if initial_count != len(muted_users) or removed:
            response += f"➜ 🎉 Chúc mừng {user} đã được phép phát ngôn 😤\n"
            try:
                pm_text = f"🎉 Bạn đã được mở mõm (cho phép phát ngôn) trong nhóm '{group_name}' bởi Quản trị viên! Hãy nói chuyện văn minh lịch sự nhé! 😊👍"
                bot.send(Message(text=pm_text), thread_id=author_id, thread_type=ThreadType.USER)
            except Exception as e:
                print(f"[WARNING] Không thể gửi tin nhắn riêng mở cấm thủ công cho {author_id}: {e}")
        else:
            response += f"➜ 😲 {user} không có trong danh sách cấm phát ngôn 🤧\n"
    
    settings['muted_users'] = muted_users
    settings['violations'] = violations
    write_settings(bot.uid, settings)
    return response

def block_users_from_group(bot, author_ids, thread_id):
    response = ''
    block_user = []
    settings = read_settings(bot.uid)

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

    write_settings(bot.uid, settings)

    if block_user:
        blocked_users_str = ', '.join(block_user)
        response = f"➜ :v {blocked_users_str} đã bị chặn khỏi nhóm 🤧"
    else:
        response = "➜ Không ai bị chặn khỏi nhóm 🤧"
    
    return response

def unblock_users_from_group(bot, author_ids, thread_id):
    response = ''
    unblocked_users = []
    settings = read_settings(bot.uid)

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
        
        write_settings(bot.uid, settings)

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
            bot.blockUsersInGroup(uid, thread_id)
            user_name = get_user_name_by_id(bot, uid)
            response += f"➜ 💪 Đã kick người dùng 😫 {user_name} khỏi nhóm thành công ✅\n"
        except Exception as e:
            user_name = get_user_name_by_id(bot, uid)
            response += f"➜ 😲 Không thể kick người dùng 😫 {user_name} khỏi nhóm 🤧\n"
    
    return response

def promote_to_admin(bot, mentioned_uids, thread_id):
    try:
        bot.addGroupAdmins(mentioned_uids, thread_id)
        response = ""
        for uid in mentioned_uids:
            response += f"🎉 Đã nâng quyền admin cho người dùng 👤 {get_user_name_by_id(bot, uid)} trong nhóm! ✅\n"
        return response
    except Exception as e:
        return f"❌ Đã xảy ra lỗi khi nâng quyền admin: {str(e)}"

def remove_adminn(bot, mentioned_uids, thread_id):
    try:
        bot.removeGroupAdmins(mentioned_uids, thread_id)
        response = ""
        for uid in mentioned_uids:
            response += f"❌ Đã xóa quyền admin của người dùng 👤 {get_user_name_by_id(bot, uid)} trong nhóm! ✅\n"
        return response
    except Exception as e:
        return f"❌ Đã xảy ra lỗi khi xóa quyền admin: {str(e)}"

def extract_uids_from_mentions(message_object):
    uids = []
    if message_object.mentions:
        uids = [mention['uid'] for mention in message_object.mentions if 'uid' in mention]
    return uids

def add_admin(bot, author_id, mentioned_uids):
    settings = read_settings(bot.uid)
    admin_bot = settings.get("admin_bot", [])
    high_level_admins = settings.get("high_level_admins", [])
    response = ""

    if author_id != high_level_admins[0]:
        response = "❌Bạn không phải admin bot!"
    else:
        for uid in mentioned_uids:
            if uid in admin_bot:
                user_name = get_user_name_by_id(bot, uid) if get_user_name_by_id(bot, uid) else "Người dùng không tồn tại"
                response += f"➜ Người dùng 👑 {user_name} đã có trong danh sách Admin 🤖BOT 🤧\n"
            else:
                admin_bot.append(uid)
                user_name = get_user_name_by_id(bot, uid) if get_user_name_by_id(bot, uid) else "Người dùng không tồn tại"
                response += f"➜ Đã thêm 👑 {user_name} vào danh sách Admin 🤖BOT ✅\n"

    settings['admin_bot'] = admin_bot
    write_settings(bot.uid, settings)
    return response

def remove_admin(bot, author_id, mentioned_uids):
    settings = read_settings(bot.uid)
    admin_bot = settings.get("admin_bot", [])
    high_level_admins = settings.get("high_level_admins", [])
    response = ""

    if author_id != high_level_admins[0]:
        response = "❌Bạn không phải admin bot!"
    else:
        for uid in mentioned_uids:
            if uid in admin_bot:
                user_name = get_user_name_by_id(bot, uid) if get_user_name_by_id(bot, uid) else "Người dùng không tồn tại"
                admin_bot.remove(uid)
                response += f"➜ Đã xóa người dùng 👑 {user_name} khỏi danh sách Admin 🤖BOT ✅\n"
            else:
                user_name = get_user_name_by_id(bot, uid) if get_user_name_by_id(bot, uid) else "Người dùng không tồn tại"
                response += f"➜ Người dùng 👑 {user_name} không có trong danh sách Admin 🤖BOT 🤧\n"

    settings['admin_bot'] = admin_bot
    write_settings(bot.uid, settings)
    return response

def add_approved(bot, author_id, mentioned_uids, settings, expiry_time=None):
    if not is_admin(bot, author_id):
        return "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
    approved_users = settings.setdefault("approved_users", [])
    response = ""
    for uid in mentioned_uids:
        if uid not in approved_users:
            approved_users.append(uid)
            
            # Lưu thời gian hết hạn
            approved_expiry = settings.setdefault("approved_users_expiry", {})
            approved_expiry[uid] = expiry_time
            settings["approved_users_expiry"] = approved_expiry
            
            if expiry_time:
                expiry_str = datetime.fromtimestamp(expiry_time).strftime("%H:%M:%S %d/%m/%Y")
                response += f"➜ Đã thêm người dùng ✅ {get_user_name_by_id(bot, uid)} vào danh sách được duyệt đến {expiry_str} ✅\n"
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
                
            # Thực hiện dọn dẹp tin nhắn cảnh báo chưa được duyệt trước đó
            cleanup_pending_messages(bot, uid)
        else:
            # Nếu đã được duyệt từ trước, vẫn cho phép cập nhật lại thời hạn mới
            approved_expiry = settings.setdefault("approved_users_expiry", {})
            approved_expiry[uid] = expiry_time
            settings["approved_users_expiry"] = approved_expiry
            
            if expiry_time:
                expiry_str = datetime.fromtimestamp(expiry_time).strftime("%H:%M:%S %d/%m/%Y")
                response += f"➜ Đã cập nhật hạn duyệt dùng BOT cho người dùng ✅ {get_user_name_by_id(bot, uid)} đến {expiry_str} ✅\n"
                
                try:
                    inbox_text = f"🎉 Chào bạn, Admin đã gia hạn quyền sử dụng TXA Bot của bạn đến {expiry_str}! Hãy tiếp tục trải nghiệm nhé. 🌸"
                    bot.send(Message(text=inbox_text), thread_id=uid, thread_type=ThreadType.USER)
                except Exception as e:
                    print(f"[ERROR] Không thể gửi tin nhắn riêng cho {uid}: {e}")
            else:
                response += f"➜ Người dùng ✅ {get_user_name_by_id(bot, uid)} đã có trong danh sách được duyệt vô thời hạn 🤧\n"

    settings['approved_users'] = approved_users
    write_settings(bot.uid, settings)
    return response

def remove_approved(bot, author_id, mentioned_uids, settings):
    if not is_admin(bot, author_id):
        return "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
    approved_users = settings.setdefault("approved_users", [])
    response = ""
    for uid in mentioned_uids:
        if uid in approved_users:
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
    write_settings(bot.uid, settings)
    return response

def list_approved(bot, author_id, settings):
    if not is_admin(bot, author_id):
        return "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"

    approved_users = settings.get("approved_users", [])
    if not approved_users:
        return "➜ 🎉 Danh sách được duyệt trống! 🌼"

    result = "➜ ✅ Danh sách người dùng được duyệt: 🤖\n"
    for idx, uid in enumerate(approved_users, start=1):
        user_name = get_user_name_by_id(bot, uid)
        result += f"{idx}. ✅ {user_name} - {uid}\n"

    return result

def cleanup_pending_messages(bot, target_uid):
    try:
        settings = read_settings(bot.uid)
        pending_cleanups = settings.get("pending_cleanups", {})
        
        target_uid_str = str(target_uid)
        target_uid_int = None
        try:
            target_uid_int = int(target_uid)
        except:
            pass

        found_key = None
        if target_uid_str in pending_cleanups:
            found_key = target_uid_str
        elif target_uid_int is not None and str(target_uid_int) in pending_cleanups:
            found_key = str(target_uid_int)
        elif target_uid_int is not None and target_uid_int in pending_cleanups:
            found_key = target_uid_int

        if found_key is not None:
            cleanups = pending_cleanups[found_key]
            for msg_info in cleanups[:]:
                thread_id = msg_info.get("thread_id")
                
                # Xóa tin nhắn của người dùng gửi lệnh chưa duyệt
                user_msg_id = msg_info.get("user_msg_id")
                user_cli_msg_id = msg_info.get("user_cli_msg_id")
                if user_msg_id and user_cli_msg_id and thread_id:
                    try:
                        bot.deleteGroupMsg(user_msg_id, target_uid_str, user_cli_msg_id, thread_id)
                    except Exception as e:
                        print(f"[ERROR] Không thể xóa tin nhắn người dùng {user_msg_id}: {e}")
                
                # Xóa tin nhắn cảnh báo tương ứng của Bot
                warning_msg_id = msg_info.get("warning_msg_id")
                warning_cli_msg_id = msg_info.get("warning_cli_msg_id")
                if warning_msg_id and warning_cli_msg_id and thread_id:
                    try:
                        bot.deleteGroupMsg(warning_msg_id, bot.uid, warning_cli_msg_id, thread_id)
                    except Exception as e:
                        print(f"[ERROR] Không thể xóa tin nhắn cảnh báo Bot {warning_msg_id}: {e}")
            
            # Xóa sạch lịch sử sau khi dọn dẹp
            del pending_cleanups[found_key]
            settings["pending_cleanups"] = pending_cleanups
            write_settings(bot.uid, settings)
    except Exception as e:
        print(f"[ERROR] Lỗi khi dọn dẹp tin nhắn chờ: {e}")

def parse_expiration_time(time_arg: str) -> Optional[float]:
    if not time_arg:
        return None
    time_arg = time_arg.strip()
    if not time_arg:
        return None
        
    # Thử parse số giây
    if time_arg.isdigit():
        return time.time() + int(time_arg)
        
    # Thử parse định dạng ngày giờ: H:M:S d/m/Y hoặc H:M:S d/m/y
    # Ví dụ: 10:30:00 06/06/2026
    datetime_pattern = r'^(\d{1,2}):(\d{1,2}):(\d{1,2})\s+(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$'
    match = re.match(datetime_pattern, time_arg)
    if match:
        h, m, s, day, month, year = match.groups()
        h, m, s, day, month, year = int(h), int(m), int(s), int(day), int(month), int(year)
        if year < 100:
            year += 2000
        try:
            dt = datetime(year, month, day, h, m, s)
            return dt.timestamp()
        except Exception as e:
            print(f"[ERROR] parse_expiration_time datetime error: {e}")
            return None
            
    return None

def clean_pycache():
    import shutil
    deleted_dirs = 0
    deleted_files = 0
    for root, dirs, files in os.walk("."):
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

def add_skip(bot, author_id, mentioned_uids):
    if not is_admin(bot, author_id):
        return "❌Bạn không phải admin bot!"
    
    settings = read_settings(bot.uid)
    admin_bot = settings.get("skip_bot", [])
    response = ""
    for uid in mentioned_uids:
        user_name = get_user_name_by_id(bot, uid)
        if uid not in admin_bot:
            admin_bot.append(uid)
            response += f"🚦Đã thêm người dùng 👑 {user_name} vào danh sách ưu tiên 🤖Bot ✅\n"
        else:
            response += f"🚦Người dùng 👑 {user_name} đã có trong danh sách ưu tiên 🤖Bot 🤧\n"
    settings['skip_bot'] = admin_bot
    write_settings(bot.uid, settings)
    return response

def remove_skip(bot, author_id, mentioned_uids):
    if not is_admin(bot, author_id):
        return "❌Bạn không phải admin bot!"
    
    settings = read_settings(bot.uid)
    admin_bot = settings.get("skip_bot", [])
    response = ""
    for uid in mentioned_uids:
        if uid in admin_bot:
            admin_bot.remove(uid)
            response += f"🚦Đã xóa người dùng 👑 {get_user_name_by_id(bot, uid)} khỏi danh sách ưu tiên 🤖Bot ✅\n"
        else:
            response += f"🚦Người dùng 👑 {get_user_name_by_id(bot, uid)} không có trong danh sách ưu tiên 🤖Bot 🤧\n"
    settings['skip_bot'] = admin_bot
    write_settings(bot.uid, settings)
    return response

def get_blocked_members(bot, thread_id, page=1, count=50):
    try:
        response = bot.get_blocked_members(thread_id, page, count)
        if not response.get("success"):
            return "❌ Không thể lấy danh sách bị chặn."
        
        blocked_data = response.get("blocked_members", {}).get("data", {}).get("blocked_members", [])
        if not blocked_data:
            return "📌 Không có thành viên nào bị chặn trong nhóm."

        result = "🚫 Danh sách thành viên bị chặn:\n"
        for member in blocked_data:
            result += f"🔹 ID: {member['id']}\n"
            result += f"🔹 Tên hiển thị: {member['dName']}\n"
            result += "----------------------\n"
        return result
    except Exception as e:
        return f"❌ Đã xảy ra lỗi khi lấy danh sách bị chặn: {str(e)}"

def get_group_admins(bot, thread_id):
    try:
        group_info = bot.fetchGroupInfo(groupId=thread_id)
        admin_ids = group_info.gridInfoMap[thread_id].get('adminIds', [])
        creator_id = group_info.gridInfoMap[thread_id].get('creatorId', None)

        if not admin_ids:
            return "📌 Không có admin trong nhóm."

        result = "🚀 Danh sách admin trong nhóm:\n"
        if creator_id:
            creator_name = get_user_name_by_id(bot, creator_id)
            result += f"👑 {creator_name}\n"

        for admin_id in admin_ids:
            user_name = get_user_name_by_id(bot, admin_id)
            result += f"🔹 {user_name}\n"
        return result
    except Exception as e:
        return f"❌ Đã xảy ra lỗi khi lấy danh sách admin: {str(e)}"

def remove_link(bot, thread_id):
    try:
        group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        bot.dislink(grid=thread_id)
        return f"🔗 Link nhóm {group.name} đã được xóa! ✅"
    except Exception as e:
        return f"❌ Đã xảy ra lỗi khi xóa link nhóm: {str(e)}"

def newlink(bot, thread_id):
    try:
        group_name = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id].name
        bot.newlink(grid=thread_id)
        return f"🔗 Link nhóm {group_name} đã tạo mới ✅"
    except Exception as e:
        return f"❌ Đã xảy ra lỗi khi tạo link nhóm: {str(e)}"

def list_bots(bot, thread_id):
    settings = read_settings(bot.uid)
    response = " "
    group_info = bot.fetchGroupInfo(thread_id)
    group_name = group_info.gridInfoMap.get(thread_id, {}).get('name', 'N/A')
    bot_name = get_user_name_by_id(bot, bot.uid)
    response += f"👥 Nhóm: {group_name}\n"
    response += f"🤖 Admin: {bot_name}\n"
    
    spam_enabled = settings.get('spam_enabled', {}).get(str(thread_id), True)
    anti_poll = settings.get('anti_poll', True)
    video_enabled = settings.get('video_enabled', True)
    card_enabled = settings.get('card_enabled', True)
    file_enabled = settings.get('file_enabled', True)
    image_enabled = settings.get('image_enabled', True)
    chat_enabled = settings.get('chat_enabled', True)
    voice_enabled = settings.get('voice_enabled', True)
    sticker_enabled = settings.get('sticker_enabled', True)
    gif_enabled = settings.get('gif_enabled', True)
    doodle_enabled = settings.get('doodle_enabled', True)
    allow_link = settings.get('allow_link', {}).get(str(thread_id), True)
    sos_status = settings.get('sos_status', True)
    undo_enabled = settings.get('undo_enabled', {}).get(thread_id, True)
    
    status_icon = lambda enabled: "⭕️" if enabled else "✅"

    response += (
        f"{status_icon(spam_enabled)} Anti-Spam 💢\n"
        f"{status_icon(anti_poll)} Anti-Poll 👍\n"
        f"{status_icon(video_enabled)} Anti-Video ▶️\n"
        f"{status_icon(card_enabled)} Anti-Card 🛡️\n"
        f"{status_icon(file_enabled)} Anti-File 🗂️\n"
        f"{status_icon(image_enabled)} Anti-Photo 🏖\n"
        f"{status_icon(chat_enabled)} SafeMode 🩹\n"
        f"{status_icon(voice_enabled)} Anti-Voice 🔊\n"
        f"{status_icon(sticker_enabled)} Anti-Sticker 😊\n"
        f"{status_icon(gif_enabled)} Anti-Gif 🖼️\n"
        f"{status_icon(doodle_enabled)} Anti-Draw ✏️\n"
        f"{status_icon(sos_status)} SOS 🆘\n"
        f"{status_icon(allow_link)} Anti-Link 🔗\n"
        f"{status_icon(undo_enabled)} Anti-Undo 🔗\n"
    )
    return response

def reload_modules(self, message_object, thread_id: Optional[str], thread_type: Optional[str]):
    if thread_id is None or thread_type is None:
        raise ValueError("thread_id and thread_type must be provided")

    current_modules = [name for name in sys.modules.keys() if name.startswith("modules.")]
    
    modules_to_reload = [m for m in current_modules if m != "modules"]
    base_modules = ["modules."]
    reload_candidates = []
    
    for module in modules_to_reload:
        similarity = difflib.SequenceMatcher(None, module, "modules.").ratio()
        if similarity > 0.5:
            reload_candidates.append(module)
    
    for name in reload_candidates:
        if name in sys.modules:
            del sys.modules[name]
    
    for module_name in reload_candidates:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            self.replyMessage(
                Message(text=f"⚠️ Lỗi khi reload {module_name}: {str(e)}"), 
                message_object, 
                thread_id=thread_id, 
                thread_type=thread_type
            )
            continue
    
    self.replyMessage(
        Message(text="🚦Đã sửa chữa lỗi treo lệnh command ✅"), 
        message_object, 
        thread_id=thread_id, 
        thread_type=thread_type
    )

def get_dominant_color(image_path):
    try:
        if not os.path.exists(image_path):
            print(f"File ảnh không tồn tại: {image_path}")
            return (0, 0, 0)

        img = Image.open(image_path).convert("RGB")
        img = img.resize((150, 150), Image.Resampling.LANCZOS)
        pixels = img.getdata()

        if not pixels:
            print(f"Không thể lấy dữ liệu pixel từ ảnh: {image_path}")
            return (0, 0, 0)

        r, g, b = 0, 0, 0
        for pixel in pixels:
            r += pixel[0]
            g += pixel[1]
            b += pixel[2]
        total = len(pixels)
        if total == 0:
            return (0, 0, 0)
        r, g, b = r // total, g // total, b // total
        return (r, g, b)

    except Exception as e:
        print(f"Lỗi khi phân tích màu nổi bật: {e}")
        return (0, 0, 0)

def get_contrasting_color(base_color, alpha=255):
    r, g, b = base_color[:3]
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return (255, 255, 255, alpha) if luminance < 0.5 else (0, 0, 0, alpha)

def random_contrast_color(base_color):
    r, g, b, _ = base_color
    box_luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    
    if box_luminance > 0.5:
        r = random.randint(0, 50)
        g = random.randint(0, 50)
        b = random.randint(0, 50)
    else:
        r = random.randint(200, 255)
        g = random.randint(200, 255)
        b = random.randint(200, 255)
    
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    s = min(1.0, s + 0.9)
    v = min(1.0, v + 0.7)
    
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    
    text_luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    if abs(text_luminance - box_luminance) < 0.3:
        if box_luminance > 0.5:
            r, g, b = colorsys.hsv_to_rgb(h, s, min(1.0, v * 0.4))
        else:
            r, g, b = colorsys.hsv_to_rgb(h, s, min(1.0, v * 1.7))
    
    return (int(r * 255), int(g * 255), int(b * 255), 255)

def download_avatar(avatar_url, save_path=os.path.join(CACHE_PATH, "user_avatar.png")):
    if not avatar_url:
        return None
    try:
        resp = requests.get(avatar_url, stream=True, timeout=5)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            return save_path
    except Exception as e:
        print(f"❌ Lỗi tải avatar: {e}")
    return None

def generate_menu_image(bot, author_id, thread_id, thread_type):
    images = glob.glob(os.path.join(BACKGROUND_PATH, "*.jpg")) + \
             glob.glob(os.path.join(BACKGROUND_PATH, "*.png")) + \
             glob.glob(os.path.join(BACKGROUND_PATH, "*.jpeg"))
    if not images:
        print("❌ Không tìm thấy ảnh trong thư mục background/")
        return None

    image_path = random.choice(images)

    try:
        size = (1920, 600)
        final_size = (1280, 380)
        bg_image = Image.open(image_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=7))
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        dominant_color = get_dominant_color(image_path)
        r, g, b = dominant_color
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

        box_colors = [
            (255, 20, 147, 90),
            (128, 0, 128, 90),
            (0, 100, 0, 90),
            (0, 0, 139, 90),
            (184, 134, 11, 90),
            (138, 3, 3, 90),
            (0, 0, 0, 90)
        ]

        box_color = random.choice(box_colors)

        box_x1, box_y1 = 90, 60
        box_x2, box_y2 = size[0] - 90, size[1] - 60
        draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=75, fill=box_color)

        font_arial_path = "font/arial unicode ms.otf"
        font_emoji_path = "font/NotoEmoji-Bold.ttf"
        
        try:
            font_text_large = ImageFont.truetype(font_arial_path, size=76)
            font_text_big = ImageFont.truetype(font_arial_path, size=68)
            font_text_small = ImageFont.truetype(font_arial_path, size=64)
            font_text_bot = ImageFont.truetype(font_arial_path, size=58)
            font_time = ImageFont.truetype(font_arial_path, size=56)
            font_icon = ImageFont.truetype(font_emoji_path, size=60)
            font_icon_large = ImageFont.truetype(font_emoji_path, size=175)
            font_name = ImageFont.truetype(font_emoji_path, size=60)
        except Exception as e:
            print(f"❌ Lỗi tải font: {e}")
            font_text_large = ImageFont.load_default(size=76)
            font_text_big = ImageFont.load_default(size=68)
            font_text_small = ImageFont.load_default(size=64)
            font_text_bot = ImageFont.load_default(size=58)
            font_time = ImageFont.load_default(size=56)
            font_icon = ImageFont.load_default(size=60)
            font_icon_large = ImageFont.load_default(size=175)
            font_name = ImageFont.load_default(size=60)

        def draw_text_with_shadow(draw, position, text, font, fill, shadow_color=(0, 0, 0, 250), shadow_offset=(2, 2)):
            x, y = position
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_color)
            draw.text((x, y), text, font=font, fill=fill)

        vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        vietnam_now = datetime.now(vietnam_tz)
        hour = vietnam_now.hour
        formatted_time = vietnam_now.strftime("%H:%M")
        time_icon = "🌤️" if 6 <= hour < 18 else "🌙"
        time_text = f" {formatted_time}"
        time_x = box_x2 - 250
        time_y = box_y1 + 10
        
        box_rgb = box_color[:3]
        box_luminance = (0.299 * box_rgb[0] + 0.587 * box_rgb[1] + 0.114 * box_rgb[2]) / 255
        last_lines_color = (255, 255, 255, 220) if box_luminance < 0.5 else (0, 0, 0, 220)

        time_color = last_lines_color

        if time_x >= 0 and time_y >= 0 and time_x < size[0] and time_y < size[1]:
            try:
                icon_x = time_x - 75
                icon_color = random_contrast_color(box_color)
                draw_text_with_shadow(draw, (icon_x, time_y - 8), time_icon, font_icon, icon_color)
                draw.text((time_x, time_y), time_text, font=font_time, fill=time_color)
            except Exception as e:
                print(f"❌ Lỗi vẽ thời gian lên ảnh: {e}")
                draw_text_with_shadow(draw, (time_x - 75, time_y - 8), "⏰", font_icon, (255, 255, 255, 255))
                draw.text((time_x, time_y), " ??;??", font=font_time, fill=time_color)

        user_info = bot.fetchUserInfo(author_id) if author_id else None
        user_name = "Unknown"
        if user_info and hasattr(user_info, 'changed_profiles') and author_id in user_info.changed_profiles:
            user = user_info.changed_profiles[author_id]
            user_name = getattr(user, 'name', None) or getattr(user, 'displayName', None) or f"ID_{author_id}"

        greeting_name = "Chủ Nhân" if is_admin(bot, author_id) else user_name

        emoji_colors = {
            "🎵": random_contrast_color(box_color),
            "😁": random_contrast_color(box_color),
            "🖤": random_contrast_color(box_color),
            "💞": random_contrast_color(box_color),
            "🤖": random_contrast_color(box_color),
            "💻": random_contrast_color(box_color),
            "📅": random_contrast_color(box_color),
            "🎧": random_contrast_color(box_color),
            "🌙": random_contrast_color(box_color),
            "🌤️": (200, 150, 50, 255)
        }

        text_lines = [
            f"Hi, {greeting_name}",
            f"💞 Chào mừng đến với menu 🤖 BOT",
            f"{bot.prefix}bot on/off: 🚀 Bật/Tắt tính năng",
            "😁 Bot Sẵn Sàng Phục 🖤",
            f"🤖Bot: {bot.me_name} 💻Version: {bot.version} 📅Update {bot.date_update}"
        ]

        color1 = random_contrast_color(box_color)
        color2 = random_contrast_color(box_color)
        while color1 == color2:
            color2 = random_contrast_color(box_color)
        text_colors = [
            color1,
            color2,
            last_lines_color,
            last_lines_color,
            last_lines_color
        ]

        text_fonts = [
            font_text_large,
            font_text_big,
            font_text_bot,
            font_text_bot,
            font_text_small
        ]

        line_spacing = 85
        start_y = box_y1 + 10

        avatar_url = user_info.changed_profiles[author_id].avatar if user_info and hasattr(user_info, 'changed_profiles') and author_id in user_info.changed_profiles else None
        avatar_path = download_avatar(avatar_url)
        if avatar_path and os.path.exists(avatar_path):
            avatar_size = 200
            try:
                avatar_img = Image.open(avatar_path).convert("RGBA").resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
                border_size = avatar_size + 10
                rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
                draw_border = ImageDraw.Draw(rainbow_border)
                steps = 360
                for i in range(steps):
                    h = i / steps
                    r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
                    draw_border.arc([(0, 0), (border_size-1, border_size-1)], start=i, end=i + (360 / steps), fill=(int(r * 255), int(g * 255), int(b * 255), 255), width=5)
                avatar_y = (box_y1 + box_y2 - avatar_size) // 2
                overlay.paste(rainbow_border, (box_x1 + 40, avatar_y), rainbow_border)
                overlay.paste(avatar_img, (box_x1 + 45, avatar_y + 5), mask)
            except Exception as e:
                print(f"❌ Lỗi xử lý avatar: {e}")
                draw.text((box_x1 + 60, (box_y1 + box_y2) // 2 - 140), "🐳", font=font_icon, fill=(0, 139, 139, 255))
        else:
            draw.text((box_x1 + 60, (box_y1 + box_y2) // 2 - 140), "🐳", font=font_icon, fill=(0, 139, 139, 255))

        current_line_idx = 0
        for i, line in enumerate(text_lines):
            if not line:
                current_line_idx += 1
                continue

            parts = []
            current_part = ""
            for char in line:
                if ord(char) > 0xFFFF:
                    if current_part:
                        parts.append(current_part)
                        current_part = ""
                    parts.append(char)
                else:
                    current_part += char
            if current_part:
                parts.append(current_part)

            total_width = 0
            part_widths = []
            current_font = font_text_bot if i == 4 else text_fonts[i]
            for part in parts:
                font_to_use = font_icon if any(ord(c) > 0xFFFF for c in part) else current_font
                width = draw.textbbox((0, 0), part, font=font_to_use)[2]
                part_widths.append(width)
                total_width += width

            max_width = box_x2 - box_x1 - 300
            if total_width > max_width:
                font_size = int(current_font.getbbox("A")[3] * max_width / total_width * 0.9)
                if font_size < 60:
                    font_size = 60
                try:
                    current_font = ImageFont.truetype(font_arial_path, size=font_size) if os.path.exists(font_arial_path) else ImageFont.load_default(size=font_size)
                except Exception as e:
                    print(f"❌ Lỗi điều chỉnh font size: {e}")
                    current_font = ImageFont.load_default(size=font_size)
                total_width = 0
                part_widths = []
                for part in parts:
                    font_to_use = font_icon if any(ord(c) > 0xFFFF for c in part) else current_font
                    width = draw.textbbox((0, 0), part, font=font_to_use)[2]
                    part_widths.append(width)
                    total_width += width

            text_x = (box_x1 + box_x2 - total_width) // 2
            text_y = start_y + current_line_idx * line_spacing + (current_font.getbbox("A")[3] // 2)

            current_x = text_x
            for part, width in zip(parts, part_widths):
                if any(ord(c) > 0xFFFF for c in part):
                    emoji_color = emoji_colors.get(part, random_contrast_color(box_color))
                    draw_text_with_shadow(draw, (current_x, text_y), part, font_icon, emoji_color)
                    if part == "🤖" and i == 4:
                        draw_text_with_shadow(draw, (current_x, text_y - 5), part, font_icon, emoji_color)
                else:
                    if i < 2:
                        draw_text_with_shadow(draw, (current_x, text_y), part, current_font, text_colors[i])
                    else:
                        draw.text((current_x, text_y), part, font=current_font, fill=text_colors[i])
                current_x += width
            current_line_idx += 1

        right_icons = ["🤖"]
        right_icon = random.choice(right_icons)
        icon_right_x = box_x2 - 225
        icon_right_y = (box_y1 + box_y2 - 180) // 2
        draw_text_with_shadow(draw, (icon_right_x, icon_right_y), right_icon, font_icon_large, emoji_colors.get(right_icon, (80, 80, 80, 255)))

        final_image = Image.alpha_composite(bg_image, overlay)
        final_image = final_image.resize(final_size, Image.Resampling.LANCZOS)
        os.makedirs(os.path.dirname(OUTPUT_IMAGE_PATH), exist_ok=True)
        final_image.save(OUTPUT_IMAGE_PATH, "PNG", quality=95)
        print(f"✅ Ảnh menu đã được lưu: {OUTPUT_IMAGE_PATH}")
        return OUTPUT_IMAGE_PATH

    except Exception as e:
        print(f"❌ Lỗi xử lý ảnh menu: {e}")
        return None

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        return user_info.zaloName or user_info.displayName
    except Exception as e:
        return "Unknown User"

def handle_bot_command(bot, message_object, author_id, thread_id, thread_type, command):
    def send_bot_response():
        settings = read_settings(bot.uid)
        allowed_thread_ids = settings.get('allowed_thread_ids', [])
        admin_bot = settings.get("admin_bot", [])
        banned_users = settings.get("banned_users", [])
        chat_user = (thread_type == ThreadType.USER)

        if author_id in banned_users:
            return

        if not (author_id in admin_bot or thread_id in allowed_thread_ids or chat_user):
            return
        try:

            spam_enabled = settings.get('spam_enabled', {}).get(str(thread_id), True)
            anti_poll = settings.get('anti_poll', True)
            video_enabled = settings.get('video_enabled', True)
            card_enabled = settings.get('card_enabled', True)
            file_enabled = settings.get('file_enabled', True)
            image_enabled = settings.get('image_enabled', True)
            chat_enabled = settings.get('chat_enabled', True)
            voice_enabled = settings.get('voice_enabled', True)
            sticker_enabled = settings.get('sticker_enabled', True)
            gif_enabled = settings.get('gif_enabled', True)
            doodle_enabled = settings.get('doodle_enabled', True)
            allow_link = settings.get('allow_link', {}).get(str(thread_id), True)
            undo_enabled = settings.get('undo_enabled', {}).get(thread_id, True)
            sos_status = settings.get('sos_status', True)

            status_icon = lambda enabled: "✅" if enabled else "⭕️"

            f"{status_icon(spam_enabled)} Anti-Spam 💢\n"
            f"{status_icon(anti_poll)} Anti-Poll 👍\n"
            f"{status_icon(video_enabled)} Anti-Video ▶️\n"
            f"{status_icon(card_enabled)} Anti-Card 🛡️\n"
            f"{status_icon(file_enabled)}Anti-File 🗂️\n"
            f"{status_icon(image_enabled)} Anti-Photo 🏖\n"
            f"{status_icon(chat_enabled)} SafeMode 🩹\n"
            f"{status_icon(voice_enabled)} Anti-Voice 🔊\n"
            f"{status_icon(sticker_enabled)} Anti-Sticker 😊\n"
            f"{status_icon(gif_enabled)} Anti-Gif 🖼️\n"
            f"{status_icon(doodle_enabled)} Anti-Draw ✏️\n"
            f"{status_icon(sos_status)}SOS 🆘\n"
            f"{status_icon(allow_link)} Anti-Link 🔗\n"
            f"{status_icon(undo_enabled)} Anti-Undo 🔗\n"



            parts = command.split()
            response = ""
            if len(parts) == 1:
                response = (
                        f"{get_user_name_by_id(bot, author_id)}\n"
                        f"➜ {bot.prefix}bot info/policy: ♨️ Thông tin/Tác giả/Thời gian/Chính sách BOT\n"
                        f"➜ {bot.prefix}bot setup on/off: ⚙️ Bật/Tắt Nội quy BOT (OA)\n"
                        f"➜ {bot.prefix}bot anti on/off/setup: 🚦Bật/Tắt Anti (OA)\n"
                        f"➜ {bot.prefix}bot newlink/dislink: 🔗 Tạo/hủy link nhóm (OA)\n"
                        f"➜ {bot.prefix}bot fix: 🔧 Sữa lỗi treo lệnh(OA)\n"
                        f"➜ {bot.prefix}bot chat on/off: 🩹 Chế độ an toàn text (OA)\n"
                        f"➜ {bot.prefix}bot on/off: ⚙️ Bật/Tắt BOT (OA)\n"
                        f"➜ {bot.prefix}bot remote add/remove/list: 🌐 Cấp/thu hồi/xem quyền kích hoạt từ xa\n"
                        f"➜ {bot.prefix}bot admin add/remove/list: 👑 Thêm/xóa Admin 🤖BOT\n"
                        f"➜ {bot.prefix}bot approved add/remove/list: 👑 Cấp/thu hồi/xem danh sách được duyệt\n"
                        f"➜ {bot.prefix}bot skip add/remove/list: 👑 Thêm/xóa ưu tiên 🤖BOT (OA)\n"
                        f"➜ {bot.prefix}bot leader add/remove/list: 👑 Thêm/xóa Trưởng/Phó (OA)\n"
                        f"➜ {bot.prefix}bot autostk on/off: ✉️ Gửi tin nhắn(OA)\n"
                        f"➜ {bot.prefix}bot noiquy: 💢 Nội quy box\n"
                        f"➜ {bot.prefix}bot ban/vv/unban list: 😷 Khóa user\n"
                        f"➜ {bot.prefix}bot kick: 💪 Kick user (OA)\n"
                        f"➜ {bot.prefix}bot sos: 🆘 Khóa box (OA)\n"
                        f"➜ {bot.prefix}bot block/unblock/list: 💪 Chặn người dùng (OA)\n"
                        f"➜ {bot.prefix}bot link on/off: 🔗 Cấm link (OA)\n"
                        f"➜ {bot.prefix}bot file on/off: 🗂️ Cấm file (OA)\n"
                        f"➜ {bot.prefix}bot video on/off: ▶️ Cấm video (OA)\n"
                        f"➜ {bot.prefix}bot sticker on/off: 😊 Cấm sticker (OA)\n"
                        f"➜ {bot.prefix}bot gif on/off: 🖼️ Cấm Gif (OA)\n"
                        f"➜ {bot.prefix}bot voice on/off: 🔊 Cấm voice (OA)\n"
                        f"➜ {bot.prefix}bot photo on/off: 🏖 Cấm ảnh (OA)\n"
                        f"➜ {bot.prefix}bot draw on/off: ✏️ Cấm vẽ hình (OA)\n"
                        f"➜ {bot.prefix}bot anti poll on/off: 👍 Cấm bình chọn (OA)\n"
                        f"➜ {bot.prefix}bot rule word [n] [m]: 📖 Cấm n lần vi phạm, phạt m phút (OA)\n"
                        f"➜ {bot.prefix}bot word add/remove/list [từ cấm]: ✍️ Thêm/xóa từ cấm (OA)\n"
                        f" ➜ {bot.prefix}bot welcome on/off: 🎊 Welcome (OA)\n"
                        f"➜ {bot.prefix}bot card on/off: 🛡️ Cấm Card (OA)\n"
                        f"➜ {bot.prefix}bot cam add/remove/list>: 🛡️ Thêm Vào Danh Sách Cấm (OA)\n"
                        f"🤖 BOT {get_user_name_by_id(bot, bot.uid)} luôn sẵn sàng phục vụ bạn! 🌸\n"
                    )
            else:
                action = parts[1].lower()
                
                if action == 'on':
                    target_id = parts[2].strip() if len(parts) > 2 else thread_id
                    is_remote = (target_id != thread_id)
                    is_bot_adm = is_admin(bot, author_id)
                    is_grp_adm = is_group_admin_or_creator(bot, author_id, target_id)
                    
                    if not (is_bot_adm or is_grp_adm):
                        response = "➜ Lệnh này chỉ khả thi với chủ nhân hoặc admin nhóm 🤧"
                    elif is_remote and thread_type != ThreadType.GROUP:
                        if is_grp_adm and not is_bot_adm:
                            settings = read_settings(bot.uid)
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
                    is_bot_adm = is_admin(bot, author_id)
                    is_grp_adm = is_group_admin_or_creator(bot, author_id, target_id)
                    
                    if not (is_bot_adm or is_grp_adm):
                        response = "➜ Lệnh này chỉ khả thi với chủ nhân hoặc admin nhóm 🤧"
                    elif is_remote and thread_type != ThreadType.GROUP:
                        if is_grp_adm and not is_bot_adm:
                            settings = read_settings(bot.uid)
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
                        response = f"➜ Vui lòng nhập [list/add/remove] sau lệnh: {bot.prefix}bot remote 🤧\n➜ Ví dụ: {bot.prefix}bot remote list hoặc {bot.prefix}bot remote add @tag hoặc {bot.prefix}bot remote remove @tag ✅"
                    else:
                        settings = read_settings(bot.uid)
                        remote_allowed_users = settings.get("remote_allowed_users", [])
                        sub_action = parts[2].lower()
                        if sub_action == 'add':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {bot.prefix}bot remote add 🤧\n➜ Ví dụ: {bot.prefix}bot remote add @tag ✅"
                            else:
                                if not is_admin(bot, author_id):
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
                                    write_settings(bot.uid, settings)
                        elif sub_action == 'remove':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {bot.prefix}bot remote remove 🤧\n➜ Ví dụ: {bot.prefix}bot remote remove @tag ✅"
                            else:
                                if not is_admin(bot, author_id):
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
                                    write_settings(bot.uid, settings)
                        elif sub_action == 'list':
                            if remote_allowed_users:
                                response = "➜ 🌐 Danh sách được cấp quyền kích hoạt từ xa 👑\n"
                                for idx, uid in enumerate(remote_allowed_users, start=1):
                                    response += f"      ➜ {idx}. 👑 {get_user_name_by_id(bot, uid)}\n"
                            else:
                                response = "➜ Chưa có ai được cấp quyền kích hoạt từ xa 🤧"
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot remote {sub_action} không được hỗ trợ 🤧"

                elif action == 'fix':
                    response = reload_modules(bot, message_object, thread_id, thread_type)

                elif action == 'autostk':
                    if not is_admin(bot, author_id):
                        response = "❌ Bạn không phải admin bot!"
                    elif len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: bot autostk 🤧\n➜ Ví dụ: {bot.prefix}bot autostk on hoặc {bot.prefix}bot autostk off ✅"
                    else:
                        stk_action = parts[2].lower()
                        if stk_action in ['on', 'off']:
                            settings.setdefault('auto_sticker', {})
                            settings['auto_sticker'][thread_id] = (stk_action == 'on')
                            status = "bật 🟢" if stk_action == 'on' else "tắt 🔴"
                            response = f"➜ Tính năng tự động gửi sticker đã được {status}"
                            write_settings(bot.uid, settings)
                        else:
                            response = f"➜ Lệnh bot autostk {stk_action} không hợp lệ 🤧"

                elif action == 'policy':
                    if not is_admin(bot, author_id):
                        response = "❌Bạn không phải admin bot!"
                    elif thread_type != ThreadType.GROUP:
                        response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                    elif len(parts) < 3:
                        # Show current policy config
                        settings = read_settings(bot.uid)
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
                            f"   ➜ {bot.prefix}bot policy [loại] [on/off]\n"
                            f"   VD: {bot.prefix}bot policy link on\n"
                            f"3️⃣ Cài đặt chi tiết hình phạt:\n"
                            f"   ➜ {bot.prefix}bot policy [loại] [lần] [phút] [hành_động]\n"
                            f"   Hành động: mute (Khóa mõm) / kick (Trục xuất) / warn (Cảnh báo)\n"
                            f"   VD: {bot.prefix}bot policy word 3 60 mute\n"
                            f"   VD: {bot.prefix}bot policy link 2 30 kick"
                        )
                    else:
                        policy_type = parts[2].lower()
                        valid_policies = ["word", "link", "sticker", "image", "flood"]
                        
                        if policy_type not in valid_policies:
                            response = f"➜ Loại policy không hợp lệ 🤧\n➜ Chọn: {', '.join(valid_policies)}"
                        elif len(parts) == 4 and parts[3].lower() in ('on', 'off'):
                            # Toggle on/off
                            settings = read_settings(bot.uid)
                            settings.setdefault("policies", {})
                            settings["policies"].setdefault(thread_id, {})
                            settings["policies"][thread_id].setdefault(policy_type, {"threshold": 3, "duration": 30, "action": "mute"})
                            
                            if parts[3].lower() == 'on':
                                settings["policies"][thread_id][policy_type]["enabled"] = True
                                response = f"✅ Policy [{policy_type}] đã BẬT cho nhóm này"
                            else:
                                settings["policies"][thread_id][policy_type]["enabled"] = False
                                response = f"⭕ Policy [{policy_type}] đã TẮT cho nhóm này"
                            
                            write_settings(bot.uid, settings)
                        elif len(parts) >= 5:
                            try:
                                threshold = int(parts[3])
                                duration = int(parts[4])
                                action_type = parts[5].lower() if len(parts) > 5 else "mute"
                                
                                if action_type not in ["mute", "kick", "warn"]:
                                    response = f"➜ Hành động không hợp lệ 🤧 Chọn: mute/kick/warn"
                                else:
                                    settings = read_settings(bot.uid)
                                    settings.setdefault("policies", {})
                                    settings["policies"].setdefault(thread_id, {})
                                    settings["policies"][thread_id][policy_type] = {
                                        "enabled": True,
                                        "threshold": threshold,
                                        "duration": duration,
                                        "action": action_type
                                    }
                                    write_settings(bot.uid, settings)
                                    
                                    action_text = {"mute": "😷 Khóa mõm", "kick": "💪 Kick", "warn": "⚠️ Cảnh báo"}.get(action_type, "😷 Khóa mõm")
                                    response = f"✅ Policy [{policy_type}] đã cập nhật:\n   Vi phạm {threshold} lần → {action_text} {duration} phút"
                            except ValueError:
                                response = "➜ Số lần và phút phạt phải là số nguyên 🤧"
                        else:
                            response = f"➜ Cú pháp: {bot.prefix}bot policy {policy_type} [on/off] hoặc {bot.prefix}bot policy {policy_type} [lần] [phút] [mute/kick/warn]"

                elif action == 'removelink':
                    if not is_admin(bot, author_id):
                        response = "❌Bạn không phải admin bot!"
                    else:
                        response = remove_link(bot, thread_id)
                elif action == 'newlink':
                    if not is_admin(bot, author_id):
                        response = "❌Bạn không phải admin bot!"
                    else:
                        response = newlink(bot, thread_id)
                elif action == 'skip':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [add/remove/list] sau lệnh: {bot.prefix}bot skip 🤧\n➜ Ví dụ: {bot.prefix}bot skip add @TXA ✅"
                    else:
                        sub_action = parts[2].lower()
                        if sub_action == 'add':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {bot.prefix}bot skip add ??\n➜ Ví dụ: {bot.prefix}bot skip add @TXA ✅"
                            else:
                                mentioned_uids = extract_uids_from_mentions(message_object)
                                settings = read_settings(bot.uid)
                                
                                if not is_admin(bot, author_id):
                                    response = "❌Bạn không phải admin bot!"
                                else:
                                    response = add_skip(bot, author_id, mentioned_uids)
                        elif sub_action == 'remove':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {bot.prefix}bot skip remove 🤧\n➜ Ví dụ: {bot.prefix}bot skip remove @TXA ✅"
                            else:
                                mentioned_uids = extract_uids_from_mentions(message_object)
                                settings = read_settings(bot.uid)
                                
                                if not is_admin(bot, author_id):
                                    response = "❌Bạn không phải admin bot!"
                                else:
                                    response = remove_skip(bot, author_id, mentioned_uids)
                        elif sub_action == 'list':
                            settings = read_settings(bot.uid)
                            skip_list = settings.get("skip_bot", [])
                            if skip_list:
                                response = "🚦 Danh sách người dùng được ưu tiên: \n"
                                for uid in skip_list:
                                    response += f"👑 {get_user_name_by_id(bot, uid)} - {uid}\n"
                            else:
                                response = "🚦 Chưa có người dùng nào trong danh sách ưu tiên 🤖"
                elif action == 'leader':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [add/remove] sau lệnh: {bot.prefix}bot leader 🤧\n➜ Ví dụ: {bot.prefix}bot leader add @Hero ✅"
                    else:
                        sub_action = parts[2].lower()
                        
                      
                        if sub_action == 'add':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {bot.prefix}bot leader add 🤧\n➜ Ví dụ: {bot.prefix}bot leader add @Hero ✅"
                            else:
                                mentioned_uids = extract_uids_from_mentions(message_object)
                                
                                if not is_admin(bot, author_id):
                                    response = "❌Bạn không phải admin bot!"
                                else:
                                    response = promote_to_admin(bot, mentioned_uids, thread_id)
                        elif sub_action == 'remove':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {bot.prefix}bot admin remove 🤧\n➜ Ví dụ: {bot.prefix}bot admin remove @Hero ✅"
                            else:
                                mentioned_uids = extract_uids_from_mentions(message_object)
                                
                                if not is_admin(bot, author_id):
                                    response = "❌Bạn không phải admin bot!"
                                else:
                                    response = remove_adminn(bot, mentioned_uids, thread_id)
                        
                        elif sub_action == 'list':
                            
                            response = get_group_admins(bot, thread_id)

                        
                        else:
                            response = "➜ Lệnh không hợp lệ. Vui lòng chọn từ [add/remove/list]."
        
                elif action == 'anti':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [poll on/off] sau lệnh: {bot.prefix}bot anti 🤧\n➜ Ví dụ: {bot.prefix}bot anti poll on ✅"
                    else:
                        sub_action = parts[2].lower()
                        if sub_action == 'poll':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot anti poll 🤧\n➜ Ví dụ: {bot.prefix}bot anti poll on ✅"
                            else:
                                sub_sub_action = parts[3].lower()
                                if not is_admin(bot, author_id):
                                    response = "❌Bạn không phải admin bot!"
                                elif sub_sub_action == 'off':  
                                    settings = read_settings(bot.uid)
                                    settings["anti_poll"] = True
                                    write_settings(bot.uid, settings)
                                    response = f"{status_icon(anti_poll)} Anti-Poll 👍\n"
                                elif sub_sub_action == 'on':  
                                    settings = read_settings(bot.uid)
                                    settings["anti_poll"] = False
                                    write_settings(bot.uid, settings)
                                    response = f"{status_icon(anti_poll)} Anti-Poll 👍\n"
                                else:
                                    response = "➜ Lệnh không hợp lệ. Vui lòng chọn 'on' hoặc 'off' sau lệnh anti poll 🤧"
                                
                elif action == 'chat':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot chat 🤧\n➜ Ví dụ: {bot.prefix}bot chat on hoặc {bot.prefix}bot chat off ✅"
                    else:
                        chat_action = parts[2].lower()
                        settings = read_settings(bot.uid)

                        if chat_action == 'off':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['chat_enabled'] = True  
                                response = f"{status_icon(chat_enabled)} SafeMode 🩹\n"
                        elif chat_action == 'on':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['chat_enabled'] = False  
                                response = f"{status_icon(chat_enabled)} SafeMode 🩹\n"
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot chat {chat_action} không hợp lệ 🤧"
                        
                        write_settings(bot.uid, settings)  

                elif action == 'sticker':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot sticker 🤧\n➜ Ví dụ: {bot.prefix}bot sticker on hoặc {bot.prefix}bot sticker off ✅"
                    else:
                        sticker_action = parts[2].lower()
                        settings = read_settings(bot.uid)

                        if sticker_action == 'off':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['sticker_enabled'] = True  
                                response = f"{status_icon(sticker_enabled)} Anti-Sticker 😊\n"
                                
                        elif sticker_action == 'on':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['sticker_enabled'] = False  
                                response = f"{status_icon(sticker_enabled)} Anti-Sticker 😊\n"
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot sticker {sticker_action} không hợp lệ 🤧"
                        
                        write_settings(bot.uid, settings)

                elif action == 'draw':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot draw 🤧\n➜ Ví dụ: {bot.prefix}bot draw on hoặc {bot.prefix}bot draw off ✅"
                    else:
                        draw_action = parts[2].lower()
                        settings = read_settings(bot.uid)

                        if draw_action == 'off':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['doodle_enabled'] = True  
                                response = f"{status_icon(doodle_enabled)} Anti-Draw ✏️\n"
                        elif draw_action == 'on':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['doodle_enabled'] = False  
                                response = f"{status_icon(doodle_enabled)} Anti-Draw ✏️\n"
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot draw {draw_action} không hợp lệ 🤧"
                        
                        write_settings(bot.uid, settings)

                elif action == 'gif':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot gif 🤧\n➜ Ví dụ: {bot.prefix}bot gif on hoặc {bot.prefix}bot gif off ✅"
                    else:
                        gif_action = parts[2].lower()
                        settings = read_settings(bot.uid)

                        if gif_action == 'off':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['gif_enabled'] = True  
                                response = f"{status_icon(gif_enabled)} Anti-Gif 🖼️\n"
                        elif gif_action == 'on':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['gif_enabled'] = False  
                                response = f"{status_icon(gif_enabled)} Anti-Gif 🖼️\n"
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot gif {gif_action} không hợp lệ 🤧"
                        
                        write_settings(bot.uid, settings)

                elif action == 'video':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot video 🤧\n➜ Ví dụ: {bot.prefix}bot video on hoặc {bot.prefix}bot video off ✅"
                    else:
                        video_action = parts[2].lower()
                        settings = read_settings(bot.uid)

                        if video_action == 'off':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['video_enabled'] = True  
                                response = f"{status_icon(video_enabled)} Anti-Video ▶️\n"
                        elif video_action == 'on':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['video_enabled'] = False  
                                response = f"{status_icon(video_enabled)} Anti-Video ▶️\n"
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot video {video_action} không hợp lệ 🤧"
                        
                        write_settings(bot.uid, settings)

                elif action == 'photo':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot image 🤧\n➜ Ví dụ: {bot.prefix}bot image on hoặc {bot.prefix}bot image off ✅"
                    else:
                        image_action = parts[2].lower()
                        settings = read_settings(bot.uid)

                        if image_action == 'off':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['image_enabled'] = True  
                                response = f"{status_icon(image_enabled)} Anti-Photo 🏖\n"
                        elif image_action == 'on':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['image_enabled'] = False  
                                response = f"{status_icon(image_enabled)} Anti-Photo 🏖\n"
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot video {image_action} không hợp lệ 🤧"
                        
                        write_settings(bot.uid, settings)

                elif action == 'voice':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot voice 🤧\n➜ Ví dụ: {bot.prefix}bot voice on hoặc {bot.prefix}bot voice off ✅"
                    else:
                        voice_action = parts[2].lower()
                        settings = read_settings(bot.uid)

                        if voice_action == 'off':
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['voice_enabled'] = True  
                                response = f"{status_icon(voice_enabled)} Anti-Voice 🔊\n"
                        elif voice_action == 'on':
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['voice_enabled'] = False  
                                response = f"{status_icon(voice_enabled)} Anti-Voice 🔊\n"
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot video {voice_action} không hợp lệ 🤧"
                        
                        write_settings(bot.uid, settings)

                elif action == 'file':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot file 🤧\n➜ Ví dụ: {bot.prefix}bot file on hoặc {bot.prefix}bot file off ✅"
                    else:
                        file_action = parts[2].lower()
                        settings = read_settings(bot.uid)

                        if file_action == 'off':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['file_enabled'] = True  
                                response = f"{status_icon(file_enabled)} Anti-File 🗂️\n"
                                
                        elif file_action == 'on':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['file_enabled'] = False  
                                response = f"{status_icon(file_enabled)} Anti-File 🗂️\n"
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot video {file_action} không hợp lệ 🤧"
                        
                        write_settings(bot.uid, settings)

                elif action == 'card':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot card 🤧\n➜ Ví dụ: {bot.prefix}bot card on hoặc {bot.prefix}bot card off ✅"
                    else:
                        card_action = parts[2].lower()
                        settings = read_settings(bot.uid)

                        if card_action == 'on':
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['card_enabled'] = False  
                                response = f"{status_icon(card_enabled)} Anti-Card 🛡️\n"
                        elif card_action == 'off':  
                            if not is_admin(bot, author_id):  
                                response = "❌Bạn không phải admin bot!"
                            else:
                                settings['card_enabled'] = True  
                                response = f"{status_icon(card_enabled)} Anti-Card 🛡️\n"
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot card {card_action} không hợp lệ 🤧"
                        
                        write_settings(bot.uid, settings)

                elif action == 'welcome':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot welcome 🤧\n➜ Ví dụ: {bot.prefix}bot welcome on hoặc {bot.prefix}bot welcome off ✅"
                    else:
                        settings = read_settings(bot.uid)
                        setup_action = parts[2].lower()
                        if setup_action == 'on':
                            if not is_admin(bot, author_id):
                                response = "❌Bạn không phải admin bot!"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                response = handle_welcome_on(bot, thread_id)
                        elif setup_action == 'off':
                            if not is_admin(bot, author_id):
                                response = "❌Bạn không phải admin bot!"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                response = handle_welcome_off(bot, thread_id)
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot welcome {setup_action} không được hỗ trợ 🤧"
                
                elif action in ('spam', 'anti'):
                    if not is_admin(bot, author_id):
                        response = "❌Bạn không phải admin bot!"
                    elif len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot {action} 🤧\n➜ Ví dụ: {bot.prefix}bot {action} on hoặc {bot.prefix}bot {action} off ✅"
                    else:
                        spam_action = parts[2].lower()
                        settings = read_settings(bot.uid)

                        if 'spam_enabled' not in settings:
                            settings['spam_enabled'] = {}

                        if spam_action == 'on':
                            settings['spam_enabled'][thread_id] = True  
                            response = f"{status_icon(spam_enabled)} Anti-Spam 💢\n"
                        elif spam_action == 'off':
                            settings['spam_enabled'][thread_id] = False  
                            response = f"{status_icon(spam_enabled)} Anti-Spam 💢\n"
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot {action} {spam_action} không hợp lệ 🤧"
                        
                        write_settings(bot.uid, settings)
                        
                elif action == 'undo':
                    if not is_admin(bot, author_id):
                        response = "❌Bạn không phải admin bot!"
                    elif len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot undo 📦\n➜ Ví dụ: {bot.prefix}bot undo on hoặc {bot.prefix}bot undo off ✅"
                    else:
                        undo_action = parts[2].lower()
                        settings = read_settings(bot.uid)

                        if 'undo_enabled' not in settings:
                           settings['undo_enabled'] = {}

                        if undo_action == 'on':
                           settings['undo_enabled'][thread_id] = True
                           response = f"{undo_enabled} Anti-Undo 💢\n"
                        elif undo_action == 'off':
                           settings['undo_enabled'][thread_id] = False
                           response = f"{undo_enabled} Anti-Undo💢\n"
                        else:
                            response = f"⚠️ Lệnh {bot.prefix}bot undo {undo_action} không hợp lệ 😵"

                        write_settings(bot.uid, settings)
                elif action == 'info':
                    response = (
    "╭────────────────────────────╮\n"
    f"│ 🤖 Bot phiên bản: {bot.version}\n"
    f"│ 📅 Cập nhật lần cuối: {bot.date_update}\n"
    f"│ 👨‍💻 Nhà phát triển: {bot.me_name}\n"
    f"│ 📖 Hướng dẫn: Dùng lệnh [{bot.prefix}bot/help]\n"
    "│ ⏳ Thời gian phản hồi: 1 giây\n"
    "│ ⚡ Tính năng nổi bật:\n"
    "│  ├➜ 🛡️ Anti-spam,anti-radi, chặn link, từ cấm\n"
    "│  ├➜ 🤬 Kiểm soát nội dung chửi thề\n"
    "│  ├➜ 🚫 Tự động duyệt & chặn spammer\n"
    "│  ├➜ 🔊 Quản lý giọng nói & sticker\n"
    "│  ├➜ 🖼️ Hỗ trợ hình ảnh, GIF, video\n"
    "│  ├➜ 🗳️ Kiểm soát cuộc khảo sát\n"
    "│  ├➜ 🔗 Bảo vệ nhóm khỏi link độc hại\n"
    "│  └➜ 🔍 Kiểm tra & phân tích tin nhắn\n"
    "╰────────────────────────────╯"
)

                elif action == 'approved':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [list/add/remove] sau lệnh: {bot.prefix}bot approved 🤧\n➜ Ví dụ: {bot.prefix}bot approved list hoặc {bot.prefix}bot approved add @username hoặc {bot.prefix}bot approved remove @username ✅"
                    else:
                        settings = read_settings(bot.uid)
                        sub_action = parts[2].lower()
                        if sub_action == 'add':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {bot.prefix}bot approved add 🤧\n➜ Ví dụ: {bot.prefix}bot approved add @username ✅"
                            else:
                                mentioned_uids = extract_uids_from_mentions(message_object)
                                response = add_approved(bot, author_id, mentioned_uids, settings)
                        elif sub_action == 'remove':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {bot.prefix}bot approved remove 🤧\n➜ Ví dụ: {bot.prefix}bot approved remove @username ✅"
                            else:
                                mentioned_uids = extract_uids_from_mentions(message_object)
                                response = remove_approved(bot, author_id, mentioned_uids, settings)
                        elif sub_action == 'list':
                            response = list_approved(bot, author_id, settings)
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot approved {sub_action} không được hỗ trợ 🤧"

                elif action == 'clean':
                    if not is_admin(bot, author_id):
                        response = "❌Bạn không phải admin bot!"
                    else:
                        deleted_dirs, deleted_files = clean_pycache()
                        response = f"🧹 Đã dọn dẹp hệ thống thành công!\n➜ Xóa {deleted_dirs} thư mục __pycache__\n➜ Xóa {deleted_files} tệp .pyc/.pyo"

                elif action == 'admin':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [list/add/remove] sau lệnh: {bot.prefix}bot admin 🤧\n➜ Ví dụ: {bot.prefix}bot admin list hoặc {bot.prefix}bot admin add @TXA hoặc {bot.prefix}bot admin remove @TXA ✅"
                    else:
                        settings = read_settings(bot.uid)
                        admin_bot = settings.get("admin_bot", [])  
                        sub_action = parts[2].lower()
                        if sub_action == 'add':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {bot.prefix}bot admin add 🤧\n➜ Ví dụ: {bot.prefix}bot admin add @TXA ✅"
                            else:
                                if not admin_cao(bot, author_id):
                                    response = "❌Bạn không phải admin bot!"
                                else:
                                    mentioned_uids = extract_uids_from_mentions(message_object)
                                    response = add_admin(bot, author_id, mentioned_uids)
                        elif sub_action == 'remove':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {bot.prefix}bot admin remove 🤧\n➜ Ví dụ: {bot.prefix}bot admin remove @TXA ✅"
                            else:
                                if not admin_cao(bot, author_id):
                                    response = "❌Bạn không phải admin bot!"
                                else:
                                    mentioned_uids = extract_uids_from_mentions(message_object)
                                    response = remove_admin(bot, author_id, mentioned_uids)
                        elif sub_action == 'list':
                            if admin_bot:
                                response = f"🚦🧑‍💻 Danh sách Admin 🤖BOT {get_user_name_by_id(bot, bot.uid)}\n"
                                for idx, uid in enumerate(admin_bot, start=1):
                                    response += f"➜   {idx}. {get_user_name_by_id(bot, uid)} - {uid}\n"
                            else:
                                response = "➜ Không có Admin BOT nào trong danh sách 🤧"
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot admin {sub_action} không được hỗ trợ 🤧"


                elif action == 'setup':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot setup 🤧\n➜ Ví dụ: {bot.prefix}bot setup on hoặc {bot.prefix}bot setup off ✅"
                    else:
                        setup_action = parts[2].lower()
                        if setup_action == 'on':
                            if not is_admin(bot, author_id):
                                response = "❌Bạn không phải admin bot!"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                response = setup_bot_on(bot, thread_id)
                        elif setup_action == 'off':
                            if not is_admin(bot, author_id):
                                response = "❌Bạn không phải admin bot!"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                response = setup_bot_off(bot,thread_id)
                        else:
                            response = f"➜ Lệnh {bot.prefix}bot setup {setup_action} không được hỗ trợ 🤧"
                elif action == 'link':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [on/off] sau lệnh: {bot.prefix}bot link 🤧\n➜ Ví dụ: {bot.prefix}bot link on hoặc {bot.prefix}bot link off ✅"
                    else:
                        link_action = parts[2].lower()
                        if not is_admin(bot, author_id):
                            response = "❌Bạn không phải admin bot!"
                        elif thread_type != ThreadType.GROUP:
                            response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                        else:
                            settings = read_settings(bot.uid)

                            if 'allow_link' not in settings:
                                settings['allow_link'] = {}

                            
                            if link_action == 'on':
                                settings['allow_link'][thread_id] = True
                                response = f"{status_icon(allow_link)} Anti-Link 🔗\n"
                            elif link_action == 'off':
                                settings['allow_link'][thread_id] = False
                                response = f"{status_icon(allow_link)} Anti-Link 🔗\n"
                            else:
                                response = f"➜ Lệnh {bot.prefix}bot link {link_action} không được hỗ trợ 🤧"
                        write_settings(bot.uid, settings)
                elif action == 'word':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [add/remove/list] sau lệnh: {bot.prefix}bot word 🤧\n➜ Ví dụ: {bot.prefix}bot word list hoặc {bot.prefix}bot word add [từ khóa] ✅"
                    else:
                        sub_action = parts[2].lower()
                        if sub_action == 'list':
                            settings = read_settings(bot.uid)
                            forbidden_words = settings.get('forbidden_words', [])
                            if forbidden_words:
                                response = "➜ 🚫 Danh sách từ cấm hiện tại:\n"
                                for idx, w in enumerate(forbidden_words, start=1):
                                    response += f"      ➜ {idx}. {w}\n"
                            else:
                                response = "➜ Không có từ cấm nào trong danh sách 🤧"
                        elif len(parts) < 4:
                            response = f"➜ Vui lòng nhập [từ khóa] sau lệnh: {bot.prefix}bot word {sub_action} 🤧\n➜ Ví dụ: {bot.prefix}bot word {sub_action} [từ cấm] ✅"
                        else:
                            if not is_admin(bot, author_id):
                                response = "❌Bạn không phải admin bot!"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                word = ' '.join(parts[3:]) 
                                if sub_action == 'add':
                                    response = add_forbidden_word(bot, author_id, word)
                                elif sub_action == 'remove':
                                    response = remove_forbidden_word(bot, author_id, word)
                                else:
                                    response = f"➜ Lệnh [{bot.prefix}bot word {sub_action}] không được hỗ trợ 🤧\n➜ Ví dụ: {bot.prefix}bot word add [từ khóa] hoặc {bot.prefix}bot word remove [từ khóa] ✅"
                elif action == 'noiquy':
                    settings = read_settings(bot.uid)
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
                        response = f"➜ Vui lòng nhập 'list' hoặc 'ban @tag' sau lệnh: {bot.prefix}bot 🤧\n➜ Ví dụ: {bot.prefix}bot ban list hoặc {bot.prefix}bot ban @user ✅"
                    else:
                        sub_action = parts[2].lower()

                        if sub_action == 'list':
                            result = print_muted_users_in_group(bot, thread_id)
                            if result['mentions']:
                                bot.replyMessage(Message(text=result['text'], mention=MultiMention(result['mentions'])), message_object, thread_id, thread_type, ttl=9000)
                            else:
                                bot.replyMessage(Message(text=result['text']), message_object, thread_id, thread_type, ttl=9000)
                            return
                        elif sub_action == 'vv':
                            if not is_admin(bot, author_id):
                                response = "➜ Lệnh này chỉ khả thi với quản trị viên 🤧"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            elif not check_admin_group(bot, thread_id):
                                response = "➜ 🤖BOT không có quyền quản trị nhóm để thực hiện lệnh này 🤧"
                            else:
                                uids = extract_uids_from_mentions(message_object)
                                if not uids:
                                    response = f"➜ Vui lòng tag người cần ban sau lệnh: {bot.prefix}bot ban vv @username 🤧"
                                else:
                                    response = ban_users_permanently(bot, uids, thread_id)
                        else:
                            if not is_admin(bot, author_id):
                                response = "➜ Lệnh này chỉ khả thi với quản trị viên 🤧"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            elif not check_admin_group(bot, thread_id):
                                response = "➜ Lệnh này không khả thi do 🤖BOT không có quyền quản trị nhóm 🤧"
                            else:
                                uids = extract_uids_from_mentions(message_object)
                                response = add_users_to_ban_list(bot, uids, thread_id, "Quản trị viên cấm")


                elif action == 'unban':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập @tag tên sau lệnh: {bot.prefix}bot unban 🤧\n➜ Ví dụ: {bot.prefix}bot unban @TXA ✅"
                    else:
                        if not is_admin(bot, author_id):
                            response = "❌Bạn không phải admin bot!"
                        elif thread_type != ThreadType.GROUP:
                            response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                        else:
                            
                            uids = extract_uids_from_mentions(message_object)
                            response = remove_users_from_ban_list(bot, uids, thread_id)
                elif action == 'block':
                      
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập @tag tên sau lệnh: {bot.prefix}bot block 🤧\n➜ Ví dụ: {bot.prefix}bot block @TXA ✅"
                    else:
                        s_action = parts[2]  
                      
                        if s_action == 'list':
                            result = print_blocked_users_in_group(bot, thread_id)
                            if result['mentions']:
                                bot.replyMessage(Message(text=result['text'], mention=MultiMention(result['mentions'])), message_object, thread_id, thread_type, ttl=9000)
                            else:
                                bot.replyMessage(Message(text=result['text']), message_object, thread_id, thread_type, ttl=9000)
                            return
                        else:
                         
                            if not is_admin(bot, author_id):
                                response = "❌Bạn không phải admin bot!"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            elif check_admin_group(bot,thread_id)==False:
                                response = "➜ Lệnh này không khả thi do 🤖BOT không có quyền cầm 🔑 key nhóm 🤧"
                            else:
                              
                                uids = extract_uids_from_mentions(message_object)
                                response = block_users_from_group(bot, uids, thread_id)
                elif action == 'sos':
                    if not is_admin(bot, author_id):
                        response = "❌Bạn không phải admin bot!"
                    else:
                        settings = read_settings(bot.uid)
                        sos_status = settings.get("sos_status", False)

                        if sos_status:
                            bot.changeGroupSetting(groupId=thread_id, lockSendMsg=0)
                            settings["sos_status"] = False
                            response = f"{status_icon(sos_status)}SOS 🆘\n"
                        else:
                            bot.changeGroupSetting(groupId=thread_id, lockSendMsg=1)
                            settings["sos_status"] = True
                            response = f"{status_icon(sos_status)}SOS 🆘\n"

                        write_settings(bot.uid, settings)
  
                elif action == 'unblock':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập UID sau lệnh: {bot.prefix}bot unblock 🤧\n➜ Ví dụ: {bot.prefix}bot unblock 8421834556970988033, 842183455697098804... ✅"
                    else:
                        if not is_admin(bot, author_id):
                            response = "❌Bạn không phải admin bot!"
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
                        response = f"➜ Vui lòng nhập @tag tên sau lệnh: {bot.prefix}bot kick 🤧\n➜ Ví dụ: {bot.prefix}bot kick @TXA ✅"
                    else:
                        if not is_admin(bot, author_id):
                            response = "❌Bạn không phải admin bot!"
                        elif thread_type != ThreadType.GROUP:
                            response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                        elif check_admin_group(bot,thread_id)==False:
                                response = "➜ Lệnh này không khả thi do 🤖BOT không có quyền cầm 🔑 key nhóm 🤧"
                        else:
                            uids = extract_uids_from_mentions(message_object)
                            response = kick_users_from_group(bot, uids, thread_id)
                
                elif action == 'rule':
                    if len(parts) < 5:
                        response = f"➜ Vui lòng nhập word [n lần] [m phút] sau lệnh: {bot.prefix}bot rule 🤧\n➜ Ví dụ: {bot.prefix}bot rule word 3 30 ✅"
                    else:
                        rule_type = parts[2].lower()
                        try:
                            threshold = int(parts[3])
                            duration = int(parts[4])
                        except ValueError:
                            response = "➜ Số lần và phút phạt phải là số nguyên 🤧"
                        else:
                            settings = read_settings(bot.uid)
                            if rule_type not in ["word", "spam"]:
                                response = f"➜ Lệnh {bot.prefix}bot rule {rule_type} không được hỗ trợ 🤧\n➜ Ví dụ: {bot.prefix}bot rule word 3 30✅"
                            else:
                                if not is_admin(bot, author_id):
                                    response = "❌Bạn không phải admin bot!"
                                elif thread_type != ThreadType.GROUP:
                                    response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                                else:
                                    settings.setdefault("rules", {})
                                    settings["rules"][rule_type] = {
                                        "threshold": threshold,
                                        "duration": duration
                                    }
                                    write_settings(bot.uid, settings)
                                    response = f"➜ 🔄 Đã cập nhật nội quy cho {rule_type}: Nếu vi phạm {threshold} lần sẽ bị phạt {duration} phút ✅"
                elif action == 'cam':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập [add/remove] sau lệnh: {bot.prefix}bot cam 🤧\n➜ Ví dụ: {bot.prefix}bot cam add @TXA ✅"
                    else:
                        sub_action = parts[2].lower()
                        if sub_action == 'add':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {bot.prefix}bot cam add 🤧\n➜ Ví dụ: {bot.prefix}bot cam add @TXA ✅"
                            if not admin_cao(bot, author_id):
                                response = "❌Bạn không phải admin bot!"
                            else:
                                mentioned_uids = extract_uids_from_mentions(message_object)
                                response = ban_user_from_commands(bot, author_id, mentioned_uids)
                        elif sub_action == 'remove':
                            if len(parts) < 4:
                                response = f"➜ Vui lòng @tag tên người dùng sau lệnh: {bot.prefix}bot cam remove 🤧\n➜ Ví dụ: {bot.prefix}bot cam remove @TXA ✅"
                            if not admin_cao(bot, author_id):
                                response = "❌Bạn không phải admin bot!"
                            else:
                                mentioned_uids = extract_uids_from_mentions(message_object)
                                response = unban_user_from_commands(bot, author_id, mentioned_uids)
                        elif sub_action == 'list':
                            response = list_banned_users(bot)

                else:
                    bot.sendReaction(message_object, "❌", thread_id, thread_type)
            
            if response:
                if len(parts) == 1:
                    os.makedirs(CACHE_PATH, exist_ok=True)
    
                    image_path = generate_menu_image(bot, author_id, thread_id, thread_type)
                    if not image_path:
                        bot.sendMessage("❌ Không thể tạo ảnh menu!", thread_id, thread_type)
                        return
                    reaction = [
                        "❌", "🤧", "🐞", "😊", "🔥", "👍", "💖", "🚀",
                        "😍", "😂", "😢", "😎", "🙌", "💪", "🌟", "🍀",
                        "🎉", "🦁", "🌈", "🍎", "⚡", "🔔", "🎸", "🍕",
                        "🏆", "📚", "🦋", "🌍", "⛄", "🎁", "💡", "🐾",
                        "😺", "🐶", "🐳", "🦄", "🌸", "🍉", "🍔", "🎄",
                        "🎃", "👻", "☃️", "🌴", "🏀", "⚽", "🎾", "🏈",
                        "🚗", "✈️", "🚢", "🌙", "☀️", "⭐", "⛅", "☔",
                        "⌛", "⏰", "💎", "💸", "📷", "🎥", "🎤", "🎧",
                        "🍫", "🍰", "🍩", "☕", "🍵", "🍷", "🍹", "🥐",
                        "🐘", "🦒", "🐍", "🦜", "🐢", "🦀", "🐙", "🦈",
                        "🍓", "🍋", "🍑", "🥥", "🥪", "🍝", "🍣",
                        "🎲", "🎯", "🎱", "🎮", "🎰", "🧩", "🧸", "🎡",
                        "🏰", "🗽", "🗼", "🏔️", "🏝️", "🏜️", "🌋", "⛲",
                        "📱", "💻", "🖥️", "🖨️", "⌨️", "🖱️", "📡", "🔋",
                        "🔍", "🔎", "🔑", "🔒", "🔓", "📩", "📬", "📮",
                        "💢", "💥", "💫", "💦", "💤", "🚬", "💣", "🔫",
                        "🩺", "💉", "🩹", "🧬", "🔬", "🔭", "🧪", "🧫",
                        "🧳", "🎒", "👓", "🕶️", "👔", "👗", "👠", "🧢",
                        "🦷", "🦴", "👀", "👅", "👄", "👶", "👩", "👨",
                        "🚶", "🏃", "💃", "🕺", "🧘", "🏄", "🏊", "🚴",
                        "🍄", "🌾", "🌻", "🌵", "🌿", "🍂", "🍁", "🌊",
                        "🛠️", "🔧", "🔨", "⚙️", "🪚", "🪓", "🧰", "⚖️",
                        "🧲", "🪞", "🪑", "🛋️", "🛏️", "🪟", "🚪", "🧹"
                    ]

                    num_reactions = random.randint(5, 15)
                    selected_reactions = random.sample(reaction, num_reactions)

                    for emoji in selected_reactions:
                        bot.sendReaction(message_object, emoji, thread_id, thread_type)
                    bot.sendLocalImage(
                        imagePath=image_path,
                        message=Message(text=response, mention=Mention(author_id, length=len(f"{get_user_name_by_id(bot, author_id)}"), offset=0)),
                        thread_id=thread_id,
                        thread_type=thread_type,
                        width=1920,
                        height=600,
                        ttl=60000
                    )
                    
                    try:
                        if os.path.exists(image_path):
                            os.remove(image_path)
                    except Exception as e:
                        print(f"❌ Lỗi khi xóa ảnh: {e}")
                else:
                    reaction = [
                        "❌", "🤧", "🐞", "😊", "🔥", "👍", "💖", "🚀",
                        "😍", "😂", "😢", "😎", "🙌", "💪", "🌟", "🍀",
                        "🎉", "🦁", "🌈", "🍎", "⚡", "🔔", "🎸", "🍕",
                        "🏆", "📚", "🦋", "🌍", "⛄", "🎁", "💡", "🐾",
                        "😺", "🐶", "🐳", "🦄", "🌸", "🍉", "🍔", "🎄",
                        "🎃", "👻", "☃️", "🌴", "🏀", "⚽", "🎾", "🏈",
                        "🚗", "✈️", "🚢", "🌙", "☀️", "⭐", "⛅", "☔",
                        "⌛", "⏰", "💎", "💸", "📷", "🎥", "🎤", "🎧",
                        "🍫", "🍰", "🍩", "☕", "🍵", "🍷", "🍹", "🥐",
                        "🐘", "🦒", "🐍", "🦜", "🐢", "🦀", "🐙", "🦈",
                        "🍓", "🍋", "🍑", "🥥", "🥪", "🍝", "🍣",
                        "🎲", "🎯", "🎱", "🎮", "🎰", "🧩", "🧸", "🎡",
                        "🏰", "🗽", "🗼", "🏔️", "🏝️", "🏜️", "🌋", "⛲",
                        "📱", "💻", "🖥️", "🖨️", "⌨️", "🖱️", "📡", "🔋",
                        "🔍", "🔎", "🔑", "🔒", "🔓", "📩", "📬", "📮",
                        "💢", "💥", "💫", "💦", "💤", "🚬", "💣", "🔫",
                        "🩺", "💉", "🩹", "🧬", "🔬", "🔭", "🧪", "🧫",
                        "🧳", "🎒", "👓", "🕶️", "👔", "👗", "👠", "🧢",
                        "🦷", "🦴", "👀", "👅", "👄", "👶", "👩", "👨",
                        "🚶", "🏃", "💃", "🕺", "🧘", "🏄", "🏊", "🚴",
                        "🍄", "🌾", "🌻", "🌵", "🌿", "🍂", "🍁", "🌊",
                        "🛠️", "🔧", "🔨", "⚙️", "🪚", "🪓", "🧰", "⚖️",
                        "🧲", "🪞", "🪑", "🛋️", "🛏️", "🪟", "🚪", "🧹"
                    ]

                    num_reactions = random.randint(5, 15)
                    selected_reactions = random.sample(reaction, num_reactions)

                    for emoji in selected_reactions:
                        bot.sendReaction(message_object, emoji, thread_id, thread_type)
                    bot.replyMessage(Message(text=response),message_object, thread_id=thread_id, thread_type=thread_type,ttl=9000)
        
        except Exception as e:
            print(f"Error: {e}")
            bot.replyMessage(Message(text="➜ 🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type)

    thread = Thread(target=send_bot_response)
    thread.start()
























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
            text_bbox = draw.textbbox((current_x, text_position[1]), char, font=selected_font)
            text_width = text_bbox[2] - text_bbox[0]
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
        settings = read_settings(bot.uid)
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
                'main_text': f'Chào mừng, {user_name}',
                'group_name_text': group_name,
                'credit_text': f"Được duyệt bởi {ow_name}" if ow_name else "Đã được duyệt vào nhóm",
                'msg': f"🎉 Chào mừng {user_name} đã được duyệt vào nhóm" + (f" bởi {ow_name}! 🚀" if ow_name else "! 🚀"),
                'mention': Mention(uid=uid, offset=12, length=len(user_name))
            },
            GroupEventType.LEAVE: {
                'main_text': f'Tạm biệt, {user_name}',
                'group_name_text': group_name,
                'credit_text': "Đã rời khỏi nhóm",
                'msg': f"👋 Hẹn gặp lại {user_name} nhé! Chúc bạn luôn vui vẻ và gặp nhiều may mắn trên con đường phía trước! ✨",
                'mention': Mention(uid=uid, offset=15, length=len(user_name))
            },
            GroupEventType.ADD_ADMIN: {
                'main_text': f'Chúc mừng, {user_name}',
                'group_name_text': group_name,
                'credit_text': f"bổ nhiệm làm phó nhóm🔑",
                'msg': f' {user_name}',
                'mention': None
            },
            GroupEventType.REMOVE_ADMIN: {
                'main_text': f'Rất tiếc, {user_name}',
                'group_name_text': group_name,
                'credit_text': f"Đã bị xóa vai trò nhóm",
                'msg': f' {user_name}',
                'mention': None
            },
            GroupEventType.REMOVE_MEMBER: {
                'main_text': f'Thanh trừng, {user_name}',
                'group_name_text': group_name,
                'credit_text': f"Bị kick bởi {ow_name}" if ow_name else "Đã bị kick khỏi nhóm",
                'msg': f"💀 R.I.P {user_name} đã bị {ow_name} thanh trừng thẳng tay khỏi nhóm '{group_name}'! Tiễn vong, chúc đầu thai sang nhóm khác ngoan ngoãn hơn nhé! ⚰️" if ow_name else f"💀 R.I.P {user_name} đã bị thanh trừng thẳng tay khỏi nhóm '{group_name}'! Tiễn vong, chúc đầu thai sang nhóm khác ngoan ngoãn hơn nhé! ⚰️",
                'mention': Mention(uid=uid, offset=8, length=len(user_name))
            },
            GroupEventType.JOIN_REQUEST: {
                'main_text': f'Yêu cầu tham gia ',
                'group_name_text': group_name,
                'credit_text': f"{user_name}",
                'msg': f' {user_name}',
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

        time_text = f" {time.strftime('%d/%m/%Y')}   {time.strftime('%H:%M:%S')}     Executed by {ow_name}" if ow_name else f" {time.strftime('%d/%m/%Y')}      {time.strftime('%H:%M:%S')}"
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
        
        settings = read_settings(client.uid)
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

def handle_welcome_on(bot, thread_id: str) -> str:
    settings = read_settings(bot.uid)
    if "welcome" not in settings:
        settings["welcome"] = {}
    settings["welcome"][thread_id] = True
    write_settings(bot.uid, settings)
    return f"🚦Chế độ welcome đã 🟢 Bật 🎉"

def handle_welcome_off(bot, thread_id: str) -> str:
    settings = read_settings(bot.uid)
    if "welcome" in settings and thread_id in settings["welcome"]:
        settings["welcome"][thread_id] = False
        write_settings(bot.uid, settings)
        return f"🚦Chế độ welcome đã 🔴 Tắt 🎉"
    return "🚦Nhóm chưa có thông tin cấu hình welcome để 🔴 Tắt 🤗"

def get_allow_welcome(bot, thread_id: str) -> bool:
    settings = read_settings(bot.uid)
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