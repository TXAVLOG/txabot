import requests
from zlapi.models import Message
from modules.utils.image_sender import ImageSender
from core.bot_sys import read_settings, write_settings

image_sender = ImageSender()

txa = {
    "name": "Video ngẫu nhiên",
    "desc": {
        "vdgirl": "Video gái ngẫu nhiên",
        "vdcos": "Video Cosplay ngẫu nhiên",
        "vdanime": "Video Anime ngẫu nhiên",
        "vdsexy": "Video sexy ngẫu nhiên",
        "vdchill": "Video chill ngẫu nhiên",
        "vdgai": "Video gái"
    },
    "author": "TXA",
    "command": ["vdgirl", "vdcos", "vdanime", "vdsexy", "vdchill", "vdgai"]
}

def check_permission(bot, author_id):
    settings = read_settings(bot.uid)
    admin_bot = settings.get("admin_bot", [])
    high_level_admins = settings.get("high_level_admins", [])
    silver_users = settings.get("silver_users", [])
    
    is_super_admin = (author_id == bot.uid) or (author_id in high_level_admins)
    is_admin_bot = is_super_admin or (author_id in admin_bot)
    is_silver = is_admin_bot or (author_id in silver_users)
    return is_silver

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    parts = message_text[len(prefix):].strip().split()
    cmd = parts[0].lower() if parts else ""
    args = parts[1:] if len(parts) > 1 else []
    
    if cmd == 'vdgirl':
        handle_vdgirl_command(bot, message_object, thread_id, thread_type, author_id, args)
    elif cmd == 'vdcos':
        handle_vdcos_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'vdanime':
        handle_vdanime_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'vdsexy':
        handle_vdsexy_command(bot, message_object, thread_id, thread_type, author_id, args)
    elif cmd == 'vdchill':
        handle_vdchill_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'vdgai':
        handle_vdgai_command(bot, message_object, thread_id, thread_type, author_id)

def handle_vdgirl_command(bot, message_object, thread_id, thread_type, author_id, args):
    """Gửi video girl hoặc bật/tắt lệnh"""
    if args and args[0].lower() in ["on", "off"]:
        if not check_permission(bot, author_id):
            bot.replyMessage(Message(text="❌ Bạn không có quyền sử dụng tính năng này! (Yêu cầu S_AD/ADMIN trở lên)"), message_object, thread_id, thread_type)
            return
        
        status = args[0].lower() == "on"
        settings = read_settings(bot.uid)
        
        if "disabled_vdgirl" not in settings:
            settings["disabled_vdgirl"] = {}
            
        settings["disabled_vdgirl"][thread_id] = not status
        write_settings(bot.uid, settings)
        
        status_text = "Bật ✅" if status else "Tắt ❌"
        bot.replyMessage(Message(text=f"🚦 Lệnh {bot.prefix}vdgirl đã được {status_text} trong nhóm này!"), message_object, thread_id, thread_type)
        return

    settings = read_settings(bot.uid)
    disabled_vdgirl = settings.get("disabled_vdgirl", {})
    if disabled_vdgirl.get(thread_id, False):
        bot.replyMessage(Message(text="⚠️ Lệnh vdgirl đã bị tắt trong nhóm này! Vui lòng liên hệ S_AD hoặc ADMIN để bật lại."), message_object, thread_id, thread_type)
        return

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

def handle_vdsexy_command(bot, message_object, thread_id, thread_type, author_id, args):
    """Gửi video sexy hoặc bật/tắt lệnh"""
    if args and args[0].lower() in ["on", "off"]:
        if not check_permission(bot, author_id):
            bot.replyMessage(Message(text="❌ Bạn không có quyền sử dụng tính năng này! (Yêu cầu S_AD/ADMIN trở lên)"), message_object, thread_id, thread_type)
            return
        
        status = args[0].lower() == "on"
        settings = read_settings(bot.uid)
        
        if "disabled_vdsexy" not in settings:
            settings["disabled_vdsexy"] = {}
            
        settings["disabled_vdsexy"][thread_id] = not status
        write_settings(bot.uid, settings)
        
        status_text = "Bật ✅" if status else "Tắt ❌"
        bot.replyMessage(Message(text=f"🚦 Lệnh {bot.prefix}vdsexy đã được {status_text} trong nhóm này!"), message_object, thread_id, thread_type)
        return

    settings = read_settings(bot.uid)
    disabled_vdsexy = settings.get("disabled_vdsexy", {})
    if disabled_vdsexy.get(thread_id, False):
        bot.replyMessage(Message(text="⚠️ Lệnh vdsexy đã bị tắt trong nhóm này! Vui lòng liên hệ S_AD hoặc ADMIN để bật lại."), message_object, thread_id, thread_type)
        return

    api_url = 'https://vdang1.sbs/videos/vdsexy'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        video_url = data.get('url', '')
        if not video_url:
            raise Exception("Không lấy được URL video từ API.")
        
        # Use fallback thumbnail
        thumbnail_url = image_sender.upload_fallback_thumbnail(bot, thread_id, thread_type) or 'https://vdang1.sbs/images/gaisexy'
        duration = '1000'
        
        try:
            author_info = bot.fetchUserInfo(author_id).changed_profiles.get(author_id, {})
            author_name = author_info.get('zaloName', 'User')
            caption = f"[ {author_name} ] Video sexy ngẫu nhiên"
        except Exception:
            caption = "Video sexy ngẫu nhiên"
            
        bot.sendRemoteVideo(
            videoUrl=video_url, 
            thumbnailUrl=thumbnail_url,
            duration=duration,
            message=Message(text=caption),
            thread_id=thread_id,
            thread_type=thread_type,
            width=1080,
            height=1920,
            ttl=180000
        )
    except Exception as e:
        # Fallback to local image_sender if API fails
        error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "vdsexy")
        if error:
            bot.replyMessage(Message(text=f"❌ Lỗi API: {str(e)}\n{error}"), message_object, thread_id, thread_type)

def handle_vdchill_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi video chill"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "vdchill")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)

def handle_vdgai_command(bot, message_object, thread_id, thread_type, author_id):
    """Gửi video gai"""
    error = image_sender.send_image(bot, message_object, thread_id, thread_type, author_id, "vdgai")
    if error:
        bot.replyMessage(Message(text=error), message_object, thread_id, thread_type)
