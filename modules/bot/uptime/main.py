import os
import time
import random
import platform
from datetime import datetime
from typing import Tuple
import emoji
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from zlapi.models import Message

# Try to import psutil, make it optional
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# ── Font paths ──────────────────────────────────────────────────────────────
FONT_TITLE  = "font/Kai.ttf"
FONT_TEXT   = "font/arial unicode ms.otf"
FONT_BOLD   = "font/UTM AvoBold.ttf"
FONT_EMOJI  = "font/NotoEmoji-Bold.ttf"
FONT_FALLBACKS = [
    "font/arial unicode ms.otf",
    "font/Roboto-Regular.ttf",
    "font/arial.ttf",
]

BACKGROUND_PATH = "background/"
CACHE_PATH      = "modules/cache/"

txa = {
    "name": "Uptime",
    "desc": "Xem thời gian hoạt động và thông tin hệ thống của bot",
    "author": "TXA",
    "command": "uptime"
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, client=None):
    handle_uptime_command(bot, message_object, thread_id, thread_type, author_id, client)

# ── Helpers ─────────────────────────────────────────────────────────────────
def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    for p in ([path] + FONT_FALLBACKS):
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()

def _text_w(font, text: str) -> int:
    try:
        bb = font.getbbox(text)
        return bb[2] - bb[0]
    except Exception:
        try:
            return int(font.getlength(text))
        except Exception:
            return len(text) * (getattr(font, 'size', 12))

def _is_emoji(ch: str) -> bool:
    return ch in emoji.EMOJI_DATA

