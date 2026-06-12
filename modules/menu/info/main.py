import os
import re
import random
import textwrap
import requests
import emoji
from datetime import datetime
from io import BytesIO
from threading import Thread
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageOps, ImageFont, ImageFilter

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

def info(message, message_object, thread_id, thread_type, author_id, client):
    try:
        mentions = message_object.mentions
        if mentions:
            target_id = mentions[0]['uid']
        else:
            parts = message.strip().split()
            if len(parts) >= 2:
                raw_uid = parts[-1].strip()
                if raw_uid.isdigit():
                    target_id = raw_uid
                else:
                    target_id = author_id
            else:
                target_id = author_id

        user_info = client.fetchUserInfo(target_id)
        user = user_info.changed_profiles.get(target_id) if user_info and getattr(user_info, 'changed_profiles', None) else None
        if not user:
            client.send(
                Message(text="❌ Không thể lấy thông tin người dùng."),
                thread_id=thread_id,
                thread_type=thread_type
            )
            return

        cover_url = getattr(user, 'cover', None)
        avatar_url = getattr(user, 'avatar', None)

        main_canvas = Image.new("RGBA", (1000, 1250), (242, 239, 249, 255))
        draw = ImageDraw.Draw(main_canvas)

        card_canvas = Image.new("RGBA", (900, 1120), (255, 255, 255, 255))
        cover_height = 320
        if cover_url:
            try:
                cover_resp = requests.get(cover_url, timeout=5)
                if cover_resp.status_code == 200:
                    cover_img = Image.open(BytesIO(cover_resp.content)).convert("RGBA")
                    cover_img = ImageOps.fit(cover_img, (900, cover_height), centering=(0.5, 0.5))
                    overlay_cover = Image.new("RGBA", (900, cover_height), (0, 0, 0, 40))
                    cover_img = Image.alpha_composite(cover_img, overlay_cover)
                    card_canvas.paste(cover_img, (0, 0))
            except Exception as e:
                print("Lỗi tải cover:", e)
                cover_default = Image.new("RGBA", (900, cover_height), (40, 30, 60, 255))
                card_canvas.paste(cover_default, (0, 0))
        else:
            cover_default = Image.new("RGBA", (900, cover_height), (40, 30, 60, 255))
            card_canvas.paste(cover_default, (0, 0))

        card_mask = Image.new("L", (900, 1120), 0)
        card_mask_draw = ImageDraw.Draw(card_mask)
        card_mask_draw.rounded_rectangle([(0, 0), (900, 1120)], radius=40, fill=255)
        
        card_rounded = Image.new("RGBA", (900, 1120), (0, 0, 0, 0))
        card_rounded.paste(card_canvas, (0, 0), card_mask)

        main_canvas.paste(card_rounded, (50, 50), card_rounded)

        draw.ellipse([(400, 270), (600, 470)], fill=(255, 255, 255, 255))

        avatar_size = 180
        if avatar_url:
            try:
                avatar_resp = requests.get(avatar_url, timeout=5)
                if avatar_resp.status_code == 200:
                    avatar_img = Image.open(BytesIO(avatar_resp.content)).convert("RGBA")
                    avatar_img = ImageOps.fit(avatar_img, (avatar_size, avatar_size), centering=(0.5, 0.5))
                    avatar_mask = Image.new("L", (avatar_size, avatar_size), 0)
                    avatar_mask_draw = ImageDraw.Draw(avatar_mask)
                    avatar_mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                    avatar_img.putalpha(avatar_mask)
                    main_canvas.paste(avatar_img, (410, 280), avatar_img)
            except Exception as e:
                print("Lỗi tải avatar:", e)
                draw.ellipse([(410, 280), (590, 460)], fill=(200, 200, 200, 255))
        else:
            draw.ellipse([(410, 280), (590, 460)], fill=(200, 200, 200, 255))

        font_path = "font/arial unicode ms.otf"
        font_bold_path = "font/arial unicode ms bold.otf"
        font_sf_path = "font/SF-Pro.ttf"
        
        if not os.path.exists(font_path): font_path = "arial.ttf"
        if not os.path.exists(font_bold_path): font_bold_path = "arialbd.ttf"
        if not os.path.exists(font_sf_path): font_sf_path = "arial.ttf"

        f_name = ImageFont.truetype(font_bold_path, 42)
        f_uid = ImageFont.truetype(font_sf_path, 28)
        f_badge = ImageFont.truetype(font_sf_path, 20)
        f_bio_title = ImageFont.truetype(font_bold_path, 24)
        f_bio_text = ImageFont.truetype(font_path, 28)
        f_box_title = ImageFont.truetype(font_path, 20)
        f_box_value = ImageFont.truetype(font_bold_path, 24)
        f_box_value_sf = ImageFont.truetype(font_sf_path, 24)
        f_footer = ImageFont.truetype(font_path, 24)
        
        emoji_font_path = "font/NotoEmoji-Bold.ttf"
        f_emoji = ImageFont.truetype(emoji_font_path, 32) if os.path.exists(emoji_font_path) else ImageFont.truetype(font_path, 32)

        display_name = getattr(user, 'displayName', 'Unknown') or 'Unknown'
        name_bbox = draw.textbbox((0, 0), display_name, font=f_name)
        name_w = name_bbox[2] - name_bbox[0]
        name_x = 500 - name_w // 2
        draw.text((name_x, 480), display_name, fill=(0, 0, 0, 255), font=f_name)

        user_id_str = getattr(user, 'userId', 'Unknown') or 'Unknown'
        uid_text = f"@{user_id_str}"
        uid_bbox = draw.textbbox((0, 0), uid_text, font=f_uid)
        uid_w = uid_bbox[2] - uid_bbox[0]
        uid_x = 500 - uid_w // 2
        draw.text((uid_x, 535), uid_text, fill=(120, 120, 120, 255), font=f_uid)

        is_mobile_online = getattr(user, 'isActive', 0) in (1, "1", True)
        is_pc_online = getattr(user, 'isActivePC', 0) in (1, "1", True)
        is_web_online = getattr(user, 'isActiveWeb', 0) in (1, "1", True)

        devices = [
            {"name": "Mobile", "icon": "📱", "online": is_mobile_online},
            {"name": "PC", "icon": "💻", "online": is_pc_online},
            {"name": "Web", "icon": "🌐", "online": is_web_online}
        ]

        badge_w = 150
        badge_h = 44
        badge_spacing = 15
        total_badges_w = 3 * badge_w + 2 * badge_spacing
        badge_start_x = 500 - total_badges_w // 2
        badge_y = 580

        for idx, dev in enumerate(devices):
            bx = badge_start_x + idx * (badge_w + badge_spacing)
            draw.rounded_rectangle([(bx, badge_y), (bx + badge_w, badge_y + badge_h)], radius=15, fill=(242, 238, 251, 255))
            
            dot_color = (46, 204, 113, 255) if dev["online"] else (231, 76, 60, 255)
            draw.ellipse([(bx + 15, badge_y + 17), (bx + 25, badge_y + 27)], fill=dot_color)
            
            status_str = "Online" if dev["online"] else "Offline"
            badge_text = f"{dev['icon']} {status_str}"
            draw.text((bx + 35, badge_y + 8), badge_text, fill=(92, 58, 182, 255), font=f_badge)

        bio_y_start = 640
        bio_y_end = 760
        draw.rounded_rectangle([(90, bio_y_start), (910, bio_y_end)], radius=15, fill=(248, 247, 252, 255))
        draw.rounded_rectangle([(90, bio_y_start), (100, bio_y_end)], radius=5, fill=(92, 58, 182, 255))

        draw.text((120, bio_y_start + 15), "Bio", fill=(162, 158, 179, 255), font=f_bio_title)

        status_text = getattr(user, 'status', None) or "Không có tiểu sử"
        max_bio_w = 750
        wrapped_bio = textwrap.fill(status_text, width=int(max_bio_w / (f_bio_text.size * 0.5)))
        bio_lines = wrapped_bio.split('\n')[:2]
        for line_idx, line in enumerate(bio_lines):
            draw.text((120, bio_y_start + 48 + line_idx * 32), line, fill=(74, 71, 84, 255), font=f_bio_text)

        dob_str = "Ẩn"
        dob_val = getattr(user, 'dob', None)
        if dob_val:
            try:
                dob_str = datetime.fromtimestamp(float(dob_val)).strftime("%d/%m/%Y")
            except Exception as e:
                print(f"[info] Lỗi parse dob: {e}")
                dob_str = "Ẩn"
        if not dob_str:
            dob_str = "Ẩn"

        last_action_str = "Không xác định"
        last_action_val = getattr(user, 'lastActionTime', None)
        if last_action_val:
            try:
                last_action_str = datetime.fromtimestamp(float(last_action_val)/1000).strftime("%H:%M %d/%m/%Y")
            except Exception as e:
                print(f"[info] Lỗi parse lastActionTime: {e}")
                last_action_str = "Không xác định"
        if not last_action_str:
            last_action_str = "Không xác định"

        created_str = "Không xác định"
        created_val = getattr(user, 'createdTs', None)
        if created_val:
            try:
                created_str = datetime.fromtimestamp(float(created_val)).strftime("%d/%m/%Y")
            except Exception as e:
                print(f"[info] Lỗi parse createdTs: {e}")
                created_str = "Không xác định"
        if not created_str:
            created_str = "Không xác định"
        
        biz_pkg = "Thường"
        biz_val = getattr(user, 'bizPkg', None)
        if biz_val:
            label_val = None
            if hasattr(biz_val, 'label'):
                label_val = biz_val.label
            elif isinstance(biz_val, dict):
                label_val = biz_val.get('label')
            
            if isinstance(label_val, dict):
                biz_pkg = label_val.get('VI') or label_val.get('EN') or "Business"
            elif isinstance(label_val, str):
                biz_pkg = label_val
            elif label_val:
                biz_pkg = str(label_val)
        if not biz_pkg:
            biz_pkg = "Thường"
            
        gender_str = "Không xác định"
        gender_val = getattr(user, 'gender', None)
        if gender_val == 0 or gender_val == '0':
            gender_str = "Nam"
        elif gender_val == 1 or gender_val == '1':
            gender_str = "Nữ"

        info_boxes = [
            {"title": "UID", "value": str(user_id_str) if user_id_str is not None else "Ẩn", "icon": "🏷️", "is_sf": True},
            {"title": "Giới tính", "value": str(gender_str) if gender_str is not None else "Không xác định", "icon": "⚧", "is_sf": False},
            {"title": "Ngày sinh", "value": str(dob_str) if dob_str is not None else "Ẩn", "icon": "🎂", "is_sf": False},
            {"title": "Số điện thoại", "value": "Ẩn", "icon": "📱", "is_sf": False},
            {"title": "Business", "value": str(biz_pkg) if biz_pkg is not None else "Thường", "icon": "💼", "is_sf": False},
            {"title": "Tài khoản", "value": "Hợp lệ", "icon": "🛡️", "is_sf": False},
            {"title": "Ngày tạo", "value": str(created_str) if created_str is not None else "Không xác định", "icon": "⏰", "is_sf": True},
            {"title": "Hoạt động cuối", "value": str(last_action_str) if last_action_str is not None else "Không xác định", "icon": "🔄", "is_sf": True}
        ]

        box_w = 400
        box_h = 80
        col_gap = 20
        row_gap = 15
        start_box_y = 790

        for box_idx, box in enumerate(info_boxes):
            col = box_idx % 2
            row = box_idx // 2

            bx = 90 + col * (box_w + col_gap)
            by = start_box_y + row * (box_h + row_gap)

            draw.rounded_rectangle([(bx, by), (bx + box_w, by + box_h)], radius=15, fill=(248, 247, 252, 255))

            draw.text((bx + 20, by + 22), box["icon"], fill=(92, 58, 182, 255), font=f_emoji)

            draw.text((bx + 80, by + 12), box["title"], fill=(162, 158, 179, 255), font=f_box_title)

            val_font = f_box_value_sf if box["is_sf"] else f_box_value
            val_text = str(box["value"]) if box["value"] is not None else "Không xác định"
            max_val_w = 300
            val_bbox = draw.textbbox((0, 0), val_text, font=val_font)
            val_w = val_bbox[2] - val_bbox[0]
            if val_w > max_val_w:
                temp_font = ImageFont.truetype(font_sf_path if box["is_sf"] else font_path, 20)
                val_bbox = draw.textbbox((0, 0), val_text, font=temp_font)
                val_w = val_bbox[2] - val_bbox[0]
                if val_w > max_val_w:
                    val_text = val_text[:18] + "..."
                val_font = temp_font

            draw.text((bx + 80, by + 40), val_text, fill=(74, 71, 84, 255), font=val_font)

        footer_text = "Chúc bạn một ngày tốt lành!"
        footer_bbox = draw.textbbox((0, 0), footer_text, font=f_footer)
        footer_w = footer_bbox[2] - footer_bbox[0]
        footer_x = 500 - footer_w // 2
        draw.text((footer_x, 1190), footer_text, fill=(162, 158, 179, 255), font=f_footer)

        image_path = os.path.join(CACHE_PATH, f"info_{target_id}.png")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        main_canvas.convert("RGB").save(image_path, "JPEG", quality=95)

        user_name = display_name
        message_info = f"🚦 {get_user_name_by_id(client, author_id)} profile {user_name} của bạn đây ✅"
        
        client.sendLocalImage(
            imagePath=image_path,
            thread_id=thread_id,
            thread_type=thread_type,
            message=Message(text=message_info, mention=Mention(author_id, length=len(f"{get_user_name_by_id(client, author_id)}"), offset=3)),
            height=1250,
            width=1000,
            ttl=6000000
        )
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as ex:
            print("Lỗi xóa file tạm info:", ex)

    except Exception as e:
        import traceback
        traceback.print_exc()
        client.send(
            Message(text=f"Đã xảy ra lỗi: {str(e)}"),
            thread_id=thread_id,
            thread_type=thread_type
        )

def handle_info_command(message, message_object, thread_id, thread_type, author_id, client):
    def run():
        info(message, message_object, thread_id, thread_type, author_id, client)
    Thread(target=run).start()

txa = {
    "name": "info",
    "desc": "Lệnh xem thông tin cá nhân dạng thẻ ảnh Premium v2.",
    "author": "TXA",
    "command": "info"
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    words = message_text.strip().split()
    if len(words) >= 2 and words[0].lower() == f"{prefix}info" and words[1].lower() == "qr":
        from modules.menu.info_qr.main import handle_info_qr_command
        handle_info_qr_command(message_text, message_object, thread_id, thread_type, author_id, bot)
    else:
        handle_info_command(message_text, message_object, thread_id, thread_type, author_id, bot)
