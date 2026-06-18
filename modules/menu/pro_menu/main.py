import colorsys
from datetime import datetime, timedelta, timezone
import glob
import importlib.util
from io import BytesIO
import json
import os
import random
import sys
import unicodedata
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont
import emoji
import requests
from core.bot_sys import is_admin
from core.bot_sys import get_user_name_by_id
import modules.txacommand as txacommand
from zlapi.models import *
from zlapi._util import now, getClientMessageType
from PIL import ImageFilter

BACKGROUND_PATH = "background/"
CACHE_PATH = "modules/cache/"
OUTPUT_IMAGE_PATH = os.path.join(CACHE_PATH, "menu.png")

HIDDEN_MODULE_TOKENS = (
    "hiden",
    "pro_menu",
    "menu_or",
    "func_kickall",
    "func_leave",
    "func_disbox",
    "func_spam_call",
    "func_src",
    "join_gr",
    "join_gr1",
    "spamjoin",
    "treo",
)

def no_accent(s):
    if not s:
        return ""
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8')
    return s.lower().strip()

def handle_menu_commands(message, message_object, thread_id, thread_type, author_id, bot):
    modules_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    txac_configs = {}
    
    for entry in os.listdir(modules_dir):
        entry_path = os.path.join(modules_dir, entry)
        if os.path.isdir(entry_path):
            txac_file = os.path.join(entry_path, "txac.py")
            if os.path.exists(txac_file):
                try:
                    module_name = f"modules.{entry}.txac"
                    if module_name in sys.modules:
                        del sys.modules[module_name]
                    spec = importlib.util.spec_from_file_location(module_name, txac_file)
                    txac_mod = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = txac_mod
                    spec.loader.exec_module(txac_mod)
                    
                    if hasattr(txac_mod, "CONFIG"):
                        txac_configs[entry] = txac_mod.CONFIG
                except Exception as e:
                    print(f"❌ Lỗi khi nạp cấu hình từ {txac_file}: {e}")

    # Group commands dynamically
    modules_data = {}
    for cmd, info in txacommand.loaded_commands.items():
        module_path = info['module_path']
        parts = module_path.split('.')
        
        parent_dir = parts[1] if len(parts) > 1 else ""
        sub_dir = parts[2] if len(parts) > 2 else ""
        file_name = parts[3] if len(parts) > 3 else "main"
        rel_file_path = f"{sub_dir}/{file_name}.py"
        
        parent_cfg = txac_configs.get(parent_dir, {})
        if parent_cfg.get("group_by_parent", False):
            group_key = f"group.{parent_dir}"
            info_name = parent_cfg.get("title", parent_dir.title())
            info_desc = parent_cfg.get("title", parent_dir.title())
        else:
            group_key = module_path
            sub_cfg = parent_cfg.get("modules", {}).get(rel_file_path, {})
            info_name = sub_cfg.get("title", info['name'])
            info_desc = info['desc']
            
        if group_key not in modules_data:
            modules_data[group_key] = {
                'name': info_name,
                'desc': info_desc,
                'commands': set(),
                'parent_dir': parent_dir,
                'sub_dir': sub_dir,
                'rel_file_path': rel_file_path,
                'is_grouped': parent_cfg.get("group_by_parent", False)
            }
        modules_data[group_key]['commands'].add(cmd)

    category_titles = {
        "bot": ("🤖", "Hệ thống bot"),
        "utils": ("🔧", "Tiện ích"),
        "downloader": ("📥", "Tải xuống"),
        "ai": ("🧠", "Trí tuệ nhân tạo"),
        "auto": ("🤖", "Tự động"),
        "fun": ("🤭", "Giải trí"),
        "images": ("👩‍💼", "Kho ảnh"),
        "videos": ("🎬", "Kho video"),
        "game": ("🎮", "Trò chơi"),
        "music": ("🎵", "Âm nhạc"),
        "news": ("🗞️", "Tin tức & Tỷ giá"),
        "menu": ("🩴", "Menu hệ thống")
    }

    order_dirs = ["bot", "utils", "downloader", "ai", "auto", "fun", "images", "videos", "game", "music", "news", "menu"]
    prefix = getattr(bot, 'prefix', '!')
    
    # 1. Thu thập tất cả các lệnh và phẳng hóa thành một danh sách
    flat_commands = []
    
    for parent_dir in order_dirs:
        parent_cfg = txac_configs.get(parent_dir)
        if not parent_cfg:
            continue
            
        emoji_cat, title_cat = category_titles.get(parent_dir, ("❖", parent_dir.title()))
        cat_cmds = []
        
        if parent_cfg.get("group_by_parent", False):
            group_key = f"group.{parent_dir}"
            if group_key in modules_data:
                m_info = modules_data[group_key]
                cmds = sorted(list(m_info['commands']))
                if "cmds" in parent_cfg:
                    cmds = [c for c in cmds if c in parent_cfg["cmds"]]
                
                if cmds:
                    main_cmd = cmds[0]
                    title = parent_cfg.get("title", parent_dir.title())
                    
                    t_per = 'all'
                    cmd_info = txacommand.loaded_commands.get(main_cmd, {})
                    if cmd_info:
                        t_per = cmd_info.get('t-per', 'all')
                    perm_suffix = ""
                    if t_per == 'admin':
                        perm_suffix = " (AD)"
                    elif t_per in ['s-admin', 's-ad']:
                        perm_suffix = " (S-AD)"
                        
                    cat_cmds.append({
                        "cmd": f"{prefix}{main_cmd}{perm_suffix}",
                        "desc": title,
                        "parent_dir": parent_dir,
                        "emoji_cat": emoji_cat,
                        "title_cat": title_cat
                    })
        else:
            for rel_file_path, sub_cfg in parent_cfg.get("modules", {}).items():
                sub_parts = rel_file_path.replace(".py", "").split('/')
                if len(sub_parts) < 2:
                    continue
                sub_dir, file_name = sub_parts[0], sub_parts[1]
                group_key = f"modules.{parent_dir}.{sub_dir}.{file_name}"
                
                if any(h in group_key for h in HIDDEN_MODULE_TOKENS):
                    continue
                    
                if group_key in modules_data:
                    m_info = modules_data[group_key]
                    cmds = sorted(list(m_info['commands']))
                    
                    if "cmds" in sub_cfg:
                        cmds = [c for c in cmds if c in sub_cfg["cmds"]]
                        cmds.sort(key=lambda x: sub_cfg["cmds"].index(x))
                    else:
                        cmds = [cmds[0]] if cmds else []
                    
                    for cmd in cmds:
                        title = sub_cfg.get("title", m_info['name'])
                        if title.startswith("pro_"):
                            title = title[4:]
                        title = title.replace("_", " ").title()
                        
                        cmd_info = txacommand.loaded_commands.get(cmd, {})
                        cmd_desc = cmd_info.get('desc', title)
                        
                        t_per = cmd_info.get('t-per', 'all')
                        perm_suffix = ""
                        if t_per == 'admin':
                            perm_suffix = " (AD)"
                        elif t_per in ['s-admin', 's-ad']:
                            perm_suffix = " (S-AD)"
                            
                        cat_cmds.append({
                            "cmd": f"{prefix}{cmd}{perm_suffix}",
                            "desc": cmd_desc,
                            "parent_dir": parent_dir,
                            "emoji_cat": emoji_cat,
                            "title_cat": title_cat
                        })
        if cat_cmds:
            flat_commands.extend(cat_cmds)

    # 2. Xử lý các đối số đầu vào (trang hoặc lọc theo danh mục)
    parts = message.strip().split()
    arg = ""
    if len(parts) > 1:
        arg = " ".join(parts[1:]).strip()

    current_page = 1
    total_pages = (len(flat_commands) + 49) // 50
    category_name = None
    commands_to_draw = []

    if not arg:
        # Mặc định trang 1
        commands_to_draw = flat_commands[0:50]
    else:
        # Kiểm tra xem có phải số trang không
        try:
            page = int(arg)
            if page < 1 or page > total_pages:
                bot.replyMessage(
                    Message(text=f"⚠️ Số trang không hợp lệ! Vui lòng nhập số trang trong khoảng từ 1 đến {total_pages}."),
                    message_object, thread_id, thread_type
                )
                return
            current_page = page
            commands_to_draw = flat_commands[(page - 1) * 50 : page * 50]
        except ValueError:
            # Không phải số trang, kiểm tra xem có phải tên danh mục không
            matched_parent_dir = None
            matched_title_cat = None
            matched_emoji_cat = None
            norm_arg = no_accent(arg)
            
            for parent_dir, (emoji_cat, title_cat) in category_titles.items():
                if norm_arg == no_accent(parent_dir) or norm_arg == no_accent(title_cat):
                    matched_parent_dir = parent_dir
                    matched_title_cat = title_cat
                    matched_emoji_cat = emoji_cat
                    break
                    
            if matched_parent_dir:
                commands_to_draw = [item for item in flat_commands if item["parent_dir"] == matched_parent_dir]
                category_name = matched_title_cat
                current_page = 1
                total_pages = 1
            else:
                available_cats = ", ".join([title for _, title in category_titles.values()])
                bot.replyMessage(
                    Message(text=f"⚠️ Không tìm thấy danh mục nào tên \"{arg}\"!\n💡 Các danh mục khả dụng:\n👉 {available_cats}"),
                    message_object, thread_id, thread_type
                )
                return

    # 3. Phân chia đều các lệnh cần vẽ vào 4 cột
    num_cmds = len(commands_to_draw)
    columns = [[], [], [], []]
    
    if num_cmds > 0:
        base_size = num_cmds // 4
        remainder = num_cmds % 4
        col_sizes = [base_size + (1 if i < remainder else 0) for i in range(4)]
        
        col_commands = []
        idx = 0
        for size in col_sizes:
            col_commands.append(commands_to_draw[idx : idx + size])
            idx += size
            
        for col_idx in range(4):
            cmds_in_col = col_commands[col_idx]
            last_parent_dir = None
            for item_idx, item in enumerate(cmds_in_col):
                pd = item["parent_dir"]
                if pd != last_parent_dir:
                    # Kiểm tra xem danh mục này có phải là phần tiếp theo của cột trước hay không
                    is_continuation = False
                    if col_idx > 0 and item_idx == 0:
                        prev_col_cmds = col_commands[col_idx - 1]
                        if prev_col_cmds and prev_col_cmds[-1]["parent_dir"] == pd:
                            is_continuation = True
                            
                    suffix = " (TIẾP)" if is_continuation else ""
                    columns[col_idx].append({
                        "type": "title",
                        "text": f"{item['emoji_cat']} {item['title_cat']}{suffix}".upper()
                    })
                    last_parent_dir = pd
                columns[col_idx].append({
                    "type": "cmd",
                    "cmd": item["cmd"],
                    "desc": item["desc"]
                })

    # 4. Chuẩn bị caption văn bản gửi kèm ảnh
    user_name = get_user_name_by_id(bot, author_id)
    line1 = f"{user_name}\n"
    if category_name:
        line2 = f"➜ 📁 DANH MỤC: {category_name.upper()}\n"
        line3 = f"(Hiển thị danh sách toàn bộ các lệnh thuộc danh mục {category_name})\n"
    else:
        line2 = f"➜ 📖 HỆ THỐNG MENU - TRANG {current_page}/{total_pages}\n"
        line3 = f"(Dùng {bot.prefix}menu <số> hoặc {bot.prefix}menu <tên danh mục> để chuyển)\n"
    line4 = f"➜ 💡 Dùng {bot.prefix}bot để xem thiết lập và hướng dẫn quản trị."
    
    command_names = line1 + line2 + line3 + line4
    
    # Tính toán offset động cho styles
    styles_list = [
        MessageStyle(offset=0, length=len(line1), style="bold", auto_format=False),
        MessageStyle(offset=0, length=len(line1), style="italic", auto_format=False),
        MessageStyle(offset=0, length=len(line1), style="color", color="00e5ff", auto_format=False),
        
        MessageStyle(offset=len(line1), length=len(line2), style="bold", auto_format=False),
        MessageStyle(offset=len(line1), length=len(line2), style="italic", auto_format=False),
        MessageStyle(offset=len(line1), length=len(line2), style="color", color="ff4081", auto_format=False),
        
        MessageStyle(offset=len(line1) + len(line2), length=len(line3), style="italic", auto_format=False),
        MessageStyle(offset=len(line1) + len(line2), length=len(line3), style="color", color="ffeb3b", auto_format=False),
        
        MessageStyle(offset=len(line1) + len(line2) + len(line3), length=len(line4), style="italic", auto_format=False),
        MessageStyle(offset=len(line1) + len(line2) + len(line3), length=len(line4), style="color", color="00e676", auto_format=False)
    ]
    multi_style = MultiMsgStyle(styles_list)

    image_path = generate_menu_image(bot, author_id, thread_id, thread_type, columns, current_page, total_pages, category_name)
    
    reactions = [
        "❌", "🤧", "🐞", "😊", "🔥", "👍", "💖", "🚀",
        "😍", "😂", "😢", "😎", "🙌", "💪", "🌟", "🍀",
        "🎉", "🦁", "🌈", "🍎", "⚡", "🔔", "🎸", "🍕"
    ]
    if random.random() > 0.3:
        bot.sendReaction(message_object, random.choice(reactions), thread_id, thread_type)
    bot.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
    
    if image_path and os.path.exists(image_path):
        try:
            uploadImage = bot._uploadImage(image_path, thread_id, thread_type)
            if not uploadImage or "normalUrl" not in uploadImage:
                raise Exception("Không thể upload ảnh menu lên Zalo")
                
            photo_params = {
                "photoId": uploadImage.get("photoId", int(now() * 2)),
                "clientId": uploadImage.get("clientFileId", int(now() - 1000)),
                "desc": command_names,
                "width": 1280,
                "height": 933,
                "rawUrl": uploadImage["normalUrl"],
                "thumbUrl": uploadImage["thumbUrl"],
                "hdUrl": uploadImage["hdUrl"],
                "thumbSize": "53932",
                "fileSize": "247671",
                "hdSize": "344622",
                "zsource": -1,
                "jcp": json.dumps({"sendSource": 1, "convertible": "jxl"}),
                "ttl": 60000,
                "imei": bot._imei
            }
            
            photo_params["mentionInfo"] = str(Mention(author_id, length=len(user_name), offset=0))
            photo_params["textProperties"] = str(multi_style)
            
            photo_params["qmsgOwner"] = str(int(message_object.uidFrom) or bot.uid)
            photo_params["qmsgId"] = message_object.msgId
            photo_params["qmsgCliId"] = message_object.cliMsgId
            photo_params["qmsgType"] = getClientMessageType(message_object.msgType)
            photo_params["qmsg"] = message_object.content
            photo_params["qmsgTs"] = message_object.ts
            photo_params["qmsgAttach"] = json.dumps(message_object.content.toDict()) if not isinstance(message_object.content, str) else json.dumps({})
            photo_params["qmsgTTL"] = 0
            
            is_group = False
            if hasattr(thread_type, "value"):
                is_group = (thread_type.value == ThreadType.GROUP.value)
            else:
                is_group = (thread_type == ThreadType.GROUP or thread_type == 1 or str(thread_type).lower() in ["group", "1"])
                
            if is_group:
                photo_params["grid"] = str(thread_id)
                photo_params["oriUrl"] = uploadImage["normalUrl"]
            else:
                photo_params["toid"] = str(thread_id)
                photo_params["normalUrl"] = uploadImage["normalUrl"]
            
            bot.sendLocalImage(
                imagePath=image_path,
                thread_id=thread_id,
                thread_type=thread_type,
                width=1280,
                height=933,
                custom_payload={"params": photo_params},
                ttl=60000
            )
        except Exception as e:
            print(f"❌ Lỗi khi gửi ảnh menu qua custom_payload: {e}")
            bot.replyMessage(
                Message(
                    text=command_names,
                    mention=Mention(author_id, length=len(user_name), offset=0),
                    style=multi_style
                ),
                message_object,
                thread_id,
                thread_type
            )
            
        try:
            os.remove(image_path)
        except Exception as e:
            print(f"❌ Lỗi khi xóa ảnh: {e}")
    else:
        bot.replyMessage(
            Message(
                text=command_names,
                mention=Mention(author_id, length=len(user_name), offset=0),
                style=multi_style
            ),
            message_object,
            thread_id,
            thread_type
        )

