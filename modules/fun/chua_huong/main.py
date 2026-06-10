"""
Module: chua_huong ⛩️
Lệnh đi chùa thắp hương cầu may mắn.

Cách dùng:
  .chua              → random chùa, random lời cầu
  .chua list         → xem danh sách chùa có thể chọn
  .chua <số>         → chọn chùa theo số thứ tự từ list
  .chua <số> <lời>   → chọn chùa + lời cầu tùy chỉnh
"""

import os
import json
import random
import time
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from zlapi.models import Message, MessageStyle, MultiMsgStyle

# ─── Paths ───────────────────────────────────────────────────────────────────
_BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
_API_DIR    = os.path.abspath(os.path.join(_BASE_DIR, "../../../Api"))
_CACHE_DIR  = os.path.abspath(os.path.join(_BASE_DIR, "../../../cache"))
_FONT_ARIAL = os.path.abspath(os.path.join(_BASE_DIR, "../../../font/arial unicode ms.otf"))
_FONT_NOTO_EMOJI = os.path.abspath(os.path.join(_BASE_DIR, "../../../font/NotoEmoji-Bold.ttf"))
_FONT_EMOJI_TTF = os.path.abspath(os.path.join(_BASE_DIR, "../../../font/emoji.ttf"))
_FONT_EMOJI_TTC = os.path.abspath(os.path.join(_BASE_DIR, "../../../font/emoji.ttc"))
_CHUA_JSON  = os.path.join(_API_DIR, "chua.json")
os.makedirs(_CACHE_DIR, exist_ok=True)

# ─── Danh sách chùa ──────────────────────────────────────────────────────────
CHUA_LIST = [
    {"id": 1,  "name": "Chùa Hương",       "dia_chi": "Mỹ Đức, Hà Nội",       "icon": "⛩️",  "img_key": "chua_huong"},
    {"id": 2,  "name": "Chùa Bái Đính",    "dia_chi": "Ninh Bình",             "icon": "🏯",  "img_key": "bai_dinh"},
    {"id": 3,  "name": "Chùa Yên Tử",      "dia_chi": "Quảng Ninh",            "icon": "⛰️",  "img_key": "yen_tu"},
    {"id": 4,  "name": "Chùa Thiên Mụ",    "dia_chi": "Huế",                   "icon": "🌸",  "img_key": "thien_mu"},
    {"id": 5,  "name": "Chùa Linh Ứng",    "dia_chi": "Đà Nẵng",               "icon": "🌊",  "img_key": "linh_ung"},
    {"id": 6,  "name": "Chùa Giác Lâm",    "dia_chi": "TP. Hồ Chí Minh",       "icon": "🕯️",  "img_key": "giac_lam"},
    {"id": 7,  "name": "Chùa Một Cột",     "dia_chi": "Ba Đình, Hà Nội",       "icon": "🏛️",  "img_key": "mot_cot"},
    {"id": 8,  "name": "Chùa Tây Thiên",   "dia_chi": "Vĩnh Phúc",             "icon": "🌿",  "img_key": "tay_thien"},
    {"id": 9,  "name": "Chùa Long Sơn",    "dia_chi": "Nha Trang, Khánh Hòa",  "icon": "🏖️",  "img_key": "long_son"},
    {"id": 10, "name": "Chùa Phúc Khánh",  "dia_chi": "Đống Đa, Hà Nội",       "icon": "🔔",  "img_key": "phuc_khanh"},
    {"id": 11, "name": "Chùa Trần Quốc",   "dia_chi": "Hồ Tây, Hà Nội",        "icon": "🌅",  "img_key": "tran_quoc"},
    {"id": 12, "name": "Chùa Vĩnh Nghiêm", "dia_chi": "Quận 3, TP.HCM",        "icon": "🌺",  "img_key": "vinh_nghiem"},
    {"id": 13, "name": "Chùa Tam Chúc",    "dia_chi": "Hà Nam",                "icon": "🏔️",  "img_key": "tam_chuc"},
    {"id": 14, "name": "Chùa Thầy",        "dia_chi": "Quốc Oai, Hà Nội",      "icon": "🍃",  "img_key": "chua_thay"},
    {"id": 15, "name": "Chùa Dâu",         "dia_chi": "Thuận Thành, Bắc Ninh", "icon": "🌾",  "img_key": "chua_dau"},
]

