import os
import json
import requests
import tempfile
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from zlapi.models import Message

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.abspath(os.path.join(BASE_DIR, "../../../txa.json"))
FONT_EMOJI = os.path.abspath(os.path.join(BASE_DIR, "../../../font/NotoEmoji-Bold.ttf"))
FONT_ARIAL = os.path.abspath(os.path.join(BASE_DIR, "../../../font/arial unicode ms.otf"))
FONT_UNICODE_BOLD = os.path.abspath(os.path.join(BASE_DIR, "../../../font/arial unicode ms bold.otf"))

KAIROBOT_BASE_URL = os.getenv("KAIROBOT_BASE_URL", "https://kairobot.qzz.io").rstrip("/")

def _read_api_key():
    """Read API key from environment or config file."""
    for key in ("KAIROBOT_APIKEY", "KAIROBOT_API_KEY", "TXA_APIKEY", "TXA_API_KEY"):
        value = os.getenv(key)
        if value:
            return value.strip()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        bot_data = (config.get("data") or [{}])[0]
        for key in ("kairobot_api_key", "kairobot_apikey", "apikey", "api_key"):
            value = bot_data.get(key)
            if value:
                return str(value).strip()
    except Exception:
        pass
    return ""

def get_freefire_data(uid):
    """Fetch Free Fire player data from KaiRobot API."""
    try:
        api_key = _read_api_key()
        if not api_key:
            raise RuntimeError("Thiếu API key KaiRobot.")
        
        url = f"{KAIROBOT_BASE_URL}/freefire/player-info/{uid}"
        params = {"apikey": api_key}
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return None
        
        if isinstance(data, dict) and "data" in data:
            inner = data["data"]
            if isinstance(inner, dict):
                if "basicInfo" in inner or "profileInfo" in inner:
                    return inner
                if "data" in inner and isinstance(inner["data"], dict):
                    return inner["data"]
            return inner
        
        if isinstance(data, dict) and ("basicInfo" in data or "profileInfo" in data):
            return data
        
        if isinstance(data, list) and len(data) > 0:
            first = data[0]
            if isinstance(first, dict) and ("basicInfo" in first or "profileInfo" in first):
                return first
        
        return data
            
    except Exception as e:
        print(f"[ERROR] Lỗi khi lấy dữ liệu Free Fire: {e}")
        return None

def get_rank_name(rank_value):
    """Convert rank number to rank name (Free Fire BR ranking system - Latest)."""
    if not rank_value:
        return "Không xác định"

    try:
        rank_num = int(rank_value)
    except:
        return str(rank_value)

    # Latest Free Fire BR Ranking Points System (Vietnamese)
    if rank_num < 1000:
        return "Đồng I"
    elif rank_num < 1300:
        return "Đồng III"
    elif rank_num < 1400:
        return "Bạc I"
    elif rank_num < 1500:
        return "Bạc II"
    elif rank_num < 1600:
        return "Bạc III"
    elif rank_num < 1725:
        return "Vàng I"
    elif rank_num < 1850:
        return "Vàng II"
    elif rank_num < 1975:
        return "Vàng III"
    elif rank_num < 2100:
        return "Vàng IV"
    elif rank_num < 2225:
        return "Bạch Kim I"
    elif rank_num < 2350:
        return "Bạch Kim II"
    elif rank_num < 2475:
        return "Bạch Kim III"
    elif rank_num < 2600:
        return "Bạch Kim IV"
    elif rank_num < 2750:
        return "Bạch Kim V"
    elif rank_num < 2900:
        return "Kim Cương I"
    elif rank_num < 3050:
        return "Kim Cương II"
    elif rank_num < 3200:
        return "Kim Cương III"
    elif rank_num < 3350:
        return "Kim Cương IV"
    elif rank_num < 3500:
        return "Kim Cương V"
    elif rank_num < 4300:
        return "Huyền thoại"
    elif rank_num < 4900:
        return "Huyền thoại - Siêu Huyền thoại"
    elif rank_num < 6300:
        return "Siêu Huyền thoại"
    elif rank_num < 7100:
        return "Cao thủ 1 sao"
    elif rank_num < 8000:
        return "Cao thủ 2 sao"
    elif rank_num < 9000:
        return "Đại cao thủ 3 sao"
    elif rank_num < 10000:
        return "Đại cao thủ 4 sao"
    else:
        return "Thách đấu"

