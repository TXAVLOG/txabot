import inspect
from core.bot_sys import is_admin, read_settings, write_settings, get_user_name_by_id, cleanup_pending_messages
from zlapi.models import Message, ThreadType, Mention

txa = {
    "name": "Duyet quyen",
    "desc": "Duyệt hoặc hủy duyệt quyền sử dụng các lệnh kho ảnh cho thành viên.",
    "author": "TXA",
    "command": ["duyet", "unduyet"]
}

def duyet_cmd(bot, message_object, thread_id, thread_type, author_id, message_text):
    if not is_admin(bot, author_id):
        bot.replyMessage(
            Message(text="❌ Bạn không có quyền sử dụng lệnh này (Chỉ dành cho Admin Bot)."),
            message_object, thread_id, thread_type
        )
        return

    target_uid = None
    if message_object.mentions:
        target_uid = message_object.mentions[0]['uid']
    else:
        parts = message_text.split()
        if len(parts) > 1:
            target_uid = parts[1].strip()
            if target_uid.startswith('@'):
                target_uid = target_uid[1:]

    if not target_uid:
        bot.replyMessage(
            Message(text="⚠️ Vui lòng tag người dùng hoặc nhập UID để duyệt quyền.\n➜ Cú pháp: !duyet <@tag/ID>"),
            message_object, thread_id, thread_type
        )
        return

    if not target_uid.isdigit():
        bot.replyMessage(
            Message(text="⚠️ ID người dùng không hợp lệ! Vui lòng nhập UID dạng số hoặc tag trực tiếp người đó."),
            message_object, thread_id, thread_type
        )
        return

    settings = read_settings(bot.uid)
    approved_users = settings.setdefault("image_approved_users", [])

    if target_uid in approved_users:
        target_name = get_user_name_by_id(bot, target_uid)
        bot.replyMessage(
            Message(text=f"💡 Người dùng {target_name} ({target_uid}) đã được duyệt từ trước rồi."),
            message_object, thread_id, thread_type
        )
        return

    # Lấy time_arg cho !duyet
    time_arg = ""
    if message_object.mentions:
        mention = message_object.mentions[0]
        offset = mention['offset']
        length = mention['length']
        time_arg = message_text[offset + length:].strip()
    else:
        parts = message_text.split()
        if len(parts) > 2:
            time_arg = " ".join(parts[2:])

    from core.bot_sys import parse_expiration_time, datetime
    expiry_time = None
    if time_arg:
        expiry_time = parse_expiration_time(time_arg)
        if not expiry_time:
            bot.replyMessage(
                Message(text="⚠️ Định dạng thời gian không hợp lệ! Vui lòng nhập số giây (ví dụ: 60) hoặc ngày giờ (ví dụ: 10:30:00 06/06/2026)."),
                message_object, thread_id, thread_type
            )
            return

    approved_users.append(target_uid)
    settings["image_approved_users"] = approved_users
    
    # Lưu thời gian hết hạn của kho ảnh
    image_expiry = settings.setdefault("image_approved_users_expiry", {})
    image_expiry[target_uid] = expiry_time
    settings["image_approved_users_expiry"] = image_expiry
    
    write_settings(bot.uid, settings)

    # Thực hiện dọn dẹp các tin nhắn chưa duyệt trước đó
    cleanup_pending_messages(bot, target_uid)

    target_name = get_user_name_by_id(bot, target_uid)
    
    # Gửi tin nhắn riêng (Inbox) báo cho người dùng biết
    try:
        if expiry_time:
            expiry_str = datetime.fromtimestamp(expiry_time).strftime("%H:%M:%S %d/%m/%Y")
            inbox_text = f"🎉 Chào bạn, bạn đã được Admin duyệt quyền sử dụng các lệnh kho ảnh của TXA Bot đến {expiry_str}! Hãy trải nghiệm nhé. 🌸"
        else:
            inbox_text = f"🎉 Chào bạn, bạn đã được Admin duyệt quyền sử dụng các lệnh kho ảnh của TXA Bot vô thời hạn! Hãy trải nghiệm nhé. 🌸"
        bot.send(Message(text=inbox_text), thread_id=target_uid, thread_type=ThreadType.USER)
    except Exception as e:
        print(f"[ERROR] Không thể gửi tin nhắn riêng cho {target_uid}: {e}")

    # Gửi phản hồi lại nhóm chat / thread hiện tại
    if expiry_time:
        expiry_str = datetime.fromtimestamp(expiry_time).strftime("%H:%M:%S %d/%m/%Y")
        response_text = f"✅ Đã duyệt quyền sử dụng các lệnh kho ảnh cho {target_name} ({target_uid}) đến {expiry_str}.\n💡 Bot đã tự động tạo nhắc nhở thông báo khi hết hạn."
    else:
        response_text = f"✅ Đã duyệt quyền sử dụng các lệnh kho ảnh cho {target_name} ({target_uid}) vô thời hạn."
        
    mention = None
    if target_name != "Unknown User":
        if expiry_time:
            response_text = f"✅ Đã duyệt quyền sử dụng các lệnh kho ảnh cho {target_name} đến {expiry_str}.\n💡 Bot đã tự động tạo nhắc nhở thông báo khi hết hạn."
        else:
            response_text = f"✅ Đã duyệt quyền sử dụng các lệnh kho ảnh cho {target_name} vô thời hạn."
        offset = response_text.find(target_name)
        length = len(target_name)
        mention = Mention(uid=target_uid, length=length, offset=offset)

    bot.replyMessage(Message(text=response_text, mention=mention), message_object, thread_id, thread_type)


