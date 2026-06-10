import colorsys
from datetime import datetime
import glob
import json
import os
import random
from threading import Thread
import time
import pytz
import requests
from zlapi.models import *
from core.bot_sys import is_admin, read_settings, write_settings
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO

BACKGROUND_PATH = "background/"
CACHE_PATH = "modules/cache/"
OUTPUT_IMAGE_PATH = os.path.join(CACHE_PATH, "or.png")

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
        size = (1920, 600)
        final_size = (1280, 380)
        bg_image = Image.open(image_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=7))
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        dominant_color = get_dominant_color(image_path)
        r, g, b = dominant_color
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

        box_colors = [
            (255, 20, 147, 90),
            (128, 0, 128, 90),
            (0, 100, 0, 90),
            (0, 0, 139, 90),
            (184, 134, 11, 90),
            (138, 3, 3, 90),
            (0, 0, 0, 90)
        ]

        box_color = random.choice(box_colors)

        box_x1, box_y1 = 90, 60
        box_x2, box_y2 = size[0] - 90, size[1] - 60
        draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=75, fill=box_color)

        font_arial_path = "font/arial unicode ms.otf"
        font_emoji_path = "font/NotoEmoji-Bold.ttf"
        
        try:
            font_text_large = ImageFont.truetype(font_arial_path, size=76)
            font_text_big = ImageFont.truetype(font_arial_path, size=68)
            font_text_small = ImageFont.truetype(font_arial_path, size=64)
            font_text_bot = ImageFont.truetype(font_arial_path, size=58)
            font_time = ImageFont.truetype(font_arial_path, size=56)
            font_icon = ImageFont.truetype(font_emoji_path, size=60)
            font_icon_large = ImageFont.truetype(font_emoji_path, size=175)
            font_name = ImageFont.truetype(font_emoji_path, size=60)
        except Exception as e:
            print(f"❌ Lỗi tải font: {e}")
            font_text_large = ImageFont.load_default(size=76)
            font_text_big = ImageFont.load_default(size=68)
            font_text_small = ImageFont.load_default(size=64)
            font_text_bot = ImageFont.load_default(size=58)
            font_time = ImageFont.load_default(size=56)
            font_icon = ImageFont.load_default(size=60)
            font_icon_large = ImageFont.load_default(size=175)
            font_name = ImageFont.load_default(size=60)

        def draw_text_with_shadow(draw, position, text, font, fill, shadow_color=(0, 0, 0, 250), shadow_offset=(2, 2)):
            x, y = position
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_color)
            draw.text((x, y), text, font=font, fill=fill)

        vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        vietnam_now = datetime.now(vietnam_tz)
        hour = vietnam_now.hour
        formatted_time = vietnam_now.strftime("%H:%M")
        time_icon = "🌤️" if 6 <= hour < 18 else "🌙"
        time_text = f" {formatted_time}"
        time_x = box_x2 - 250
        time_y = box_y1 + 10
        
        box_rgb = box_color[:3]
        box_luminance = (0.299 * box_rgb[0] + 0.587 * box_rgb[1] + 0.114 * box_rgb[2]) / 255
        last_lines_color = (255, 255, 255, 220) if box_luminance < 0.5 else (0, 0, 0, 220)

        time_color = last_lines_color

        if time_x >= 0 and time_y >= 0 and time_x < size[0] and time_y < size[1]:
            try:
                icon_x = time_x - 75
                icon_color = random_contrast_color(box_color)
                draw_text_with_shadow(draw, (icon_x, time_y - 8), time_icon, font_icon, icon_color)
                draw.text((time_x, time_y), time_text, font=font_time, fill=time_color)
            except Exception as e:
                print(f"❌ Lỗi vẽ thời gian lên ảnh: {e}")
                draw_text_with_shadow(draw, (time_x - 75, time_y - 8), "⏰", font_icon, (255, 255, 255, 255))
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
            "🌤️": (200, 150, 50, 255)
        }

        text_lines = [
            f"Hi, {greeting_name}",
            f"💞 Menu Đuổi Hình Bắt Chữ 🆎",
            f"{bot.prefix}dhbc on/off: 🚀 Bật/Tắt tính năng",
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

        line_spacing = 85
        start_y = box_y1 + 10

        avatar_url = user_info.changed_profiles[author_id].avatar if user_info and hasattr(user_info, 'changed_profiles') and author_id in user_info.changed_profiles else None
        avatar_path = download_avatar(avatar_url)
        if avatar_path and os.path.exists(avatar_path):
            avatar_size = 200
            try:
                avatar_img = Image.open(avatar_path).convert("RGBA").resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
                border_size = avatar_size + 10
                rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
                draw_border = ImageDraw.Draw(rainbow_border)
                steps = 360
                for i in range(steps):
                    h = i / steps
                    r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
                    draw_border.arc([(0, 0), (border_size-1, border_size-1)], start=i, end=i + (360 / steps), fill=(int(r * 255), int(g * 255), int(b * 255), 255), width=5)
                avatar_y = (box_y1 + box_y2 - avatar_size) // 2
                overlay.paste(rainbow_border, (box_x1 + 40, avatar_y), rainbow_border)
                overlay.paste(avatar_img, (box_x1 + 45, avatar_y + 5), mask)
            except Exception as e:
                print(f"❌ Lỗi xử lý avatar: {e}")
                draw.text((box_x1 + 60, (box_y1 + box_y2) // 2 - 140), "🐳", font=font_icon, fill=(0, 139, 139, 255))
        else:
            draw.text((box_x1 + 60, (box_y1 + box_y2) // 2 - 140), "🐳", font=font_icon, fill=(0, 139, 139, 255))

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
            current_font = font_text_bot if i == 4 else text_fonts[i]
            for part in parts:
                font_to_use = font_icon if any(ord(c) > 0xFFFF for c in part) else current_font
                width = draw.textbbox((0, 0), part, font=font_to_use)[2]
                part_widths.append(width)
                total_width += width

            max_width = box_x2 - box_x1 - 300
            if total_width > max_width:
                font_size = int(current_font.getbbox("A")[3] * max_width / total_width * 0.9)
                if font_size < 60:
                    font_size = 60
                try:
                    current_font = ImageFont.truetype(font_arial_path, size=font_size) if os.path.exists(font_arial_path) else ImageFont.load_default(size=font_size)
                except Exception as e:
                    print(f"❌ Lỗi điều chỉnh font size: {e}")
                    current_font = ImageFont.load_default(size=font_size)
                total_width = 0
                part_widths = []
                for part in parts:
                    font_to_use = font_icon if any(ord(c) > 0xFFFF for c in part) else current_font
                    width = draw.textbbox((0, 0), part, font=font_to_use)[2]
                    part_widths.append(width)
                    total_width += width

            text_x = (box_x1 + box_x2 - total_width) // 2
            text_y = start_y + current_line_idx * line_spacing + (current_font.getbbox("A")[3] // 2)

            current_x = text_x
            for part, width in zip(parts, part_widths):
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
                current_x += width
            current_line_idx += 1

        right_icons = ["🆎", "🎯", "💞"]
        right_icon = random.choice(right_icons)
        icon_right_x = box_x2 - 225
        icon_right_y = (box_y1 + box_y2 - 180) // 2
        draw_text_with_shadow(draw, (icon_right_x, icon_right_y), right_icon, font_icon_large, emoji_colors.get(right_icon, (80, 80, 80, 255)))

        final_image = Image.alpha_composite(bg_image, overlay)
        final_image = final_image.resize(final_size, Image.Resampling.LANCZOS)
        os.makedirs(os.path.dirname(OUTPUT_IMAGE_PATH), exist_ok=True)
        final_image.save(OUTPUT_IMAGE_PATH, "PNG", quality=95)
        print(f"✅ Ảnh menu đã được lưu: {OUTPUT_IMAGE_PATH}")
        return OUTPUT_IMAGE_PATH

    except Exception as e:
        print(f"❌ Lỗi xử lý ảnh menu: {e}")
        return None

timeLimit = 60  # 60 seconds timeout

game_sessions = {}

attendance_file = 'modules/game/dhbc/attendance.json'
economy_file = 'modules/game/dhbc/economy.json'

Vietnamese_chars = ['a', 'ă', 'â', 'b', 'c', 'd', 'đ', 'e', 'ê', 'g', 'h', 'i', 'k', 'l', 'm', 'n', 'o', 'ô', 'ơ', 'p', 'q', 'r', 's', 't', 'u', 'ư', 'v', 'x', 'y']

def read_json(file):
    try:
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"[WARNING] File không tồn tại: {file}")
            return {}
    except json.JSONDecodeError as e:
        print(f"[ERROR] Lỗi khi đọc file JSON: {file}, Chi tiết: {e}")
        return {}
    
def write_json(file, data):
    try:
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Lỗi khi ghi dữ liệu vào file {file}: {e}")

def get_coins(user_id):
    economy = read_json(economy_file)
    return economy.get(str(user_id), 0)

def add_coins(user_id, amount):
    economy = read_json(economy_file)
    economy[str(user_id)] = economy.get(str(user_id), 0) + amount
    write_json(economy_file, economy)
    return economy[str(user_id)]

def save_score(user_id, score):
    leaderboard = read_json('modules/game/dhbc/scoreboard.json')
    leaderboard[user_id] = leaderboard.get(user_id, 0) + score
    write_json('modules/game/dhbc/scoreboard.json', leaderboard)

def generate_scrambled_letters(answer):
    answer_chars = list(answer.lower())
    num_random = 14 - len(answer_chars)
    random_chars = random.choices(Vietnamese_chars, k=num_random)
    all_chars = answer_chars + random_chars
    random.shuffle(all_chars)
    return ' '.join(all_chars)

def handle_attendance(user_id, client, thread_id, thread_type):
    today = datetime.today().strftime('%Y-%m-%d')
    attendance_data = read_json(attendance_file)
    
    # Kiểm tra nếu người chơi đã điểm danh hôm nay chưa
    if str(user_id) in attendance_data and attendance_data[str(user_id)] == today:
        client.sendMessage(
            Message(text="⚠️ Bạn đã điểm danh hôm nay rồi. Bạn chỉ có thể điểm danh một lần trong ngày."),
            thread_id=thread_id,
            thread_type=thread_type,
        )
        return
    attendance_data[str(user_id)] = today
    write_json(attendance_file, attendance_data)
    save_score(user_id, 100)
    add_coins(user_id, 50)  # Give 50 coins for daily attendance
    client.sendMessage(
        Message(text="🎉 Chúc mừng bạn đã điểm danh thành công và nhận 100 điểm + 50 coins!"),
        thread_id=thread_id,
        thread_type=thread_type,
    )
def get_current_top_and_score(user_id):
    leaderboard = read_json('modules/game/dhbc/scoreboard.json')
    user_score = leaderboard.get(str(user_id), 0)
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)
    position = next((i + 1 for i, (uid, _) in enumerate(sorted_leaderboard) if uid == str(user_id)), None)
    return position, user_score
def get_image_dimensions(url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        image.verify()
        return image.size
    except requests.exceptions.RequestException as req_error:
        return None
    except Exception as e:
        return None

asked_questions = set()
reaction_threads = {}

def send_countdown_and_check_timeout(thread_id, thread_type, question_msg_id, client, correct_answer):
    try:
        # Send 30 ⏳ reactions to the question message
        reactions_to_send = ['⏳'] * 30
        for reaction in reactions_to_send:
            client.sendReaction(question_msg_id, reaction, thread_id, thread_type)
            time.sleep(0.05)
        
        # Remove one reaction every second
        for i in range(30):
            time.sleep(1)
            # Try to remove a reaction if API supports it, otherwise just continue
            # Since we don't have a removeReaction function, we'll skip this part, but leave a placeholder
            pass
            
        # Wait remaining time (since timeLimit is 60s and we spent 30s removing reactions)
        remaining_time = max(0, timeLimit - 30)
        time.sleep(remaining_time)
        
        # Check if question is still active (not answered yet)
        if thread_id in game_sessions and question_msg_id in game_sessions[thread_id]:
            # Time's up! Reveal answer and clean up
            client.sendMessage(
                Message(text=f"⏰ Hết thời gian! Đáp án là: {correct_answer}"),
                thread_id=thread_id,
                thread_type=thread_type
            )
            # Try to delete the question message if API supports it
            try:
                # Assuming there's a deleteMessage function, otherwise skip
                if hasattr(client, 'deleteMessage'):
                    client.deleteMessage(question_msg_id, thread_id, thread_type)
            except:
                pass
                
            del game_sessions[thread_id][question_msg_id]
            if not game_sessions[thread_id]:
                del game_sessions[thread_id]
                
    except Exception as e:
        print(f"[ERROR] Lỗi xử lý countdown: {e}")

def send_next_question(thread_id, thread_type, client):
    try:
        if thread_id in game_sessions:
            session = game_sessions[thread_id]
            for msg_id, data in session.items():
                if time.time() - data['timestamp'] > timeLimit:
                    del game_sessions[thread_id][msg_id]
                    client.sendMessage(
                        Message(text="⏰ Bạn đã hết thời gian trả lời câu hỏi cũ. Câu hỏi mới sẽ được gửi."),
                        thread_id=thread_id,
                        thread_type=thread_type,
                    )
                    break  
            if game_sessions[thread_id]:
                client.sendMessage(
                    Message(text="⚠️ Bạn vẫn còn một câu hỏi chưa trả lời. Hãy trả lời câu hỏi đó trước khi bắt đầu câu hỏi mới."),
                    thread_id=thread_id,
                    thread_type=thread_type,
                )
                return

        data = read_json('modules/game/dhbc/data.json')
        if not data or 'doanhinh' not in data or not data['doanhinh']:
            raise ValueError("Dữ liệu câu hỏi không hợp lệ hoặc trống.")

        available_questions = [
            question for question in data['doanhinh']
            if question['tukhoa'] not in asked_questions and 'link' in question
        ]
        if not available_questions:
            client.sendMessage(
                Message(text="❌ Không còn câu hỏi mới nào. Vui lòng nạp thêm câu hỏi!"),
                thread_id=thread_id,
                thread_type=thread_type,
            )
            return

        question = random.choice(available_questions)
        asked_questions.add(question['tukhoa'])

        headers = {'User-Agent': 'Mozilla/5.0'}
        os.makedirs('modules/game/dhbc/cache', exist_ok=True)
        image_path = 'modules/game/dhbc/cache/next_question.png'
        print(f"[DEBUG] Đang tải ảnh từ: {question['link']}")
        image_response = requests.get(question['link'], headers=headers, timeout=10)
        image_response.raise_for_status()
        with open(image_path, 'wb') as f:
            f.write(image_response.content)

        width, height = get_image_dimensions(question['link'], headers)
        if not width or not height:
            raise ValueError("Kích thước ảnh không xác định.")

        scrambled_letters = generate_scrambled_letters(question['tukhoa'])
        hint = f"Từ này có {question['sokitu']} ký tự.\n"
        hint += f"🔤 Chữ cái trộn: {scrambled_letters}"

        message_to_send = Message(
            text=f"Vui lòng trả lời câu hỏi dưới đây\n{hint}\n⏰ Bạn có {timeLimit}s để trả lời!\n💡 Gõ \"{client.prefix}dhbc hint\" để dùng 20 coins để mở gợi ý chữ cái đầu!"
        )
        sent_message = client.sendLocalImage(
            image_path,
            message=message_to_send,
            thread_id=thread_id,
            thread_type=thread_type,
            width=width,
            height=height,
        )
        print(f"[DEBUG] Tin nhắn đã được gửi: {sent_message}")

        game_sessions[thread_id] = {
            sent_message.msgId: {
                "tukhoa": question['tukhoa'],
                "timestamp": time.time(),
                "hint_used": False
            }
        }
        
        # Start the countdown and timeout check thread
        if sent_message and hasattr(sent_message, 'msgId'):
            countdown_thread = Thread(target=send_countdown_and_check_timeout, args=(thread_id, thread_type, sent_message.msgId, client, question['tukhoa']))
            countdown_thread.daemon = True
            countdown_thread.start()
            
    except KeyError as e:
        print(f"[ERROR] Lỗi thiếu trường trong dữ liệu: {e}")
        client.sendMessage(
            Message(text=f"Đã xảy ra lỗi: Thiếu trường {e} trong dữ liệu câu hỏi"),
            thread_id=thread_id,
            thread_type=thread_type,
        )
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Lỗi khi tải ảnh: {e}")
        client.sendMessage(
            Message(text=f"Đã xảy ra lỗi khi tải ảnh: {e}"),
            thread_id=thread_id,
            thread_type=thread_type,
        )
    except ValueError as e:
        print(f"[ERROR] Lỗi dữ liệu câu hỏi: {e}")
        client.sendMessage(
            Message(text=f"Đã xảy ra lỗi: {e}"),
            thread_id=thread_id,
            thread_type=thread_type,
        )
    except Exception as e:
        print(f"[ERROR] Lỗi không mong muốn: {type(e).__name__} - {e}")
        client.sendMessage(
            Message(text=f"Đã xảy ra lỗi không mong muốn: {e}"),
            thread_id=thread_id,
            thread_type=thread_type,
        )

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        return user_info.zaloName or user_info.displayName
    except Exception:
        return "Unknown User"

def handle_hint(user_id, client, thread_id, thread_type):
    try:
        if thread_id not in game_sessions or not game_sessions[thread_id]:
            client.sendMessage(
                Message(text="⚠️ Không có câu hỏi nào đang chờ giải đáp để dùng hint!"),
                thread_id=thread_id,
                thread_type=thread_type,
            )
            return
        
        session = game_sessions[thread_id]
        for msg_id, data in session.items():
            if data.get('hint_used', False):
                client.sendMessage(
                    Message(text="⚠️ Bạn đã dùng hint cho câu hỏi này rồi!"),
                    thread_id=thread_id,
                    thread_type=thread_type,
                )
                return
            
            current_coins = get_coins(user_id)
            if current_coins < 20:
                client.sendMessage(
                    Message(text=f"❌ Bạn không đủ coins! Bạn cần 20 coins để mở hint, bạn hiện có {current_coins} coins."),
                    thread_id=thread_id,
                    thread_type=thread_type,
                )
                return
            
            add_coins(user_id, -20)
            correct_answer = data["tukhoa"]
            first_char = correct_answer[0].upper()
            data['hint_used'] = True
            
            client.sendMessage(
                Message(text=f"💡 Gợi ý: Chữ cái đầu tiên của từ là \"{first_char}\"! Bạn đã dùng 20 coins."),
                thread_id=thread_id,
                thread_type=thread_type,
            )
            return
            
    except Exception as e:
        print(f"[ERROR] Lỗi xử lý hint: {e}")
        client.sendMessage(
            Message(text=f"Đã xảy ra lỗi khi dùng hint: {e}"),
            thread_id=thread_id,
            thread_type=thread_type,
        )

def handle_answer(message, thread_id, thread_type, user_id, client, is_correct, is_quitting=False):
    try:
        position, user_score = get_current_top_and_score(user_id)
        user = get_user_name_by_id(client, user_id)
        if isinstance(message, dict) and 'tukhoa' in message:
            correct_answer = message['tukhoa']
        else:
            if thread_id in game_sessions:
                session = game_sessions[thread_id]
                for msg_id, data in session.items():
                    correct_answer = data["tukhoa"]
                    break
            else:
                correct_answer = None

        if is_quitting:
            save_score(user_id, -5)
            response_message = f"❌ {user} đã đầu hàng!\n{user} bị trừ [20] điểm khi đầu hàng\nTổng điểm: {user_score - 20}\nTop: {position} trong bảng xếp hạng.\nBạn sẽ bị trừ 5 điểm khi không trả lời."
        elif is_correct:
            save_score(user_id, 10)
            add_coins(user_id, 15)  # Give 15 coins for correct answer
            current_coins = get_coins(user_id)
            response_message = f"🎉 Chúc mừng {user} đã trả lời đúng!\n{user} được cộng [10] điểm và 15 coins khi trả lời đúng\nTổng điểm: {user_score + 10}\nTổng coins: {current_coins}\nTop: {position} trong bảng xếp hạng."
        else:
            save_score(user_id, -5)
            response_message = f"❌ Rất tiếc {user} đã trả lời sai.\n{user} bị trừ [5] điểm khi trả lời sai\nTổng điểm: {user_score - 5}\nTop: {position} trong bảng xếp hạng."

        # Thêm bảng xếp hạng vào thông báo
        leaderboard_message = get_leaderboard(client)  # Lấy bảng xếp hạng
        response_message += f"\n=============================\n{leaderboard_message}"

        mention = Mention(uid=user_id, length=len(user), offset=response_message.index(user))
        client.send(
            Message(text=response_message, mention=mention),
            thread_id=thread_id,
            thread_type=thread_type,
        )

        # Nếu trả lời đúng, gửi câu hỏi tiếp theo
        if is_correct and not is_quitting:
            if thread_id in game_sessions:
                del game_sessions[thread_id]
            send_next_question(thread_id, thread_type, client)

    except Exception as e:
        print(f"[ERROR] Lỗi khi xử lý trả lời: {e}")
        client.sendMessage(
            Message(text=f"Đã xảy ra lỗi khi xử lý câu trả lời: {e}"),
            thread_id=thread_id,
            thread_type=thread_type,
        )

def handle_quit_command(message, thread_id, thread_type, user_id, client):
    if thread_id in game_sessions:
        session = game_sessions[thread_id]
        for msg_id, data in session.items():
            handle_answer(message, thread_id, thread_type, user_id, client, is_correct=False, is_quitting=True)
            del game_sessions[thread_id][msg_id]
            return

    client.sendMessage(
        Message(text="⚠️ Bạn chưa tham gia câu hỏi nào để đầu hàng."),
        thread_id=thread_id,
        thread_type=thread_type,
    )

# Hàm lấy bảng xếp hạng
def get_leaderboard(client):
    leaderboard = read_json('modules/game/dhbc/scoreboard.json')
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)
    leaderboard_message = "🎉 Bảng xếp hạng 🎯:\n"

    # Lấy 5 người đứng đầu
    for i, (user_id, score) in enumerate(sorted_leaderboard[:10]):
        user_name = get_user_name_by_id(client, user_id)
        leaderboard_message += f"{i + 1}. {user_name} [{score}] điểm\n"

    return leaderboard_message

def send_answer_for_admin(thread_id, thread_type, client):
    try:
        if thread_id not in game_sessions or not game_sessions[thread_id]:
            client.sendMessage(
                Message(text="⚠️ Không có câu hỏi nào đang chờ giải đáp."),
                thread_id=thread_id,
                thread_type=thread_type,
            )
            return

        session = game_sessions[thread_id]
        for msg_id, data in session.items():
            correct_answer = data["tukhoa"]
            client.sendMessage(
                Message(text=f"Đáp án là: [{correct_answer}]\n🤪Chơi game vui vẻ\nKhông cay bạn nhé🤣"),
                thread_id=thread_id,
                thread_type=thread_type,
            )

    except Exception as e:
        print(f"[ERROR] Lỗi khi gửi đáp án cho admin: {e}")
        client.sendMessage(
            Message(text=f"Đã xảy ra lỗi khi gửi đáp án: {e}"),
            thread_id=thread_id,
            thread_type=thread_type,
        )
def handle_bc_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "bc" not in settings:
        settings["bc"] = {}
    settings["bc"][thread_id] = True
    write_settings(bot.uid, settings)
    return f"🚦Lệnh {bot.prefix}dhbc đã được Bật 🚀 trong nhóm này ✅"

def handle_bc_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "bc" in settings and thread_id in settings["bc"]:
        settings["bc"][thread_id] = False
        write_settings(bot.uid, settings)
        return f"🚦Lệnh {bot.prefix}dhbc đã Tắt ⭕️ trong nhóm này ✅"
    return "🚦Nhóm chưa có thông tin cấu hình dhbc để ⭕️ Tắt 🤗"

def handle_dhbc_command(client, message_object, author_id, thread_id, thread_type, message):
    try:
        settings = read_settings(client.uid)
        words = message.strip().split()
        if not words:
            return False
        cmd_word = words[0]
        user_message = message[len(cmd_word):].strip().lower()
        if user_message == "on":
            if not is_admin(client, author_id):  
                response = "❌Bạn không phải admin bot!"
            else:
                response = handle_bc_on(client, thread_id)
            client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        elif user_message == "off":
            if not is_admin(client, author_id):  
                response = "❌Bạn không phải admin bot!"
            else:
                response = handle_bc_off(client, thread_id)
            client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        
        if not (settings.get("bc", {}).get(thread_id, False)):
            return False
        
        content = message.strip().split()
        commands = "dhbc"
    
        if len(content) < 2:
            msg = "".join([
                f"\n📝 Bắt đầu trò chơi ({client.prefix}{commands} batdau)\n"
                f"🎁 Nhận quà hàng ngày ({client.prefix}{commands} daily)\n"
                f"🏆 Xem bảng xếp hạng ({client.prefix}{commands} bxh)\n"
                f"💡 Mở gợi ý ({client.prefix}{commands} hint)\n"
                f"✋ Đầu hàng ({client.prefix}{commands} dauhang)\n"
                f"💬 Đáp án (admin) ({client.prefix}{commands} dapans)\n"
            ])
            os.makedirs(CACHE_PATH, exist_ok=True)
    
            image_path = generate_menu_image(client, author_id, thread_id, thread_type)
            if not image_path:
                client.sendMessage("❌ Không thể tạo ảnh menu!", thread_id, thread_type)
                return

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
                client.sendReaction(message_object, random.choice(reaction), thread_id, thread_type)
            client.sendReaction(message_object, "TBOT OK ✅", thread_id, thread_type)
            client.sendLocalImage(
                imagePath=image_path,
                message=Message(text=msg, mention=Mention(author_id, length=len(f"{get_user_name_by_id(client, author_id)}"), offset=0)),
                thread_id=thread_id,
                thread_type=thread_type,
                width=1920,
                height=600,
                ttl=240000
            )
            
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"❌ Lỗi khi xóa ảnh: {e}")
            return "no_reaction"  # Thêm return để tránh lỗi tiếp tục xử lý

        if len(content) >= 2:
            command = content[1].lower()

        if content[1] == 'daily':
            handle_attendance(author_id, client, thread_id, thread_type)
            return

        if content[1] == 'batdau':
            save_score(author_id, -5)
            send_next_question(thread_id, thread_type, client)
            return
        if content[1] == 'bxh':
            leaderboard_message = get_leaderboard(client)
            client.sendMessage(
                Message(text=leaderboard_message),
                thread_id=thread_id,
                thread_type=thread_type,
            )
            return
        if content[1] == 'hint':
            handle_hint(author_id, client, thread_id, thread_type)
            return
        if content[1] == 'dapans':
            send_answer_for_admin(thread_id, thread_type, client)
            if not is_admin(client, author_id):
                msg = "• Không đủ đẳng cấp để sử dụng!!\n"
                styles = MultiMsgStyle([MessageStyle(offset=0, length=2, style="color", color="#f38ba8", auto_format=False),
                                        MessageStyle(offset=2, length=len(msg)-2, style="color", color="#cdd6f4", auto_format=False),
                                        MessageStyle(offset=0, length=len(msg), style="font", size="13", auto_format=False)])
                client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type)
                return
            return

        if content[1] == 'dauhang':
            handle_quit_command(message, thread_id, thread_type, author_id, client)
            return

        if thread_id in game_sessions:
            session = game_sessions[thread_id]

            if isinstance(session, dict):
                for msg_id, data in session.items():
                    if time.time() - data['timestamp'] > timeLimit:
                        client.sendMessage(
                            Message(text=f"⏰ Bạn hết thời gian trả lời!\nVui lòng nhập [{client.prefix}{commands} batdau] để bắt đầu chơi tiếp."),
                            thread_id=thread_id,
                            thread_type=thread_type,
                        )
                        del game_sessions[thread_id][msg_id]
                        return

                    answer = " ".join(content[1:]).strip().lower()
                    if answer == data['tukhoa'].lower():
                        handle_answer(message, thread_id, thread_type, author_id, client, is_correct=True)
                    else:
                        handle_answer(message, thread_id, thread_type, author_id, client, is_correct=False)
                    return
            else:
                client.sendMessage(
                    Message(text="➜ 🐞 Đã xảy ra lỗi: Phiên trò chơi không hợp lệ!"),
                    thread_id=thread_id,
                    thread_type=thread_type,
                )
                return
    except Exception as e:
        client.replyMessage(Message(text=f"➜ 🐞 Đã xảy ra lỗi: {e}🤧"), message_object, thread_id=thread_id, thread_type=thread_type)

txa = {
    "name": "pro_dhbc",
    "desc": "Game đoán từ: đoán từ khóa dựa trên gợi ý. Hỗ trợ chơi game vui nhộn trong nhóm. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['dhbc']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'dhbc': handle_dhbc_command
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
        return func(*args)