def get_cs_rank_name(cs_rank_value):
    """Convert CS rank number to rank name (Free Fire CS ranking system)."""
    if not cs_rank_value:
        return "Không xác định"

    try:
        cs_rank_num = int(cs_rank_value)
    except:
        return str(cs_rank_value)

    # Free Fire Clash Squad Ranking System (Vietnamese)
    # Bronze (Đồng): 0 to 8 stars
    if cs_rank_num < 9:
        if cs_rank_num < 3:
            return "Đồng I"
        elif cs_rank_num < 6:
            return "Đồng II"
        else:
            return "Đồng III"
    # Silver (Bạc): 9 to 20 stars
    elif cs_rank_num < 21:
        if cs_rank_num < 13:
            return "Bạc I"
        elif cs_rank_num < 17:
            return "Bạc II"
        else:
            return "Bạc III"
    # Gold (Vàng): 21 to 36 stars
    elif cs_rank_num < 37:
        if cs_rank_num < 25:
            return "Vàng I"
        elif cs_rank_num < 29:
            return "Vàng II"
        elif cs_rank_num < 33:
            return "Vàng III"
        else:
            return "Vàng IV"
    # Platinum (Bạch Kim): 37 to 56 stars
    elif cs_rank_num < 57:
        if cs_rank_num < 42:
            return "Bạch Kim I"
        elif cs_rank_num < 47:
            return "Bạch Kim II"
        elif cs_rank_num < 52:
            return "Bạch Kim III"
        else:
            return "Bạch Kim IV"
    # Diamond (Kim Cương): 57 to 86 stars
    elif cs_rank_num < 87:
        if cs_rank_num < 63:
            return "Kim Cương I"
        elif cs_rank_num < 69:
            return "Kim Cương II"
        elif cs_rank_num < 75:
            return "Kim Cương III"
        elif cs_rank_num < 81:
            return "Kim Cương IV"
        else:
            return "Kim Cương V"
    # Heroic and above (Huyền thoại trở lên): >= 87 stars
    else:
        stars = cs_rank_num - 87
        if stars <= 0:
            stars = 1
        
        # Tiers by stars:
        # - Huyền thoại: 1 - 24 sao
        # - Siêu huyền thoại: 25 - 49 sao
        # - Cao thủ: 50 - 99 sao
        # - Đại Cao Thủ: >= 100 sao
        if stars < 25:
            return f"Huyền thoại {stars}★"
        elif stars < 50:
            return f"Siêu huyền thoại {stars}★"
        elif stars < 100:
            return f"Cao thủ {stars}★"
        else:
            return f"Đại Cao Thủ {stars}★"

