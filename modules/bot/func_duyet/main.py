import inspect
from core.bot_sys import is_admin, read_settings, write_settings, get_user_name_by_id, cleanup_pending_messages, is_group_admin_or_creator
from zlapi.models import Message, ThreadType, Mention

txa = {
    "name": "Duyệt quyền và quản lý key",
    "desc": {
        "duyet": "Duyệt dùng Bot",
        "unduyet": "Hủy duyệt dùng Bot",
        "capkey": "Cấp key vàng/bạc",
        "huykey": "Hủy key",
        "listkey": "Danh sách key",
        "duyetmedia": "Duyệt gửi media",
        "duyetanh": "Duyệt gửi ảnh"
    },
    "author": "TXA",
    "command": ["duyet", "unduyet", "capkey", "huykey", "listkey", "duyetmedia", "duyetanh"],
    "help": {
        "duyet": {
            "usage": [
                "{prefix}duyet <@tag/UID>",
                "{prefix}duyet <@tag/UID> <thoi_gian>"
            ],
            "examples": [
                "{prefix}duyet @user",
                "{prefix}duyet 123456789 10"
            ],
            "notes": [
                "Chi Admin BOT moi su dung duoc.",
                "Co the tag hoac nhap UID so.",
                "Thoi gian tinh theo ngay, mac dinh la khong han."
            ]
        },
        "unduyet": {
            "usage": [
                "{prefix}unduyet <@tag/UID>"
            ],
            "examples": [
                "{prefix}unduyet @user"
            ],
            "notes": [
                "Huy quyen dung Bot cho thanh vien."
            ]
        },
        "capkey": {
            "usage": [
                "{prefix}capkey <@tag/UID> <vang/bac> <thoi_gian>"
            ],
            "examples": [
                "{prefix}capkey @user vang 30"
            ],
            "notes": [
                "Cap key vang hoac bac cho thanh vien.",
                "Thoi gian tinh theo ngay."
            ]
        }
    }
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
    
    # Tạo Zalo Todo nhắc hẹn nếu có thời hạn
    if expiry_time:
        try:
            todo_content = f"Hạn dùng Kho ảnh của {target_name}"
            bot.sendTodo(
                target_id=target_uid,
                content=todo_content,
                mid=message_object.msgId,
                author_id=author_id,
                thread_type=thread_type,
                thread_id=thread_id if thread_type == ThreadType.GROUP else None,
                dueDate=int(expiry_time * 1000)
            )
        except Exception as todo_err:
            print(f"[ERROR] Không thể tạo Zalo Todo nhắc hẹn: {todo_err}")
    
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


def get_gold_key_holder(bot, thread_id, settings):
    group_keys = settings.setdefault("group_keys", {})
    group_key = group_keys.setdefault(thread_id, {})
    gold_holder = group_key.get("gold")
    if not gold_holder:
        # Fallback to group creator
        try:
            group_info = bot.fetchGroupInfo(thread_id).gridInfoMap.get(thread_id)
            if group_info:
                gold_holder = group_info.creatorId
                group_key["gold"] = gold_holder
                settings["group_keys"] = group_keys
                write_settings(bot.uid, settings)
        except Exception:
            pass
    return gold_holder

def has_key_permission(bot, author_id, thread_id, settings):
    if is_admin(bot, author_id):
        return True
    gold_holder = get_gold_key_holder(bot, thread_id, settings)
    if gold_holder:
        if str(author_id) == str(gold_holder):
            return True
    else:
        if is_group_admin_or_creator(bot, author_id, thread_id):
            return True
    return False

def capkey_cmd(bot, message_object, thread_id, thread_type, author_id, message_text):
    if thread_type != ThreadType.GROUP:
        bot.replyMessage(
            Message(text="❌ Lệnh này chỉ sử dụng được trong nhóm chat!"),
            message_object, thread_id, thread_type
        )
        return

    settings = read_settings(bot.uid)
    if not has_key_permission(bot, author_id, thread_id, settings):
        bot.replyMessage(
            Message(text="❌ Bạn không có quyền sử dụng lệnh này (Chỉ dành cho Admin/Key Vàng của nhóm)."),
            message_object, thread_id, thread_type
        )
        return

    parts = message_text.split()
    if len(parts) < 3:
        bot.replyMessage(
            Message(text=f"⚠️ Cú pháp không hợp lệ!\n➜ Sử dụng: {getattr(bot, 'prefix', '!')}capkey <vang/bac> <@tag/ID>"),
            message_object, thread_id, thread_type
        )
        return

    key_type = parts[1].lower()
    if key_type not in ["vang", "gold", "bac", "silver"]:
        bot.replyMessage(
            Message(text="⚠️ Loại key không hợp lệ! Vui lòng chọn 'vang' hoặc 'bac'."),
            message_object, thread_id, thread_type
        )
        return

    target_uid = None
    if message_object.mentions:
        target_uid = message_object.mentions[0]['uid']
    else:
        raw_uid = parts[2].strip()
        if raw_uid.startswith('@'):
            raw_uid = raw_uid[1:]
        if raw_uid.isdigit():
            target_uid = raw_uid

    if not target_uid:
        bot.replyMessage(
            Message(text="⚠️ Vui lòng tag người dùng hoặc nhập UID để cấp key."),
            message_object, thread_id, thread_type
        )
        return

    target_name = get_user_name_by_id(bot, target_uid)
    group_keys = settings.setdefault("group_keys", {})
    group_key = group_keys.setdefault(thread_id, {})
    
    if key_type in ["vang", "gold"]:
        old_gold = group_key.get("gold")
        
        # Thử đổi Owner trên Zalo
        zalo_msg = ""
        try:
            bot.changeGroupOwner(target_uid, thread_id)
            zalo_msg = "\n👑 [Zalo] Đã chuyển quyền Trưởng nhóm (Owner) thành công."
        except Exception as e:
            zalo_msg = f"\n⚠️ [Zalo] Không thể chuyển quyền Trưởng nhóm trên hệ thống Zalo (Chi tiết: {e})."

        group_key["gold"] = target_uid
        silver_list = group_key.setdefault("silver", [])
        if target_uid in silver_list:
            silver_list.remove(target_uid)
            group_key["silver"] = silver_list
            
        settings["group_keys"] = group_keys
        write_settings(bot.uid, settings)
        
        response_text = f"👑 Đã cấp Key Vàng (Admin nhóm) cho {target_name} ({target_uid})!{zalo_msg}"
        if old_gold:
            old_name = get_user_name_by_id(bot, old_gold)
            response_text += f"\n💡 Quyền Key Vàng của {old_name} ({old_gold}) đã bị thu hồi."
    else:
        silver_list = group_key.setdefault("silver", [])
        if target_uid in silver_list:
            bot.replyMessage(
                Message(text=f"💡 Người dùng {target_name} đã có Key Bạc từ trước rồi."),
                message_object, thread_id, thread_type
            )
            return
            
        gold_holder = group_key.get("gold")
        if target_uid == gold_holder:
            bot.replyMessage(
                Message(text=f"⚠️ Người dùng {target_name} đang giữ Key Vàng, không thể cấp thêm Key Bạc."),
                message_object, thread_id, thread_type
            )
            return
            
        # Thử thêm Admin trên Zalo
        zalo_msg = ""
        try:
            bot.addGroupAdmins(target_uid, thread_id)
            zalo_msg = "\n🥈 [Zalo] Đã thêm quyền Phó nhóm (Admin) thành công."
        except Exception as e:
            zalo_msg = f"\n⚠️ [Zalo] Không thể thêm quyền Phó nhóm trên hệ thống Zalo (Chi tiết: {e})."

        silver_list.append(target_uid)
        group_key["silver"] = silver_list
        settings["group_keys"] = group_keys
        write_settings(bot.uid, settings)
        
        response_text = f"🥈 Đã cấp Key Bạc cho {target_name} ({target_uid}) thành công!{zalo_msg}"

    mention = None
    if target_name != "Unknown User":
        offset = response_text.find(target_name)
        length = len(target_name)
        mention = Mention(uid=target_uid, length=length, offset=offset)

    bot.replyMessage(Message(text=response_text, mention=mention), message_object, thread_id, thread_type)

def huykey_cmd(bot, message_object, thread_id, thread_type, author_id, message_text):
    if thread_type != ThreadType.GROUP:
        bot.replyMessage(
            Message(text="❌ Lệnh này chỉ sử dụng được trong nhóm chat!"),
            message_object, thread_id, thread_type
        )
        return

    settings = read_settings(bot.uid)
    if not has_key_permission(bot, author_id, thread_id, settings):
        bot.replyMessage(
            Message(text="❌ Bạn không có quyền sử dụng lệnh này (Chỉ dành cho Admin/Key Vàng của nhóm)."),
            message_object, thread_id, thread_type
        )
        return

    parts = message_text.split()
    if len(parts) < 3:
        bot.replyMessage(
            Message(text=f"⚠️ Cú pháp không hợp lệ!\n➜ Sử dụng: {getattr(bot, 'prefix', '!')}huykey <vang/bac> <@tag/ID>"),
            message_object, thread_id, thread_type
        )
        return

    key_type = parts[1].lower()
    if key_type not in ["vang", "gold", "bac", "silver"]:
        bot.replyMessage(
            Message(text="⚠️ Loại key không hợp lệ! Vui lòng chọn 'vang' hoặc 'bac'."),
            message_object, thread_id, thread_type
        )
        return

    target_uid = None
    if message_object.mentions:
        target_uid = message_object.mentions[0]['uid']
    else:
        raw_uid = parts[2].strip()
        if raw_uid.startswith('@'):
            raw_uid = raw_uid[1:]
        if raw_uid.isdigit():
            target_uid = raw_uid

    if not target_uid:
        bot.replyMessage(
            Message(text="⚠️ Vui lòng tag người dùng hoặc nhập UID để thu hồi key."),
            message_object, thread_id, thread_type
        )
        return

    target_name = get_user_name_by_id(bot, target_uid)
    group_keys = settings.setdefault("group_keys", {})
    group_key = group_keys.setdefault(thread_id, {})

    if key_type in ["vang", "gold"]:
        gold_holder = group_key.get("gold")
        if not gold_holder or str(gold_holder) != str(target_uid):
            bot.replyMessage(
                Message(text=f"⚠️ Người dùng {target_name} ({target_uid}) không giữ Key Vàng của nhóm."),
                message_object, thread_id, thread_type
            )
            return
            
        group_key["gold"] = None
        settings["group_keys"] = group_keys
        write_settings(bot.uid, settings)
        response_text = f"👑 Đã thu hồi Key Vàng của {target_name} ({target_uid})! Nhóm hiện chưa có Key Vàng mới."
    else:
        silver_list = group_key.setdefault("silver", [])
        if target_uid not in silver_list:
            bot.replyMessage(
                Message(text=f"⚠️ Người dùng {target_name} ({target_uid}) không có Key Bạc."),
                message_object, thread_id, thread_type
            )
            return
            
        # Thử gỡ Admin trên Zalo
        zalo_msg = ""
        try:
            bot.removeGroupAdmins(target_uid, thread_id)
            zalo_msg = "\n🥈 [Zalo] Đã gỡ quyền Phó nhóm thành công."
        except Exception as e:
            zalo_msg = f"\n⚠️ [Zalo] Không thể gỡ quyền Phó nhóm trên hệ thống Zalo (Chi tiết: {e})."

        silver_list.remove(target_uid)
        group_key["silver"] = silver_list
        settings["group_keys"] = group_keys
        write_settings(bot.uid, settings)
        response_text = f"🥈 Đã thu hồi Key Bạc của {target_name} ({target_uid}) thành công!{zalo_msg}"

    mention = None
    if target_name != "Unknown User":
        offset = response_text.find(target_name)
        length = len(target_name)
        mention = Mention(uid=target_uid, length=length, offset=offset)

    bot.replyMessage(Message(text=response_text, mention=mention), message_object, thread_id, thread_type)

def listkey_cmd(bot, message_object, thread_id, thread_type, author_id, message_text):
    if thread_type != ThreadType.GROUP:
        bot.replyMessage(
            Message(text="❌ Lệnh này chỉ sử dụng được trong nhóm chat!"),
            message_object, thread_id, thread_type
        )
        return

    settings = read_settings(bot.uid)
    group_keys = settings.get("group_keys", {})
    group_key = group_keys.get(thread_id, {})
    
    gold_holder = get_gold_key_holder(bot, thread_id, settings)
    silver_list = group_key.get("silver", [])
    
    response = "🔑 DANH SÁCH KEY CỦA NHÓM\n\n"
    
    if gold_holder:
        gold_name = get_user_name_by_id(bot, gold_holder)
        response += f"👑 Key Vàng (Admin nhóm):\n➜ {gold_name} ({gold_holder})\n\n"
    else:
        response += "👑 Key Vàng (Admin nhóm):\n➜ Chưa thiết lập (Mặc định là Trưởng nhóm)\n\n"
        
    response += "🥈 Danh sách Key Bạc:\n"
    if silver_list:
        for idx, uid in enumerate(silver_list, start=1):
            name = get_user_name_by_id(bot, uid)
            response += f"{idx}. {name} ({uid})\n"
    else:
        response += "➜ Trống"
        
    bot.replyMessage(Message(text=response), message_object, thread_id, thread_type)

def duyetmedia_cmd(bot, message_object, thread_id, thread_type, author_id, message_text):
    if not is_admin(bot, author_id):
        bot.replyMessage(
            Message(text="❌ Bạn không có quyền sử dụng lệnh này (Chỉ dành cho Admin Bot)."),
            message_object, thread_id, thread_type
        )
        return

    parts = message_text.split()
    if len(parts) < 2:
        bot.replyMessage(
            Message(text="⚠️ Vui lòng nhập trạng thái bật/tắt.\n➜ Cú pháp: !duyetmedia <on/off> hoặc <bat/tat>"),
            message_object, thread_id, thread_type
        )
        return

    action = parts[1].lower()
    settings = read_settings(bot.uid)

    if action in ["on", "bat", "bật"]:
        settings["media_commands_active"] = True
        write_settings(bot.uid, settings)
        bot.replyMessage(
            Message(text="✅ Đã bật tính năng sử dụng các lệnh gửi ảnh/video. Người dùng được duyệt có thể sử dụng bình thường."),
            message_object, thread_id, thread_type
        )
    elif action in ["off", "tat", "tắt"]:
        settings["media_commands_active"] = False
        write_settings(bot.uid, settings)
        bot.replyMessage(
            Message(text="🚫 Đã tắt tính năng sử dụng các lệnh gửi ảnh/video đối với tất cả thành viên (trừ Admin)."),
            message_object, thread_id, thread_type
        )
    else:
        bot.replyMessage(
            Message(text="⚠️ Trạng thái không hợp lệ! Vui lòng chọn 'on' hoặc 'off' (hoặc 'bat' / 'tat')."),
            message_object, thread_id, thread_type
        )

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'duyet': duyet_cmd,
        'unduyet': unduyet_cmd,
        'capkey': capkey_cmd,
        'huykey': huykey_cmd,
        'listkey': listkey_cmd,
        'duyetmedia': duyetmedia_cmd,
        'duyetanh': duyetmedia_cmd
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
