import time
import threading
from zlapi.models import *
from core.bot_sys import is_admin

# Global dictionary to track spam sessions per thread
# Format: { thread_id: { 'is_spamming': bool, 'text': str, 'delay': int (ms), 'ttl': int (ms) } }
spam_sessions = {}
sessions_lock = threading.Lock()

txa = {
    "name": "spamgroup",
    "desc": "Spam nhóm với độ trễ tùy chỉnh và tin nhắn tự hủy TTL",
    "author": "TXA",
    "command": ["spamgroup"]
}

def handle_spamgroup_command(bot, message_object, author_id, thread_id, thread_type, message_text):
    global spam_sessions

    if not is_admin(bot, author_id):
        bot.replyMessage(Message(text="⚠️ Bạn không có quyền sử dụng lệnh này!"), message_object, thread_id, thread_type)
        return

    prefix = getattr(bot, 'prefix', '.')
    cmd_name = "spamgroup"
    
    # Extract arguments after command
    args = message_text[len(prefix) + len(cmd_name):].strip()

    def send_syntax_error():
        bot.replyMessage(
            Message(
                text=f"⚠️ Cú pháp sai. Dùng:\n"
                     f"➜ {prefix}spamgroup <nội dung>|<delay (ms)>\n"
                     f"➜ {prefix}spamgroup delay|<giá trị mới (ms)>\n"
                     f"➜ {prefix}spamgroup set|<ttl (ms)>\n"
                     f"➜ {prefix}spamgroup stop"
            ),
            message_object, thread_id, thread_type
        )

    if not args:
        send_syntax_error()
        return

    # Get or initialize session for this thread
    with sessions_lock:
        if thread_id not in spam_sessions:
            spam_sessions[thread_id] = {
                "is_spamming": False,
                "text": "",
                "delay": 1000,   # Default 1s
                "ttl": 10000,    # Default 10s TTL
            }
        session = spam_sessions[thread_id]

    # STOP ACTION
    if args.lower() == "stop":
        with sessions_lock:
            if session["is_spamming"]:
                session["is_spamming"] = False
                bot.replyMessage(Message(text="✅ Đã dừng spam nhóm."), message_object, thread_id, thread_type)
            else:
                bot.replyMessage(Message(text="⚠️ Không có spam nào đang chạy trong nhóm này."), message_object, thread_id, thread_type)
        return

    # CHANGE DELAY ACTION
    if args.lower().startswith("delay|"):
        try:
            new_delay = int(args.split("|")[1].strip())
            if new_delay < 100:  # Safety limit of 100ms minimum to prevent extreme spam
                bot.replyMessage(Message(text="⚠️ Độ trễ tối thiểu phải là 100ms!"), message_object, thread_id, thread_type)
                return
        except (ValueError, IndexError):
            bot.replyMessage(Message(text="⚠️ Độ trễ mới không hợp lệ!"), message_object, thread_id, thread_type)
            return

        with sessions_lock:
            session["delay"] = new_delay
            is_currently_spamming = session["is_spamming"]
        
        bot.replyMessage(Message(text=f"✅ Đã đổi độ trễ thành {new_delay}ms."), message_object, thread_id, thread_type)
        
        # If spamming, thread will pick up the new delay automatically
        return

    # CHANGE TTL ACTION
    if args.lower().startswith("set|"):
        try:
            new_ttl = int(args.split("|")[1].strip())
            if new_ttl < 0:
                bot.replyMessage(Message(text="⚠️ TTL không được âm!"), message_object, thread_id, thread_type)
                return
        except (ValueError, IndexError):
            bot.replyMessage(Message(text="⚠️ TTL không hợp lệ!"), message_object, thread_id, thread_type)
            return

        with sessions_lock:
            session["ttl"] = new_ttl
            
        bot.replyMessage(Message(text=f"✅ Đã thiết lập thời gian tự hủy (TTL) thành {new_ttl}ms."), message_object, thread_id, thread_type)
        return

    # START SPAM ACTION (content|delay_ms)
    if "|" in args:
        parts = args.split("|")
        msg_content = parts[0].strip()
        try:
            delay = int(parts[1].strip())
            if delay < 100:
                bot.replyMessage(Message(text="⚠️ Độ trễ tối thiểu phải là 100ms!"), message_object, thread_id, thread_type)
                return
        except ValueError:
            send_syntax_error()
            return

        if not msg_content:
            send_syntax_error()
            return

        with sessions_lock:
            session["text"] = msg_content
            session["delay"] = delay
            session["is_spamming"] = True

        bot.replyMessage(
            Message(text=f"✅ Bắt đầu spam nhóm:\n➜ Nội dung: \"{msg_content}\"\n⏱ Độ trễ: {delay}ms\n🕒 Tự hủy (TTL): {session['ttl']}ms"),
            message_object, thread_id, thread_type
        )

        def spam_loop(tid):
            global spam_sessions
            try:
                while True:
                    with sessions_lock:
                        sess = spam_sessions.get(tid)
                        if not sess or not sess["is_spamming"]:
                            return
                        text_to_send = sess["text"]
                        ttl_val = sess["ttl"]
                        delay_ms = sess["delay"]
                    
                    try:
                        # Send message with TTL self-destruction
                        bot.send(Message(text=text_to_send), tid, thread_type, ttl=ttl_val)
                    except Exception as e:
                        print(f"[ERROR] spamgroup error in thread {tid}: {e}")
                    
                    time.sleep(delay_ms / 1000.0)
            finally:
                with sessions_lock:
                    if tid in spam_sessions:
                        spam_sessions[tid]["is_spamming"] = False

        thread = threading.Thread(target=spam_loop, args=(thread_id,), daemon=True)
        thread.start()
        return

    send_syntax_error()

def txa_command(bot, message_object, author_id, thread_id, thread_type, message_text):
    handle_spamgroup_command(bot, message_object, author_id, thread_id, thread_type, message_text)