def create_freefire_card(data, output_path):
    """Create beautiful Free Fire player card image."""
    try:
        if not data:
            return False
            
        # KaiRobot API returns data directly with basicInfo, profileInfo, etc.
        basic_info = data.get("basicInfo", {})
        profile_info = data.get("profileInfo", {})
        clan_info = data.get("clanBasicInfo", {})
        social_info = data.get("socialInfo", {})
        
        # Extract data
        nickname = basic_info.get("nickname", "Unknown")
        uid = basic_info.get("accountId", "Unknown")
        level = basic_info.get("level", 0)
        region = basic_info.get("region", "Unknown")
        rank_value = basic_info.get("rankingPoints", 0)
        cs_rank_value = basic_info.get("csRankingPoints", 0)
        rank_name = get_rank_name(rank_value)
        cs_rank_name = get_cs_rank_name(cs_rank_value)
        exp = basic_info.get("exp", 0)
        likes = basic_info.get("liked", 0)
        badge_cnt = basic_info.get("badgeCnt", 0)
        prime_level = basic_info.get("primePrivilegeDetail", {}).get("primeLevel", 0)
        
        clan_name = clan_info.get("clanName") or clan_info.get("name") or "Không có"
        clan_level = clan_info.get("clanLevel", 0)
        
        gender = social_info.get("gender", "").replace("Gender_", "").title() if social_info.get("gender") else "Unknown"
        language = social_info.get("language", "").replace("Language_", "").title() if social_info.get("language") else "Unknown"
        
        # Image dimensions
        width, height = 1080, 720
        
        # Create image with modern gradient background
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw dark gaming gradient background
        for y in range(height):
            ratio = y / height
            # Gradient from dark purple/black to deep violet-blue
            r = int(10 + (22 * ratio))
            g = int(8 + (12 * ratio))
            b = int(20 + (42 * ratio))
            draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b, 255))
            
        # Draw very subtle tech lines on background (diagonal gaming stripes, sparse)
        stripe_draw = ImageDraw.Draw(img)
        for x_offset in range(-width, width, 140):
            stripe_draw.line([(x_offset, 0), (x_offset + height, height)], fill=(255, 255, 255, 2), width=1)

        # Glassmorphism main card panel
        card_x, card_y = 50, 110
        card_w, card_h = width - 100, height - 190
        
        # Composite semi-transparent panel background
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Rounded rectangle with transparency
        overlay_draw.rounded_rectangle(
            [(card_x, card_y), (card_x + card_w, card_y + card_h)],
            radius=24,
            fill=(255, 255, 255, 12),
            outline=(255, 255, 255, 45),
            width=2
        )
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        try:
            # Try loading SF-Pro if it exists in font directory, otherwise fallback to FONT_ARIAL
            font_dir = os.path.abspath(os.path.join(BASE_DIR, "../../../font"))
            sf_pro_path = os.path.join(font_dir, "SF-Pro.ttf")
            font_to_use = sf_pro_path if os.path.exists(sf_pro_path) else FONT_ARIAL
            
            font_title = ImageFont.truetype(font_to_use, 48)
            font_nickname = ImageFont.truetype(FONT_UNICODE_BOLD, 38)  # Use FONT_UNICODE_BOLD to support superscript letters and symbols without boxes
            font_large = ImageFont.truetype(font_to_use, 38)
            font_medium = ImageFont.truetype(font_to_use, 26)
            font_sub = ImageFont.truetype(font_to_use, 20)
            font_small = ImageFont.truetype(font_to_use, 16)
        except Exception as e:
            print(f"Font loading error: {e}")
            font_title = font_nickname = font_large = font_medium = font_sub = font_small = ImageFont.load_default()

        # Draw Title: "FREE FIRE PROFILE"
        title_text = "FREE FIRE PROFILE"
        title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
        title_x = (width - title_bbox[2]) // 2
        # Draw text glow
        draw.text((title_x - 1, 40 - 1), title_text, font=font_title, fill=(255, 50, 50, 80))
        draw.text((title_x + 1, 40 + 1), title_text, font=font_title, fill=(255, 50, 50, 80))
        draw.text((title_x, 40), title_text, font=font_title, fill=(255, 70, 85, 255)) # Vibrant FF Red

        # Nickname and basic info on left
        x_left = card_x + 50
        y_pos = card_y + 40
        
        # Level Badge & VIP Badge
        badge_w, badge_h = 100, 36
        overlay_badge = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        ob_draw = ImageDraw.Draw(overlay_badge)
        
        # Draw LV Badge
        ob_draw.rounded_rectangle([(x_left, y_pos), (x_left + badge_w, y_pos + badge_h)], radius=8, fill=(255, 193, 7, 255))
        
        # Draw VIP Badge if prime_level > 0
        vip_offset = 0
        if prime_level > 0:
            vip_offset = 120
            ob_draw.rounded_rectangle([(x_left + badge_w + 10, y_pos), (x_left + badge_w + 10 + badge_w, y_pos + badge_h)], radius=8, fill=(255, 69, 0, 255)) # Orange-Red for VIP
            
        img = Image.alpha_composite(img, overlay_badge)
        draw = ImageDraw.Draw(img)
        
        # Draw LV Text
        lvl_text = f"LV.{level}"
        lvl_bbox = draw.textbbox((0, 0), lvl_text, font=font_small)
        lvl_x = x_left + (badge_w - lvl_bbox[2]) // 2
        lvl_y = y_pos + (badge_h - lvl_bbox[3]) // 2 - 2
        draw.text((lvl_x, lvl_y), lvl_text, font=font_small, fill=(0, 0, 0, 255))
        
        # Draw VIP Text
        if prime_level > 0:
            vip_text = f"VIP {prime_level}"
            vip_bbox = draw.textbbox((0, 0), vip_text, font=font_small)
            vip_x = x_left + badge_w + 10 + (badge_w - vip_bbox[2]) // 2
            vip_y = y_pos + (badge_h - vip_bbox[3]) // 2 - 2
            draw.text((vip_x, vip_y), vip_text, font=font_small, fill=(255, 255, 255, 255))
            
        # Nickname (right next to badges)
        draw.text((x_left + badge_w + 20 + vip_offset, y_pos - 4), nickname, font=font_nickname, fill=(255, 255, 255, 255))
        y_pos += 55
        
        # UID & Region
        draw.text((x_left, y_pos), f"UID: {uid}", font=font_sub, fill=(180, 185, 210, 255))
        draw.text((x_left + 280, y_pos), f"Region: {region}", font=font_sub, fill=(180, 185, 210, 255))
        y_pos += 40
        
        # Created Date & Days Elapsed
        create_timestamp = int(basic_info.get("createAt", 0))
        if create_timestamp > 0:
            create_date = datetime.fromtimestamp(create_timestamp)
            days_elapsed = (datetime.now() - create_date).days
            create_text = f"Ngày tạo: {create_date.strftime('%d/%m/%Y')} ({days_elapsed} ngày)"
            draw.text((x_left, y_pos), create_text, font=font_sub, fill=(180, 185, 210, 255))
            y_pos += 40
        
        # Draw horizontal divider
        draw.line([(x_left, y_pos), (card_x + card_w - 50, y_pos)], fill=(255, 255, 255, 25), width=1)
        y_pos += 30

        # Layout: Stats on Left, Rank Cards on Right
        stats_y = y_pos
        def draw_stat_item(x, y, label, val, val_color=(255, 255, 255, 255)):
            draw.text((x, y), label, font=font_sub, fill=(140, 145, 170, 255))
            draw.text((x, y + 25), str(val), font=font_medium, fill=val_color)
            
        gold_coins = basic_info.get("hippoTotalWorth", 0)
        
        draw_stat_item(x_left, stats_y, "EXP", f"{exp:,}", (100, 200, 255, 255))
        draw_stat_item(x_left + 190, stats_y, "LIKES", f"{likes:,}", (255, 105, 180, 255))
        draw_stat_item(x_left + 380, stats_y, "VÀNG", f"{gold_coins:,}", (255, 215, 0, 255))
        
        stats_y += 75
        draw_stat_item(x_left, stats_y, "QUÂN ĐOÀN", f"{clan_name}", (0, 230, 118, 255))
        draw_stat_item(x_left + 190, stats_y, "BADGES", f"{badge_cnt}", (255, 140, 0, 255))
        draw_stat_item(x_left + 380, stats_y, "VIP", f"{prime_level}" if prime_level > 0 else "0", (255, 105, 180, 255))
        
        # Extra details below left stats
        extra_y = stats_y + 80
        details = []
        if prime_level > 0:
            details.append(f"VIP {prime_level}")
        details.append(f"Gender: {gender}")
        details.append(f"Lang: {language}")
        draw.text((x_left, extra_y), " | ".join(details), font=font_sub, fill=(160, 165, 190, 255))

        # Right Side: Rank Cards (BR Rank, CS Rank)
        right_x = card_x + card_w - 450
        rank_box_w = 400
        rank_box_h = 100
        
        # BR Rank Box (Dark filled background with border glow)
        br_y = y_pos - 10
        br_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        br_o_draw = ImageDraw.Draw(br_overlay)
        br_o_draw.rounded_rectangle([(right_x, br_y), (right_x + rank_box_w, br_y + rank_box_h)], radius=12, fill=(0, 0, 0, 80), outline=(255, 140, 0, 150), width=2)
        img = Image.alpha_composite(img, br_overlay)
        draw = ImageDraw.Draw(img)
        
        # Title of box
        draw.text((right_x + 20, br_y + 15), "BATTLE ROYALE", font=font_small, fill=(255, 140, 0, 255))
        draw.text((right_x + 20, br_y + 42), rank_name, font=font_medium, fill=(255, 255, 255, 255))
        draw.text((right_x + rank_box_w - 20, br_y + 44), f"Points: {rank_value}", font=font_sub, fill=(180, 185, 210, 255), anchor="ra")

        # CS Rank Box
        cs_y = br_y + rank_box_h + 20
        cs_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        cs_o_draw = ImageDraw.Draw(cs_overlay)
        cs_o_draw.rounded_rectangle([(right_x, cs_y), (right_x + rank_box_w, cs_y + rank_box_h)], radius=12, fill=(0, 0, 0, 80), outline=(0, 200, 255, 150), width=2)
        img = Image.alpha_composite(img, cs_overlay)
        draw = ImageDraw.Draw(img)
        
        # Title of box
        draw.text((right_x + 20, cs_y + 15), "CLASH SQUAD", font=font_small, fill=(0, 200, 255, 255))
        draw.text((right_x + 20, cs_y + 42), cs_rank_name, font=font_medium, fill=(255, 255, 255, 255))
        draw.text((right_x + rank_box_w - 20, cs_y + 44), f"Stars: {cs_rank_value}", font=font_sub, fill=(180, 185, 210, 255), anchor="ra")

        # Footer with timestamp
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        footer_text = f"TXABOT • {timestamp}"
        footer_bbox = draw.textbbox((0, 0), footer_text, font=font_small)
        footer_x = (width - footer_bbox[2]) // 2
        draw.text((footer_x, height - 45), footer_text, font=font_small, fill=(110, 115, 140, 255))

        # Save image
        img.save(output_path, "PNG")
        return True
        
    except Exception as e:
        print(f"[ERROR] Lỗi khi tạo card Free Fire: {e}")
        return False

