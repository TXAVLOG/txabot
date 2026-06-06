import colorsys
import os
import platform
import time
import random
import psutil
import shutil
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from zlapi.models import Message
from core.bot_sys import read_settings, get_user_name_by_id

txa = {
    "name": "Details",
    "desc": "Xem thông tin hệ thống của máy chủ và cấu hình cài đặt nhóm hiện tại dưới dạng hình ảnh",
    "author": "TXA",
    "command": "details"
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, client=None):
    handle_details_command(bot, message_object, thread_id, thread_type, author_id, client)

BACKGROUND_PATH = "background/"
CACHE_PATH = "modules/cache/"
font_path_arial = "font/arial unicode ms.otf"
font_paci = "font/Kai.ttf"
font_emoji = "font/NotoEmoji-Bold.ttf"
DEFAULT_FONT_FALLBACKS = [
    "arial.ttf",
    "DejaVuSans.ttf",
    "LiberationSans-Regular.ttf",
    "NotoEmoji-Bold.ttf"
]

def load_font_with_fallback(primary_paths, size):
    candidates = []
    if isinstance(primary_paths, (list, tuple)):
        candidates.extend(primary_paths)
    elif primary_paths:
        candidates.append(primary_paths)
    candidates.extend(DEFAULT_FONT_FALLBACKS)

    for path in candidates:
        if not path:
            continue
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue

    return ImageFont.load_default()

def format_bytes(value, decimals=1):
    if value < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    return f"{value:.{decimals}f} {units[idx]}"

def get_system_metrics():
    # OS
    os_name = f"{platform.system()} {platform.release()}"
    
    # CPU usage and cores
    cpu_cores = psutil.cpu_count(logical=True)
    cpu_usage = f"{psutil.cpu_percent(interval=None)}%"
    
    # RAM usage
    virtual_mem = psutil.virtual_memory()
    ram_usage = f"{format_bytes(virtual_mem.used)} / {format_bytes(virtual_mem.total)}"
    
    # Process memory usage
    process = psutil.Process(os.getpid())
    process_mem = format_bytes(process.memory_info().rss)
    
    # Disk usage
    total, used, free = shutil.disk_usage("/")
    disk_usage = f"{format_bytes(used)} / {format_bytes(total)}"
    
    return {
        "os": os_name,
        "cpu_cores": f"{cpu_cores} Cores",
        "cpu_usage": cpu_usage,
        "ram": ram_usage,
        "process_mem": process_mem,
        "disk": disk_usage
    }

def format_uptime(uptime_seconds):
    days = uptime_seconds // (24 * 3600)
    uptime_seconds %= (24 * 3600)
    hours = uptime_seconds // 3600
    uptime_seconds %= 3600
    minutes = uptime_seconds // 60
    seconds = uptime_seconds % 60
    
    parts = []
    if days > 0: parts.append(f"{days} ngày")
    if hours > 0: parts.append(f"{hours} giờ")
    if minutes > 0: parts.append(f"{minutes} phút")
    if seconds > 0 or not parts: parts.append(f"{seconds} giây")
    return ", ".join(parts)

