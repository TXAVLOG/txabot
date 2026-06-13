import time
import threading
from zlapi.models import *
from core.bot_sys import is_admin

# Global dictionary to track running state of treo per thread
running_threads = {}
threads_lock = threading.Lock()

txa = {
    "name": "treo",
    "desc": "Gửi tin nhắn định kỳ để treo bot tránh offline/sleep",
    "author": "TXA",
    "command": ["treo"],
    "t-per": "admin"
}

def handle_treo_command(bot, message_object, author_id, thread_id, thread_type, message_text):
    global running_threads

    parts = message_text.strip().split()
    if len(parts) < 2:
        bot.replyMessage(Message(text="⚠️ Cú pháp: \n➜ .treo on [độ trễ (giây)] [nội dung] (Mặc định: 27s, 'treo')\n➜ .treo stop (Dừng treo)"), message_object, thread_id, thread_type)
        return

    action = parts[1].lower()

    if action == "stop":
        with threads_lock:
            if thread_id in running_threads and running_threads[thread_id]:
                running_threads[thread_id] = False
                bot.replyMessage(Message(text="🛑 Đã dừng treo bot trong nhóm này!"), message_object, thread_id, thread_type)
            else:
                bot.replyMessage(Message(text="⚠️ Nhóm này hiện không chạy chế độ treo."), message_object, thread_id, thread_type)
        return

    if action != "on":
        bot.replyMessage(Message(text="⚠️ Lệnh không hợp lệ! Vui lòng dùng: .treo on hoặc .treo stop"), message_object, thread_id, thread_type)
        return

    # Parse delay and custom message
    delay = 27
    content = "treo"

    if len(parts) >= 3:
        try:
            delay = int(parts[2])
            if delay <= 0:
                bot.replyMessage(Message(text="⚠️ Độ trễ phải lớn hơn 0!"), message_object, thread_id, thread_type)
                return
        except ValueError:
            bot.replyMessage(Message(text="⚠️ Độ trễ phải là một số nguyên!"), message_object, thread_id, thread_type)
            return

    if len(parts) >= 4:
        content = " ".join(parts[3:])

    with threads_lock:
        if running_threads.get(thread_id, False):
            bot.replyMessage(Message(text="⚠️ Chế độ treo đang chạy trong nhóm này rồi!"), message_object, thread_id, thread_type)
            return
        running_threads[thread_id] = True

    bot.replyMessage(
        Message(text=f"🚀 Bắt đầu chế độ treo bot!\n➜ Độ trễ: {delay} giây\n➜ Nội dung: \"{content}\""),
        message_object, thread_id, thread_type
    )

    def treo_loop(tid, dly, msg_text):
        global running_threads
        try:
            while True:
                with threads_lock:
                    if not running_threads.get(tid, False):
                        return
                try:
                    bot.send(Message(text=msg_text), tid, thread_type)
                except Exception as e:
                    print(f"[ERROR] treo error in thread {tid}: {e}")
                time.sleep(dly)
        finally:
            with threads_lock:
                running_threads[tid] = False

    thread = threading.Thread(target=treo_loop, args=(thread_id, delay, content), daemon=True)
    thread.start()

def txa_command(bot, message_object, author_id, thread_id, thread_type, message_text):
    handle_treo_command(bot, message_object, author_id, thread_id, thread_type, message_text)
