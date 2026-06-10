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
    if cs_rank_num < 500:
        return "Đồng"
    elif cs_rank_num < 1000:
        return "Bạc"
    elif cs_rank_num < 1500:
        return "Vàng"
    elif cs_rank_num < 2000:
        return "Bạch Kim"
    elif cs_rank_num < 2500:
        return "Kim Cương"
    elif cs_rank_num < 3000:
        return "Anh Hùng"
    else:
        return "Thiên Bá"

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
        rank_value = basic_info.get("rank", 0)
        cs_rank_value = basic_info.get("csRank", 0)
        rank_name = get_rank_name(rank_value)
        cs_rank_name = get_cs_rank_name(cs_rank_value)
        exp = basic_info.get("exp", 0)
        likes = basic_info.get("liked", 0)
        badge_cnt = basic_info.get("badgeCnt", 0)
        prime_level = basic_info.get("primePrivilegeDetail", {}).get("primeLevel", 0)
        
        clan_name = clan_info.get("clanName", "Không có clan")
        clan_level = clan_info.get("clanLevel", 0)
        
        gender = social_info.get("gender", "").replace("Gender_", "").title() if social_info.get("gender") else "Unknown"
        language = social_info.get("language", "").replace("Language_", "").title() if social_info.get("language") else "Unknown"
        
        # Image dimensions (responsive)
        width, height = 1080, 600
        
        # Create image with gradient background
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Background gradient (Free Fire theme: orange/red gradient)
        for y in range(height):
            r = int(45 + (40 * y / height))
            g = int(20 + (10 * y / height))
            b = int(15 + (5 * y / height))
            draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b, 255))
        
        # Add decorative border
        draw.rectangle([(30, 30), (width - 30, height - 30)], 
                       outline=(255, 140, 0, 200), width=4)
        draw.rectangle([(35, 35), (width - 35, height - 35)], 
                       outline=(255, 140, 0, 150), width=2)
        
        # Load fonts
        try:
            font_large = ImageFont.truetype(FONT_ARIAL, 52)
            font_medium = ImageFont.truetype(FONT_ARIAL, 38)
            font_small = ImageFont.truetype(FONT_ARIAL, 30)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Title with emoji
        title = "🎮 FREE FIRE PROFILE 🎮"
        title_bbox = draw.textbbox((0, 0), title, font=font_large)
        title_x = (width - title_bbox[2]) // 2
        draw.text((title_x, 60), title, font=font_large, fill=(255, 215, 0, 255))
        
        # Player info
        y_pos = 140
        
        # Nickname
        nickname_text = f"👤 {nickname}"
        draw.text((60, y_pos), nickname_text, font=font_medium, fill=(255, 255, 255, 255))
        y_pos += 55
        
        # UID
        uid_text = f"🆔 UID: {uid}"
        draw.text((60, y_pos), uid_text, font=font_medium, fill=(255, 255, 255, 255))
        y_pos += 55
        
        # Level and Region
        level_text = f"⭐ Level: {level} | 🌍 Region: {region}"
        draw.text((60, y_pos), level_text, font=font_medium, fill=(255, 255, 255, 255))
        y_pos += 55
        
        # Rank
        rank_text = f"🏆 Rank: {rank_name} (#{rank_value}) | 🔫 CS Rank: {cs_rank_name} (#{cs_rank_value})"
        draw.text((60, y_pos), rank_text, font=font_medium, fill=(255, 255, 255, 255))
        y_pos += 55
        
        # Stats
        stats_text = f"💪 EXP: {exp:,} | ❤️ Likes: {likes:,}"
        draw.text((60, y_pos), stats_text, font=font_medium, fill=(255, 255, 255, 255))
        y_pos += 55
        
        # Prime level
        if prime_level > 0:
            prime_text = f"💎 Prime: Level {prime_level}"
            draw.text((60, y_pos), prime_text, font=font_medium, fill=(255, 215, 0, 255))
            y_pos += 55
        
        # Clan info
        clan_text = f"👥 Clan: {clan_name} (Level {clan_level})"
        draw.text((60, y_pos), clan_text, font=font_medium, fill=(255, 140, 0, 255))
        
        # Additional info
        info_text = f"👥 Gender: {gender} | 🗣️ Language: {language}"
        draw.text((60, y_pos + 40), info_text, font=font_small, fill=(200, 200, 200, 255))
        
        # Badge count
        badge_text = f"🎖️ Badges: {badge_cnt}"
        draw.text((width - 60, y_pos), badge_text, font=font_small, fill=(255, 255, 255, 255), anchor="ra")
        
        # Footer with timestamp
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        footer_text = f"Generated: {timestamp} | Powered by TXABOT 🤖"
        footer_bbox = draw.textbbox((0, 0), footer_text, font=font_small)
        footer_x = (width - footer_bbox[2]) // 2
        draw.text((footer_x, height - 45), footer_text, font=font_small, fill=(200, 200, 200, 255))
        
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
            # Send card image
            bot.sendLocalImage(
                output_path,
                message=Message(text=f"✅ Profile Free Fire cho UID {uid}"),
                thread_id=thread_id,
                thread_type=thread_type,
                width=1080,
                height=600
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

def txa_command(bot, message_object, author_id, thread_id, thread_type, message):
    """Handle Free Fire command."""
    parts = message.strip().split()
    
    if len(parts) < 2:
        help_text = (
            "🎮 FREE FIRE UID - Hướng dẫn sử dụng\n\n"
            "➜ Cú pháp: {prefix}ff <UID>\n"
            "➜ Ví dụ: {prefix}ff 123456789\n\n"
            "📌 Lưu ý: Cung cấp UID Free Fire hợp lệ để xem profile."
        ).format(prefix=getattr(bot, 'prefix', '.'))
        
        bot.send(Message(text=help_text), thread_id, thread_type)
        return
    
    uid = parts[1].strip()
    
    # Validate UID (should be numeric)
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