# Fallback image URLs nếu chua.json chưa có key tương ứng
# (ảnh chùa đẹp public — mày điền link thật vào chua.json để override)
_FALLBACK_URLS = {
    "chua_huong":  "https://upload.wikimedia.org/wikipedia/commons/5/57/Ch%C3%B9a_H%C6%B0%C6%A1ng.jpg",
    "bai_dinh":    "https://upload.wikimedia.org/wikipedia/commons/d/d9/M%E1%BB%98T_G%C3%93C_CH%C3%99A_B%C3%81I_%C4%90%C3%8DNH_-_panoramio.jpg",
    "yen_tu":      "https://upload.wikimedia.org/wikipedia/commons/3/31/N%C3%BAi_Y%C3%AAn_T%E1%BB%AD.jpg",
    "thien_mu":    "https://upload.wikimedia.org/wikipedia/commons/8/88/ThienMuPagoda.jpg",
    "linh_ung":    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Linh_Ung_Pagoda_14.jpg/960px-Linh_Ung_Pagoda_14.jpg",
    "long_son":    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Ch%E1%BB%A3_Long_S%C6%A1n.jpg/960px-Ch%E1%BB%A3_Long_S%C6%A1n.jpg?_=20140409185808",
    "tran_quoc":   "https://upload.wikimedia.org/wikipedia/commons/3/35/Tran_Quoc_Buddhist_Pagoda%2C_Hanoi%2C_6th_century_%2824%29_%2837610879445%29.jpg?utm_source=commons.wikimedia.org&utm_campaign=index&utm_content=original",
}

# ─── Danh sách lời cầu nguyện ─────────────────────────────────────────────
CAU_NGUYEN_LIST = [
    "Cầu bình an, sức khỏe dồi dào, gia đình hạnh phúc",
    "Cầu công việc thuận lợi, thăng tiến hanh thông",
    "Cầu tình duyên suôn sẻ, gặp được người tri kỷ",
    "Cầu học hành giỏi giang, thi đỗ như ý",
    "Cầu tài lộc dồi dào, vạn sự như ý",
    "Cầu gia đình hòa thuận, cha mẹ sống lâu trăm tuổi",
    "Cầu mọi ước nguyện đều thành hiện thực năm nay",
    "Cầu buôn bán phát đạt, tiền vào như nước",
    "Cầu vượt qua mọi khó khăn, tai qua nạn khỏi",
    "Cầu sự nghiệp rộng mở, danh tiếng vang xa",
    "Cầu bình an qua dịch bệnh, thiên tai",
    "Cầu con cái ngoan ngoãn, học giỏi thành tài",
    "Cầu hóa giải xui xẻo, rước phúc lộc về nhà",
    "Cầu xuất hành thuận lợi, đi đâu cũng may mắn",
    "Cầu tâm được an yên, phiền não tan biến",
    "Cầu trúng số độc đắc, đổi đời sang giàu 😂",
    "Cầu crush nhắn tin trước, tình yêu đến sớm",
    "Cầu deadline không bao giờ đến, sếp luôn vui vẻ",
    "Cầu wifi 5 vạch mọi nơi, pin điện thoại không bao giờ hết",
]

