# -*- coding: utf-8 -*-
from zlapi.models import Message, MultiMsgStyle, MessageStyle, ThreadType

txa = {
    "name": "callgroup",
    "desc": {
        "callgroup": "Gọi điện nhóm trên Zalo"
    },
    "author": "Light",
    "command": ["callgroup"],
    "t-per": "admin"
}

def style_warning(text):
    lines = text.split('\n')
    first_line = lines[0] if lines else ""
    styles = [MessageStyle(offset=0, length=len(text), style="font", size="0", auto_format=False)]
    if first_line:
        first_line_len = len(first_line) + 1
        styles.append(MessageStyle(offset=0, length=first_line_len, style="color", color="#F7B503", auto_format=False))
        styles.append(MessageStyle(offset=0, length=first_line_len, style="bold", auto_format=False))
    return MultiMsgStyle(styles)

def style_success(text):
    lines = text.split('\n')
    first_line = lines[0] if lines else ""
    styles = [MessageStyle(offset=0, length=len(text), style="font", size="0", auto_format=False)]
    if first_line:
        first_line_len = len(first_line) + 1
        styles.append(MessageStyle(offset=0, length=first_line_len, style="color", color="#15A85F", auto_format=False))
        styles.append(MessageStyle(offset=0, length=first_line_len, style="bold", auto_format=False))
    return MultiMsgStyle(styles)

def style_error(text):
    lines = text.split('\n')
    first_line = lines[0] if lines else ""
    styles = [MessageStyle(offset=0, length=len(text), style="font", size="0", auto_format=False)]
    if first_line:
        first_line_len = len(first_line) + 1
        styles.append(MessageStyle(offset=0, length=first_line_len, style="color", color="#DB342E", auto_format=False))
        styles.append(MessageStyle(offset=0, length=first_line_len, style="bold", auto_format=False))
    return MultiMsgStyle(styles)

def txa_command(client, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(client, "prefix", ".")
    parts = message_text.split()
    
    if len(parts) < 2:
        msg = f"WARNING\n    {prefix}callgroup @user1 @user2\n    {prefix}callgroup <uid1> <uid2>\n    {prefix}callgroup <link> @user"
        client.replyMessage(Message(text=msg, style=style_warning(msg)), message_object, thread_id, thread_type)
        return

    if parts[1].lower() == "all":
        msg = f"WARNING\n    Không thể gọi tất cả thành viên!\n    Vui lòng tag hoặc nhập UID cụ thể.\n    Ví dụ: {prefix}callgroup @user1 @user2"
        client.replyMessage(Message(text=msg, style=style_warning(msg)), message_object, thread_id, thread_type)
        return

    target_group_id = None
    start_idx = 1
    
    if parts[1].startswith("https://zalo.me/g/"):
        try:
            group_info = client.getIDsGroup(parts[1])
            if group_info and 'groupId' in group_info:
                target_group_id = group_info['groupId']
                start_idx = 2
                
                if len(parts) > start_idx and parts[start_idx].lower() == "all":
                    msg = "WARNING\n    Không thể gọi tất cả thành viên!\n    Vui lòng tag hoặc nhập UID cụ thể."
                    client.replyMessage(Message(text=msg, style=style_warning(msg)), message_object, thread_id, thread_type)
                    return
            else:
                msg = "ERROR\n    Link nhóm không hợp lệ!"
                client.replyMessage(Message(text=msg, style=style_error(msg)), message_object, thread_id, thread_type)
                return
        except:
            msg = "ERROR\n    Link nhóm không hợp lệ!"
            client.replyMessage(Message(text=msg, style=style_error(msg)), message_object, thread_id, thread_type)
            return
    else:
        if thread_type != ThreadType.GROUP:
            msg = "ERROR\n    Chỉ dùng trong nhóm hoặc cung cấp link nhóm!"
            client.replyMessage(Message(text=msg, style=style_error(msg)), message_object, thread_id, thread_type)
            return
        target_group_id = thread_id

    uids = []
    if message_object.mentions:
        for mention in message_object.mentions:
            uids.append(mention['uid'])
    else:
        for p in parts[start_idx:]:
            if p.isdigit():
                uids.append(p)

    if not uids:
        msg = f"WARNING\n    {prefix}callgroup @user1 @user2\n    {prefix}callgroup <uid1> <uid2>"
        client.replyMessage(Message(text=msg, style=style_warning(msg)), message_object, thread_id, thread_type)
        return

    if len(uids) > 7:
        msg = "ERROR\n    Chỉ có thể gọi tối đa 7 người cùng lúc!"
        client.replyMessage(Message(text=msg, style=style_error(msg)), message_object, thread_id, thread_type)
        return

    names = []
    for uid in uids:
        try:
            user_info = client.fetchUserInfo(uid)
            profile = user_info.changed_profiles.get(str(uid), {})
            name = profile.get('displayName', uid)
            names.append(name)
        except:
            names.append(uid)

    try:
        loading_msg = "CALL GROUP\n    Đang thực hiện cuộc gọi nhóm..."
        client.replyMessage(Message(text=loading_msg, style=style_success(loading_msg)), message_object, thread_id, thread_type)

        result = client.callGroup(target_group_id, uids)
        
        if result:
            msg = f"SUCCESS\n    Đã gọi {len(uids)} người!"
            client.replyMessage(Message(text=msg, style=style_success(msg)), message_object, thread_id, thread_type)
        else:
            msg = "ERROR\n    Gọi nhóm thất bại!"
            client.replyMessage(Message(text=msg, style=style_error(msg)), message_object, thread_id, thread_type)

    except Exception as e:
        err = str(e).lower()
        if "not found" in err:
            msg = "ERROR\n    Một số UID không hợp lệ!"
        elif "permission" in err:
            msg = "ERROR\n    Bot không có quyền gọi nhóm!"
        else:
            msg = f"ERROR\n    {str(e)[:50]}"
        client.replyMessage(Message(text=msg, style=style_error(msg)), message_object, thread_id, thread_type)
