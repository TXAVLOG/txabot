import colorsys
from datetime import datetime
import glob
import os
import threading

import pytz
from zlapi.models import *
from bs4 import BeautifulSoup
import requests
from core.bot_sys import get_user_name_by_id, is_admin, read_settings, write_settings
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BACKGROUND_PATH = "background/"
CACHE_PATH = "modules/cache/"
OUTPUT_IMAGE_PATH = os.path.join(CACHE_PATH, "phatnguoi.png")

def get_dominant_color(image_path):
    try:
        if not os.path.exists(image_path):
            print(f"File ảnh không tồn tại: {image_path}")
            return (0, 0, 0)

        img = Image.open(image_path).convert("RGB")
        img = img.resize((150, 150), Image.Resampling.LANCZOS)
        pixels = img.getdata()

        if not pixels:
            print(f"Không thể lấy dữ liệu pixel từ ảnh: {image_path}")
            return (0, 0, 0)

        r, g, b = 0, 0, 0
        for pixel in pixels:
            r += pixel[0]
            g += pixel[1]
            b += pixel[2]
        total = len(pixels)
        if total == 0:
            return (0, 0, 0)
        r, g, b = r // total, g // total, b // total
        return (r, g, b)

    except Exception as e:
        print(f"Lỗi khi phân tích màu nổi bật: {e}")
        return (0, 0, 0)

def get_contrasting_color(base_color, alpha=255):
    r, g, b = base_color[:3]
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return (255, 255, 255, alpha) if luminance < 0.5 else (0, 0, 0, alpha)

def random_contrast_color(base_color):
    r, g, b, _ = base_color
    box_luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    
    if box_luminance > 0.5:
        r = random.randint(0, 50)
        g = random.randint(0, 50)
        b = random.randint(0, 50)
    else:
        r = random.randint(200, 255)
        g = random.randint(200, 255)
        b = random.randint(200, 255)
    
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    s = min(1.0, s + 0.9)
    v = min(1.0, v + 0.7)
    
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    
    text_luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    if abs(text_luminance - box_luminance) < 0.3:
        if box_luminance > 0.5:
            r, g, b = colorsys.hsv_to_rgb(h, s, min(1.0, v * 0.4))
        else:
            r, g, b = colorsys.hsv_to_rgb(h, s, min(1.0, v * 1.7))
    
    return (int(r * 255), int(g * 255), int(b * 255), 255)

def download_avatar(avatar_url, save_path=os.path.join(CACHE_PATH, "user_avatar.png")):
    if not avatar_url:
        return None
    try:
        resp = requests.get(avatar_url, stream=True, timeout=5)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            return save_path
    except Exception as e:
        print(f"❌ Lỗi tải avatar: {e}")
    return None

