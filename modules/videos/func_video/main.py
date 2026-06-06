from zlapi.models import Message
from modules.utils.image_sender import ImageSender

image_sender = ImageSender()

txa = {
    "name": "Video ngẫu nhiên",
    "desc": "Gửi các thể loại video ngắn ngẫu nhiên (vdgirl, vdcos, vdanime, vdsexy)",
    "author": "TXA",
    "command": ["vdgirl", "vdcos", "vdanime", "vdsexy"]
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    if cmd == 'vdgirl':
        handle_vdgirl_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'vdcos':
        handle_vdcos_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'vdanime':
        handle_vdanime_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'vdsexy':
        handle_vdsexy_command(bot, message_object, thread_id, thread_type, author_id)

def handle_vdgirl_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi video girl"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "vdgirl")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_vdcos_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi video cosplay"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "vdcos")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_vdanime_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi video anime"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "vdanime")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_vdsexy_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi video sexy"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "vdsexy")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)
