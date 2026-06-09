from zlapi.models import Message
from modules.utils.image_sender import ImageSender
from core.bot_sys import read_settings, write_settings, is_admin

image_sender = ImageSender()

txa = {
    "name": "Ảnh ngẫu nhiên",
    "desc": {
        "girl": "Ảnh gái ngẫu nhiên",
        "zgirl": "Ảnh gái ngẫu nhiên",
        "cosplay": "Ảnh Cosplay ngẫu nhiên",
        "anime": "Ảnh Anime ngẫu nhiên",
        "boy": "Ảnh trai ngẫu nhiên",
        "boy6mui": "Ảnh trai 6 múi",
        "girlsexy": "Ảnh gái sexy",
        "girlnguc": "Ảnh gái ngực khủng",
        "girlnude": "Ảnh gái nude",
        "girllon": "Ảnh gái nhạy cảm"
    },
    "author": "TXA",
    "command": ["girl", "zgirl", "cosplay", "anime", "boy", "boy6mui", "girlsexy", "girlnguc", "girlnude", "girllon"]
}

def is_image_command_enabled(bot, thread_id, command):
    """Check if an image command is enabled for the thread"""
    settings = read_settings(bot.uid)
    disabled_commands = settings.get("disabled_image_commands", {})
    if thread_id in disabled_commands:
        return command not in disabled_commands[thread_id]
    return True

def set_image_command_enabled(bot, thread_id, command, enabled):
    """Enable/disable an image command for the thread"""
    settings = read_settings(bot.uid)
    disabled_commands = settings.get("disabled_image_commands", {})
    if thread_id not in disabled_commands:
        disabled_commands[thread_id] = []
    if enabled:
        if command in disabled_commands[thread_id]:
            disabled_commands[thread_id].remove(command)
    else:
        if command not in disabled_commands[thread_id]:
            disabled_commands[thread_id].append(command)
    settings["disabled_image_commands"] = disabled_commands
    write_settings(bot.uid, settings)

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    parts = message_text[len(prefix):].split()
    if not parts:
        return
    cmd = parts[0].lower()
    
    # Check for on/off subcommand
    if len(parts) >= 2 and parts[1].lower() in ["on", "off"]:
        if not is_admin(bot, author_id):
            bot.replyMessage(Message(text="❌ Bạn không phải admin bot!"), message_object, thread_id, thread_type)
            return
        enabled = parts[1].lower() == "on"
        set_image_command_enabled(bot, thread_id, cmd, enabled)
        status = "bật" if enabled else "tắt"
        bot.replyMessage(Message(text=f"✅ Đã {status} lệnh {prefix}{cmd} cho nhóm này!"), message_object, thread_id, thread_type)
        return
    
    # Check if command is enabled
    if not is_image_command_enabled(bot, thread_id, cmd):
        bot.replyMessage(Message(text=f"❌ Lệnh {prefix}{cmd} đã bị tắt cho nhóm này!"), message_object, thread_id, thread_type)
        return
    
    # Normal command handling
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
    bot.sendReaction(message_object, "Con cặc🍆", thread_id, thread_type)
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "girlnude")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_girllon_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi ảnh girl lồn"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "girllon")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)
