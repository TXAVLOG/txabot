import time
import threading
from zlapi.models import *
from core.bot_sys import is_admin

txa = {
    "name": "spamjoin",
    "desc": "Tự động gia nhập và rời nhóm liên tục theo số lần chỉ định bằng link",
    "author": "TXA",
    "command": ["spamjoin"],
    "t-per": "admin"
}

def handle_spamjoin_command(bot, message_object, author_id, thread_id, thread_type, message_text):
    parts = message_text.strip().split()
    if len(parts) < 3:
        bot.replyMessage(Message(text="⚠️ Cú pháp: .spamjoin [link_nhóm] [số_lần]"), message_object, thread_id, thread_type)
        return

    url = parts[1].strip()
    try:
        count = int(parts[2].strip())
    except ValueError:
        bot.replyMessage(Message(text="⚠️ Số lần phải là số nguyên dương!"), message_object, thread_id, thread_type)
        return

    if count <= 0:
        bot.replyMessage(Message(text="⚠️ Số lần phải lớn hơn 0!"), message_object, thread_id, thread_type)
        return

    if not url.startswith("https://zalo.me/"):
        bot.replyMessage(Message(text="⚠️ Link nhóm không hợp lệ! Yêu cầu bắt đầu bằng 'https://zalo.me/'"), message_object, thread_id, thread_type)
        return

    bot.replyMessage(Message(text=f"⏳ Bắt đầu tiến trình spamjoin ({count} lần) gửi yêu cầu và rời nhóm..."), message_object, thread_id, thread_type)

    def spamjoin_loop():
        success_count = 0
        error_count = 0
        group_name = "Không rõ"
        group_id = None

        # Resolve group ID first
        try:
            group_info = bot.checkGroup(url)
            if group_info and 'groupId' in group_info:
                group_id = group_info['groupId']
                group_name = group_info.get('name', 'Không rõ')
        except Exception as e:
            print(f"[WARN] Failed to get group info before join: {e}")

        for i in range(count):
            try:
                # 1. Join Group
                join_result = bot.joinGroup(url)
                
                # Check error codes if join_result is dict
                if isinstance(join_result, dict) and 'error_code' in join_result:
                    ec = join_result['error_code']
                    if ec not in [0, 240, 1022]:
                        error_count += 1
                        time.sleep(1.0)
                        continue

                # 2. Resolve Group ID if not already resolved
                if not group_id:
                    try:
                        group_info = bot.checkGroup(url)
                        if group_info and 'groupId' in group_info:
                            group_id = group_info['groupId']
                            group_name = group_info.get('name', 'Không rõ')
                    except Exception as e:
                        print(f"[WARN] Failed to check group info during loop: {e}")

                if not group_id:
                    error_count += 1
                    time.sleep(1.0)
                    continue

                # Small delay after joining
                time.sleep(1.0)

                # 3. Leave Group
                bot.leaveGroup(group_id, silent=True)
                success_count += 1

                # Delay before next iteration to avoid being rate-limited too fast
                time.sleep(1.0)

            except Exception as e:
                print(f"[ERROR] Error during spamjoin iteration {i+1}: {e}")
                error_count += 1
                time.sleep(1.0)

        # Send completion report
        report_msg = (
            f"✔️ Hoàn thành tiến trình spamjoin nhóm \"{group_name}\"!\n"
            f"➜ Tổng số lần chạy: {count}\n"
            f"➜ Thành công (Tham gia + Thoát): {success_count}\n"
            f"➜ Thất bại: {error_count}"
        )
        bot.replyMessage(Message(text=report_msg), message_object, thread_id, thread_type)

    threading.Thread(target=spamjoin_loop, daemon=True).start()

def txa_command(bot, message_object, author_id, thread_id, thread_type, message_text):
    handle_spamjoin_command(bot, message_object, author_id, thread_id, thread_type, message_text)
