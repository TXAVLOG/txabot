import os
import time
import random
import platform
from datetime import datetime
from typing import Tuple
import emoji
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from zlapi.models import Message
from core.bot_sys import get_tech_icon

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
    text = text.replace("\uFE0F", "")
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

def _pct_value(text: str) -> float:
    try:
        return float(str(text).replace("%", "").strip())
    except Exception:
        return 0.0

def _cover_resize(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_size = (int(src_w * scale), int(src_h * scale))
    img = img.resize(new_size, Image.Resampling.LANCZOS)
    left = (img.width - target_w) // 2
    top = (img.height - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))

def _draw_shadow_text(draw, pos, text, font, fill, shadow=(0, 0, 0, 190), offset=(2, 3)):
    x, y = pos
    draw.text((x + offset[0], y + offset[1]), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)

def _draw_bar(draw, x, y, w, h, pct, color, label, value, font_label, font_value):
    pct = max(0.0, min(100.0, pct))
    draw.text((x, y - 30), label, font=font_label, fill=(220, 230, 255, 230))
    vw = _text_w(font_value, value)
    draw.text((x + w - vw, y - 31), value, font=font_value, fill=(255, 255, 255, 245))
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=(255, 255, 255, 28))
    fill_w = int(w * pct / 100)
    if fill_w > 0:
        draw.rounded_rectangle([x, y, x + fill_w, y + h], radius=h // 2, fill=color)
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, outline=(255, 255, 255, 32), width=1)

