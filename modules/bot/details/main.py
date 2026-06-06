import os
import platform
import time
import random
import shutil
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import emoji
from zlapi.models import Message
from core.bot_sys import read_settings, get_user_name_by_id

# Try to import psutil, make it optional
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

txa = {
    "name": "Details",
    "desc": "Xem thông tin hệ thống của máy chủ và cấu hình cài đặt nhóm hiện tại dưới dạng hình ảnh",
    "author": "TXA",
    "command": "details"
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, client=None):
    handle_details_command(bot, message_object, thread_id, thread_type, author_id, client)

# ── Paths ───────────────────────────────────────────────────────────────────
BACKGROUND_PATH = "background/"
CACHE_PATH      = "modules/cache/"
FONT_TEXT_PATH  = "font/arial unicode ms.otf"
FONT_TITLE_PATH = "font/Kai.ttf"
FONT_EMOJI_PATH = "font/NotoEmoji-Bold.ttf"

# ── Font helpers (dùng chung cả project) ────────────────────────────────────
def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except (OSError, IOError):
        return ImageFont.load_default()

def _char_width(font: ImageFont.FreeTypeFont, char: str) -> int:
    try:
        return font.getbbox(char)[2] - font.getbbox(char)[0]
    except Exception:
        try:
            return int(font.getlength(char))
        except Exception:
            return font.size

# ── draw_text_with_emoji — chuẩn của project (txa.py) ──────────────────────
def is_emoji(ch: str) -> bool:
    return ch in emoji.EMOJI_DATA

