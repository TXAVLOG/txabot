from core.bot_sys import admin_cao
from zlapi.models import *

def command__allan_cd(message, message_object, thread_id, thread_type, author_id, client):
    try:
        if not admin_cao(client, author_id):
            return
        parts = message.split(" ", 1)
        if len(parts) < 2:
            return

        tagall_message = parts[1].strip()

        try:
            group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
            members = group_info.get('memVerList', [])
            if not members:
                return
            
            text = f"<b>{tagall_message}</b>"
            mentions = []
            offset = len(text)
            
            for member in members:
                member_parts = member.split('_', 1)
                if len(member_parts) != 2:
                    continue
                user_id, user_name = member_parts
                mention = Mention(uid=user_id, offset=offset, length=len(user_name) + 1, auto_format=False)
                mentions.append(mention)
                offset += len(user_name) + 2

            multi_mention = MultiMention(mentions)

            try:
                styles = MultiMsgStyle([
                    MessageStyle(offset=0, length=len(text), style="color", color="#DB342E", auto_format=False),
                    MessageStyle(offset=0, length=len(text), style="bold", size="15", auto_format=False)
                ])
                client.send(
                    Message(text=text, style=styles, mention=multi_mention, parse_mode="HTML"),
                    thread_id=thread_id,
                    thread_type=ThreadType.GROUP
                )
            except Exception as e:
                print(f"Lỗi khi gửi tin nhắn: {e}")

        except Exception as e:
            print(f"Lỗi: {e}")

    except ZaloAPIException as e:
        print(f"Lỗi API: {e}")
    except Exception as e:
        print(f"Lỗi chung: {e}")

def command_allan_for_link(message, message_object, thread_id, thread_type, author_id, self):
    try:
        if not admin_cao(self, author_id):
            return
        parts = message.split(" ", 2)
        if len(parts) < 3:
            return

        target_thread_id = parts[1].strip()
        tagall_message = parts[2].strip()

        group_info = self.fetchGroupInfo(target_thread_id).gridInfoMap[target_thread_id]
        members = group_info.get('memVerList', [])
        if not members:
            return
        
        text = f"{tagall_message}"
        mentions = []
        offset = len(text)
        
        for member in members:
            member_parts = member.split('_', 1)
            if len(member_parts) != 2:
                continue
            user_id, user_name = member_parts
            mention = Mention(uid=user_id, offset=offset, length=len(user_name) + 1, auto_format=False)
            mentions.append(mention)
            offset += len(user_name) + 2

        multi_mention = MultiMention(mentions)
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(text), style="color", color="#DB342E", auto_format=False),
            MessageStyle(offset=0, length=len(text), style="bold", size="15", auto_format=False)
        ])
        self.send(
            Message(
                text=text,
                style=styles,
                mention=multi_mention
            ),
            target_thread_id,
            thread_type
        )
        
        action = ":-bye"
        self.sendReaction(message_object, action, target_thread_id, thread_type, reactionType=75)

    except Exception as e:
        error_message = Message(text=f"⚠️ Có lỗi xảy ra: {str(e)}")
        self.sendMessage(error_message, thread_id, thread_type)

txa = {
    "name": "pro_allan",
    "desc": "Tự động like, reaction, và tương tác với tin nhắn trong nhóm. Hỗ trợ nhiều loại reaction. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['lmao', 'all']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'lmao': command_allan_for_link,
        'all': command__allan_cd
    }
    
    func = dispatch_map.get(cmd)
    if func:
        import inspect
        sig = inspect.signature(func)
        args_map = {
            'bot': bot,
            'client': bot,
            'message_object': message_object,
            'thread_id': thread_id,
            'thread_type': thread_type,
            'author_id': author_id,
            'message': message_text,
            'message_text': message_text,
            'message_lower': message_text.lower()
        }
        args = []
        for param_name in sig.parameters:
            if param_name in args_map:
                args.append(args_map[param_name])
            else:
                args.append(None)
        func(*args)