def unduyet_cmd(bot, message_object, thread_id, thread_type, author_id, message_text):
    if not is_admin(bot, author_id):
        bot.replyMessage(
            Message(text="❌ Bạn không có quyền sử dụng lệnh này (Chỉ dành cho Admin Bot)."),
            message_object, thread_id, thread_type
        )
        return

    target_uid = None
    if message_object.mentions:
        target_uid = message_object.mentions[0]['uid']
    else:
        parts = message_text.split()
        if len(parts) > 1:
            target_uid = parts[1].strip()
            if target_uid.startswith('@'):
                target_uid = target_uid[1:]

    if not target_uid:
        bot.replyMessage(
            Message(text="⚠️ Vui lòng tag người dùng hoặc nhập UID để hủy duyệt quyền.\n➜ Cú pháp: !unduyet <@tag/ID>"),
            message_object, thread_id, thread_type
        )
        return

    if not target_uid.isdigit():
        bot.replyMessage(
            Message(text="⚠️ ID người dùng không hợp lệ! Vui lòng nhập UID dạng số hoặc tag trực tiếp người đó."),
            message_object, thread_id, thread_type
        )
        return

    settings = read_settings(bot.uid)
    approved_users = settings.setdefault("image_approved_users", [])

    if target_uid not in approved_users:
        target_name = get_user_name_by_id(bot, target_uid)
        bot.replyMessage(
            Message(text=f"💡 Người dùng {target_name} ({target_uid}) chưa từng được duyệt quyền kho ảnh."),
            message_object, thread_id, thread_type
        )
        return

    approved_users.remove(target_uid)
    settings["image_approved_users"] = approved_users
    
    # Xóa lịch sử hết hạn kho ảnh của user
    image_expiry = settings.get("image_approved_users_expiry", {})
    image_expiry.pop(target_uid, None)
    settings["image_approved_users_expiry"] = image_expiry
    
    write_settings(bot.uid, settings)

    target_name = get_user_name_by_id(bot, target_uid)

    # Gửi tin nhắn riêng (Inbox) báo cho người dùng biết
    try:
        inbox_text = f"⚠️ Chào bạn, bạn đã bị Admin hủy quyền sử dụng các lệnh kho ảnh của TXA Bot."
        bot.send(Message(text=inbox_text), thread_id=target_uid, thread_type=ThreadType.USER)
    except Exception as e:
        print(f"[ERROR] Không thể gửi tin nhắn riêng cho {target_uid}: {e}")

    # Gửi phản hồi lại nhóm chat / thread hiện tại
    response_text = f"✅ Đã hủy duyệt quyền sử dụng các lệnh kho ảnh đối với {target_name} ({target_uid})."
    mention = None
    if target_name != "Unknown User":
        response_text = f"✅ Đã hủy duyệt quyền sử dụng các lệnh kho ảnh đối với {target_name}."
        offset = response_text.find(target_name)
        length = len(target_name)
        mention = Mention(uid=target_uid, length=length, offset=offset)

    bot.replyMessage(Message(text=response_text, mention=mention), message_object, thread_id, thread_type)


def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'duyet': duyet_cmd,
        'unduyet': unduyet_cmd
    }
    
    func = dispatch_map.get(cmd)
    if func:
        sig = inspect.signature(func)
        args_map = {
            'bot': bot,
            'message_object': message_object,
            'thread_id': thread_id,
            'thread_type': thread_type,
            'author_id': author_id,
            'message_text': message_text
        }
        args = []
        for param_name in sig.parameters:
            if param_name in args_map:
                args.append(args_map[param_name])
            else:
                args.append(None)
        func(*args)