def handle_freefire_uid(bot, message_object, thread_id, thread_type, uid):
    """Handle Free Fire UID command."""
    loading_msg = bot.send(Message(text=f"🔍 Đang lấy thông tin UID {uid}... Vui lòng đợi ⏳"), thread_id, thread_type, ttl=60000)
    
    try:
        # Fetch data
        data = get_freefire_data(uid)
        
        if not data:
            bot.send(Message(text=f"❌ Không thể lấy thông tin cho UID {uid}. Vui lòng kiểm tra lại UID hoặc thử lại sau."), thread_id, thread_type)
            try:
                bot.deleteMessage(loading_msg)
            except:
                pass
            return
        
        # Check if data is valid (KaiRobot returns data directly)
        if not data or not isinstance(data, dict):
            bot.send(Message(text=f"❌ Dữ liệu trả về không hợp lệ cho UID {uid}."), thread_id, thread_type)
            try:
                bot.deleteMessage(loading_msg)
            except:
                pass
            return
        
        # Create card
        output_path = os.path.join(tempfile.gettempdir(), f"freefire_{uid}_{thread_id}.png")
        success = create_freefire_card(data, output_path)
        
        if success:
            # Construct the detailed profile review text
            basic_info = data.get("basicInfo", {})
            social_info = data.get("socialInfo", {})
            clan_info = data.get("clanBasicInfo", {})
            
            nickname = basic_info.get("nickname", "Unknown")
            level = basic_info.get("level", 0)
            likes = basic_info.get("liked", 0)
            prime_level = basic_info.get("primePrivilegeDetail", {}).get("primeLevel", 0)
            
            rank_value = basic_info.get("rankingPoints", 0)
            cs_rank_value = basic_info.get("csRankingPoints", 0)
            
            # Map ranks
            rank_name = get_rank_name(rank_value)
            cs_rank_name = get_cs_rank_name(cs_rank_value)
            
            # Translate socialInfo
            gender_raw = social_info.get("gender", "")
            gender = "Nam" if "MALE" in gender_raw.upper() else ("Nữ" if "FEMALE" in gender_raw.upper() else "Không xác định")
            
            lang_raw = social_info.get("language", "")
            lang = "Tiếng Việt" if "VIETNAMESE" in lang_raw.upper() else ("Tiếng Anh" if "ENGLISH" in lang_raw.upper() else "Không xác định")
            
            time_act_raw = social_info.get("timeActive", "")
            time_act = "Buổi tối" if "NIGHT" in time_act_raw.upper() else ("Ban ngày" if "DAY" in time_act_raw.upper() else "Không xác định")
            
            time_on_raw = social_info.get("timeOnline", "")
            time_on = "Cuối tuần" if "WEEKEND" in time_on_raw.upper() else ("Ngày thường" if "WEEKDAY" in time_on_raw.upper() else "Không xác định")
            
            mode_pref_raw = social_info.get("modePrefer", "")
            mode_pref = "Clash Squad" if "CS" in mode_pref_raw.upper() else ("Battle Royale" if "BR" in mode_pref_raw.upper() else "Không xác định")
            
            signature = social_info.get("signature", "Không có")
            
            # Fast review
            create_timestamp = int(basic_info.get("createAt", 0))
            year_created = ""
            if create_timestamp > 0:
                year_created = datetime.fromtimestamp(create_timestamp).year
                
            has_clan = clan_info.get("clanId")
            is_captain = has_clan and clan_info.get("captainId") == basic_info.get("accountId")
            
            br_rank_id = basic_info.get("rank", 0)
            cs_rank_id = basic_info.get("csRank", 0)
            cs_peak_points = basic_info.get("csPeakPoints", 0)
            
            review_text = (
                f"✅ Profile Free Fire cho UID {uid}\n\n"
                "📱 THÔNG TIN XÃ HỘI\n"
                f"➜ Giới tính: {gender}\n"
                f"➜ Ngôn ngữ: {lang}\n"
                f"➜ Thời gian chơi chủ yếu: {time_act}\n"
                f"➜ Thời gian online: {time_on}\n"
                f"➜ Chế độ yêu thích: {mode_pref}\n"
                f"➜ Chữ ký: \"{signature}\"\n\n"
                "🏆 THÔNG TIN XẾP HẠNG\n"
                f"➜ Xếp hạng BR (Sinh tồn): {br_rank_id} - {rank_name} (Điểm: {rank_value:,})\n"
                f"➜ Xếp hạng CS (Tử chiến): {cs_rank_id} - {cs_rank_name} (Điểm: {cs_rank_value:,})\n"
                f"➜ Điểm đỉnh cao CS: {cs_peak_points:,}\n\n"
                "⭐ ĐÁNH GIÁ NHANH\n"
            )
            
            if year_created:
                review_text += f"🔥 Tài khoản đời {year_created}\n"
            review_text += f"🔥 Level {level}\n"
            review_text += f"🔥 {likes:,} likes\n"
            if prime_level > 0:
                review_text += f"🔥 Prime {prime_level}\n"
            review_text += f"🔥 BR {rank_name}\n"
            review_text += f"🔥 CS {cs_rank_name}\n"
            
            if is_captain:
                review_text += f"🔥 Có bang riêng ({clan_info.get('clanName', 'Không rõ')})\n"
            elif has_clan:
                review_text += f"🔥 Thành viên bang ({clan_info.get('clanName', 'Không rõ')})\n"
                
            review_text += f"🔥 Điểm BR rất cao ({rank_value} điểm)\n"
            
            # Global assessment
            if level >= 60 and rank_value >= 6000:
                review_text += f"🔥 Hồ sơ thuộc nhóm tài khoản chơi lâu năm và rank cao của máy chủ {basic_info.get('region', 'VN')}"
            else:
                review_text += f"🔥 Tài khoản năng nổ của máy chủ {basic_info.get('region', 'VN')}"

            # Send card image with message
            bot.sendLocalImage(
                output_path,
                message=Message(text=review_text),
                thread_id=thread_id,
                thread_type=thread_type,
                width=1080,
                height=720
            )
            
            # Clean up
            try:
                os.remove(output_path)
            except:
                pass
            
            # Delete loading message
            try:
                bot.deleteMessage(loading_msg)
            except:
                pass
        else:
            bot.send(Message(text=f"❌ Không thể tạo card cho UID {uid}."), thread_id, thread_type)
            try:
                bot.deleteMessage(loading_msg)
            except:
                pass
            
    except Exception as e:
        bot.send(Message(text=f"❌ Lỗi khi xử lý UID Free Fire: {str(e)}"), thread_id, thread_type)
        try:
            bot.deleteMessage(loading_msg)
        except:
            pass

