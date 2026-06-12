import os
import re
import random
import requests
import emoji
from io import BytesIO
from threading import Thread
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageOps, ImageFont, ImageFilter
import traceback

from zlapi.models import Message, Mention
from core.bot_sys import get_user_name_by_id

CACHE_PATH = "modules/cache/"

def is_emoji(character: str) -> bool:
    return character in emoji.EMOJI_DATA

def interpolate_colors(colors: List[Tuple[int, int, int]], text_length: int, change_every: int = 1) -> List[Tuple[int, int, int]]:
    result = []
    for i in range(text_length):
        color_idx = (i // change_every) % len(colors)
        result.append(colors[color_idx])
    return result

def create_text(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, 
                emoji_font: ImageFont.FreeTypeFont, text_position: Tuple[int, int], 
                gradient_colors: List[Tuple[int, int, int]]):
    gradient = interpolate_colors(gradient_colors, text_length=len(text), change_every=4)
    current_x = text_position[0]

    for i, char in enumerate(text):
        color = tuple(gradient[i])
        try:
            is_emoji_char = ord(char) >= 0x1F000 or is_emoji(char)
            selected_font = emoji_font if is_emoji_char and emoji_font else font
            draw.text((current_x, text_position[1]), char, fill=color, font=selected_font)
            try:
                text_width = selected_font.getlength(char)
            except AttributeError:
                text_bbox = draw.textbbox((0, 0), char, font=selected_font)
                text_width = text_bbox[2] - text_bbox[0]
                if text_width == 0 and char == " ":
                    text_width = selected_font.size // 3
            current_x += text_width
        except Exception as e:
            print(f"Lỗi khi vẽ ký tự '{char}': {e}. Bỏ qua ký tự này.")
            continue

def create_gradient_colors(num_colors):
    colors = []
    for _ in range(num_colors):
        colors.append((random.randint(100, 175), random.randint(100, 180), random.randint(100, 170)))
    return colors

def qr(message, message_object, thread_id, thread_type, author_id, client):
    try:
        mentions = message_object.mentions
        if mentions:
            target_id = mentions[0]['uid']
        else:
            target_id = author_id

        # Get content text (custom text to show on the QR Card)
        prefix = getattr(client, 'prefix', '.')
        words = message.split()
        content = ""
        if words:
            first_word = words[0].lower()
            if first_word in [f"{prefix}info_qr", f"{prefix}infoqr", f"{prefix}qr"]:
                content = " ".join(words[1:]).strip()
            elif len(words) >= 2 and f"{words[0].lower()} {words[1].lower()}" in [f"{prefix}info qr", f"{prefix}zl qr"]:
                content = " ".join(words[2:]).strip()
            else:
                if first_word.startswith(prefix):
                    content = " ".join(words[1:]).strip()
                else:
                    content = message.strip()
        else:
            content = ""

        # Strip mention display names to avoid duplicated info
        if mentions:
            for mention in mentions:
                try:
                    user_info_req = client.fetchUserInfo(mention['uid'])
                    if user_info_req and getattr(user_info_req, 'changed_profiles', None):
                        user_profile = user_info_req.changed_profiles.get(mention['uid'])
                        if user_profile and getattr(user_profile, 'displayName', None):
                            mention_text = f"@{user_profile.displayName}"
                            content = content.replace(mention_text.lower(), "").strip()
                            content = content.replace(user_profile.displayName.lower(), "").strip()
                except Exception as e:
                    print(f"Lỗi khi strip mention: {e}")
            content = re.sub(r'@[^\s]+', '', content).strip()
            content = ''.join(c for c in content if c.isalnum() or c.isspace() or is_emoji(c))
        
        if not content:
            content = "😍Hãy kết bạn với tôi 😊"

        user_info = client.fetchUserInfo(target_id)
        user = user_info.changed_profiles.get(target_id) if user_info and getattr(user_info, 'changed_profiles', None) else None
        if not user:
            client.send(
                Message(text="❌ Không thể lấy thông tin người dùng."),
                thread_id=thread_id,
                thread_type=thread_type
            )
            return

        background_dir = "background"
        if not os.path.exists(background_dir):
            os.makedirs(background_dir, exist_ok=True)
            
        background_files = [os.path.join(background_dir, f) for f in os.listdir(background_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
        if not background_files:
            client.send(
                Message(text="Không có ảnh nền nào trong thư mục 'background'."),
                thread_id=thread_id,
                thread_type=thread_type
            )
            return
            
        background_path = random.choice(background_files)
        background = Image.open(background_path).convert("RGBA")
        background = background.resize((840, 1280), Image.Resampling.LANCZOS)
        background = background.filter(ImageFilter.GaussianBlur(radius=5))

        qr_link = None
        if hasattr(client, "getQRLink"):
            try:
                qr_data = client.getQRLink(target_id)
                if qr_data and target_id in qr_data:
                    qr_link = qr_data[target_id]
            except Exception as e:
                print(f"[info_qr] Lỗi gọi client.getQRLink: {e}")

        if not qr_link:
            qr_link = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data=https://zalo.me/{target_id}"

        qr_response = requests.get(qr_link, timeout=10)
        if qr_response.status_code != 200:
            client.send(
                Message(text="Không thể tải mã QR từ máy chủ Zalo."),
                thread_id=thread_id,
                thread_type=thread_type
            )
            return

        qr_image = Image.open(BytesIO(qr_response.content)).convert("RGBA")
        qr_size = 400
        qr_image = qr_image.resize((qr_size, qr_size), Image.Resampling.LANCZOS)

        avatar_url = getattr(user, 'avatar', None)
        avatar_size = 150
        avatar_image = None
        if avatar_url:
            try:
                avatar_response = requests.get(avatar_url, timeout=5)
                if avatar_response.status_code == 200:
                    avatar_image = Image.open(BytesIO(avatar_response.content)).convert("RGBA")
                    avatar_image = ImageOps.fit(avatar_image, (avatar_size, avatar_size), Image.Resampling.LANCZOS)
                    mask = Image.new("L", avatar_image.size, 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                    avatar_image.putalpha(mask)
            except Exception as e:
                print(f"❌ Lỗi tải avatar cho QR: {e}")

        overlay = Image.new("RGBA", background.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        random_color = (random.randint(0, 50), random.randint(0, 50), random.randint(50, 100), 200)

        rect_x0 = (840 - 640) // 2
        rect_y0 = (1280 - 1000) // 2
        rect_x1 = rect_x0 + 640
        rect_y1 = rect_y0 + 1000

        radius = 50
        draw.rounded_rectangle(
            [rect_x0, rect_y0, rect_x1, rect_y1],
            radius=radius,
            fill=random_color
        )

        avatar_x = (840 - avatar_size) // 2
        avatar_y = rect_y0 + 50

        if avatar_image:
            overlay.paste(avatar_image, (avatar_x, avatar_y), avatar_image)
        else:
            draw.ellipse([(avatar_x, avatar_y), (avatar_x + avatar_size, avatar_y + avatar_size)], fill=(200, 200, 200, 255))

        qr_x = (840 - qr_size) // 2
        qr_y = (1280 - qr_size) // 2
        overlay.paste(qr_image, (qr_x, qr_y), qr_image)

        user_name = getattr(user, 'displayName', 'Unknown') or 'Unknown'

        font_path = "font/arial unicode ms bold.otf"
        if not os.path.exists(font_path):
            font_path = "arial.ttf"
            
        font = ImageFont.truetype(font_path, 46)
        random_name_color = (random.randint(150, 255), random.randint(150, 255), random.randint(150, 255), 255)

        text_size = draw.textbbox((0, 0), user_name, font=font)
        text_x = (840 - (text_size[2] - text_size[0])) // 2
        text_y = avatar_y + avatar_size + 20
        draw.text((text_x, text_y), user_name, fill=random_name_color, font=font)

        qr_font_path = "font/arial unicode ms.otf"
        if not os.path.exists(qr_font_path):
            qr_font_path = "arial.ttf"
            
        qr_font = ImageFont.truetype(qr_font_path, 30)
        qr_large_font = ImageFont.truetype(qr_font_path, 44)

        emoji_font_path = "font/NotoEmoji-Bold.ttf"
        emoji_font = ImageFont.truetype(emoji_font_path, 44) if os.path.exists(emoji_font_path) else qr_large_font

        qr_bottom_font = ImageFont.truetype(qr_font_path, 28)
        text_color = (255, 255, 255, 255)

        text_qr = "Liên hệ Zalo"
        qr_text_size = draw.textbbox((0, 0), text_qr, font=qr_font)
        qr_text_x = (840 - (qr_text_size[2] - qr_text_size[0])) // 2
        qr_text_y = qr_y - 50

        draw.text((qr_text_x, qr_text_y), text_qr, fill=text_color, font=qr_font)
        
        text_qr_large = content
        qr_text_large_size = draw.textbbox((0, 0), text_qr_large, font=qr_large_font)
        qr_text_large_x = (840 - (qr_text_large_size[2] - qr_text_large_size[0])) // 2
        qr_text_large_y = qr_y + qr_size + 30

        gradient_colors = [
            (random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)),
            (random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)),
            (random.randint(200, 255), random.randint(200, 255), random.randint(200, 255))
        ]
        create_text(draw, text_qr_large, qr_large_font, emoji_font, (qr_text_large_x, qr_text_large_y), gradient_colors)

        text_qr_bottom = "Mở Zalo bấm nút quét QR để kết bạn"
        qr_text_bottom_size = draw.textbbox((0, 0), text_qr_bottom, font=qr_bottom_font)
        qr_text_bottom_x = (840 - (qr_text_bottom_size[2] - qr_text_bottom_size[0])) // 2
        qr_text_bottom_y = rect_y1 - 60

        draw.text((qr_text_bottom_x, qr_text_bottom_y), text_qr_bottom, fill=text_color, font=qr_bottom_font)

        combined = Image.alpha_composite(background, overlay)
        image_path = os.path.join(CACHE_PATH, f"qr_{target_id}.png")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        combined.save(image_path)
        
        sender_name = get_user_name_by_id(client, author_id)
        message_text_res = f"🚦 {sender_name} QR code {user_name} của bạn đây ✅"
        client.sendLocalImage(
            imagePath=image_path,
            thread_id=thread_id,
            thread_type=thread_type,
            height=1280,
            width=840,
            message=Message(text=message_text_res, mention=Mention(author_id, length=len(sender_name), offset=3)),
            ttl=6000000
        )
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as ex:
            print("Lỗi xóa file tạm qr:", ex)
            
    except Exception as e:
        traceback.print_exc()
        client.send(
            Message(text=f"Đã xảy ra lỗi khi tạo mã QR: {str(e)}"),
            thread_id=thread_id,
            thread_type=thread_type
        )

def handle_info_qr_command(message, message_object, thread_id, thread_type, author_id, client):
    def run():
        qr(message, message_object, thread_id, thread_type, author_id, client)
    Thread(target=run).start()

txa = {
    "name": "info_qr",
    "desc": "Lệnh tạo mã QR thông tin cá nhân dạng thẻ ảnh Premium v2.",
    "author": "TXA",
    "command": ['info_qr', 'infoqr', 'qr']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    handle_info_qr_command(message_text, message_object, thread_id, thread_type, author_id, bot)