def get_dominant_color(image_path):
    try:
        if not os.path.exists(image_path):
            return (0, 0, 0)
        img = Image.open(image_path).convert("RGB")
        img = img.resize((150, 150), Image.Resampling.LANCZOS)
        pixels = img.getdata()
        if not pixels:
            return (0, 0, 0)
        r, g, b = 0, 0, 0
        for pixel in pixels:
            r += pixel[0]
            g += pixel[1]
            b += pixel[2]
        total = len(pixels)
        if total == 0:
            return (0, 0, 0)
        return (r // total, g // total, b // total)
    except Exception as e:
        print(f"Lỗi khi phân tích màu nổi bật: {e}")
        return (0, 0, 0)

def random_contrast_color(base_color):
    r, g, b, _ = base_color
    box_luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    if box_luminance > 0.5:
        r, g, b = random.randint(0, 50), random.randint(0, 50), random.randint(0, 50)
    else:
        r, g, b = random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    s = min(1.0, s + 0.9)
    v = min(1.0, v + 0.7)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255), 255)

def download_avatar(avatar_url, save_path=os.path.join(CACHE_PATH, "user_avatar.png")):
    if not avatar_url:
        return None
    try:
        resp = requests.get(avatar_url, stream=True, timeout=5) 
        if resp.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            return save_path
    except Exception as e:
        print(f"❌ Lỗi tải avatar: {e}")
    return None