# ─── Danh sách kết quả cầu may ───────────────────────────────────────────────
KET_QUA_LIST = [
    ("🌟 THƯỢNG THƯỢNG CÁT",    "Vận trình đại hanh! Phúc lộc thọ hội tụ đủ đầy. Mọi sự mong cầu đều thành hiện thực trong nay mai!"),
    ("💎 ĐẠI CÁT",              "Tài lộc sẽ đến trong 3 ngày tới. Quý nhân phù trợ tứ phương, cơ hội tốt ập đến bất ngờ!"),
    ("🌈 THƯỢNG CÁT",           "Vận may đang trên đà tăng tiến. Hãy nắm bắt cơ hội và tiến lên, Phật đã phù hộ!"),
    ("🍀 TRUNG CÁT",            "Vận trình ổn định, từng bước vững chắc. Kiên nhẫn sẽ được đền đáp xứng đáng!"),
    ("🌺 TIỂU CÁT",             "Mọi chuyện sẽ dần ổn định. Tránh tranh cãi, giữ tâm bình an sẽ gặp điều tốt!"),
    ("☀️ BÁN CÁT BÁN HUNG",    "Vận số lúc lên lúc xuống, cần thận trọng trong các quyết định quan trọng!"),
    ("⚡ CÁT TINH CHIẾU MỆNH", "Ngôi sao may mắn đang chiếu vào cuộc đời bạn. Hành động ngay hôm nay!"),
    ("🔮 VẬN SỐ CHUYỂN BIẾN",  "Đây là thời điểm bước ngoặt. Dũng cảm thay đổi, vận may sẽ theo sau!"),
    ("🌙 CÁT THẦN PHÙ TRỢ",    "Được thiên thần hộ mệnh che chở. Đêm nay nằm mơ thấy điều tốt lành!"),
    ("🏆 PHẬT ĐỘ ĐẠI HANH",    "Lòng thành tâm đã cảm động Phật tổ! Nguyện cầu ắt được toại nguyện!"),
    ("🎯 CHÍNH TINH ĐẮC VỊ",   "Mọi kế hoạch đang đi đúng hướng. Tiếp tục kiên trì, thành công không xa!"),
    ("💫 VẠN SỰ NHƯ Ý",        "Trời đất phù hộ, vạn sự như ý! Hôm nay là ngày đặc biệt may mắn của bạn!"),
]

RAINBOW_COLORS = ["#f00e0e", "#f8f700", "#09f926", "#233ee6", "#46d0e5", "#9b23e6", "#f91be4"]
NEON_COLORS    = ["#00e5ff", "#ff4081", "#ffeb3b", "#00e676", "#ff9100", "#e040fb", "#18ffff"]

# ─── Helpers ─────────────────────────────────────────────────────────────────
def _load_font(path, size, fallback_size=None):
    try:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    except Exception:
        pass
    return ImageFont.load_default(size=fallback_size or size)


def _load_emoji_font(size):
    for font_path in [_FONT_NOTO_EMOJI, _FONT_EMOJI_TTF, _FONT_EMOJI_TTC]:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except Exception:
            continue
    return None


def _styled_msg(text, colors=None):
    if colors is None:
        colors = NEON_COLORS
    lines = text.split('\n')
    styles, offset = [], 0
    for i, line in enumerate(lines):
        color = colors[i % len(colors)]
        styles.append(MessageStyle(style="color", color=color, offset=offset, length=len(line), auto_format=False))
        offset += len(line) + 1
    if lines:
        styles.append(MessageStyle(style="font", size="14", offset=0, length=offset - 1, auto_format=False))
    return Message(text=text, style=MultiMsgStyle(styles))


def _is_emoji(char):
    try:
        # Thử import emoji package
        import emoji
        return char in emoji.EMOJI_DATA
    except Exception:
        # Fallback: kiểm tra range Unicode
        return (0x1F000 <= ord(char) <= 0x1FAFF or 
                0x2600 <= ord(char) <= 0x26FF or 
                0x2700 <= ord(char) <= 0x27BF or 
                0x2B00 <= ord(char) <= 0x2BFF or 
                0x1F600 <= ord(char) <= 0x1F64F or 
                0x1F680 <= ord(char) <= 0x1F6FF)


def _draw_mixed_text(draw, text, x, y, font_text, font_emoji, fill):
    """Vẽ text với emoji-aware, dùng đúng font cho từng ký tự."""
    cx = x
    for char in text:
        use_font = font_emoji if (_is_emoji(char) and font_emoji) else font_text
        try:
            draw.text((cx, y), char, font=use_font, fill=fill)
            try:
                cx += use_font.getlength(char)
            except AttributeError:
                bb = draw.textbbox((0, 0), char, font=use_font)
                cx += bb[2] - bb[0]
        except Exception:
            pass


def _measure_mixed(draw, text, font_text, font_emoji):
    """Đo width của mixed text."""
    total = 0
    for char in text:
        use_font = font_emoji if (_is_emoji(char) and font_emoji) else font_text
        try:
            total += use_font.getlength(char)
        except AttributeError:
            bb = draw.textbbox((0, 0), char, font=use_font)
            total += bb[2] - bb[0]
    return total