def draw_mixed(draw, text: str, pos: Tuple[int, int],
               font, emoji_font, fill, center_w: int = 0):
    """Vẽ text có emoji, tùy chọn căn giữa trong center_w px."""
    if center_w:
        total = sum(
            _text_w(emoji_font if _is_emoji(c) else font, c) + (1 if _is_emoji(c) else 0)
            for c in text
        )
        pos = (pos[0] + (center_w - total) // 2, pos[1])
    x, y = pos
    for ch in text:
        f  = emoji_font if _is_emoji(ch) else font
        oy = y - f.size // 6 if _is_emoji(ch) else y
        draw.text((x, oy), ch, font=f, fill=fill)
        x += _text_w(f, ch) + (1 if _is_emoji(ch) else 0)
    return x

def format_uptime_seconds(secs: int):
    d, secs = divmod(secs, 86400)
    h, secs = divmod(secs, 3600)
    m, s    = divmod(secs, 60)
    return d, h, m, s

def _fmt_bytes(val: float, dec: int = 1) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while val >= 1024 and i < len(units) - 1:
        val /= 1024; i += 1
    return f"{val:.{dec}f} {units[i]}"

def get_system_info():
    info = {
        "cpu_usage": "N/A",
        "ram_used": "N/A",
        "ram_total": "N/A",
        "ram_pct": "N/A",
        "proc_mem": "N/A",
        "os": f"{platform.system()} {platform.release()}",
    }
    
    if PSUTIL_AVAILABLE:
        try:
            vm = psutil.virtual_memory()
            cpu_pct = psutil.cpu_percent(interval=0.1)
            proc = psutil.Process(os.getpid())
            info["cpu_usage"] = f"{cpu_pct:.1f}%"
            info["ram_used"] = _fmt_bytes(vm.used)
            info["ram_total"] = _fmt_bytes(vm.total)
            info["ram_pct"] = f"{vm.percent}%"
            info["proc_mem"] = _fmt_bytes(proc.memory_info().rss)
        except Exception as e:
            print(f"[uptime] Error getting psutil metrics: {e}")
    
    return info

# ── Image builder ────────────────────────────────────────────────────────────
def create_uptime_image(bot_name: str, days: int, hours: int,
                        minutes: int, seconds: int, start_ts: float) -> str:
    W, H = 1000, 800
    PAD  = 50

    sys_info = get_system_info()

    # ── Background ────────────────────────────────────────────────────
    bg_path = None
    if os.path.exists(BACKGROUND_PATH):
        imgs = [os.path.join(BACKGROUND_PATH, f)
                for f in os.listdir(BACKGROUND_PATH)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if imgs:
            bg_path = random.choice(imgs)

    if bg_path:
        bg = Image.open(bg_path).convert("RGBA").resize((W, H))
        bg = bg.filter(ImageFilter.GaussianBlur(radius=12))
    else:
        bg = Image.new("RGBA", (W, H), (10, 18, 40, 255))
        draw_bg = ImageDraw.Draw(bg)
        for y in range(H):
            r = y / H
            c = tuple(int(a + (b - a) * r) for a, b in zip((5, 14, 41), (15, 60, 110)))
            draw_bg.line([(0, y), (W, y)], fill=c + (255,))

    ov   = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ov)

    # Glass card
    draw.rounded_rectangle(
        [PAD - 10, PAD - 10, W - PAD + 10, H - PAD + 10],
        radius=32, fill=(8, 15, 35, 190), outline=(255, 255, 255, 30), width=2
    )

    # ── Fonts ──────────────────────────────────────────────────────────
    f_title  = _font(FONT_TITLE, 52)
    f_header = _font(FONT_TITLE, 28)
    f_value  = _font(FONT_BOLD,  58)
    f_label  = _font(FONT_TEXT,  22)
    f_sub    = _font(FONT_TEXT,  20)
    f_emoji  = _font(FONT_EMOJI, 52)
    f_emoji2 = _font(FONT_EMOJI, 28)

    # ── Title ──────────────────────────────────────────────────────────
    draw_mixed(draw, "⚡ Uptime & System Info", (PAD + 10, PAD + 8),
               f_title, f_emoji, (255, 214, 165, 255))

    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    draw_mixed(draw, f"🤖 {bot_name}  |  🗓️ {uptime_str}  |  💻 {sys_info['os']}",
               (PAD + 10, PAD + 74), f_sub, f_emoji2, (200, 215, 255, 210))

    draw.line([PAD, PAD + 116, W - PAD, PAD + 116],
              fill=(255, 255, 255, 40), width=2)

    # ── 4 metric boxes (1 hàng ngang) ─────────────────────────────────
    metrics = [
        ("Ngày",  days,    (235,  86, 149)),
        ("Giờ",   hours,   (255, 165,  40)),
        ("Phút",  minutes, ( 34, 197,  94)),
        ("Giây",  seconds, ( 59, 130, 246)),
    ]

    BOX_W   = 180
    BOX_H   = 140
    total_w = BOX_W * 4 + 24 * 3          # 4 boxes + 3 gaps
    start_x = (W - total_w) // 2
    box_y   = PAD + 136

    for i, (label, val, rgb) in enumerate(metrics):
        bx = start_x + i * (BOX_W + 24)
        by = box_y

        # Shadow
        draw.rounded_rectangle(
            [bx + 4, by + 4, bx + BOX_W + 4, by + BOX_H + 4],
            radius=20, fill=(0, 0, 0, 80)
        )
        # Box
        draw.rounded_rectangle(
            [bx, by, bx + BOX_W, by + BOX_H],
            radius=20, fill=rgb + (230,)
        )
        # Highlight strip top
        draw.rounded_rectangle(
            [bx + 8, by + 6, bx + BOX_W - 8, by + 30],
            radius=10, fill=(255, 255, 255, 45)
        )
        # Value
        val_str = str(val)
        vw = _text_w(f_value, val_str)
        draw.text(
            (bx + (BOX_W - vw) // 2, by + 30),
            val_str, font=f_value, fill=(255, 255, 255, 255)
        )
        # Label
        lw = _text_w(f_label, label)
        draw.text(
            (bx + (BOX_W - lw) // 2, by + BOX_H - 34),
            label, font=f_label, fill=(255, 255, 255, 230)
        )

    # ── System info section ─────────────────────────────────────────
    sys_y = box_y + BOX_H + 30
    sys_metrics = [
        ("📊 CPU Usage", sys_info['cpu_usage']),
        ("💾 RAM Usage", sys_info['ram_used'] + " / " + sys_info['ram_total']),
        ("🤖 Bot Memory", sys_info['proc_mem']),
    ]

    for i, (label, value) in enumerate(sys_metrics):
        col_width = (W - PAD * 2) // 3
        bx = PAD + i * col_width
        by = sys_y
        
        draw.rounded_rectangle(
            [bx, by, bx + col_width - 16, by + 70],
            radius=16, fill=(255, 255, 255, 8), outline=(255, 255, 255, 20), width=1
        )
        
        draw_mixed(draw, label, (bx + 16, by + 12), f_sub, f_emoji2, (200, 210, 255, 220))
        vw = _text_w(f_header, value)
        draw.text((bx + 16, by + 38), value, font=f_header, fill=(255, 255, 255, 240))

    # ── Last boot info ─────────────────────────────────────────────────
    boot_y = sys_y + 85
    last_boot = datetime.fromtimestamp(start_ts).strftime("%d/%m/%Y  %H:%M:%S")

    draw.rounded_rectangle(
        [PAD, boot_y, W - PAD, boot_y + 66],
        radius=16, fill=(255, 255, 255, 12), outline=(255, 255, 255, 25), width=1
    )
    draw_mixed(draw, "🕐 Khởi động lần cuối:",
               (0, boot_y + 10), f_header, f_emoji2, (180, 210, 255, 210),
               center_w=W)
    bw = _text_w(f_sub, last_boot)
    draw.text(
        ((W - bw) // 2, boot_y + 38),
        last_boot, font=f_sub, fill=(220, 235, 255, 240)
    )

    # ── Accent bar ─────────────────────────────────────────────────────
    bar_y = H - PAD + 12
    accent = [(255, 93, 47, 220), (123, 97, 255, 210), (34, 197, 94, 220), (59, 130, 246, 210)]
    seg = (W - PAD * 2) // len(accent)
    for i, col in enumerate(accent):
        sx = PAD + i * seg
        draw.rounded_rectangle([sx, bar_y, sx + seg - 4, bar_y + 14], radius=7, fill=col)

    # ── Compose ────────────────────────────────────────────────────────
    final = Image.alpha_composite(bg, ov)
    os.makedirs(CACHE_PATH, exist_ok=True)
    path = os.path.join(CACHE_PATH, f"uptime_{int(time.time())}.png")
    final.convert("RGB").save(path, "PNG", quality=95)
    return path

# ── Command handler ──────────────────────────────────────────────────────────
def handle_uptime_command(bot, message_object, thread_id, thread_type, author_id, client=None):
    active = client if client else bot
    start_ts = getattr(active, "start_time", time.time())
    d, h, m, s = format_uptime_seconds(int(time.time() - start_ts))
    bot_name = getattr(bot, "me_name", "TXABOT")

    img_path = None
    try:
        img_path = create_uptime_image(bot_name, d, h, m, s, start_ts)
        active.sendLocalImage(img_path, thread_id=thread_id, thread_type=thread_type,
                              width=1000, height=800)
    except Exception as e:
        print(f"[uptime] Error: {e}")
        try:
            sys_info = get_system_info()
            active.replyMessage(
                Message(text=f"⏳ Bot đã hoạt động {d} ngày {h} giờ {m} phút {s} giây.\n📊 CPU: {sys_info['cpu_usage']}\n💾 RAM: {sys_info['ram_used']}/{sys_info['ram_total']}"),
                message_object, thread_id, thread_type
            )
        except Exception:
            pass
    finally:
        if img_path and os.path.exists(img_path):
            try:
                os.remove(img_path)
            except Exception:
                pass
