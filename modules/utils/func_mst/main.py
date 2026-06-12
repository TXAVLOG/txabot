import colorsys
from datetime import datetime
import glob
import json
import os
import random
import threading

import pytz
import requests
from core.bot_sys import is_admin, read_settings, write_settings
from core.bot_sys import get_user_name_by_id
from zlapi.models import *
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BACKGROUND_PATH = "background/"
CACHE_PATH = "modules/cache/"
OUTPUT_IMAGE_PATH = os.path.join(CACHE_PATH, "mst.png")

def mst_save(bot, message_object, author_id, thread_id, thread_type, command):
    def save_sticker():
        try:
            if not is_admin(bot, author_id):
                msg = "❌Bạn không phải admin bot!\n"
                bot.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=120000)
                return
            
            parts = command.split()
            if len(parts) < 3 or parts[1] != "save":
                response = "➜ ❌ Sai cú pháp! Dùng: /mst save [tên stk]"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                return

            sticker_name = parts[2]

            if not message_object.quote or not message_object.quote.attach:
                response = "➜ ❌ Vui lòng reply vào tin nhắn chứa sticker để lưu."
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                return

            attach = message_object.quote.attach
            try:
                attach_data = json.loads(attach)
                sticker_url = attach_data.get('hdUrl') or attach_data.get('href')
                sticker_id = attach_data.get('id')
                cat_id = attach_data.get('catId')
                sticker_type = attach_data.get('type')

                if sticker_url:
                    sticker_dir = os.path.join('stickers', 'mst', 'images')
                    os.makedirs(sticker_dir, exist_ok=True)
                    sticker_path = os.path.join(sticker_dir, f"{sticker_name}.json")

                    sticker_data = {
                        "url": sticker_url,
                        "height": attach_data.get('height'),
                        "width": attach_data.get('width'),
                        "saved_by": author_id 
                    }
                elif sticker_id and cat_id and sticker_type:
                    sticker_dir = os.path.join('stickers', 'mst', 'stickers')
                    os.makedirs(sticker_dir, exist_ok=True)
                    sticker_path = os.path.join(sticker_dir, f"{sticker_name}.json")

                    sticker_data = {
                        "id": sticker_id,
                        "catId": cat_id,
                        "type": sticker_type,
                        "saved_by": author_id 
                    }
                else:
                    response = "➜ ❌ Không tìm thấy URL hoặc thông tin sticker trong tin nhắn được trả lời."
                    bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                    return

                with open(sticker_path, 'w', encoding='utf-8') as f:
                    json.dump(sticker_data, f, ensure_ascii=False, indent=4)

                response = f"➜ Sticker '{sticker_name}' đã được lưu thành công!"
            except json.JSONDecodeError:
                response = "➜ ❌ Dữ liệu đính kèm không hợp lệ."

            bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
        except Exception as e:
            print(f"Error: {e}")
            bot.replyMessage(Message(text="➜ 🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type)

    thread = threading.Thread(target=save_sticker)
    thread.start()

def mst_send(bot, message_object, author_id, thread_id, thread_type, command):
    def send_sticker():
        try:
            if not is_admin(bot, author_id):
                msg = "❌Bạn không phải admin bot!\n"
                bot.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=120000)
                return
            
            parts = command.split()
            if len(parts) < 2:
                response = "➜ ❌ Sai cú pháp! Dùng: mst [tên sticker]"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                return

            sticker_name = parts[1]
            sticker_dir = os.path.join('stickers', 'mst', 'images')
            sticker_path = os.path.join(sticker_dir, f"{sticker_name}.json")

            if not os.path.exists(sticker_path):
                sticker_dir = os.path.join('stickers', 'mst', 'stickers')
                sticker_path = os.path.join(sticker_dir, f"{sticker_name}.json")

            if not os.path.exists(sticker_path):
                response = f"➜ ❌ Không tìm thấy sticker '{sticker_name}'."
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                return

            with open(sticker_path, 'r', encoding='utf-8') as f:
                sticker_data = json.load(f)

            if sticker_data.get("saved_by") != author_id:
                response = f"➜ ❌ Bạn không có quyền sử dụng sticker '{sticker_name}'."
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                return

            if 'url' in sticker_data:
                sticker_file_path = download_image(sticker_data["url"])
                if sticker_file_path:
                    uploaded_url = upload_to_uguu(sticker_file_path)
                    if uploaded_url:
                        bot.send_custom_sticker(
                            staticImgUrl=uploaded_url,
                            animationImgUrl=uploaded_url,
                            thread_id=thread_id,
                            thread_type=thread_type,
                            reply=message_object,
                            width=sticker_data.get("width"),
                            height=sticker_data.get("height"),
                            ttl=100000
                        )
                    else:
                        response = "➜ ❌ Không thể tải sticker lên Uguu."
                        bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                    os.remove(sticker_file_path)
                else:
                    response = "➜ ❌ Không thể tải sticker từ URL."
                    bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
            elif 'id' in sticker_data and 'catId' in sticker_data and 'type' in sticker_data:
                bot.sendSticker(
                    stickerId=sticker_data["id"],
                    cateId=sticker_data["catId"],
                    stickerType=sticker_data["type"],
                    thread_id=thread_id,
                    thread_type=thread_type,
                    ttl=100000
                )
            # No bot.replyMessage here unless there's an error
        except Exception as e:
            print(f"Error: {e}")
            bot.replyMessage(Message(text="➜ 🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)

    thread = threading.Thread(target=send_sticker)
    thread.start()

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
    response = requests.get(url)
    if response.status_code == 200:
        file_name = os.path.basename(url)
        file_path = os.path.join(os.getcwd(), file_name)  
        with open(file_path, "wb") as f:
            f.write(response.content)
        return file_path
    return None

def mst_find(bot, message_object, author_id, thread_id, thread_type, command):
    def find_sticker():
        try:
            if not is_admin(bot, author_id):
                msg = "❌Bạn không phải admin bot!\n"
                bot.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=120000)
                return
            
            parts = command.split()
            if len(parts) < 3 or parts[1] != "find":
                response = "➜ ❌ Sai cú pháp! Dùng: /mst find [tên sticker]"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                return

            sticker_name = parts[2]
            custom_stickers_dir = os.path.join('stickers', 'mst', 'images')
            collected_stickers_dir = os.path.join('stickers', 'mst', 'stickers')
            custom_stickers = []
            collected_stickers = []

            if os.path.exists(custom_stickers_dir):
                for file_name in os.listdir(custom_stickers_dir):
                    if file_name.endswith('.json'):
                        with open(os.path.join(custom_stickers_dir, file_name), 'r', encoding='utf-8') as f:
                            sticker_data = json.load(f)
                            if sticker_data.get("saved_by") == author_id and sticker_name in file_name:
                                custom_stickers.append(f"{file_name[:-5]} (ID: {sticker_data.get('id')})")

            if os.path.exists(collected_stickers_dir):
                for file_name in os.listdir(collected_stickers_dir):
                    if file_name.endswith('.json'):
                        with open(os.path.join(collected_stickers_dir, file_name), 'r', encoding='utf-8') as f:
                            sticker_data = json.load(f)
                            if sticker_data.get("saved_by") == author_id and sticker_name in file_name:
                                collected_stickers.append(f"{file_name[:-5]} (Sticker ID: {sticker_data.get('id')}, Cate ID: {sticker_data.get('catId')})")

            if not custom_stickers and not collected_stickers:
                response = f"➜ ❌ Không tìm thấy sticker '{sticker_name}'."
            else:
                response = f"😂 Danh sách Custom Sticker tự sáng tạo:\n" + "\n".join(custom_stickers) + "\n\n😆 Danh sách Sticker Zalo sưu tầm:\n" + "\n".join(collected_stickers)

            bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
        except Exception as e:
            print(f"Error: {e}")
            bot.replyMessage(Message(text="➜ 🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type)

    thread = threading.Thread(target=find_sticker)
    thread.start()

def mst_del(bot, message_object, author_id, thread_id, thread_type, command):
    def delete_sticker():
        try:
            if not is_admin(bot, author_id):
                msg = "❌Bạn không phải admin bot!\n"
                bot.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=120000)
                return
            
            parts = command.split()
            if len(parts) < 3 or parts[1] != "del":
                response = "➜ ❌ Sai cú pháp! Dùng: /mst del [tên sticker]"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                return

            sticker_name = parts[2]
            sticker_dir = os.path.join('stickers', 'mst', 'images')
            sticker_path = os.path.join(sticker_dir, f"{sticker_name}.json")

            if not os.path.exists(sticker_path):
                sticker_dir = os.path.join('stickers', 'mst', 'stickers')
                sticker_path = os.path.join(sticker_dir, f"{sticker_name}.json")

            if not os.path.exists(sticker_path):
                response = f"➜ ❌ Không tìm thấy sticker '{sticker_name}'."
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                return

            with open(sticker_path, 'r', encoding='utf-8') as f:
                sticker_data = json.load(f)

            if sticker_data.get("saved_by") != author_id:
                response = f"➜ ❌ Bạn không có quyền xóa sticker '{sticker_name}'."
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                return

            os.remove(sticker_path)
            response = f"➜ Sticker '{sticker_name}' đã được xóa thành công!"
            bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
        except Exception as e:
            print(f"Error: {e}")
            bot.replyMessage(Message(text="➜ 🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type)

    thread = threading.Thread(target=delete_sticker)
    thread.start()

def handle_mst_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "mst" not in settings:
        settings["mst"] = {}
    settings["mst"][thread_id] = True
    write_settings(bot.uid, settings)
    return f"🚦Lệnh {bot.prefix}mst đã được Bật 🚀 trong nhóm này ✅"

def handle_mst_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "mst" in settings and thread_id in settings["mst"]:
        settings["mst"][thread_id] = False
        write_settings(bot.uid, settings)
        return f"🚦Lệnh {bot.prefix}mst đã Tắt ⭕️ trong nhóm này ✅"
    return "🚦Nhóm chưa có thông tin cấu hình mst để ⭕️ Tắt 🤗"

def mst(bot, message_object, author_id, thread_id, thread_type, command):
    def send_utilities_response():
        settings = read_settings(bot.uid)
    
        user_message = command.replace(f"{bot.prefix}mst ", "").strip().lower()
        if user_message == "on":
            if not is_admin(bot, author_id):  
                response = "❌Bạn không phải admin bot!"
            else:
                response = handle_mst_on(bot, thread_id)
            bot.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        elif user_message == "off":
            if not is_admin(bot, author_id):  
                response = "❌Bạn không phải admin bot!"
            else:
                response = handle_mst_off(bot, thread_id)
            bot.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
            return
        
        if not (settings.get("mst", {}).get(thread_id, False)):
            return
        parts = command.split()
        if len(parts) == 1:
            response = (
                f"{get_user_name_by_id(bot, author_id)}\n"
                f"  ➜ /mst save [tên stk]: Lưu sticker bằng cách reply vào sticker\n"
                f"  ➜ /mst [tên sticker]: 🤪 Gửi Sticker (chỉ người lưu mới gửi được)\n"
                f"  ➜ /mst find [tên sticker]: 🔎 Tìm Sticker theo tên\n"
                f"  ➜ /mst del [tên sticker]: 🗑️ Xóa Sticker theo tên\n"
            )
            os.makedirs(CACHE_PATH, exist_ok=True)
    
            image_path = generate_menu_image(bot, author_id, thread_id, thread_type)
            if not image_path:
                bot.sendMessage("❌ Không thể tạo ảnh menu!", thread_id, thread_type)
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
                bot.sendReaction(message_object, random.choice(reaction), thread_id, thread_type)
            bot.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
            bot.sendLocalImage(
                imagePath=image_path,
                message=Message(text=response, mention=Mention(author_id, length=len(f"{get_user_name_by_id(bot, author_id)}"), offset=0)),
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
            return  # Thêm return để tránh lỗi tiếp tục xử lý

        subcommand = parts[1] if len(parts) > 1 else None
        if subcommand == 'save':
            mst_save(bot, message_object, author_id, thread_id, thread_type, command)
        elif subcommand == 'find':
            mst_find(bot, message_object, author_id, thread_id, thread_type, command)
        elif subcommand == 'del':
            mst_del(bot, message_object, author_id, thread_id, thread_type, command)
        else:
            mst_send(bot, message_object, author_id, thread_id, thread_type, command)

    thread = threading.Thread(target=send_utilities_response)
    thread.start()

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
            f"💞 Chào mừng đến menu 😁 My Custom Sticker",
            f"{bot.prefix}mst on/off: 🚀 Bật/Tắt tính năng",
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

        right_icons = ["🤣"]
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

txa = {
    "name": "mst",
    "desc": "Quản lý sticker: lưu, gửi, xóa sticker. Admin có thể lưu sticker từ tin nhắn và gửi lại khi cần. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['mst']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'mst': mst
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