def generate_menu_image(bot, author_id, thread_id, thread_type):
    images = glob.glob(os.path.join(BACKGROUND_PATH, "*.jpg")) + \
             glob.glob(os.path.join(BACKGROUND_PATH, "*.png")) + \
             glob.glob(os.path.join(BACKGROUND_PATH, "*.jpeg"))
    if not images:
        print("❌ Không tìm thấy ảnh trong thư mục background/")
        return None

    image_path = random.choice(images)

    try:
        size = (2000, 700)
        final_size = (1600, 560)
        bg_image = Image.open(image_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=8))
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        dominant_color = get_dominant_color(image_path)
        r, g, b = dominant_color
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

        box_colors = [
            (255, 20, 147, 100),
            (128, 0, 128, 100),
            (0, 100, 0, 100),
            (0, 0, 139, 100),
            (184, 134, 11, 100),
            (138, 3, 3, 100),
            (0, 0, 0, 100)
        ]

        box_color = random.choice(box_colors)

        box_x1, box_y1 = 100, 70
        box_x2, box_y2 = size[0] - 100, size[1] - 70
        draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=80, fill=box_color)

        font_arial_path = "font/arial unicode ms.otf"
        font_emoji_path = "font/NotoEmoji-Bold.ttf"
        
        try:
            font_text_large = ImageFont.truetype(font_arial_path, size=80)
            font_text_big = ImageFont.truetype(font_arial_path, size=72)
            font_text_small = ImageFont.truetype(font_arial_path, size=68)
            font_text_bot = ImageFont.truetype(font_arial_path, size=60)
            font_time = ImageFont.truetype(font_arial_path, size=58)
            font_icon = ImageFont.truetype(font_emoji_path, size=70)
            font_icon_large = ImageFont.truetype(font_emoji_path, size=190)
            font_name = ImageFont.truetype(font_emoji_path, size=70)
        except Exception as e:
            print(f"❌ Lỗi tải font: {e}")
            font_text_large = ImageFont.load_default(size=80)
            font_text_big = ImageFont.load_default(size=72)
            font_text_small = ImageFont.load_default(size=68)
            font_text_bot = ImageFont.load_default(size=60)
            font_time = ImageFont.load_default(size=58)
            font_icon = ImageFont.load_default(size=70)
            font_icon_large = ImageFont.load_default(size=190)
            font_name = ImageFont.load_default(size=70)

        def draw_text_with_shadow(draw, position, text, font, fill, shadow_color=(0, 0, 0, 250), shadow_offset=(3, 3)):
            x, y = position
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_color)
            draw.text((x, y), text, font=font, fill=fill)

        vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        vietnam_now = datetime.now(vietnam_tz)
        hour = vietnam_now.hour
        formatted_time = vietnam_now.strftime("%H:%M")
        time_icon = "🌤️" if 6 <= hour < 18 else "🌙"
        time_text = f" {formatted_time}"
        time_x = box_x2 - 270
        time_y = box_y1 + 15
        
        box_rgb = box_color[:3]
        box_luminance = (0.299 * box_rgb[0] + 0.587 * box_rgb[1] + 0.114 * box_rgb[2]) / 255
        last_lines_color = (255, 255, 255, 230) if box_luminance < 0.5 else (0, 0, 0, 230)

        time_color = last_lines_color

        if time_x >= 0 and time_y >= 0 and time_x < size[0] and time_y < size[1]:
            try:
                icon_x = time_x - 90
                icon_color = random_contrast_color(box_color)
                draw_text_with_shadow(draw, (icon_x, time_y - 10), time_icon, font_icon, icon_color)
                draw.text((time_x, time_y), time_text, font=font_time, fill=time_color)
            except Exception as e:
                print(f"❌ Lỗi vẽ thời gian lên ảnh: {e}")
                draw_text_with_shadow(draw, (time_x - 90, time_y - 10), "⏰", font_icon, (255, 255, 255, 255))
                draw.text((time_x, time_y), " ??;??", font=font_time, fill=time_color)

        user_info = bot.fetchUserInfo(author_id) if author_id else None
        user_name = "Unknown"
        if user_info and hasattr(user_info, 'changed_profiles') and author_id in user_info.changed_profiles:
            user = user_info.changed_profiles[author_id]
            user_name = getattr(user, 'name', None) or getattr(user, 'displayName', None) or f"ID_{author_id}"

        greeting_name = "Chủ Nhân" if is_admin(bot, author_id) else user_name

        emoji_colors = {
            "🎵": random_contrast_color(box_color),
            "😁": random_contrast_color(box_color),
            "🖤": random_contrast_color(box_color),
            "💞": random_contrast_color(box_color),
            "🤖": random_contrast_color(box_color),
            "💻": random_contrast_color(box_color),
            "📅": random_contrast_color(box_color),
            "🎧": random_contrast_color(box_color),
            "🌙": random_contrast_color(box_color),
            "🌤️": (200, 150, 50, 255),
            "🚗": (255, 100, 100, 255),
            "🚀": (100, 200, 255, 255)
        }

        text_lines = [
            f"Hi, {greeting_name}",
            f"💞 Chào mừng đến menu 🚗 phạt nguội",
            f"{bot.prefix}phatnguoi on/off: 🚀 Bật/Tắt tính năng",
            "😁 Bot Sẵn Sàng Phục 🖤",
            f"🤖Bot: {bot.me_name} 💻Version: {bot.version} 📅Update {bot.date_update}"
        ]

        color1 = random_contrast_color(box_color)
        color2 = random_contrast_color(box_color)
        while color1 == color2:
            color2 = random_contrast_color(box_color)
        text_colors = [
            color1,
            color2,
            last_lines_color,
            last_lines_color,
            last_lines_color
        ]

        text_fonts = [
            font_text_large,
            font_text_big,
            font_text_bot,
            font_text_bot,
            font_text_small
        ]

        line_spacing = 95
        start_y = box_y1 + 15

        avatar_url = user_info.changed_profiles[author_id].avatar if user_info and hasattr(user_info, 'changed_profiles') and author_id in user_info.changed_profiles else None
        avatar_path = download_avatar(avatar_url)
        if avatar_path and os.path.exists(avatar_path):
            avatar_size = 220
            try:
                avatar_img = Image.open(avatar_path).convert("RGBA").resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
                border_size = avatar_size + 12
                rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
                draw_border = ImageDraw.Draw(rainbow_border)
                steps = 360
                for i in range(steps):
                    h = i / steps
                    r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
                    draw_border.arc([(0, 0), (border_size-1, border_size-1)], start=i, end=i + (360 / steps), fill=(int(r * 255), int(g * 255), int(b * 255), 255), width=6)
                avatar_y = (box_y1 + box_y2 - avatar_size) // 2
                overlay.paste(rainbow_border, (box_x1 + 50, avatar_y), rainbow_border)
                overlay.paste(avatar_img, (box_x1 + 56, avatar_y + 6), mask)
            except Exception as e:
                print(f"❌ Lỗi xử lý avatar: {e}")
                draw.text((box_x1 + 70, (box_y1 + box_y2) // 2 - 150), "🐳", font=font_icon, fill=(0, 139, 139, 255))
        else:
            draw.text((box_x1 + 70, (box_y1 + box_y2) // 2 - 150), "🐳", font=font_icon, fill=(0, 139, 139, 255))

        current_line_idx = 0
        for i, line in enumerate(text_lines):
            if not line:
                current_line_idx += 1
                continue

            parts = []
            current_part = ""
            for char in line:
                if ord(char) > 0xFFFF:
                    if current_part:
                        parts.append(current_part)
                        current_part = ""
                    parts.append(char)
                else:
                    current_part += char
            if current_part:
                parts.append(current_part)

            total_width = 0
            part_widths = []
            spacing = 8  # Spacing between each part (text or emoji)
            current_font = font_text_bot if i == 4 else text_fonts[i]
            for part in parts:
                font_to_use = font_icon if any(ord(c) > 0xFFFF for c in part) else current_font
                bbox = draw.textbbox((0, 0), part, font=font_to_use)
                width = bbox[2] - bbox[0]
                part_widths.append(width)
                total_width += width
            
            total_width += spacing * (len(parts) - 1)

            max_width = box_x2 - box_x1 - 350
            if total_width > max_width:
                font_size = int(current_font.getbbox("A")[3] * max_width / total_width * 0.9)
                if font_size < 50:
                    font_size = 50
                try:
                    current_font = ImageFont.truetype(font_arial_path, size=font_size) if os.path.exists(font_arial_path) else ImageFont.load_default(size=font_size)
                except Exception as e:
                    print(f"❌ Lỗi điều chỉnh font size: {e}")
                    current_font = ImageFont.load_default(size=font_size)
                total_width = 0
                part_widths = []
                for part in parts:
                    font_to_use = font_icon if any(ord(c) > 0xFFFF for c in part) else current_font
                    bbox = draw.textbbox((0, 0), part, font=font_to_use)
                    width = bbox[2] - bbox[0]
                    part_widths.append(width)
                    total_width += width
                total_width += spacing * (len(parts) - 1)

            text_x = (box_x1 + box_x2 - total_width) // 2
            text_y = start_y + current_line_idx * line_spacing + (current_font.getbbox("A")[3] // 2)

            current_x = text_x
            for idx, (part, width) in enumerate(zip(parts, part_widths)):
                if any(ord(c) > 0xFFFF for c in part):
                    emoji_color = emoji_colors.get(part, random_contrast_color(box_color))
                    draw_text_with_shadow(draw, (current_x, text_y), part, font_icon, emoji_color)
                    if part == "🤖" and i == 4:
                        draw_text_with_shadow(draw, (current_x, text_y - 5), part, font_icon, emoji_color)
                else:
                    if i < 2:
                        draw_text_with_shadow(draw, (current_x, text_y), part, current_font, text_colors[i])
                    else:
                        draw.text((current_x, text_y), part, font=current_font, fill=text_colors[i])
                
                if idx != len(parts) - 1:
                    current_x += width + spacing
                else:
                    current_x += width
            current_line_idx += 1

        right_icons = ["🚗"]
        right_icon = random.choice(right_icons)
        icon_right_x = box_x2 - 250
        icon_right_y = (box_y1 + box_y2 - 200) // 2
        draw_text_with_shadow(draw, (icon_right_x, icon_right_y), right_icon, font_icon_large, emoji_colors.get(right_icon, (80, 80, 80, 255)))

        final_image = Image.alpha_composite(bg_image, overlay)
        final_image = final_image.resize(final_size, Image.Resampling.LANCZOS)
        os.makedirs(os.path.dirname(OUTPUT_IMAGE_PATH), exist_ok=True)
        final_image.save(OUTPUT_IMAGE_PATH, "PNG", quality=95)
        print(f"✅ Ảnh menu đã được lưu: {OUTPUT_IMAGE_PATH}")
        return OUTPUT_IMAGE_PATH

    except Exception as e:
        print(f"❌ Lỗi xử lý ảnh menu: {e}")
        import traceback
        print(traceback.format_exc())
        return None

VEHICLE_TYPES = {
    "1": "ô tô",
    "2": "xe tải",
    "3": "xe máy",
    "4": "xe máy điện"
}

def detect_vehicle_type(plate_number):
    """Tự động nhận dạng loại xe theo quy tắc biển số Việt Nam
    
    Trả về danh sách loại xe theo thứ tự ưu tiên (thấy có khả năng nhất trước)
    """
    import re
    # Làm sạch biển số: bỏ tất cả ký tự không phải chữ và số (-, ., space, ...)
    cleaned = re.sub(r"[^A-Za-z0-9À-ỹĐđ]", "", plate_number.upper())
    
    # Ưu tiên xe máy điện nếu có chữ Đ hoặc E
    if any(c in cleaned for c in ["Đ", "E"]):
        return ["4", "3", "1", "2"]
    
    # Kiểm tra độ dài và mẫu regex
    length = len(cleaned)
    # Mẫu regex: 2 chữ cái đầu
    has_two_letters = bool(re.match(r"^[A-ZĐ]{2}", cleaned))
    has_one_letter = bool(re.match(r"^[A-ZĐ]{1}", cleaned))
    
    if length == 7 or length == 8:
        if has_two_letters:
            # Ô tô (thường 7-8 ký tự: 2 chữ + 5-6 số)
            return ["1", "2", "3", "4"]
        else:
            return ["3", "4", "1", "2"]
    elif length == 5 or length == 6:
        if has_two_letters or has_one_letter:
            # Xe máy (thường 5-6 ký tự: 1-2 chữ + 4-5 số)
            return ["3", "4", "1", "2"]
        else:
            return ["3", "4", "1", "2"]
    else:
        # Mặc định thử tất cả
        return ["1", "2", "3", "4"]

def handle_phatnguoi_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "phatnguoi" not in settings:
        settings["phatnguoi"] = {}
    settings["phatnguoi"][thread_id] = True
    write_settings(bot.uid, settings)
    return f"🚦Lệnh {bot.prefix}phatnguoi đã được Bật 🚀 trong nhóm này ✅"

def handle_phatnguoi_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "phatnguoi" in settings and thread_id in settings["phatnguoi"]:
        settings["phatnguoi"][thread_id] = False
        write_settings(bot.uid, settings)
        return f"🚦Lệnh {bot.prefix}phatnguoi đã Tắt ⭕️ trong nhóm này ✅"
    return "🚦Nhóm chưa có thông tin cấu hình phatnguoi để ⭕️ Tắt 🤗"

def phatnguoi(bot, message_object, author_id, thread_id, thread_type, command):
    settings = read_settings(bot.uid)
    cmd_text = command or ""
    
    # Parse command word to support dynamic prefix/command length
    words = cmd_text.strip().split()
    if not words:
        return False
    cmd_word = words[0]
    user_message = cmd_text[len(cmd_word):].strip().lower()
    
    if user_message == "on":
        if not is_admin(bot, author_id):  
            response = "❌Bạn không phải admin bot!"
        else:
            response = handle_phatnguoi_on(bot, thread_id)
        bot.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        return "no_reaction"
    elif user_message == "off":
        if not is_admin(bot, author_id):  
            response = "❌Bạn không phải admin bot!"
        else:
            response = handle_phatnguoi_off(bot, thread_id)
        bot.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        return "no_reaction"
        
    if not (settings.get("phatnguoi", {}).get(thread_id, False)):
        return False
        
    parts = cmd_text.split()
    user_name = get_user_name_by_id(bot, author_id)
    bot_prefix = cmd_word
    
    if len(parts) < 2:
        response = (
            f"🚦{user_name}  ⚙️\n"
            f"➜ {bot_prefix} [biển số xe]: Tra cứu thông tin phạt nguội.\n"
            "📌 Bot sẽ tự nhận diện loại xe (ô tô, xe tải, xe máy, xe máy điện).\n"
            f"VD: {bot_prefix} 60K-36752\n"
            "🤖 BOT luôn sẵn sàng phục vụ bạn! 🌸"
        )
        os.makedirs(CACHE_PATH, exist_ok=True)
        image_path = generate_menu_image(bot, author_id, thread_id, thread_type)
        if not image_path:
            bot.sendMessage("❌ Không thể tạo ảnh menu!", thread_id, thread_type)
            return "no_reaction"

        reaction = [
            "❌", "🤧", "🐞", "😊", "🔥", "👍", "💖", "🚀",
            "😍", "😂", "😢", "😎", "🙌", "💪", "🌟", "🍀",
            "🎉", "🦁", "🌈", "🍎", "⚡", "🔔", "🎸", "🍕",
            "🏆", "📚", "🦋", "🌍", "⛄", "🎁", "💡", "🐾",
            "😺", "🐶", "🐳", "🦄", "🌸", "🍉", "🍔", "🎄",
            "🎃", "👻", "☃️", "🌴", "🏀", "⚽", "🎾", "🏈",
            "🚗", "✈️", "🚢", "🌙", "☀️", "⭐", "⛅", "☔",
            "⌛", "⏰", "💎", "💸", "📷", "🎥", "🎤", "🎧",
            "🍫", "🍰", "🍩", "☕", "🍵", "🍷", "🍹", "🥐",
            "🐘", "🦒", "🐍", "🦜", "🐢", "🦀", "🐙", "🦈",
            "🍓", "🍋", "🍑", "🥥", "🥐", "🥪", "🍝", "🍣",
            "🎲", "🎯", "🎱", "🎮", "🎰", "🧩", "🧸", "🎡",
            "🏰", "🗽", "🗼", "🏔️", "🏝️", "🏜️", "🌋", "⛲",
            "📱", "💻", "🖥️", "🖨️", "⌨️", "🖱️", "📡", "🔋",
            "🔍", "🔎", "🔑", "🔒", "🔓", "📩", "📬", "📮",
            "💢", "💥", "💫", "💦", "💤", "🚬", "💣", "🔫",
            "🩺", "💉", "🩹", "🧬", "🔬", "🔭", "🧪", "🧫",
            "🧳", "🎒", "👓", "🕶️", "👔", "👗", "👠", "🧢",
            "🦷", "🦴", "👀", "👅", "👄", "👶", "👩", "👨",
            "🚶", "🏃", "💃", "🕺", "🧘", "🏄", "🏊", "🚴",
            "🍄", "🌾", "🌻", "🌵", "🌿", "🍂", "🍁", "🌊",
            "🛠️", "🔧", "🔨", "⚙️", "🪚", "🪓", "🧰", "⚖️",
            "🧲", "🪞", "🪑", "🛋️", "🛏️", "🪟", "🚪", "🧹"
        ]
        
        if random.random() > 0.3:
            bot.sendReaction(message_object, random.choice(reaction), thread_id, thread_type)
        bot.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
        bot.sendLocalImage(
            imagePath=image_path,
            message=Message(text=response, mention=Mention(author_id, length=len(f"{get_user_name_by_id(bot, author_id)}"), offset=0)),
            thread_id=thread_id,
            thread_type=thread_type,
            width=1600,
            height=560,
            ttl=240000
        )
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"❌ Lỗi khi xóa ảnh: {e}")
        return "no_reaction"

    def send_phatnguoi_response():
        try:
            plate_number = parts[1].upper()
            # Danh sách các URL để thử theo thứ tự ưu tiên
            urls = [
                "https://phatnguoixe.com/1026",
                "https://phatnguoixe.com"
            ]
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            }

            found_vehicle = None
            violations = []
            
            # Tự động nhận dạng loại xe theo biển số (thứ tự ưu tiên)
            detected_vehicle_order = detect_vehicle_type(plate_number)
            
            # Thử từng URL trong danh sách
            for url in urls:
                if found_vehicle:
                    break
                # Thử loại xe theo thứ tự ưu tiên đã nhận dạng
                for vehicle_code in detected_vehicle_order:
                    vehicle_name = VEHICLE_TYPES[vehicle_code]
                    data = {"BienSo": plate_number, "LoaiXe": vehicle_code}
                    try:
                        response = requests.post(url, data=data, headers=headers, allow_redirects=True, timeout=15)

                        if response.status_code != 200:
                            print(f"⚠️ Lỗi HTTP {response.status_code} khi truy cập URL: {url}")
                            continue

                        response.encoding = "utf-8"
                        soup = BeautifulSoup(response.text, "html.parser")

                        # Kiểm tra các thông báo không có vi phạm
                        no_violation_messages = [
                            soup.find("h3", string="Không tìm thấy vi phạm phạt nguội!"),
                            soup.find("h3", text="Không tìm thấy vi phạm phạt nguội!"),
                            soup.find(string=lambda text: text and "Không tìm thấy" in text)
                        ]
                        
                        if any(no_violation_messages):
                            continue

                        found_vehicle = vehicle_name
                        tables = soup.find_all("table", class_="css_table")
                        for table in tables:
                            violation_info = {}
                            rows = table.find_all("tr")
                            for row in rows:
                                cells = row.find_all("td")
                                if len(cells) == 2:
                                    key = cells[0].text.strip()
                                    value = cells[1].text.strip()
                                    violation_info[key] = value

                            resolution_places = [row.text.strip() for row in table.find_all("td", colspan="2")]
                            if resolution_places:
                                violation_info["Nơi giải quyết vụ việc"] = " | ".join(resolution_places)

                            if violation_info:
                                violations.append(violation_info)
                        if violations:
                            break
                    except requests.exceptions.RequestException as e:
                        print(f"❌ Lỗi khi gửi yêu cầu đến {url}: {e}")
                        continue

            if found_vehicle and violations:
                for idx, violation in enumerate(violations, 1):
                    violation_details = "\n".join([f"{key}: {value}" for key, value in violation.items()])
                    bot.replyMessage(
                        Message(text=f"🔹 Vi phạm {idx}:\n{violation_details}"),
                        message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
                    )
            elif not found_vehicle:
                bot.replyMessage(
                    Message(text=f"✅ {user_name}, không tìm thấy vi phạm nào cho biển số {plate_number}."),
                    message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
                )
            else:
                bot.replyMessage(
                    Message(text=f"✅ {user_name}, không tìm thấy vi phạm nào cho biển số {plate_number} ({found_vehicle})."),
                    message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
                )

        except Exception as e:
            print(f"Error: {e}")
            bot.replyMessage(
                Message(text="➜ 🐞 Đã xảy ra lỗi gì đó 🤧"),
                message_object, thread_id=thread_id, thread_type=thread_type
            )
        finally:
            try:
                bot.sendReaction(message_object, "/-remove", thread_id, thread_type, reactionType=-1)
            except Exception as e:
                print(f"Lỗi khi xóa reaction phạt nguội: {e}")

    thread = threading.Thread(target=send_phatnguoi_response)
    thread.start()
    return "no_reaction"

txa = {
    "name": "pro_phatnguoi",
    "desc": "Kiểm tra phạt nguội theo biển số xe. Hỗ trợ tra cứu vi phạm giao thông và gửi kết quả vào nhóm. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['phatnguoi']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'phatnguoi': phatnguoi
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
            'message_lower': message_text.lower(),
            'command': message_text,
        }
        args = []
        for param_name in sig.parameters:
            if param_name in args_map:
                args.append(args_map[param_name])
            else:
                args.append(None)
        return func(*args)