def _load_api_images():
    """Đọc chua.json từ Api folder. Format: {"key": ["url1","url2",...], ...} hoặc ["url1","url2"]"""
    if not os.path.exists(_CHUA_JSON):
        return {}
    try:
        with open(_CHUA_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return {"default": data}
        if isinstance(data, dict):
            return data
    except Exception as e:
        print(f"[chua_huong] Lỗi đọc chua.json: {e}")
    return {}


def _get_img_url(img_key):
    """Lấy URL ảnh: ưu tiên chua.json, fallback về _FALLBACK_URLS."""
    api_data = _load_api_images()
    urls = api_data.get(img_key) or api_data.get("default") or []
    if urls:
        return random.choice(urls)
    return _FALLBACK_URLS.get(img_key, "")


def _download_img(url, save_path):
    """Download ảnh từ URL, trả về True nếu OK."""
    if not url:
        return False
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://google.com/"
        }
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        if len(r.content) < 1024:
            return False
        with open(save_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"[chua_huong] Download lỗi: {e}")
        return False


def _create_result_banner(chua, user_name, loi_cau, ket_qua_title, ket_qua_desc, save_path):
    """
    Tạo ảnh banner kết quả cầu may.
    Tải ảnh chùa làm background, vẽ text overlay với đúng emoji font.
    """
    W, H = 980, 400

    # ── Load background ──
    img_url = _get_img_url(chua["img_key"])
    tmp_bg  = os.path.join(_CACHE_DIR, f"chua_bg_{int(time.time())}.jpg")
    ok      = _download_img(img_url, tmp_bg)

    if ok and os.path.exists(tmp_bg):
        try:
            bg = Image.open(tmp_bg).convert("RGBA").resize((W, H), Image.LANCZOS)
        except Exception:
            bg = _make_gradient_bg(W, H)
        finally:
            try:
                os.remove(tmp_bg)
            except Exception:
                pass
    else:
        bg = _make_gradient_bg(W, H)

    # ── Blur + dark overlay ──
    from PIL import ImageFilter
    bg = bg.filter(ImageFilter.GaussianBlur(radius=4))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 140))
    bg   = Image.alpha_composite(bg, dark)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    # ── Glass card ──
    card_color = (random.randint(20, 60), random.randint(20, 60), random.randint(40, 90), 200)
    draw.rounded_rectangle([40, 25, W - 40, H - 25], radius=28, fill=card_color)

    # ── Load fonts ──
    f_big   = _load_font(_FONT_ARIAL, 46)
    f_med   = _load_font(_FONT_ARIAL, 36)
    f_sm    = _load_font(_FONT_ARIAL, 26)
    f_xs    = _load_font(_FONT_ARIAL, 22)
    f_emoji = _load_emoji_font(38)
    f_emoji_big = _load_emoji_font(46)

    def cx_x(text, font_t, font_e):
        w = _measure_mixed(draw, text, font_t, font_e)
        return (W - w) // 2

    VIBRANT = [
        (255, 215, 0), (255, 105, 180), (0, 255, 180),
        (100, 200, 255), (255, 140, 0), (180, 255, 100)
    ]

    def vcolor():
        return random.choice(VIBRANT)

    y = 38

    # Row 1: tên chùa + icon
    line1 = f"{chua['icon']} {chua['name']}"
    x1    = cx_x(line1, f_big, f_emoji_big)
    _draw_mixed_text(draw, line1, x1, y, f_big, f_emoji_big, vcolor())

    y += 60
    # Row 2: địa chỉ
    line2 = f"📍 {chua['dia_chi']}"
    x2    = cx_x(line2, f_sm, f_emoji)
    _draw_mixed_text(draw, line2, x2, y, f_sm, f_emoji, (200, 240, 255))

    y += 48
    # Row 3: tên user + lời cầu
    line3 = f"🙏 {user_name}: {loi_cau}"
    # Wrap nếu dài
    max_w = W - 100
    if _measure_mixed(draw, line3, f_sm, f_emoji) > max_w:
        line3a = f"🙏 {user_name}"
        line3b = f"    {loi_cau}"
        x3a = cx_x(line3a, f_sm, f_emoji)
        _draw_mixed_text(draw, line3a, x3a, y, f_sm, f_emoji, (255, 255, 180))
        y += 40
        x3b = cx_x(line3b, f_sm, f_emoji)
        _draw_mixed_text(draw, line3b, x3b, y, f_sm, f_emoji, (255, 255, 180))
    else:
        x3 = cx_x(line3, f_sm, f_emoji)
        _draw_mixed_text(draw, line3, x3, y, f_sm, f_emoji, (255, 255, 180))

    y += 55
    # Row 4: kết quả title (lớn, màu rực)
    x4 = cx_x(ket_qua_title, f_med, f_emoji)
    _draw_mixed_text(draw, ket_qua_title, x4, y, f_med, f_emoji, vcolor())

    y += 52
    # Row 5: kết quả mô tả (nhỏ hơn, wrap)
    _draw_wrapped(draw, ket_qua_desc, f_xs, f_emoji, W, y, (220, 220, 220), max_line_w=W - 80)

    # Footer
    footer = f"🕯️ {time.strftime('%d/%m/%Y  %H:%M')}  •  Nam Mô A Di Đà Phật"
    xf     = cx_x(footer, f_xs, f_emoji)
    _draw_mixed_text(draw, footer, xf, H - 52, f_xs, f_emoji, (180, 180, 180))

    final = Image.alpha_composite(bg, overlay)
    final.convert("RGB").save(save_path, "JPEG", quality=92)
    return save_path