def draw_text_with_emoji(
    draw: ImageDraw.ImageDraw,
    text: str,
    pos: Tuple[int, int],
    font: ImageFont.FreeTypeFont,
    emoji_font: ImageFont.FreeTypeFont,
    fill,
) -> int:
    """Vẽ text ký tự-by-ký tự, dùng emoji_font cho emoji và font thường cho text.
    Trả về x kết thúc."""
    x, y = pos
    for ch in text:
        f = emoji_font if is_emoji(ch) else font
        # emoji nhỏ hơn một chút so với text_font để baseline đẹp hơn
        oy = y - (f.size // 6) if is_emoji(ch) else y
        draw.text((x, oy), ch, font=f, fill=fill)
        x += _char_width(f, ch) + (1 if is_emoji(ch) else 0)
    return x

# ── System metrics ──────────────────────────────────────────────────────────
def _fmt_bytes(val: float, dec: int = 1) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while val >= 1024 and i < len(units) - 1:
        val /= 1024; i += 1
    return f"{val:.{dec}f} {units[i]}"

def get_system_metrics(bot) -> dict:
    total, used, _ = shutil.disk_usage("/")
    metrics = {
        "os":          f"{platform.system()} {platform.release()}",
        "cpu_cores":   "N/A",
        "cpu_usage":   "N/A",
        "ram":         "N/A",
        "proc_mem":    "N/A",
        "proc_threads": "N/A",
        "disk_used":   _fmt_bytes(used),
        "disk_total":  _fmt_bytes(total),
        "version":     getattr(bot, "version", "1.0"),
        "load_avg":    "N/A",
        "net_sent":    "N/A",
        "net_recv":    "N/A",
        "process_count": "N/A",
    }
    
    if PSUTIL_AVAILABLE:
        try:
            vm = psutil.virtual_memory()
            proc = psutil.Process(os.getpid())
            metrics["ram"] = f"{_fmt_bytes(vm.used)} / {_fmt_bytes(vm.total)} ({vm.percent}%)"
            metrics["proc_mem"] = _fmt_bytes(proc.memory_info().rss)
            metrics["proc_threads"] = f"{proc.num_threads()} Threads"
            
            cpu_cores = psutil.cpu_count(logical=True)
            if cpu_cores:
                metrics["cpu_cores"] = f"{cpu_cores} Cores"
            
            cpu_usage = psutil.cpu_percent(interval=0.1)
            metrics["cpu_usage"] = f"{cpu_usage}%"
            
            try:
                if hasattr(psutil, "getloadavg"):
                    load1, load5, load15 = psutil.getloadavg()
                    metrics["load_avg"] = f"{load1:.2f} | {load5:.2f} | {load15:.2f}"
            except:
                pass
                
            try:
                net_io = psutil.net_io_counters()
                metrics["net_sent"] = _fmt_bytes(net_io.bytes_sent)
                metrics["net_recv"] = _fmt_bytes(net_io.bytes_recv)
            except:
                pass
                
            try:
                metrics["process_count"] = f"{len(psutil.pids())} Processes"
            except:
                pass
        except Exception as e:
            print(f"[details] Error getting psutil metrics: {e}")
    
    return metrics

def format_uptime(secs: int) -> str:
    d, secs = divmod(secs, 86400)
    h, secs = divmod(secs, 3600)
    m, s    = divmod(secs, 60)
    parts = []
    if d: parts.append(f"{d} ngày")
    if h: parts.append(f"{h} giờ")
    if m: parts.append(f"{m} phút")
    if s or not parts: parts.append(f"{s} giây")
    return ", ".join(parts)

# ── Progress bar ────────────────────────────────────────────────────────────
def draw_progress_bar(draw, x, y, w, h, pct, label, f_label, f_pct, emoji_font):
    color = (78, 203, 113, 255) if pct < 70 else (255, 193, 7, 255) if pct < 90 else (255, 107, 107, 255)
    draw_text_with_emoji(draw, label, (x, y - 30), f_label, emoji_font, (180, 220, 255, 255))
    # track
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2,
                            fill=(25, 35, 50, 220), outline=(255, 255, 255, 35), width=1)
    fill_w = max(0, int(w * pct / 100))
    if fill_w:
        draw.rounded_rectangle([x, y, x + fill_w, y + h], radius=h // 2, fill=color)
    draw.text((x + w + 10, y + 1), f"{pct:.1f}%", font=f_pct, fill=(255, 255, 255, 220))

# ── Main image builder ──────────────────────────────────────────────────────
def create_details_image(bot, uptime_str: str, thread_id: str) -> str:
    # Layout
    WIDTH     = 1280
    PAD       = 60
    COL_L_W   = 490
    COL_R_X   = PAD + COL_L_W + 50
    COL_R_W   = WIDTH - COL_R_X - PAD
    ROW_H     = 52
    SEC_H     = 48
    BAR_BLOCK = 78
    FOOTER_H  = 55

    sys_rows = 13
    cfg_rows = 11
    sys_h = SEC_H + sys_rows * ROW_H + 20 + BAR_BLOCK * 2
    cfg_h = SEC_H + cfg_rows * ROW_H
    HEIGHT = max(1200, PAD * 2 + 120 + max(sys_h, cfg_h) + FOOTER_H + 30)

    # Background
    bg_path = None
    if os.path.exists(BACKGROUND_PATH):
        imgs = [os.path.join(BACKGROUND_PATH, f) for f in os.listdir(BACKGROUND_PATH)
                if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        if imgs:
            bg_path = random.choice(imgs)

    if bg_path:
        bg = Image.open(bg_path).convert("RGBA").resize((WIDTH, HEIGHT))
        bg = bg.filter(ImageFilter.GaussianBlur(radius=10))
    else:
        bg = Image.new("RGBA", (WIDTH, HEIGHT), (20, 30, 45, 255))

    ov   = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ov)

    # Glass card
    draw.rounded_rectangle(
        [PAD - 10, PAD - 10, WIDTH - PAD + 10, HEIGHT - PAD + 10],
        radius=28, fill=(10, 18, 30, 185), outline=(255, 255, 255, 22), width=2
    )

    # Fonts
    f_title  = _load_font(FONT_TITLE_PATH, 44)
    f_header = _load_font(FONT_TITLE_PATH, 30)
    f_text   = _load_font(FONT_TEXT_PATH,  24)
    f_desc   = _load_font(FONT_TEXT_PATH,  15)
    f_emoji  = _load_font(FONT_EMOJI_PATH, 38)   # emoji font dùng chung
    f_emoji_sm = _load_font(FONT_EMOJI_PATH, 28)

    # ── Title ─────────────────────────────────────────────────────────
    bot_name = getattr(bot, "me_name", "TXABOT")
    draw_text_with_emoji(draw, f"⚡ HỆ THỐNG & CẤU HÌNH BOT",
                         (PAD, PAD + 5), f_title, f_emoji, (200, 150, 255, 255))
    draw_text_with_emoji(draw, f"🤖 Bot Name: {bot_name}  |  ⏳ Uptime: {uptime_str}",
                         (PAD, PAD + 62), f_text, f_emoji_sm, (255, 255, 255, 200))
    draw.line([PAD, PAD + 112, WIDTH - PAD, PAD + 112], fill=(255, 255, 255, 40), width=2)

    body_y = PAD + 128

    # ══════════════════════════════════════════════════════════════════
    # LEFT  — Thông tin hệ thống
    # ══════════════════════════════════════════════════════════════════
    metrics = get_system_metrics(bot)
    lx, ly = PAD, body_y

    draw_text_with_emoji(draw, "💻 THÔNG TIN HỆ THỐNG",
                         (lx, ly), f_header, f_emoji_sm, (90, 200, 250, 255))
    ly += SEC_H

    LABEL_COL = 205   # độ rộng cột label trong left col
    sys_rows_data = [
        ("Hệ điều hành",   metrics["os"],        "OS nền tảng hoạt động của bot"),
        ("CPU Cores",       metrics["cpu_cores"], "Số luồng xử lý CPU"),
        ("CPU Usage",       metrics["cpu_usage"], "Tỷ lệ sử dụng CPU hiện tại"),
        ("Load Average",    metrics["load_avg"],  "Tải trung bình hệ thống (1/5/15m)"),
        ("RAM Usage",       metrics["ram"],       "Bộ nhớ RAM đã dùng/tổng"),
        ("Bộ nhớ Bot",      metrics["proc_mem"],  "Bộ nhớ tiêu thụ bởi process bot"),
        ("Threads Bot",     metrics["proc_threads"], "Số luồng của process bot"),
        ("Ổ đĩa đã dùng",  metrics["disk_used"], "Dung lượng đã sử dụng"),
        ("Tổng dung lượng", metrics["disk_total"],"Dung lượng toàn bộ"),
        ("Network Sent",    metrics["net_sent"],  "Dữ liệu đã gửi qua mạng"),
        ("Network Recv",    metrics["net_recv"],  "Dữ liệu đã nhận qua mạng"),
        ("Process Count",   metrics["process_count"], "Tổng số tiến trình trên hệ thống"),
        ("Bot Version",     metrics["version"],   "Phiên bản bot hiện tại"),
    ]
    for label, val, desc in sys_rows_data:
        draw.text((lx, ly),              f"➜ {label}:", font=f_text, fill=(210, 215, 225, 255))
        draw.text((lx + LABEL_COL, ly),  val,            font=f_text, fill=(255, 255, 255, 255))
        draw.text((lx, ly + 26),         f"   {desc}",   font=f_desc, fill=(140, 145, 160, 200))
        ly += ROW_H

    # Progress bars
    ly += 18
    BAR_W, BAR_H = COL_L_W - 60, 20
    
    if PSUTIL_AVAILABLE:
        try:
            cpu_pct = psutil.cpu_percent(interval=None)
            draw_progress_bar(draw, lx, ly + 30, BAR_W, BAR_H, cpu_pct,
                              "📊 CPU Usage", f_text, f_text, f_emoji_sm)
            ly += BAR_BLOCK

            ram_pct = psutil.virtual_memory().percent
            draw_progress_bar(draw, lx, ly + 30, BAR_W, BAR_H, ram_pct,
                              "💾 RAM Usage", f_text, f_text, f_emoji_sm)
        except Exception as e:
            print(f"[details] Error drawing progress bars: {e}")

    # ══════════════════════════════════════════════════════════════════
    # RIGHT — Cấu hình nhóm  (1 cột, không overlap)
    # ══════════════════════════════════════════════════════════════════
    settings = read_settings(bot.uid)

    def check_status(key: str, default=True) -> bool:
        val = settings.get(key)
        if isinstance(val, dict):
            return val.get(thread_id, default)
        return val if val is not None else default

    cfg_data = [
        ("Chào mừng mem mới",    check_status("welcome",        False), "Tự động chào thành viên mới"),
        ("Chào tạm biệt mem rời", check_status("goodbye",       False), "Tự động chào tạm biệt khi mem rời nhóm"),
        ("Chống Spam tin nhắn",  check_status("spam_enabled",   False), "Chặn spam tin nhắn trong nhóm"),
        ("Đọc tin nhắn thu hồi", check_status("undo_enabled",   True),  "Bot đọc tin nhắn đã thu hồi"),
        ("Cho phép gửi Link",    not check_status("allow_link", False), "Cho phép link trong nhóm"),  # allow_link is anti-link, so invert
        ("Cho phép gửi Voice",   not check_status("voice_enabled", True), "Cho phép voice message"),  # invert
        ("Cho phép gửi Hình ảnh",not check_status("image_enabled", True), "Cho phép gửi hình ảnh"),  # invert
        ("Cho phép gửi Sticker", not check_status("sticker_enabled", True), "Cho phép gửi sticker"),  # invert
        ("Cho phép gửi Video",   not check_status("video_enabled", True), "Cho phép gửi video"),  # invert
        ("Cho phép gửi Doodle",  not check_status("doodle_enabled", True), "Cho phép gửi doodle/vẽ"),  # invert
        ("Tương tác Chat AI",    settings.get("chat", {}).get(thread_id, False), "Bật AI Gemini trả lời"),
        ("Chặn tạo bình chọn",  check_status("anti_poll", True), "Chặn tạo bình chọn trong nhóm"),
    ]

    rx, ry = COL_R_X, body_y
    draw_text_with_emoji(draw, "⚙️ CẤU HÌNH NHÓM",
                         (rx, ry), f_header, f_emoji_sm, (90, 255, 150, 255))
    ry += SEC_H

    # độ rộng phần label trước badge ON/OFF
    BADGE_X = rx + COL_R_W - 95

    for label, is_on, desc in cfg_data:
        status      = "Bật (ON)"  if is_on else "Tắt (OFF)"
        status_fill = (78, 203, 113, 255) if is_on else (255, 107, 107, 255)
        draw.text((rx, ry),         f"• {label}:", font=f_text, fill=(215, 215, 225, 255))
        draw.text((BADGE_X, ry),    status,         font=f_text, fill=status_fill)
        draw.text((rx, ry + 26),    f"   {desc}",   font=f_desc, fill=(140, 145, 160, 200))
        ry += ROW_H

    # ── Footer accent bar ──────────────────────────────────────────────
    bar_y = HEIGHT - PAD + 12
    accent = [(255, 93, 47, 210), (255, 193, 7, 210), (34, 197, 94, 210), (59, 130, 246, 210)]
    seg = (WIDTH - PAD * 2) // len(accent)
    for i, col in enumerate(accent):
        sx = PAD + i * seg
        draw.rectangle([sx, bar_y, sx + seg, bar_y + 16], fill=col)

    # ── Compose & save ─────────────────────────────────────────────────
    final = Image.alpha_composite(bg, ov)
    os.makedirs(CACHE_PATH, exist_ok=True)
    path = os.path.join(CACHE_PATH, f"bot_details_{int(time.time())}.png")
    final.convert("RGB").save(path, "PNG", quality=95)
    return path

# ── Command handler ─────────────────────────────────────────────────────────
def handle_details_command(bot, message_object, thread_id, thread_type, author_id, client=None):
    active = client if client else bot
    uptime_str = format_uptime(int(time.time() - getattr(active, "start_time", time.time())))

    temp_file = None
    try:
        active.sendReaction(message_object, "⏳", thread_id, thread_type)
        temp_file = create_details_image(active, uptime_str, thread_id)
        active.sendLocalImage(
            temp_file,
            thread_id=thread_id,
            thread_type=thread_type,
            width=1280,
            height=1200
        )
        active.sendReaction(message_object, "✅", thread_id, thread_type)
    except Exception as e:
        print(f"[details] Error: {e}")
        active.sendMessage(f"❌ Lỗi khi tải chi tiết cấu hình bot: {e}", thread_id, thread_type)
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