PET_MAP = {
    1300000001: "Mèo Kitty",
    1300000002: "Chó cơ khí",
    1300000003: "Kitty",
    1300000004: "Mechanical Pup",
    1300000005: "Báo Bóng Đêm",
    1300000006: "Shiba",
    1300000007: "Cáo Vũ Trụ",
    1300000008: "Robo",
    1300000009: "Poring",
    1300000010: "Chim Ưng Falco",
    1300000011: "Trợ thủ Waggor",
    1300000012: "Gấu trúc Rockie",
    1300000013: "Khỉ Beaston",
    1300000014: "Rồng Dreki",
    1300000015: "Trợ thủ Moony",
    1300000016: "Vịt Dr. Beanie",
    1300000017: "Hổ Sensei Tig",
    1300000018: "Thỏ Agent Hop",
    1300000019: "Trợ thủ Yeti",
    1300000020: "Rùa Flash",
    1300000021: "Trợ thủ Zasil",
    1300000022: "Cá mập Finn",
    1300000023: "Cú Hoot",
    1300000024: "Sói Fang",
    1300000025: "Xương rồng Kactus",
    1300000061: "Robo",
}

PET_SKILL_MAP = {
    1315000010: "Bức Tường Thép (Robo - Thêm lá chắn cho bom keo)",
}