# ── Image builder ────────────────────────────────────────────────────────────
def create_uptime_image(bot_name: str, days: int, hours: int,
                        minutes: int, seconds: int, start_ts: float) -> str:
    W, H = 1280, 720
    PAD = 52

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
        bg = _cover_resize(Image.open(bg_path).convert("RGBA"), (W, H))
        bg = bg.filter(ImageFilter.GaussianBlur(radius=8))
    else:
        bg = Image.new("RGBA", (W, H), (10, 18, 40, 255))
        draw_bg = ImageDraw.Draw(bg)
        for y in range(H):
            r = y / H
            c = tuple(int(a + (b - a) * r) for a, b in zip((5, 14, 41), (15, 60, 110)))
            draw_bg.line([(0, y), (W, y)], fill=c + (255,))

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ov)

    draw.rectangle([0, 0, W, H], fill=(4, 8, 18, 92))
    draw.polygon([(0, 0), (450, 0), (220, H), (0, H)], fill=(0, 229, 255, 22))
    draw.polygon([(W, 0), (W - 520, 0), (W - 260, H), (W, H)], fill=(255, 64, 129, 24))
    draw.rounded_rectangle([PAD - 12, PAD - 12, W - PAD + 12, H - PAD + 12],
                           radius=34, fill=(8, 14, 28, 172),
                           outline=(255, 255, 255, 34), width=2)

    # ── Fonts ──────────────────────────────────────────────────────────
    f_title = _font(FONT_BOLD, 52)
    f_header = _font(FONT_TITLE, 30)
    f_value = _font(FONT_BOLD, 62)
    f_small_value = _font(FONT_BOLD, 38)
    f_label = _font(FONT_TEXT, 21)
    f_sub = _font(FONT_TEXT, 20)
    f_tiny = _font(FONT_TEXT, 17)
    f_emoji = _font(FONT_EMOJI, 54)
    f_emoji2 = _font(FONT_EMOJI, 28)

    # ── Title ──────────────────────────────────────────────────────────
    draw_mixed(draw, "⚡ TXABOT UPTIME", (PAD + 18, PAD + 6),
               f_title, f_emoji, (255, 230, 170, 255))

    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    draw_mixed(draw, f"🤖 {bot_name}  |  Uptime: {uptime_str}  |  OS: {sys_info['os']}",
               (PAD + 18, PAD + 76), f_sub, f_emoji2, (225, 235, 255, 218))

    draw.line([PAD + 18, PAD + 121, W - PAD - 18, PAD + 121],
              fill=(255, 255, 255, 46), width=2)

    # ── Time cards ────────────────────────────────────────────────────
    metrics = [
        ("NGÀY", days, (255, 93, 47)),
        ("GIỜ", hours, (255, 193, 7)),
        ("PHÚT", minutes, (34, 197, 94)),
        ("GIÂY", seconds, (59, 130, 246)),
    ]

    card_x = PAD + 18
    card_y = PAD + 155
    card_w = 650
    card_h = 286
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h],
                           radius=28, fill=(0, 0, 0, 105),
                           outline=(255, 255, 255, 35), width=1)
    draw_mixed(draw, "⏳ THỜI GIAN HOẠT ĐỘNG", (card_x + 28, card_y + 24),
               f_header, f_emoji2, (255, 255, 255, 244))

    box_w = 138
    box_h = 150
    gap = 18
    start_x = card_x + 28
    box_y = card_y + 94

    for i, (label, val, rgb) in enumerate(metrics):
        bx = start_x + i * (box_w + gap)
        by = box_y

        draw.rounded_rectangle([bx + 5, by + 7, bx + box_w + 5, by + box_h + 7],
                               radius=22, fill=(0, 0, 0, 82))
        draw.rounded_rectangle([bx, by, bx + box_w, by + box_h],
                               radius=22, fill=rgb + (226,),
                               outline=(255, 255, 255, 52), width=1)
        draw.rounded_rectangle([bx + 10, by + 9, bx + box_w - 10, by + 35],
                               radius=13, fill=(255, 255, 255, 45))
        val_str = str(val)
        value_font = f_value if len(val_str) <= 2 else f_small_value
        vw = _text_w(value_font, val_str)
        _draw_shadow_text(draw, (bx + (box_w - vw) // 2, by + 38),
                          val_str, value_font, (255, 255, 255, 255))
        lw = _text_w(f_label, label)
        draw.text((bx + (box_w - lw) // 2, by + box_h - 35),
                  label, font=f_label, fill=(255, 255, 255, 232))

    # ── System panel ─────────────────────────────────────────────────
    panel_x = card_x + card_w + 30
    panel_y = card_y
    panel_w = W - PAD - 18 - panel_x
    panel_h = card_h
    draw.rounded_rectangle([panel_x, panel_y, panel_x + panel_w, panel_y + panel_h],
                           radius=28, fill=(0, 0, 0, 108),
                           outline=(255, 255, 255, 35), width=1)
    draw_mixed(draw, "SYSTEM STATUS", (panel_x + 28, panel_y + 24),
               f_header, f_emoji2, (255, 255, 255, 244))

    bar_x = panel_x + 30
    bar_w = panel_w - 60
    _draw_bar(draw, bar_x, panel_y + 104, bar_w, 18, _pct_value(sys_info["cpu_usage"]),
              (0, 229, 255, 235), "CPU Usage", sys_info["cpu_usage"], f_sub, f_sub)
    _draw_bar(draw, bar_x, panel_y + 174, bar_w, 18, _pct_value(sys_info["ram_pct"]),
              (255, 64, 129, 235), "RAM Usage", sys_info["ram_pct"], f_sub, f_sub)
    draw.text((bar_x, panel_y + 220), "RAM", font=f_tiny, fill=(180, 195, 230, 210))
    draw.text((bar_x + 52, panel_y + 220),
              f"{sys_info['ram_used']} / {sys_info['ram_total']}",
              font=f_tiny, fill=(255, 255, 255, 230))
    draw.text((bar_x, panel_y + 247), "BOT", font=f_tiny, fill=(180, 195, 230, 210))
    draw.text((bar_x + 52, panel_y + 247), sys_info["proc_mem"],
              font=f_tiny, fill=(255, 255, 255, 230))

    # ── Bottom strip ──────────────────────────────────────────────────
    boot_y = card_y + card_h + 28
    last_boot = datetime.fromtimestamp(start_ts).strftime("%d/%m/%Y  %H:%M:%S")
    bottom_h = 116
    draw.rounded_rectangle([card_x, boot_y, W - PAD - 18, boot_y + bottom_h],
                           radius=26, fill=(255, 255, 255, 18),
                           outline=(255, 255, 255, 28), width=1)
    draw_mixed(draw, "🕐 KHỞI ĐỘNG LẦN CUỐI", (card_x + 30, boot_y + 24),
               f_sub, f_emoji2, (190, 210, 255, 230))
    draw.text((card_x + 30, boot_y + 58), last_boot,
              font=f_header, fill=(255, 255, 255, 246))

    # ── Draw Tech Stack Icons ─────────────────────────────────────────
    tech_x = card_x + 480
    draw_mixed(draw, "🛠️ TECH STACK", (tech_x, boot_y + 24),
               f_sub, f_emoji2, (190, 210, 255, 230))
               
    tech_icons = ["python", "docker", "react", "javascript", "git"]
    icon_size = 42
    icon_y = boot_y + 54
    for idx, name in enumerate(tech_icons):
        try:
            icon_img = get_tech_icon(name, size=icon_size)
            if icon_img:
                ov.paste(icon_img, (tech_x + idx * (icon_size + 14), icon_y), icon_img)
        except Exception as e:
            print(f"[uptime] Error drawing tech icon {name}: {e}")

    status = "ONLINE"
    sw = _text_w(f_header, status)
    badge_x = W - PAD - 18 - 190
    draw.rounded_rectangle([badge_x, boot_y + 30, badge_x + 150, boot_y + 78],
                           radius=24, fill=(0, 230, 118, 210))
    draw.text((badge_x + (150 - sw) // 2, boot_y + 38), status,
              font=f_header, fill=(4, 18, 12, 255))

    accent = [(255, 93, 47, 235), (255, 193, 7, 235), (0, 230, 118, 235), (0, 229, 255, 235), (255, 64, 129, 235)]
    seg = (W - PAD * 2 - 36) // len(accent)
    bar_y = H - PAD - 10
    for i, col in enumerate(accent):
        sx = PAD + 18 + i * seg
        draw.rounded_rectangle([sx, bar_y, sx + seg - 8, bar_y + 12],
                               radius=6, fill=col)

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
                              width=1280, height=720)
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
