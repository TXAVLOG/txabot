from zlapi.models import Message
from modules.utils.image_sender import ImageSender

image_sender = ImageSender()

txa = {
    "name": "Ảnh ngẫu nhiên",
    "desc": "Gửi các thể loại ảnh ngẫu nhiên (girl, cosplay, anime, boy, sexy, nude, v.v.)",
    "author": "TXA",
    "command": ["girl", "zgirl", "cosplay", "anime", "boy", "boy6mui", "girlsexy", "girlnguc", "girlnude", "girllon"]
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    if cmd == 'girl':
        handle_girl_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'zgirl':
        handle_zGirl_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'cosplay':
        handle_cosplay_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'anime':
        handle_anime_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'boy':
        handle_boy_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'boy6mui':
        handle_boy6mui_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'girlsexy':
        handle_girlsexy_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'girlnguc':
        handle_girlnguc_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'girlnude':
        handle_girlnude_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'girllon':
        handle_girllon_command(bot, message_object, thread_id, thread_type, author_id)

def handle_girl_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi ảnh girl"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "girl")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_zGirl_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi ảnh zGirl"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "zGirl")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_cosplay_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi ảnh cosplay"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "cosplay")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_anime_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi ảnh anime"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "anime")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_boy_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi ảnh boy"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "boy")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_boy6mui_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi ảnh boy 6 múi"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "boy6mui")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_girlsexy_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi ảnh girl sexy"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "girlsexy")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_girlnguc_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi ảnh girl ngực"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "girlnguc")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_girlnude_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi ảnh girl nude"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "girlnude")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_girllon_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi ảnh girl lồn"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "girllon")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)