def handle_freefire_pet(bot, thread_id, thread_type, uid):
    loading_msg = bot.send(Message(text=f"🔍 Đang lấy thông tin trợ thủ cho UID {uid}..."), thread_id, thread_type, ttl=60000)
    try:
        data = get_freefire_data(uid)
        if not data:
            bot.send(Message(text="❌ Không thể lấy dữ liệu trợ thủ cho UID này."), thread_id, thread_type)
            return
        
        basic_info = data.get("basicInfo", {})
        pet_info = data.get("petInfo", {})
        nickname = basic_info.get("nickname", "Unknown")
        
        if not pet_info or not pet_info.get("id"):
            bot.send(Message(text=f"🐾 Người chơi {nickname} hiện không mang theo trợ thủ nào."), thread_id, thread_type)
            return
            
        pet_id = pet_info.get("id")
        pet_name = PET_MAP.get(pet_id, f"Trợ thủ (ID: {pet_id})")
        level = pet_info.get("level", 0)
        exp = pet_info.get("exp", 0)
        skin_id = pet_info.get("skinId", 0)
        skill_id = pet_info.get("selectedSkillId", 0)
        skill_name = PET_SKILL_MAP.get(skill_id, f"Kỹ năng (ID: {skill_id})")
        
        text = (
            "🐾 THÔNG TIN TRỢ THỦ - FREE FIRE\n\n"
            f"👤 Người chơi: {nickname} (UID: {uid})\n"
            f"🐻 Tên trợ thủ: {pet_name}\n"
            f"🧬 Cấp độ: {level} (EXP: {exp:,})\n"
            f"👕 Skin ID: {skin_id}\n"
            f"🔮 Kỹ năng sử dụng: {skill_name}"
        )
        bot.send(Message(text=text), thread_id, thread_type)
    except Exception as e:
        bot.send(Message(text=f"❌ Lỗi khi tải thông tin trợ thủ: {str(e)}"), thread_id, thread_type)
    finally:
        try:
            bot.deleteMessage(loading_msg)
        except:
            pass

