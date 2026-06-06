import os
import time
import threading
from zlapi.models import *
from core.bot_sys import is_admin, get_user_name_by_id

# Global dictionary to track running state of 2c per thread
running_threads = {}
threads_lock = threading.Lock()

txa = {
    "name": "2c",
    "desc": "Gõ nhanh 2 chữ tag liên tục người dùng",
    "author": "TXA",
    "command": ["2c"]
}

FALLBACK_PHRASES = [
    "alo alo", "sao thế", "kìa em", "rep đi", "nhanh lên", "chậm chạp", "làm gì đấy",
    "rep lẹ", "chờ tí", "đây nè", "lên đi", "ngủ à", "dậy đi", "đâu rồi", "hú hồn"
]

def handle_2c_command(bot, message_object, author_id, thread_id, thread_type, message_text):
    global running_threads

    if thread_type != ThreadType.GROUP:
        bot.replyMessage(Message(text="⚠️ Lệnh này chỉ có thể sử dụng trong nhóm chat!"), message_object, thread_id, thread_type)
        return

    if not is_admin(bot, author_id):
        bot.replyMessage(Message(text="⚠️ Bạn không có quyền sử dụng lệnh này!"), message_object, thread_id, thread_type)
        return

    parts = message_text.strip().split()
    if len(parts) < 2:
        bot.replyMessage(Message(text="⚠️ Cú pháp: \n➜ .2c on @tag (Bắt đầu chọc)\n➜ .2c stop (Dừng chọc)"), message_object, thread_id, thread_type)
        return

    action = parts[1].lower()

    if action == "stop":
        with threads_lock:
            if thread_id in running_threads and running_threads[thread_id]:
                running_threads[thread_id] = False
                bot.replyMessage(Message(text="🛑 Đã dừng chọc ghẹo thành viên!"), message_object, thread_id, thread_type)
            else:
                bot.replyMessage(Message(text="⚠️ Hiện tại không chạy chế độ chọc ghẹo nào ở nhóm này."), message_object, thread_id, thread_type)
        return

    if action != "on":
        bot.replyMessage(Message(text="⚠️ Lệnh không hợp lệ! Vui lòng dùng: .2c on @tag hoặc .2c stop"), message_object, thread_id, thread_type)
        return

    # Check for mentions
    if not message_object.mentions:
        bot.replyMessage(Message(text="⚠️ Vui lòng tag người muốn chọc ghẹo!"), message_object, thread_id, thread_type)
        return

    target_uid = message_object.mentions[0]['uid']
    target_name = get_user_name_by_id(bot, target_uid)

    with threads_lock:
        if running_threads.get(thread_id, False):
            bot.replyMessage(Message(text="⚠️ Tiến trình chọc ghẹo đang chạy trong nhóm này rồi!"), message_object, thread_id, thread_type)
            return
        running_threads[thread_id] = True

    # Try loading from 2.txt first, then choc.txt
    phrases = []
    for file_path in ["2.txt", "choc.txt"]:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    phrases = [line.strip() for line in f if line.strip()]
                if phrases:
                    break
            except Exception as e:
                print(f"[WARN] Error reading {file_path}: {e}")

    if not phrases:
        phrases = FALLBACK_PHRASES

    bot.replyMessage(Message(text=f"🚀 Bắt đầu chọc ghẹo 👤 {target_name}!"), message_object, thread_id, thread_type)

    def run_2c_loop(tid, t_uid, name_str, msg_list):
        global running_threads
        try:
            while True:
                for phrase in msg_list:
                    with threads_lock:
                        if not running_threads.get(tid, False):
                            return
                    
                    text = f"@{name_str} {phrase}"
                    mention = Mention(uid=t_uid, offset=0, length=len(name_str) + 1)
                    
                    try:
                        bot.send(Message(text=text, mention=mention), tid, thread_type)
                    except Exception as e:
                        print(f"[ERROR] 2c error in group {tid}: {e}")
                    
                    time.sleep(0.5)
        finally:
            with threads_lock:
                running_threads[tid] = False

    thread = threading.Thread(target=run_2c_loop, args=(thread_id, target_uid, target_name, phrases), daemon=True)
    thread.start()

def txa_command(bot, message_object, author_id, thread_id, thread_type, message_text):
    handle_2c_command(bot, message_object, author_id, thread_id, thread_type, message_text)
