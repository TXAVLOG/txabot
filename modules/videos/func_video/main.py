import requests
from zlapi.models import Message
from modules.utils.image_sender import ImageSender

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
    elif cmd == 'vdchill':
        handle_vdchill_command(bot, message_object, thread_id, thread_type, author_id)
    elif cmd == 'vdgai':
        handle_vdgai_command(bot, message_object, thread_id, thread_type, author_id)

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
        
        thumbnail_url = 'https://vdang1.sbs/images/gaisexy'
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