def handle_freefire_qd(bot, thread_id, thread_type, uid):
    loading_msg = bot.send(Message(text=f"🔍 Đang lấy thông tin quân đoàn cho UID {uid}..."), thread_id, thread_type, ttl=60000)
    try:
        data = get_freefire_data(uid)
        if not data:
            bot.send(Message(text="❌ Không thể lấy dữ liệu quân đoàn cho UID này."), thread_id, thread_type)
            return
        
        basic_info = data.get("basicInfo", {})
        clan_info = data.get("clanBasicInfo", {})
        nickname = basic_info.get("nickname", "Unknown")
        
        if not clan_info or not clan_info.get("clanId"):
            bot.send(Message(text=f"🛡️ Người chơi {nickname} hiện không ở trong Quân đoàn nào."), thread_id, thread_type)
            return
            
        clan_id = clan_info.get("clanId")
        clan_name = clan_info.get("clanName", "Không rõ")
        captain_id = clan_info.get("captainId", "Không rõ")
        clan_level = clan_info.get("clanLevel", 0)
        capacity = clan_info.get("capacity", 0)
        member_num = clan_info.get("memberNum", 0)
        
        text = (
            "🛡️ CHI TIẾT QUÂN ĐOÀN - FREE FIRE\n\n"
            f"👤 Thành viên: {nickname} (UID: {uid})\n"
            f"🏷️ Tên quân đoàn: {clan_name}\n"
            f"🆔 ID quân đoàn: {clan_id}\n"
            f"👑 UID Chủ quân đoàn: {captain_id}\n"
            f"🎖️ Cấp độ quân đoàn: {clan_level}\n"
            f"👥 Sĩ số: {member_num}/{capacity} thành viên"
        )
        bot.send(Message(text=text), thread_id, thread_type)
    except Exception as e:
        bot.send(Message(text=f"❌ Lỗi khi tải thông tin quân đoàn: {str(e)}"), thread_id, thread_type)
    finally:
        try:
            bot.deleteMessage(loading_msg)
        except:
            pass

