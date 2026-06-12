import time
import threading
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from zlapi.models import Message, ThreadType
from zlapi._message import MessageReaction

def extract_target_uid(bot, message_object, message_text):
    # 1. Check quote/reply
    if message_object.quote:
        return message_object.quote.ownerId
        
    # 2. Check mentions
    if message_object.mentions:
        for mention in message_object.mentions:
            uid = mention.get("uid")
            if uid and uid != "-1":
                return uid
                
    # 3. Check if UID is passed as text argument
    parts = message_text.split()
    if len(parts) > 1:
        arg = parts[1].strip()
        if arg.isdigit() and len(arg) >= 15:
            return arg
            
    return None

def get_user_messages(bot, thread_id, thread_type, target_uid, exclude_msg_id):
    target_messages = []
    target_uid_str = str(target_uid)
    exclude_msg_id_str = str(exclude_msg_id)
    known_ids = set()

    # 1. Nếu là GROUP, lấy từ API getRecentGroup trước
    if thread_type == ThreadType.GROUP:
        try:
            group_data = bot.getRecentGroup(thread_id)
            recent_msgs = []
            if hasattr(group_data, "groupMsgs"):
                recent_msgs = group_data.groupMsgs or []
            elif isinstance(group_data, dict):
                recent_msgs = group_data.get("groupMsgs", []) or []
                
            for m in reversed(recent_msgs):
                msg_id = str(m.get("msgId", ""))
                uid_from = str(m.get("uidFrom", ""))
                if msg_id == exclude_msg_id_str:
                    continue
                if uid_from == target_uid_str:
                    msg_type = m.get("msgType", "webchat")
                    target_messages.append({
                        "msgId": m.get("msgId"),
                        "cliMsgId": m.get("cliMsgId"),
                        "msgType": msg_type
                    })
                    known_ids.add(msg_id)
                    break
        except Exception as e:
            print(f"[React30] Error getting recent group messages: {e}")

    # 2. Lấy thêm từ message_history của bot nếu chưa tìm thấy
    if not target_messages:
        history = getattr(bot, "message_history", {}).get(thread_id, [])
        for m in reversed(history):
            msg_id = str(m.get("msgId", ""))
            author_id = str(m.get("author_id", ""))
            if msg_id == exclude_msg_id_str:
                continue
            if author_id == target_uid_str:
                msg_type = m.get("msgType", "webchat")
                target_messages.append({
                    "msgId": m.get("msgId"),
                    "cliMsgId": m.get("cliMsgId"),
                    "msgType": msg_type
                })
                break

    return target_messages

txa = {
    "name": "React30",
    "desc": "Thử nghiệm thả 30 react vào CHÍNH TIN NHẮN và giảm dần mỗi 1 giây (Phương án Tối ưu 1-Remove mỗi giây)",
    "author": "TXA",
    "command": ["react30"]
}

def spam_react(bot, target_msg, thread_id, thread_type, count):
    if count <= 0:
        return
    # Gửi song song các yêu cầu thả cảm xúc bằng ThreadPool
    with ThreadPoolExecutor(max_workers=count) as executor:
        futures = [
            executor.submit(bot.sendReaction, target_msg, "❤️", thread_id, thread_type)
            for _ in range(count)
        ]
        for f in futures:
            try:
                f.result()
            except Exception as e:
                print(f"[React30] Error in spam executor: {e}")

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    target_msg = None

    # 1. Nếu người dùng reply tin nhắn
    if message_object.quote:
        q = message_object.quote
        class DummyMsg:
            def __init__(self, msg_id, cli_msg_id, msg_type):
                self.msgId = msg_id
                self.cliMsgId = cli_msg_id
                self.msgType = msg_type
        target_msg = DummyMsg(q.globalMsgId, q.cliMsgId, "webchat")
    else:
        # 2. Tìm UID mục tiêu qua mention hoặc tham số
        target_uid = extract_target_uid(bot, message_object, message_text)
        if not target_uid:
            bot.replyMessage(
                Message(text="⚠️ Vui lòng reply tin nhắn cần thả react, tag người dùng hoặc cung cấp UID!"),
                message_object, thread_id, thread_type
            )
            return "no_reaction"

        # Lấy tin nhắn gần nhất của người đó
        found_msgs = get_user_messages(bot, thread_id, thread_type, target_uid, message_object.msgId)
        if found_msgs:
            m = found_msgs[0]
            class DummyMsg:
                def __init__(self, msg_id, cli_msg_id, msg_type):
                    self.msgId = msg_id
                    self.cliMsgId = cli_msg_id
                    self.msgType = msg_type
            target_msg = DummyMsg(m["msgId"], m["cliMsgId"], m.get("msgType", "webchat"))

    if not target_msg:
        bot.replyMessage(
            Message(text="❌ Không tìm thấy tin nhắn nào của người dùng này trong lịch sử để thả react!"),
            message_object, thread_id, thread_type
        )
        return "no_reaction"

    # Tối ưu hóa kích thước Connection Pool của HTTP Session để tránh nghẽn
    try:
        session = bot._state._session
        adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
    except Exception as e:
        print(f"[React30] Error optimizing connection pool: {e}")

    bot.replyMessage(
        Message(text="🤖 Đang gửi 1 loạt 30 react ❤️ vào tin nhắn mục tiêu và gỡ dần mỗi 1 giây..."),
        message_object, thread_id, thread_type
    )

    # Chạy vòng lặp giảm dần bằng cách gửi: Gỡ sạch -> Thả i cái -> Đợi -> Gỡ sạch -> Thả i-1 cái...
    def run_spam_and_countdown():
        for i in range(30, 0, -1):
            try:
                # 1. Gỡ sạch các react trước đó của bot trên tin nhắn này
                bot.sendReaction(target_msg, "/-remove", thread_id, thread_type, reactionType=-1)
            except Exception as err:
                print(f"[React30] Error removing react at step {i}: {err}")
            
            # Chờ một khoảng rất ngắn để server Zalo cập nhật trạng thái gỡ
            time.sleep(0.15)
            
            # 2. Thả i react mới song song
            spam_react(bot, target_msg, thread_id, thread_type, i)
            print(f"[React30] Step {i}: Cleared and sent {i} reactions.")
            
            # 3. Đợi khoảng thời gian còn lại của 1 giây để hiển thị số lượng i
            time.sleep(0.85)
            
        # Cuối cùng, gỡ sạch sẽ
        try:
            bot.sendReaction(target_msg, "/-remove", thread_id, thread_type, reactionType=-1)
            print("[React30] Final: Cleared all reactions.")
        except Exception as err:
            print(f"[React30] Error removing final react: {err}")

    threading.Thread(target=run_spam_and_countdown, daemon=True).start()
    return "no_reaction"
