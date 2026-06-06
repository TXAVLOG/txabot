from zlapi.models import Message
import time
import os
import requests

txa = {
    "name": "Uptime",
    "desc": "Xem thời gian hoạt động của bot và nhận ảnh gái xinh ngẫu nhiên",
    "author": "TXA",
    "command": "uptime"
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, client=None):
    handle_uptime_command(bot, message_object, thread_id, thread_type, author_id, client)

def handle_uptime_command(bot, message_object, thread_id, thread_type, author_id, client=None):
    # bot/client is passed as the first argument, depending on how it's called
    active_client = client if client else bot
    
    start_time = getattr(active_client, 'start_time', time.time())
    current_time = time.time()
    uptime_seconds = int(current_time - start_time)

    days = uptime_seconds // (24 * 3600)
    uptime_seconds %= (24 * 3600)
    hours = uptime_seconds // 3600
    uptime_seconds %= 3600
    minutes = uptime_seconds // 60
    seconds = uptime_seconds % 60

    uptime_message = f"Bot đã hoạt động được {days} ngày, {hours} giờ, {minutes} phút, {seconds} giây."
    message_to_send = Message(text=uptime_message)
    
    api_url = 'https://subhatde.id.vn/images/gai'
    image_path = 'temp_uptime_image.jpeg'
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }

        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Get image URL from JSON
        data = response.json()
        image_url = data.get('url')
        
        if image_url:
            # Download image
            image_response = requests.get(image_url, headers=headers, timeout=15)
            image_response.raise_for_status()
            
            with open(image_path, 'wb') as f:
                f.write(image_response.content)
            
            # Send local image
            active_client.sendLocalImage(
                image_path, 
                message=message_to_send,
                thread_id=thread_id,
                thread_type=thread_type
            )
            
            # Remove temp file
            if os.path.exists(image_path):
                os.remove(image_path)
        else:
            active_client.replyMessage(message_to_send, message_object, thread_id, thread_type)
            
    except Exception as e:
        # Fallback to text only on failure
        try:
            active_client.replyMessage(message_to_send, message_object, thread_id, thread_type)
        except Exception as err:
            print(f"Error sending uptime fallback: {err}")