def handle_freefire_outfit(bot, thread_id, thread_type, uid):
    loading_msg = bot.send(Message(text=f"🔍 Đang lấy thông tin tủ đồ cho UID {uid}..."), thread_id, thread_type, ttl=60000)
    try:
        data = get_freefire_data(uid)
        if not data:
            bot.send(Message(text="❌ Không thể lấy dữ liệu tủ đồ cho UID này."), thread_id, thread_type)
            return
        
        basic_info = data.get("basicInfo", {})
        profile_info = data.get("profileInfo", {})
        nickname = basic_info.get("nickname", "Unknown")
        clothes = profile_info.get("clothes", [])
        
        if not clothes:
            bot.send(Message(text=f"👕 Tủ đồ của người chơi {nickname} trống hoặc bị ẩn."), thread_id, thread_type)
            return
            
        categories = {
            "Tóc/Đầu": [],
            "Mặt/Kính": [],
            "Áo": [],
            "Quần": [],
            "Giày": [],
            "Trang phục bộ/Khác": []
        }
        
        for item_id in clothes:
            item_str = str(item_id)
            if item_str.startswith("211"):
                categories["Trang phục bộ/Khác"].append(item_id)
            elif item_str.startswith("205") or item_str.startswith("206"):
                categories["Mặt/Kính"].append(item_id)
            elif item_str.startswith("214"):
                categories["Áo"].append(item_id)
            elif item_str.startswith("203"):
                categories["Quần"].append(item_id)
            elif item_str.startswith("204"):
                categories["Giày"].append(item_id)
            else:
                categories["Trang phục bộ/Khác"].append(item_id)
                
        text = f"👕 TỦ ĐỒ NHÂN VẬT - FREE FIRE\n"
        text += f"👤 Người chơi: {nickname} (UID: {uid})\n\n"
        
        for cat, items in categories.items():
            if items:
                items_str = ", ".join(str(i) for i in items)
                text += f"➜ {cat}: {items_str}\n"
            else:
                text += f"➜ {cat}: Trống\n"
                
        bot.send(Message(text=text), thread_id, thread_type)
    except Exception as e:
        bot.send(Message(text=f"❌ Lỗi khi tải tủ đồ: {str(e)}"), thread_id, thread_type)
    finally:
        try:
            bot.deleteMessage(loading_msg)
        except:
            pass

def txa_command(bot, message_object, author_id, thread_id, thread_type, message):
    """Handle Free Fire command."""
    parts = message.strip().split()
    
    if len(parts) < 2:
        help_text = (
            "🎮 FREE FIRE COMMANDS - Hướng dẫn sử dụng\n\n"
            "➜ Xem profile: {prefix}ff <UID>\n"
            "➜ Xem trợ thủ: {prefix}ff pet <UID>\n"
            "➜ Xem quân đoàn: {prefix}ff qd <UID>\n"
            "➜ Xem tủ đồ: {prefix}ff do <UID>\n\n"
            "📌 Ví dụ: {prefix}ff pet 2958487335"
        ).format(prefix=getattr(bot, 'prefix', '.'))
        
        bot.send(Message(text=help_text), thread_id, thread_type)
        return
        
    subcmd = parts[1].strip().lower()
    if subcmd in ("pet", "qd", "do", "outfit"):
        if len(parts) < 3:
            bot.send(Message(text="❌ Vui lòng cung cấp UID sau tên lệnh."), thread_id, thread_type)
            return
        uid = parts[2].strip()
        if not uid.isdigit():
            bot.send(Message(text="❌ UID phải là số!"), thread_id, thread_type)
            return
            
        if subcmd == "pet":
            handle_freefire_pet(bot, thread_id, thread_type, uid)
        elif subcmd == "qd":
            handle_freefire_qd(bot, thread_id, thread_type, uid)
        elif subcmd in ("do", "outfit"):
            handle_freefire_outfit(bot, thread_id, thread_type, uid)
    else:
        uid = parts[1].strip()
        if not uid.isdigit():
            bot.send(Message(text="❌ UID phải là số! Vui lòng cung cấp UID hợp lệ."), thread_id, thread_type)
            return
        handle_freefire_uid(bot, message_object, thread_id, thread_type, uid)

txa = {
    "name": "Free Fire UID",
    "desc": {
        "ff": "Xem profile Free Fire",
        "freefire": "Get Free Fire UID info",
        "uid": "Lấy thông tin UID Free Fire"
    },
    "author": "TXA",
    "command": ["ff", "freefire", "uid"]
}
