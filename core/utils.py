from zlapi.models import Message, ThreadType

def send_msg(bot, thread_id, thread_type, text, reply_to=None):
    if reply_to:
        bot.replyMessage(Message(text=text), reply_to, thread_id=thread_id, thread_type=thread_type)
    else:
        bot.send(Message(text=text), thread_id=thread_id, thread_type=thread_type)

def send_media(bot, thread_id, thread_type, file_path, type="video"):
    if type == "video":
        bot.sendLocalVideo(file_path, thread_id=thread_id, thread_type=thread_type)
    elif type == "image":
        bot.sendLocalImage(file_path, thread_id=thread_id, thread_type=thread_type)