def generate_menu_image(self, author_id, thread_id, thread_type, columns=None, current_page=1, total_pages=1, category_name=None):
    size = (1920, 1400)
    final_size = (1280, 933)
    
    # 1. Tải ảnh nền anime ngẫu nhiên từ file anime.txt
    bg_image = None
    temp_bg_path = os.path.join(CACHE_PATH, f"temp_menu_bg_{random.randint(1000, 9999)}.jpg")
    
    anime_txt_path = "modules/data-send/anime.txt"
    if os.path.exists(anime_txt_path):
        try:
            with open(anime_txt_path, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip().startswith("http")]
            if urls:
                for _ in range(3):
                    url = random.choice(urls)
                    try:
                        resp = requests.get(url, timeout=3)
                        if resp.status_code == 200:
                            with open(temp_bg_path, "wb") as f_bg:
                                f_bg.write(resp.content)
                            with Image.open(temp_bg_path) as test_img:
                                test_img.verify()
                            bg_image = Image.open(temp_bg_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
                            break
                    except Exception as e:
                        print(f"[Menu BG] Lỗi khi tải ảnh từ URL {url}: {e}")
                        if os.path.exists(temp_bg_path):
                            try:
                                os.remove(temp_bg_path)
                            except:
                                pass
        except Exception as e:
            print(f"[Menu BG] Lỗi đọc file anime.txt: {e}")
            
    if bg_image is None:
        images = glob.glob(BACKGROUND_PATH + "*.jpg") + glob.glob(BACKGROUND_PATH + "*.png") + glob.glob(BACKGROUND_PATH + "*.jpeg")
        if images:
            image_path = random.choice(images)
            bg_image = Image.open(image_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        else:
            bg_image = Image.new("RGBA", size, (15, 15, 15, 255))

    try:
        bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=10))  
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Trích xuất màu nổi bật để tính toán độ tương phản nếu cần
        if os.path.exists(temp_bg_path):
            dominant_color = get_dominant_color(temp_bg_path)
        else:
            dominant_color = (15, 15, 15)
        
        box_color = (15, 15, 15, 185)
        box_x1, box_y1 = 80, 60
        box_x2, box_y2 = size[0] - 80, size[1] - 60
        draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=50, fill=box_color)

        font_arial_path = "font/arial unicode ms.otf"
        font_emoji_path = "font/NotoEmoji-Bold.ttf"
        
        try:
            font_time = ImageFont.truetype(font_arial_path, 48)
            font_date = ImageFont.truetype(font_arial_path, 28)
            font_icon = ImageFont.truetype(font_emoji_path, 52)
        except Exception as e:
            print(f"❌ Lỗi tải font: {e}")
            font_time = ImageFont.load_default()
            font_date = ImageFont.load_default()
            font_icon = ImageFont.load_default()

        def draw_text_with_shadow(draw, position, text, font, fill, shadow_color=(0, 0, 0, 240), shadow_offset=(2, 2)):
            x, y = position
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_color)
            draw.text((x, y), text, font=font, fill=fill)

        vietnam_now = datetime.now(timezone(timedelta(hours=7)))
        hour = vietnam_now.hour
        formatted_time = vietnam_now.strftime("%H:%M")
        time_icon = "🌤️" if 6 <= hour < 18 else "🌙"
        time_text = f" {formatted_time}"
        time_color = (255, 255, 255, 255)

        user_info = self.fetchUserInfo(author_id) if author_id else None
        user_name = "User"
        if user_info and hasattr(user_info, 'changed_profiles') and author_id in user_info.changed_profiles:
            user = user_info.changed_profiles[author_id]
            user_name = getattr(user, 'name', None) or getattr(user, 'displayName', None) or f"ID_{author_id}"

        from core.bot_sys import read_settings
        settings = read_settings(self.uid)
        high_level_admins = settings.get("high_level_admins", [])
        admin_bot = settings.get("admin_bot", [])
        silver_users = settings.get("silver_users", [])

        role_tag = ""
        if author_id in high_level_admins:
            role_tag = " (Super Admin)"
        elif author_id in admin_bot:
            role_tag = " (Admin)"
        elif author_id in silver_users:
            role_tag = " (Key Bạc)"

        greeting_name = f"{user_name}{role_tag}"

        # Header - Avatar & Welcome Greeting
        avatar_url = user_info.changed_profiles[author_id].avatar if user_info and author_id in user_info.changed_profiles else None
        avatar_path = download_avatar(avatar_url)
        avatar_size = 120
        avatar_y = box_y1 + 30
        
        if avatar_path and os.path.exists(avatar_path):
            try:
                avatar_img = Image.open(avatar_path).convert("RGBA").resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
                
                border_size = avatar_size + 10
                rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
                draw_border = ImageDraw.Draw(rainbow_border)
                steps = 360
                for j in range(steps):
                    h = j / steps
                    r_c, g_c, b_c = colorsys.hsv_to_rgb(h, 1.0, 1.0)
                    draw_border.arc([(0, 0), (border_size-1, border_size-1)], j, j + (360 / steps), fill=(int(r_c * 255), int(g_c * 255), int(b_c * 255), 255), width=4)
                
                overlay.paste(rainbow_border, (box_x1 + 40, avatar_y - 5), rainbow_border)
                overlay.paste(avatar_img, (box_x1 + 45, avatar_y), mask)
                avatar_img.close()
                rainbow_border.close()
            except Exception as ex:
                print(f"Lỗi paste avatar: {ex}")

        greeting_x = box_x1 + 40 + avatar_size + 30
        greeting_y = avatar_y + 15
        greeting_text = f"Hi, {greeting_name}"
        sub_greeting_text = "Chúc bạn một ngày tốt lành! Danh sách lệnh bot hỗ trợ:"
        
        try:
            font_greeting = ImageFont.truetype(font_arial_path, 40)
            font_sub_greeting = ImageFont.truetype(font_arial_path, 22)
        except:
            font_greeting = ImageFont.load_default()
            font_sub_greeting = ImageFont.load_default()
            
        greeting_color = (255, 215, 0, 255)
        draw_text_with_shadow(draw, (greeting_x, greeting_y), greeting_text, font_greeting, greeting_color)
        draw.text((greeting_x, greeting_y + 52), sub_greeting_text, font=font_sub_greeting, fill=(200, 200, 200, 255))

        # Header - Time & Date
        time_x = box_x2 - 280
        time_y = box_y1 + 30
        try:
            draw_text_with_shadow(draw, (time_x - 65, time_y - 5), time_icon, font_icon, (255, 215, 0, 255))
            draw.text((time_x, time_y), time_text, font=font_time, fill=time_color)
            formatted_date = vietnam_now.strftime("%d/%m/%Y")
            draw_text_with_shadow(draw, (time_x + 10, time_y + 58), formatted_date, font_date, (180, 180, 180, 255))
        except Exception as e:
            print(f"Error drawing time: {e}")
            
        # Header - Small bot version info
        bot_info_text = f" Bot: {self.me_name} | v{self.version}"
        bot_info_color = (0, 230, 118, 255)
        try:
            font_info_small = ImageFont.truetype(font_arial_path, 20)
        except:
            font_info_small = ImageFont.load_default()
        
        try:
            emoji_w = draw.textbbox((0, 0), "🤖", font=font_icon)[2]
        except:
            emoji_w = 20
        
        text_w = draw.textbbox((0, 0), bot_info_text, font=font_info_small)[2]
        total_w = emoji_w + 3 + text_w
        start_info_x = box_x2 - 40 - total_w
        info_y = time_y + 92
        
        try:
            draw.text((start_info_x, info_y - 2), "🤖", font=font_icon, fill=bot_info_color)
            draw_text_with_shadow(draw, (start_info_x + emoji_w + 3, info_y), bot_info_text, font_info_small, bot_info_color)
        except:
            draw_text_with_shadow(draw, (start_info_x, info_y), f"🤖{bot_info_text}", font_info_small, bot_info_color)

        # Draw total system commands count
        total_commands = len(txacommand.loaded_commands)
        total_commands_text = f" Tổng lệnh: {total_commands}"
        total_commands_color = (255, 235, 59, 255)
        
        try:
            cmd_emoji_w = draw.textbbox((0, 0), "⚡", font=font_icon)[2]
        except:
            cmd_emoji_w = 20
            
        cmd_text_w = draw.textbbox((0, 0), total_commands_text, font=font_info_small)[2]
        cmd_total_w = cmd_emoji_w + 3 + cmd_text_w
        start_cmd_x = box_x2 - 40 - cmd_total_w
        cmd_y = info_y + 25
        
        try:
            draw.text((start_cmd_x, cmd_y - 2), "⚡", font=font_icon, fill=total_commands_color)
            draw_text_with_shadow(draw, (start_cmd_x + cmd_emoji_w + 3, cmd_y), total_commands_text, font_info_small, total_commands_color)
        except:
            draw_text_with_shadow(draw, (start_cmd_x, cmd_y), f"⚡{total_commands_text}", font_info_small, total_commands_color)

        # Body - Columns drawing
        if columns:
            y_start = 240
            col_width = 380
            spacing = 60
            left_margin = 110
            
            # Pre-calculate column heights to see if we need scaling
            max_col_height = 0
            for col_items in columns:
                col_h = 0
                first_item = True
                for item in col_items:
                    if item["type"] == "title":
                        if not first_item:
                            col_h += 18
                        col_h += 42
                        first_item = False
                    elif item["type"] == "cmd":
                        col_h += 33
                        first_item = False
                max_col_height = max(max_col_height, col_h)
            
            # Để chừa không gian vẽ footer ở bottom
            available_height = (box_y2 - 65) - y_start
            
            scale = 1.0
            if max_col_height > available_height:
                scale = available_height / max_col_height
                scale = max(0.5, scale)
                
            title_font_size = max(12, int(28 * scale))
            cmd_font_size = max(11, int(22 * scale))
            desc_font_size = max(11, int(22 * scale))
            bullet_font_size = max(10, int(20 * scale))
            
            title_height_step = max(16, int(42 * scale))
            cmd_height_step = max(13, int(33 * scale))
            gap_step = max(6, int(18 * scale))

            try:
                font_title = ImageFont.truetype(font_arial_path, title_font_size)
                font_cmd = ImageFont.truetype(font_arial_path, cmd_font_size)
                font_desc = ImageFont.truetype(font_arial_path, desc_font_size)
                font_bullet = ImageFont.truetype(font_emoji_path, bullet_font_size)
            except:
                font_title = ImageFont.load_default()
                font_cmd = ImageFont.load_default()
                font_desc = ImageFont.load_default()
                font_bullet = ImageFont.load_default()

            # Beautiful neon palette
            neon_palette = [
                (0, 229, 255, 255),    # Cyan Neon
                (255, 64, 129, 255),   # Pink Neon
                (255, 235, 59, 255),   # Yellow Neon
                (0, 230, 118, 255),    # Green Neon
                (170, 0, 255, 255),    # Purple Neon
                (255, 109, 0, 255),    # Orange Neon
                (41, 121, 255, 255)    # Blue Neon
            ]
            color_idx = 0
            
            desc_color = (235, 235, 235, 255)
            bullet_color = (180, 180, 180, 255)

            for col_idx, col_items in enumerate(columns):
                x_pos = left_margin + col_idx * (col_width + spacing)
                y_pos = y_start
                
                title_color = neon_palette[color_idx % len(neon_palette)]
                cmd_color = title_color
                
                for item in col_items:
                    if item["type"] == "title":
                        if y_pos > y_start:
                            y_pos += gap_step
                            
                        title_color = neon_palette[color_idx % len(neon_palette)]
                        cmd_color = title_color
                        color_idx += 1
                            
                        parts = item["text"].split()
                        emoji_part = parts[0] if parts else "❖"
                        text_part = " " + " ".join(parts[1:]) if len(parts) > 1 else ""
                        
                        try:
                            draw.text((x_pos, y_pos), emoji_part, font=font_bullet, fill=title_color)
                            emoji_w = draw.textbbox((0, 0), emoji_part, font=font_bullet)[2]
                            current_x = x_pos + emoji_w + 5
                            for char in text_part:
                                draw_text_with_shadow(draw, (current_x, y_pos), char, font_title, title_color)
                                char_w = draw.textbbox((0, 0), char, font=font_title)[2]
                                current_x += char_w + 1
                        except:
                            current_x = x_pos
                            for char in item["text"]:
                                if emoji.emoji_count(char) > 0:
                                    draw.text((current_x, y_pos), char, font=font_bullet, fill=title_color)
                                    char_w = draw.textbbox((0, 0), char, font=font_bullet)[2]
                                else:
                                    draw_text_with_shadow(draw, (current_x, y_pos), char, font_title, title_color)
                                    char_w = draw.textbbox((0, 0), char, font=font_title)[2]
                                current_x += char_w + 1
                        y_pos += title_height_step
                    elif item["type"] == "cmd":
                        bullet = "• "
                        cmd_str = item["cmd"]
                        desc_str = f" - {item['desc']}"
                        char_spacing = 1
                        
                        draw.text((x_pos, y_pos), bullet, font=font_cmd, fill=bullet_color)
                        bullet_w = draw.textbbox((0, 0), bullet, font=font_cmd)[2]
                        
                        current_x = x_pos + bullet_w
                        for char in cmd_str:
                            if emoji.emoji_count(char) > 0:
                                draw.text((current_x, y_pos), char, font=font_bullet, fill=cmd_color)
                                char_w = draw.textbbox((0, 0), char, font=font_bullet)[2]
                            else:
                                draw_text_with_shadow(draw, (current_x, y_pos), char, font_cmd, cmd_color)
                                char_w = draw.textbbox((0, 0), char, font=font_cmd)[2]
                            current_x += char_w + char_spacing
                        cmd_w = current_x - (x_pos + bullet_w)
                        
                        avail_width = col_width - bullet_w - cmd_w - 10
                        truncated_desc = desc_str
                        desc_w = 0
                        for char in truncated_desc:
                            if emoji.emoji_count(char) > 0:
                                desc_w += draw.textbbox((0, 0), char, font=font_bullet)[2]
                            else:
                                desc_w += draw.textbbox((0, 0), char, font=font_desc)[2]
                            desc_w += char_spacing
                        desc_w -= char_spacing
                        
                        if desc_w > avail_width:
                            for k in range(len(desc_str), 0, -1):
                                truncated_desc = desc_str[:k] + "..."
                                desc_w = 0
                                for char in truncated_desc:
                                    if emoji.emoji_count(char) > 0:
                                        desc_w += draw.textbbox((0, 0), char, font=font_bullet)[2]
                                    else:
                                        desc_w += draw.textbbox((0, 0), char, font=font_desc)[2]
                                    desc_w += char_spacing
                                desc_w -= char_spacing
                                if desc_w <= avail_width:
                                    break
                                    
                        current_x = x_pos + bullet_w + cmd_w
                        for char in truncated_desc:
                            if emoji.emoji_count(char) > 0:
                                draw.text((current_x, y_pos), char, font=font_bullet, fill=desc_color)
                                char_w = draw.textbbox((0, 0), char, font=font_bullet)[2]
                            else:
                                draw.text((current_x, y_pos), char, font=font_desc, fill=desc_color)
                                char_w = draw.textbbox((0, 0), char, font=font_desc)[2]
                            current_x += char_w + char_spacing
                        y_pos += cmd_height_step

        # 5. Vẽ footer căn giữa
        if category_name:
            footer_text = f"📂 Danh mục: {category_name} | CREATE BY TXA"
        else:
            footer_text = f"📖 Trang {current_page} / {total_pages} | CREATE BY TXA"
            
        try:
            font_footer = ImageFont.truetype(font_arial_path, 24)
        except:
            font_footer = ImageFont.load_default()
            
        footer_w = draw.textbbox((0, 0), footer_text, font=font_footer)[2]
        footer_x = box_x1 + (box_x2 - box_x1 - footer_w) // 2
        footer_y = box_y2 - 55
        
        draw_text_with_shadow(draw, (footer_x, footer_y), footer_text, font_footer, (255, 235, 59, 255))

        final_image = Image.alpha_composite(bg_image, overlay)
        final_image = final_image.resize(final_size, Image.Resampling.LANCZOS)
        
        os.makedirs(os.path.dirname(OUTPUT_IMAGE_PATH), exist_ok=True)
        final_image.convert("RGB").save(OUTPUT_IMAGE_PATH, "JPEG", quality=95, optimize=True)
        
        bg_image.close()
        final_image.close()
        overlay.close()
        
        if os.path.exists(temp_bg_path):
            try:
                os.remove(temp_bg_path)
            except:
                pass
                
        return OUTPUT_IMAGE_PATH

    except Exception as e:
        print(f"❌ Lỗi xử lý ảnh menu: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_bg_path):
            try:
                os.remove(temp_bg_path)
            except:
                pass
        return None

txa = {
    "name": "pro_menu",
    "desc": "Menu chính hiển thị danh sách lệnh bot với giao diện ảnh đẹp. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['menu']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'menu': handle_menu_commands
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