def _draw_wrapped(draw, text, font_t, font_e, canvas_w, y, fill, max_line_w=860):
    """Vẽ text wrap nếu quá dài."""
    words = text.split()
    line  = ""
    lines = []
    for w in words:
        test = (line + " " + w).strip()
        if _measure_mixed(draw, test, font_t, font_e) <= max_line_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    for l in lines:
        x = (canvas_w - _measure_mixed(draw, l, font_t, font_e)) // 2
        _draw_mixed_text(draw, l, x, y, font_t, font_e, fill)
        y += 34


def _make_gradient_bg(w, h):
    """Tạo gradient background khi không có ảnh."""
    img    = Image.new("RGBA", (w, h))
    pixels = img.load()
    c1 = (30, 10, 60)
    c2 = (10, 50, 80)
    for y in range(h):
        r = int(c1[0] + (c2[0] - c1[0]) * y / h)
        g = int(c1[1] + (c2[1] - c1[1]) * y / h)
        b = int(c1[2] + (c2[2] - c1[2]) * y / h)
        for x in range(w):
            pixels[x, y] = (r, g, b, 255)
    return img


def _get_user_name(bot, author_id):
    try:
        info = bot.fetchUserInfo(author_id)
        u    = info.changed_profiles.get(author_id)
        return getattr(u, 'zaloName', None) or getattr(u, 'name', None) or "Bạn"
    except Exception:
        return "Bạn"


def _build_list_text(prefix):
    lines = [
        "⛩️ DANH SÁCH CHÙA CÓ THỂ CHỌN",
        "━━━━━━━━━━━━━━━━━━",
    ]
    for c in CHUA_LIST:
        lines.append(f"{c['icon']} {c['id']:>2}. {c['name']} — {c['dia_chi']}")
    lines += [
        "━━━━━━━━━━━━━━━━━━",
        f"💡 Cách chọn: {prefix}chua <số>",
        f"💡 VD: {prefix}chua 3  hoặc  {prefix}chua 3 cầu thi đỗ",
    ]
    return "\n".join(lines)

