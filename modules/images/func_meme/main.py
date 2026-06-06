from datetime import datetime
from io import BytesIO
import os
import random
import threading
import requests
from core.bot_sys import is_admin, read_settings, write_settings
from zlapi.models import *
from PIL import Image, ImageDraw, ImageFont

def upload_to_uguu(file_path):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    }

    try:
        with open(file_path, 'rb') as file:
            files = {'files[]': file}
            print(f"➜   Uploading file to Uguu: {file_path}")
            response = requests.post("https://uguu.se/upload", files=files, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"➜   Upload thành công!: {file_path}")
                uploaded_url = result["files"][0]["url"]
                return uploaded_url
            else:
                return None
        else:
            return None
    except Exception as e:
        print(f"➜   Lỗi khi upload file lên Uguu: {e}")
        return None

def download_image(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            file_name = os.path.splitext(os.path.basename(url))[0] + ".png"
            file_path = os.path.join(os.getcwd(), file_name)
            img.save(file_path)
            return file_path
    except Exception as e:
        print(f"➜ Lỗi khi tải ảnh: {e}")
    return None

def convert_to_webp(image_path):
    webp_path = os.path.splitext(image_path)[0] + ".webp"
    image = Image.open(image_path)
    image.save(webp_path, "WEBP")
    return webp_path

def handle_meme_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "meme" not in settings:
        settings["meme"] = {}
    settings["meme"][thread_id] = True
    write_settings(bot.uid, settings)
    return f"🚦Lệnh {bot.prefix}meme đã được Bật 🚀 trong nhóm này ✅"

def handle_meme_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "meme" in settings and thread_id in settings["meme"]:
        settings["meme"][thread_id] = False
        write_settings(bot.uid, settings)
        return f"🚦Lệnh {bot.prefix}meme đã Tắt ⭕️ trong nhóm này ✅"
    return "🚦Nhóm chưa có thông tin cấu hình meme để ⭕️ Tắt 🤗"

def meme(bot, message_object, author_id, thread_id, thread_type, command):
    def meme_command():
        user_name = get_user_name_by_id(bot, author_id)
        try:
            settings = read_settings(bot.uid)
    
            user_message = command.replace(f"{bot.prefix}meme ", "").strip().lower()
            if user_message == "on":
                if not is_admin(bot, author_id):  
                    response = "❌Bạn không phải admin bot!"
                else:
                    response = handle_meme_on(bot, thread_id)
                bot.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
                return
            elif user_message == "off":
                if not is_admin(bot, author_id):  
                    response = "❌Bạn không phải admin bot!"
                else:
                    response = handle_meme_off(bot, thread_id)
                bot.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
                return
            
            if not (settings.get("meme", {}).get(thread_id, False)):
                return
            bot_prefix = f"{bot.prefix}meme"
            parts = command.split()
            response = None  

            if len(parts) == 1:
                response = (
                    "🎉 Chào mừng đến với menu Meme! ⚙️\n"
                    "   ➜ Dùng lệnh 'meme img [nội dung]' để tìm kiếm và gửi ảnh meme.\n"
                    "   ➜ Dùng lệnh 'meme stk [nội dung]' để tạo sticker từ ảnh meme.\n"
                )
            else:
                action = parts[1].lower()

                if action == 'img' or action == 'stk':
                    if len(parts) < 3:
                        response = "➜ Vui lòng cung cấp nội dung tìm kiếm cho meme."
                    else:
                        search_query = " ".join(parts[2:])
                        url = f"https://subhatde.id.vn/pinterest?search={search_query}"
                        res = requests.get(url)
                        if res.status_code == 200:
                            data = res.json()
                            if data["count"] > 0:
                                image_url = random.choice(data["data"])
                                image_path = download_image(image_url)
                                if image_path:
                                    if action == 'img':
                                        bot.sendLocalImage(
                                            image_path, thread_id=thread_id, thread_type=thread_type,
                                            message=Message(text=f"{user_name} đây là ảnh meme của bạn '{search_query}':"), height=1000, width=1000, ttl=1200000
                                        )
                                    elif action == 'stk':
                                        webp_path = convert_to_webp(image_path)
                                        uploaded_url = upload_to_uguu(webp_path)
                                        if uploaded_url:
                                            bot.send_custom_sticker(
                                                staticImgUrl=uploaded_url,
                                                animationImgUrl=uploaded_url,
                                                thread_id=thread_id,
                                                thread_type=thread_type,
                                                reply=message_object,
                                                width=1000,
                                                height=1000,
                                                ttl=100000
                                            )
                                        if os.path.exists(webp_path):
                                            os.remove(webp_path)
                                    if os.path.exists(image_path):
                                        os.remove(image_path)
                                else:
                                    response = "➜ Không thể tải ảnh meme."
                            else:
                                response = "➜ Không tìm thấy ảnh meme nào với nội dung này."
                        else:
                            response = "➜ Đã xảy ra lỗi khi tìm kiếm ảnh meme."
                else:
                    response = f"➜ Lệnh [{bot_prefix} {action}] không được hỗ trợ 🤧"

            if response is not None:
                if len(parts) == 1:
                    temp_image_path = create_menu_image({"response": response}, 1, bot, author_id)
                    bot.sendLocalImage(
                        temp_image_path, thread_id=thread_id, thread_type=thread_type,
                        message=Message(text=response), height=500, width=1280, ttl=1200000
                    )
                    if os.path.exists(temp_image_path):
                        os.remove(temp_image_path)
                else:
                    bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
        except Exception as e:
            print(f"Error: {e}")
            bot.replyMessage(Message(text="➜ 🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type)

    thread = threading.Thread(target=meme_command)
    thread.start()

def create_menu_image(command_names, page, bot, author_id):
    
    avatar_url = None

    if author_id:
        user_info = bot.fetchUserInfo(author_id)
        avatar_url = user_info.changed_profiles.get(author_id).avatar

    start_index = (page - 1) * 10
    end_index = start_index + 10
    current_page_commands = list(command_names.items())[start_index:end_index]

    
    numbered_commands = [f"⭐ {i + start_index + 1}. {name} - {desc}" for i, (name, desc) in enumerate(current_page_commands)]

    
    background_dir = "background"
    background_files = [os.path.join(background_dir, f) for f in os.listdir(background_dir) if f.endswith(('.png', '.jpg'))]
    background_path = random.choice(background_files)
    image = Image.open(background_path).convert("RGBA")
    image = image.resize((1280, 500))

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    rect_x0 = (1280 - 1100) // 2
    rect_y0 = (500 - 300) // 2
    rect_x1 = rect_x0 + 1100
    rect_y1 = rect_y0 + 300

    radius = 50
    draw.rounded_rectangle([rect_x0, rect_y0, rect_x1, rect_y1], radius=radius, fill=(255, 255, 255, 200))
    overlay = Image.alpha_composite(image, overlay)
    if avatar_url:
        try:
            avatar_response = requests.get(avatar_url)
            avatar_image = Image.open(BytesIO(avatar_response.content)).convert("RGBA").resize((100, 100))

            gradient_size = 110
            gradient_colors = create_gradient_colors(7)
            gradient_overlay = Image.new("RGBA", (gradient_size, gradient_size), (0, 0, 0, 0))
            gradient_draw = ImageDraw.Draw(gradient_overlay)

            for i, color in enumerate(gradient_colors):
                radius = gradient_size // 2 - i
                gradient_draw.ellipse(
                    (i, i, gradient_size - i, gradient_size - i),
                    outline=color,
                    width=1
                )

            mask = Image.new("L", avatar_image.size, 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 100, 100), fill=255)
            gradient_overlay.paste(avatar_image, (5, 5), mask)

            overlay.paste(gradient_overlay, (rect_x0 + 20, rect_y0 + 100), gradient_overlay)
        except Exception:
            pass
    

    text_hi = f"Hi {user_info.changed_profiles[author_id].displayName}!" if author_id in user_info.changed_profiles else "Hi Người dùng!"
    text_welcome = f"🎊 Hi, {user_info.changed_profiles[author_id].displayName}, Tôi có thể giúp gì cho bạn?"
    bot_name = getattr(bot, "me_name", get_user_name_by_id(bot, bot.uid))
    bot_version = getattr(bot, "version", "1.0.0")
    bot_update = getattr(bot, "date_update", datetime.now().strftime("%d-%m-%y"))
    text_bot_info = f"🤖 Bot: {bot_name} 💻 version {bot_version} 🗓️ update {bot_update}"
    text_bot_ready = f"♥️ bot sẵn sàng phục vụ bạn iu :3"
    font_paci = "font/arial unicode ms.otf"
    font_emoji = "font/NotoEmoji-Bold.ttf"
    draw = ImageDraw.Draw(overlay)

    font_hi = ImageFont.truetype(font_paci, size=50) if os.path.exists(font_paci) else ImageFont.load_default()
    font_welcome = ImageFont.truetype(font_paci, size=35) if os.path.exists(font_paci) else ImageFont.load_default()
    font_bot_info = ImageFont.truetype(font_emoji, size=25) if os.path.exists(font_emoji) else ImageFont.load_default()

    x_hi = rect_x0 + (1100 - draw.textbbox((0, 0), text_hi, font=font_hi)[2]) // 2

    y_hi = rect_y0 + 10

    gradient_colors_hi = interpolate_colors(create_gradient_colors(5), len(text_hi), 1)
    for i, char in enumerate(text_hi):
        draw.text((x_hi, y_hi), char, font=font_hi, fill=gradient_colors_hi[i])
        try:
            x_hi += font_hi.getlength(char)
        except AttributeError:
            x_hi += draw.textbbox((0, 0), char, font=font_hi)[2]

    x_welcome = (1200 - draw.textbbox((0, 0), text_welcome, font=font_welcome)[2]) // 2
    y_welcome = y_hi + 60

    gradient_colors_welcome = interpolate_colors(create_gradient_colors(5), len(text_welcome), 1)
    for i, char in enumerate(text_welcome):
        draw.text((x_welcome, y_welcome), char, font=font_welcome, fill=gradient_colors_welcome[i])
        try:
            x_welcome += font_welcome.getlength(char)
        except AttributeError:
            x_welcome += draw.textbbox((0, 0), char, font=font_welcome)[2]

    x_bot_info = rect_x0 + (1100 - draw.textbbox((0, 0), text_bot_info, font=font_welcome)[2]) // 2

    y_bot_info = rect_y1 - 60

    gradient_colors_bot_info = interpolate_colors(create_gradient_colors(7), len(text_bot_info), 1)
    current_x = x_bot_info

    for i, char in enumerate(text_bot_info):
        if char in "🤖💻🗓️":
            current_font = font_bot_info
        else:
            current_font = font_welcome

        draw.text((current_x, y_bot_info), char, font=current_font, fill=gradient_colors_bot_info[i])
        try:
            char_width = current_font.getlength(char)
        except AttributeError:
            char_width = draw.textbbox((0, 0), char, font=current_font)[2]
        current_x += char_width

    y_bot_ready = y_bot_info - 80
    gradient_colors_bot_ready = interpolate_colors(create_gradient_colors(5), len(text_bot_ready), 1)
    current_x_bot_ready = (1200 - draw.textbbox((0, 0), text_bot_ready, font=font_welcome)[2]) // 2

    for i, char in enumerate(text_bot_ready):
        if char in "♥️:3🤗🎉":
            current_font = font_bot_info
        else:
            current_font = font_welcome
        draw.text((current_x_bot_ready, y_bot_ready), char, font=current_font, fill=gradient_colors_bot_ready[i])
        try:
            char_width = current_font.getlength(char)
        except AttributeError:
            char_width = draw.textbbox((0, 0), char, font=current_font)[2]
        current_x_bot_ready += char_width

    overlay = Image.alpha_composite(image, overlay)
    temp_image_path = "temp_image.png"
    overlay.save(temp_image_path)

    return temp_image_path

def create_gradient_colors(num_colors):
    return [(random.randint(100, 175), random.randint(100, 180), random.randint(100, 170)) for _ in range(num_colors)]

def interpolate_colors(colors, text_length, change_every):
    gradient = []
    num_segments = len(colors) - 1
    steps_per_segment = (text_length // change_every) + 1
    for i in range(num_segments):
        for j in range(steps_per_segment):
            if len(gradient) < text_length:
                ratio = j / steps_per_segment
                interpolated_color = (
                    int(colors[i][0] * (1 - ratio) + colors[i + 1][0] * ratio),
                    int(colors[i][1] * (1 - ratio) + colors[i + 1][1] * ratio),
                    int(colors[i][2] * (1 - ratio) + colors[i + 1][2] * ratio)
                )
                gradient.append(interpolated_color)
    while len(gradient) < text_length:
        gradient.append(colors[-1])
    return gradient[:text_length]

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        return user_info.zaloName or user_info.displayName
    except Exception as e:
        return "Unknown User"

txa = {
    "name": "pro_meme",
    "desc": "Tạo và gửi meme ngẫu nhiên vào nhóm. Hỗ trợ các loại meme vui nhộn. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['meme']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'meme': meme
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