def create_details_image(bot, uptime_str, thread_id):
    width, height = 1200, 800
    
    # Find background image
    bg_image_path = None
    if os.path.exists(BACKGROUND_PATH):
        images = [os.path.join(BACKGROUND_PATH, f) for f in os.listdir(BACKGROUND_PATH) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if images:
            bg_image_path = random.choice(images)
            
    if bg_image_path:
        background = Image.open(bg_image_path).convert("RGBA").resize((width, height))
        background_blurred = background.filter(ImageFilter.GaussianBlur(radius=8))
    else:
        # Default gradient
        background_blurred = Image.new("RGBA", (width, height), (30, 45, 60, 255))
        
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Semi-transparent box for glassmorphism
    glass_color = (15, 25, 35, 180)
    draw.rounded_rectangle([50, 50, width - 50, height - 50], radius=30, fill=glass_color, outline=(255, 255, 255, 30), width=2)
    
    # Load Fonts using safe fallback
    font_title = load_font_with_fallback([font_paci, font_path_arial], 48)
    font_header = load_font_with_fallback([font_paci, font_path_arial], 32)
    font_text = load_font_with_fallback([font_emoji, font_path_arial], 26)
    font_desc = load_font_with_fallback(font_path_arial, 16)
        
    # Draw Title
    bot_name = getattr(bot, 'me_name', 'TXABOT')
    draw.text((80, 80), f"⚡ HỆ THỐNG & CẤU HÌNH BOT", font=font_title, fill=(200, 150, 255, 255))
    draw.text((80, 140), f"🤖 Bot Name: {bot_name} | ⏳ Uptime: {uptime_str}", font=font_text, fill=(255, 255, 255, 200))
    
    # Draw Divider Line
    draw.line([80, 180, width - 80, 180], fill=(255, 255, 255, 50), width=2)
    
    # System Information
    metrics = get_system_metrics()
    sys_x = 80
    sys_y = 200
    
    draw.text((sys_x, sys_y), "💻 THÔNG TIN HỆ THỐNG", font=font_header, fill=(90, 200, 250, 255))
    sys_y += 50
    
    sys_fields = [
        ("Hệ điều hành", metrics["os"], "OS nền tảng hoạt động của bot"),
        ("CPU Cores", metrics["cpu_cores"], "Số luồng xử lý CPU"),
        ("CPU Usage", metrics["cpu_usage"], "Tỷ lệ sử dụng CPU hiện tại"),
        ("RAM Usage", metrics["ram"], "Bộ nhớ RAM đã dùng/tổng"),
        ("Bộ nhớ Bot", metrics["process_mem"], "Bộ nhớ tiêu thụ bởi process bot"),
        ("Dung lượng ổ đĩa", metrics["disk"], "Không gian lưu trữ đã dùng/tổng"),
        ("Bot Version", getattr(bot, 'version', '1.0'), "Phiên bản bot hiện tại")
    ]
    
    for label, val, desc in sys_fields:
        draw.text((sys_x, sys_y), f"➜ {label}:", font=font_text, fill=(220, 220, 220, 255))
        draw.text((sys_x + 220, sys_y), val, font=font_text, fill=(255, 255, 255, 255))
        draw.text((sys_x, sys_y + 25), f"   {desc}", font=font_desc, fill=(150, 150, 150, 200))
        sys_y += 55
        
    # Group configurations
    cfg_x = 650
    cfg_y = 200
    
    draw.text((cfg_x, cfg_y), "⚙️ CẤU HÌNH NHÓM", font=font_header, fill=(90, 255, 150, 255))
    cfg_y += 50
    
    settings = read_settings(bot.uid)
    
    # Helper to check setting status per thread
    def check_status(key, default=True, sub_key=None):
        if sub_key:
            return settings.get(key, {}).get(sub_key, {}).get(thread_id, default)
        
        val = settings.get(key)
        if isinstance(val, dict):
            return val.get(thread_id, default)
        return val if val is not None else default

    # Map settings to readable status lines
    cfg_fields = [
        ("Chào mừng mem mới (Welcome)", check_status('welcome', False), "Tự động chào thành viên mới tham gia"),
        ("Chống Spam tin nhắn", check_status('spam_enabled', False), "Chặn spam tin nhắn trong nhóm"),
        ("Đọc tin nhắn thu hồi (Undo)", check_status('undo_enabled', True), "Bot có thể đọc tin nhắn đã thu hồi"),
        ("Cho phép gửi Link", check_status('allow_link', False), "Cho phép gửi liên kết trong nhóm"),
        ("Cho phép gửi Voice", check_status('voice_enabled', True), "Cho phép gửi voice message"),
        ("Cho phép gửi Hình ảnh", check_status('image_enabled', True), "Cho phép gửi hình ảnh"),
        ("Cho phép gửi Sticker", check_status('sticker_enabled', True), "Cho phép gửi sticker"),
        ("Cho phép gửi Video", check_status('video_enabled', True), "Cho phép gửi video"),
        ("Cho phép gửi Doodle", check_status('doodle_enabled', True), "Cho phép gửi doodle/vẽ"),
        ("Tương tác Chat AI (Gemini)", settings.get('chat', {}).get(thread_id, False), "Bật AI Gemini trả lời tin nhắn"),
        ("Chặn tạo bình chọn (AntiPoll)", check_status('anti_poll', True), "Chặn tạo bình chọn trong nhóm")
    ]
    
    for label, is_enabled, desc in cfg_fields:
        status_text = "Bật (ON)" if is_enabled else "Tắt (OFF)"
        status_color = (78, 203, 113, 255) if is_enabled else (255, 107, 107, 255)
        
        draw.text((cfg_x, cfg_y), f"• {label}:", font=font_text, fill=(220, 220, 220, 255))
        draw.text((cfg_x + 360, cfg_y), status_text, font=font_text, fill=status_color)
        draw.text((cfg_x, cfg_y + 25), f"   {desc}", font=font_desc, fill=(150, 150, 150, 200))
        cfg_y += 55
        
    # Add progress bars for CPU and RAM
    progress_y = max(sys_y, cfg_y) + 30
    
    # CPU Progress Bar
    draw.text((80, progress_y), "📊 CPU Usage:", font=font_header, fill=(90, 200, 250, 255))
    progress_y += 40
    draw.rounded_rectangle([80, progress_y, 580, progress_y + 25], radius=12, fill=(30, 40, 50, 255), outline=(255, 255, 255, 50), width=2)
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_bar_width = int(500 * cpu_percent / 100)
    cpu_color = (78, 203, 113, 255) if cpu_percent < 70 else (255, 193, 7, 255) if cpu_percent < 90 else (255, 107, 107, 255)
    draw.rounded_rectangle([80, progress_y, 80 + cpu_bar_width, progress_y + 25], radius=12, fill=cpu_color)
    draw.text((590, progress_y), f"{cpu_percent}%", font=font_text, fill=(255, 255, 255, 255))
    
    # RAM Progress Bar
    progress_y += 40
    draw.text((80, progress_y), "💾 RAM Usage:", font=font_header, fill=(90, 200, 250, 255))
    progress_y += 40
    virtual_mem = psutil.virtual_memory()
    ram_percent = virtual_mem.percent
    draw.rounded_rectangle([80, progress_y, 580, progress_y + 25], radius=12, fill=(30, 40, 50, 255), outline=(255, 255, 255, 50), width=2)
    ram_bar_width = int(500 * ram_percent / 100)
    ram_color = (78, 203, 113, 255) if ram_percent < 70 else (255, 193, 7, 255) if ram_percent < 90 else (255, 107, 107, 255)
    draw.rounded_rectangle([80, progress_y, 80 + ram_bar_width, progress_y + 25], radius=12, fill=ram_color)
    draw.text((590, progress_y), f"{ram_percent}%", font=font_text, fill=(255, 255, 255, 255))
    
    # Add decorative circles
    # Circle 1 - Top Right
    draw.ellipse([width - 120, 70, width - 40, 150], outline=(200, 150, 255, 100), width=3)
    draw.ellipse([width - 100, 90, width - 60, 130], outline=(200, 150, 255, 80), width=2)
    
    # Circle 2 - Bottom Left
    draw.ellipse([50, height - 150, 130, height - 70], outline=(90, 200, 250, 100), width=3)
    draw.ellipse([70, height - 130, 110, height - 90], outline=(90, 200, 250, 80), width=2)
    
    # Circle 3 - Bottom Right
    draw.ellipse([width - 180, height - 130, width - 100, height - 50], outline=(90, 255, 150, 100), width=3)
    draw.ellipse([width - 160, height - 110, width - 120, height - 70], outline=(90, 255, 150, 80), width=2)
        
    # Combine
    final_image = Image.alpha_composite(background_blurred, overlay)
    
    # Save to temp file
    os.makedirs(CACHE_PATH, exist_ok=True)
    temp_file = os.path.join(CACHE_PATH, f"bot_details_{int(time.time())}.png")
    final_image.convert('RGB').save(temp_file, "PNG", quality=95)
    return temp_file

def handle_details_command(bot, message_object, thread_id, thread_type, author_id, client=None):
    active_client = client if client else bot
    
    start_time = getattr(active_client, 'start_time', time.time())
    uptime_seconds = int(time.time() - start_time)
    uptime_str = format_uptime(uptime_seconds)
    
    temp_file = None
    try:
        active_client.sendReaction(message_object, "⏳", thread_id, thread_type)
        temp_file = create_details_image(active_client, uptime_str, thread_id)
        
        active_client.sendLocalImage(
            temp_file,
            thread_id=thread_id,
            thread_type=thread_type,
            width=1200,
            height=800
        )
        active_client.sendReaction(message_object, "✅", thread_id, thread_type)
    except Exception as e:
        print(f"Error drawing details: {e}")
        active_client.sendMessage(f"❌ Lỗi khi tải chi tiết cấu hình bot: {e}", thread_id, thread_type)
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