# ─── Handler chính ────────────────────────────────────────────────────────────
def handle_chua_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix    = getattr(bot, 'prefix', '.')
    raw       = message_text[len(prefix):].strip()          # bỏ prefix
    parts     = raw.split(None, 2)                          # ['chua', [số], [lời]]
    user_name = _get_user_name(bot, author_id)

    # ── .chua list ──
    if len(parts) >= 2 and parts[1].lower() == "list":
        bot.replyMessage(
            _styled_msg(_build_list_text(prefix), NEON_COLORS),
            message_object,
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=120000
        )
        return

    # ── Parse số chùa và lời cầu ──
    chua      = None
    loi_cau   = None

    if len(parts) >= 2:
        arg1 = parts[1].strip()
        if arg1.isdigit():
            idx = int(arg1)
            chua = next((c for c in CHUA_LIST if c["id"] == idx), None)
            if not chua:
                bot.replyMessage(
                    _styled_msg(f"❌ Số {idx} không hợp lệ! Dùng {prefix}chua list để xem danh sách.", NEON_COLORS),
                    message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000
                )
                return
            if len(parts) >= 3:
                loi_cau = parts[2].strip()
        else:
            # Phần còn lại là lời cầu không có số chùa
            loi_cau = raw[len(parts[0]):].strip()

    if not chua:
        chua = random.choice(CHUA_LIST)
    if not loi_cau:
        loi_cau = random.choice(CAU_NGUYEN_LIST)

    ket_qua_title, ket_qua_desc = random.choice(KET_QUA_LIST)

    # Danh sách để lưu các message ID cần xóa sau
    temp_msg_ids = []

    # ── Bước 1: thông báo đang đi ──
    msg1 = bot.replyMessage(
        _styled_msg(
            f"🚌 {user_name} đang lên đường đến\n"
            f"   {chua['icon']} {chua['name']} — {chua['dia_chi']}...",
            NEON_COLORS
        ),
        message_object,
        thread_id=thread_id, thread_type=thread_type, ttl=60000
    )
    if msg1 and hasattr(msg1, 'msgId'):
        temp_msg_ids.append(msg1.msgId)

    # ── Bước 2: simulate ──
    steps = [
        f"🥾 Đã đến nơi! Bước qua cổng tam quan...",
        f"🪷 Thắp nén hương thơm, chắp tay kính cẩn...",
        f"🙏 Khấn nguyện: \"{loi_cau}\"",
        f"🔔 Chuông ngân~~ Mõ gõ~~ Tâm thành kính...",
        f"✨ Phật độ! Đang xem kết quả vận số...",
    ]
    for step in steps:
        time.sleep(1.3)
        step_msg = bot.sendMessage(
            _styled_msg(step, RAINBOW_COLORS),
            thread_id=thread_id, thread_type=thread_type, ttl=60000
        )
        if step_msg and hasattr(step_msg, 'msgId'):
            temp_msg_ids.append(step_msg.msgId)

    # ── Bước 3: tạo ảnh kết quả ──
    time.sleep(1.0)
    banner_path = os.path.join(_CACHE_DIR, f"chua_result_{int(time.time())}.jpg")

    try:
        _create_result_banner(chua, user_name, loi_cau, ket_qua_title, ket_qua_desc, banner_path)
        caption_text = (
            f"⛩️ KẾT QUẢ CẦU MAY\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Tín chủ : {user_name}\n"
            f"🏛️ Chùa   : {chua['icon']} {chua['name']}\n"
            f"🙏 Lời cầu : {loi_cau}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{ket_qua_title}\n"
            f"{ket_qua_desc}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Nam Mô A Di Đà Phật 🙏🙏🙏"
        )
        bot.sendLocalImage(
            banner_path,
            thread_id=thread_id,
            thread_type=thread_type,
            message=_styled_msg(caption_text, RAINBOW_COLORS),
            ttl=300000
        )
    except Exception as e:
        print(f"[chua_huong] Lỗi tạo/gửi banner: {e}")
        # Fallback: gửi text thuần
        bot.sendMessage(
            _styled_msg(
                f"⛩️ KẾT QUẢ CẦU MAY\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 {user_name} @ {chua['icon']} {chua['name']}\n"
                f"🙏 {loi_cau}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{ket_qua_title}\n{ket_qua_desc}\n"
                f"🙏🙏🙏 Nam Mô A Di Đà Phật",
                RAINBOW_COLORS
            ),
            thread_id=thread_id, thread_type=thread_type, ttl=300000
        )
    finally:
        if os.path.exists(banner_path):
            try:
                os.remove(banner_path)
            except Exception:
                pass
        # ── Xóa các tin nhắn tạm thời ──
        if hasattr(bot, 'deleteMessage'):
            for msg_id in temp_msg_ids:
                try:
                    bot.deleteMessage(msg_id, thread_id, thread_type)
                except Exception as e:
                    print(f"[chua_huong] Lỗi xóa tin nhắn {msg_id}: {e}")

# ─── Module metadata ─────────────────────────────────────────────────────────
txa = {
    "name": "chua_huong",
    "desc": {
        "chua": "Đi chùa thắp hương cầu may mắn 🙏 | chua list | chua <số> | chua <số> <lời cầu>",
    },
    "author": "TXA",
    "command": ["chua"]
}


def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    handle_chua_command(bot, message_object, thread_id, thread_type, author_id, message_text)
