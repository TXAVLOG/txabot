import os
import time
import threading
from zlapi.models import *
from core.bot_sys import is_admin

# Global dictionary to track running state of reonamegr per thread (group)
# Format: { thread_id: bool }
running_threads = {}
threads_lock = threading.Lock()

txa = {
    "name": "reonamegr",
    "desc": "Spam đổi tên nhóm liên tục theo nội dung file noidung.txt",
    "author": "TXA",
    "command": ["reonamegr"]
}

def handle_reonamegr_command(bot, message_object, author_id, thread_id, thread_type, message_text):
    global running_threads
    
    if thread_type != ThreadType.GROUP:
        bot.replyMessage(Message(text="⚠️ Lệnh này chỉ có thể sử dụng trong nhóm chat!"), message_object, thread_id, thread_type)
        return

    if not is_admin(bot, author_id):
        bot.replyMessage(Message(text="⚠️ Bạn không có quyền sử dụng lệnh này!"), message_object, thread_id, thread_type)
        return

    parts = message_text.strip().split()
    if len(parts) < 2:
        bot.replyMessage(Message(text="⚠️ Cú pháp: \n➜ .reonamegr on (Bắt đầu đổi tên)\n➜ .reonamegr stop (Dừng đổi tên)"), message_object, thread_id, thread_type)
        return

    action = parts[1].lower()

    if action == "stop":
        with threads_lock:
            if thread_id in running_threads and running_threads[thread_id]:
                running_threads[thread_id] = False
                bot.replyMessage(Message(text="🛑 Đã gửi yêu cầu dừng đổi tên nhóm!"), message_object, thread_id, thread_type)
            else:
                bot.replyMessage(Message(text="⚠️ Không có tiến trình đổi tên nhóm nào đang chạy ở nhóm này."), message_object, thread_id, thread_type)
        return

    if action != "on":
        bot.replyMessage(Message(text="⚠️ Lệnh không hợp lệ! Vui lòng dùng: .reonamegr on hoặc .reonamegr stop"), message_object, thread_id, thread_type)
        return

    # Check if already running in this group
    with threads_lock:
        if running_threads.get(thread_id, False):
            bot.replyMessage(Message(text="⚠️ Tiến trình spam đổi tên nhóm đang chạy rồi!"), message_object, thread_id, thread_type)
            return
        running_threads[thread_id] = True

    # Read noidung.txt
    file_path = "noidung.txt"
    if not os.path.exists(file_path):
        with threads_lock:
            running_threads[thread_id] = False
        bot.replyMessage(Message(text="❌ Không tìm thấy file noidung.txt ở thư mục gốc!"), message_object, thread_id, thread_type)
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        with threads_lock:
            running_threads[thread_id] = False
        bot.replyMessage(Message(text=f"❌ Không thể đọc file noidung.txt: {str(e)}"), message_object, thread_id, thread_type)
        return

    if not lines:
        with threads_lock:
            running_threads[thread_id] = False
        bot.replyMessage(Message(text="❌ File noidung.txt trống rỗng!"), message_object, thread_id, thread_type)
        return

    bot.replyMessage(Message(text="🚀 Bắt đầu tiến trình spam đổi tên nhóm chat liên tục!"), message_object, thread_id, thread_type)

    def reoname_loop(tid):
        global running_threads
        try:
            while True:
                for line in lines:
                    with threads_lock:
                        if not running_threads.get(tid, False):
                            return
                    try:
                        bot.changeGroupName(line, tid)
                    except Exception as e:
                        print(f"[ERROR] reonamegr error in group {tid}: {e}")
                    time.sleep(0.5) # Sleep 0.5s to avoid spam rate limit block from Zalo
        finally:
            with threads_lock:
                running_threads[tid] = False

    thread = threading.Thread(target=reoname_loop, args=(thread_id,), daemon=True)
    thread.start()

def txa_command(bot, message_object, author_id, thread_id, thread_type, message_text):
    handle_reonamegr_command(bot, message_object, author_id, thread_id, thread_type, message_text)
