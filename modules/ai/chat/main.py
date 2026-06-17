# -*- coding: UTF-8 -*-
"""
Module: chat.py
Lệnh: chat, c, ai, nói, hỏi
─────────────────────────────────────────────────────────────────
CORE FEATURES:
  1. Persistent history per thread  →  bot học từ hội thoại, càng chat càng thông minh
  2. Dynamic role detection         →  detect vai vế từ ngữ cảnh (anh/chị/em/bạn...)
  3. Consistent persona             →  xưng hô nhất quán, có cảm xúc, không tùy hứng
  4. Relationship evolution         →  tích lũy "điểm thân thiết", phản hồi thay đổi theo thời gian
  5. Admin control                  →  bật/tắt chat theo nhóm
  6. Rate limiting                  →  chống spam
  7. Image support                  →  chat qua hình ảnh
─────────────────────────────────────────────────────────────────
"""

import sys
import os
import json
import re
import time
import requests
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from core.bot_sys import read_settings, write_settings, is_admin

sys.dont_write_bytecode = True

# ─── METADATA ─────────────────────────────────────────────────────────────────
txa = {
    "name": "AI Chat",
    "desc": {
        "chat": "Trò chuyện với AI thông minh lưu lịch sử",
        "c": "Chat nhanh với AI trợ lý",
        "ai": "Hỏi đáp kiến thức cùng trí tuệ nhân tạo",
        "noi": "Trò chuyện thân mật cùng AI",
        "hoi": "Đặt câu hỏi nhanh cho trợ lý AI",
        "talk": "Trò chuyện bằng tiếng Anh hoặc tự do với AI"
    },
    "author": "TXA",
    "command": ["chat", "c", "ai", "noi", "hoi", "talk"]
}

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
HISTORY_DIR      = "chat_history"      # thư mục lưu lịch sử
MAX_HISTORY      = 20                  # số lượt tối đa đưa vào context
INTIMACY_FILE    = "chat_intimacy.json"  # file lưu điểm thân thiết
INTIMACY_CLOSE   = 30                  # ngưỡng "thân rồi"
INTIMACY_VERY_CLOSE = 80               # ngưỡng "thân lắm rồi"
RATE_LIMIT_SECONDS = 4                 # thời gian tối thiểu giữa 2 tin nhắn
API_TIMEOUT_SECONDS = 12               # giới hạn delay khi gọi AI API
MAX_API_HISTORY = 12                   # số lượt history tối đa đưa vào API

os.makedirs(HISTORY_DIR, exist_ok=True)

# ─── RATE LIMITING ─────────────────────────────────────────────────────────────
last_message_times = {}

# ─── ADMIN CONTROL ─────────────────────────────────────────────────────────────

def handle_chat_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "chat" not in settings:
        settings["chat"] = {}
    settings["chat"][thread_id] = True
    write_settings(bot.uid, settings)
    return "Ok, bật chat rồi nha, giờ thì quậy tưng bừng với TXABOT đây! 😎"

def handle_chat_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "chat" in settings and thread_id in settings["chat"]:
        settings["chat"][thread_id] = False
        write_settings(bot.uid, settings)
        return "Tắt chat rồi, buồn thiệt chứ, nhưng cần TXABOT thì cứ réo nhé! 😌"
    return "Nhóm này chưa bật chat mà, tắt gì nổi đâu đại ka! 😂"

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        name = user_info.zaloName or user_info.displayName or ""
        name = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
        return name or "Unknown User"
    except Exception:
        return "Unknown User"

# ─── SYSTEM PROMPT ────────────────────────────────────────────────────────────
# Đây là "linh hồn" của bot — quyết định toàn bộ cách ứng xử

SYSTEM_PROMPT = """Mày là TXA — AI chat Việt Nam, thông minh, dễ thương, lém lỉnh.

QUY TẮC:
1. Xưng hô: Phát hiện user gọi mày gì rồi xưng đúng vai. Chưa rõ → "mình/bạn". Giữ nhất quán.
2. Phong cách: Ngắn gọn như nhắn Zalo. 1-3 emoji/tin. Tiếng Việt tự nhiên.
3. Không bịa info, không nhận là người thật. Không biết → nói thẳng.
4. Nhớ ngữ cảnh từ lịch sử chat.
5. KHÔNG đổi vai giữa chừng, KHÔNG trả lời máy móc.
"""

# ─── HISTORY MANAGER ──────────────────────────────────────────────────────────

def _history_path(thread_id: str) -> str:
    return os.path.join(HISTORY_DIR, f"chat_{thread_id}.json")


def _load_history(thread_id: str) -> list:
    path = _history_path(thread_id)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_history(thread_id: str, history: list):
    path = _history_path(thread_id)
    try:
        # Chỉ giữ MAX_HISTORY * 2 entries gần nhất để tránh file quá lớn
        trimmed = history[-(MAX_HISTORY * 2):]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(trimmed, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[chat] Lỗi save history: {e}")


def _append_history(thread_id: str, role: str, content: str):
    history = _load_history(thread_id)
    history.append({"role": role, "content": content, "ts": int(time.time())})
    _save_history(thread_id, history)


def _get_context_history(thread_id: str, limit: int = MAX_HISTORY) -> list:
    """Lấy history để đưa vào API (chỉ role + content, bỏ ts)."""
    history = _load_history(thread_id)
    recent = history[-limit:]
    return [{"role": h["role"], "content": h["content"]} for h in recent]

# ─── INTIMACY SYSTEM ──────────────────────────────────────────────────────────

def _load_intimacy() -> dict:
    try:
        if os.path.exists(INTIMACY_FILE):
            with open(INTIMACY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_intimacy(data: dict):
    try:
        with open(INTIMACY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _get_intimacy(thread_id: str) -> int:
    return _load_intimacy().get(str(thread_id), 0)


def _add_intimacy(thread_id: str, points: int = 1):
    data = _load_intimacy()
    key  = str(thread_id)
    data[key] = data.get(key, 0) + points
    _save_intimacy(data)

# ─── ROLE DETECTOR ────────────────────────────────────────────────────────────

# Cache vai vế per thread
_role_cache: dict[str, dict] = {}

# Pattern phát hiện user gọi bot bằng gì
_ROLE_PATTERNS = {
    "user_calls_em": [
        r"\bem\b", r"\bcon\b"
    ],
    "user_calls_anh": [
        r"\banh\b", r"\b(ông|thầy|sếp|boss)\b"
    ],
    "user_calls_chi": [
        r"\bchị\b", r"\bcô\b", r"\bbà\b"
    ],
    "user_calls_ban": [
        r"\bbạn\b", r"\bcậu\b", r"\bmày\b", r"\bpạn\b"
    ],
}

def _detect_role(text: str, thread_id: str) -> dict | None:
    """
    Detect cách user gọi bot, trả về dict {bot_xung, bot_goi_user}.
    Cache lại cho thread đó.
    """
    text_lower = text.lower()

    # Check cache trước
    cached = _role_cache.get(str(thread_id))

    # Detect từ tin nhắn hiện tại
    for pattern in _ROLE_PATTERNS["user_calls_anh"]:
        if re.search(pattern, text_lower):
            role = {"bot_xung": "em", "bot_goi": "anh", "label": "em-anh"}
            _role_cache[str(thread_id)] = role
            return role

    for pattern in _ROLE_PATTERNS["user_calls_chi"]:
        if re.search(pattern, text_lower):
            role = {"bot_xung": "em", "bot_goi": "chị", "label": "em-chị"}
            _role_cache[str(thread_id)] = role
            return role

    for pattern in _ROLE_PATTERNS["user_calls_em"]:
        if re.search(pattern, text_lower):
            # User tự xưng "em" → bot là anh/chị, mặc định anh
            role = {"bot_xung": "anh", "bot_goi": "em", "label": "anh-em"}
            _role_cache[str(thread_id)] = role
            return role

    for pattern in _ROLE_PATTERNS["user_calls_ban"]:
        if re.search(pattern, text_lower):
            role = {"bot_xung": "mình", "bot_goi": "bạn", "label": "ban-be"}
            _role_cache[str(thread_id)] = role
            return role

    # Không detect được → dùng cache hoặc default
    return cached or {"bot_xung": "mình", "bot_goi": "bạn", "label": "default"}


def _build_role_hint(role: dict, intimacy: int) -> str:
    """Tạo hint về vai vế và mức độ thân thiết để inject vào system prompt."""
    bot_x = role["bot_xung"]
    bot_g = role["bot_goi"]

    level = "mới quen"
    if intimacy >= INTIMACY_VERY_CLOSE:
        level = "rất thân thiết, đã hiểu nhau nhiều"
    elif intimacy >= INTIMACY_CLOSE:
        level = "đã khá thân"

    return (
        f"\n━━━ CONTEXT HIỆN TẠI ━━━\n"
        f"• Mày xưng: [{bot_x}] — gọi user là [{bot_g}]\n"
        f"• Mức độ thân thiết: {level} (điểm: {intimacy})\n"
        f"• Giữ ĐÚNG vai vế này trong toàn bộ response."
    )

# ─── API CALLER ───────────────────────────────────────────────────────────────

def _read_api_config():
    try:
        cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../txa.json"))
        if not os.path.exists(cfg_path):
            cfg_path = "txa.json"
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        bot_data = (data.get("data") or [{}])[0]
        base = bot_data.get("kairobot_base_url", "https://kairobot.qzz.io").rstrip("/")
        key  = bot_data.get("kairobot_api_key", "")
        return base, key
    except Exception:
        return "https://kairobot.qzz.io", ""


def _sanitize_history_for_api(history: list) -> list:
    """Chuẩn history đúng schema API: chỉ giữ role/content hợp lệ."""
    allowed_roles = {"user", "assistant"}
    clean = []
    for item in history[-MAX_API_HISTORY:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role in allowed_roles and content:
            clean.append({"role": role, "content": content})
    if clean and clean[-1].get("role") != "assistant":
        clean.append({"role": "assistant", "content": "Mình nghe rồi."})
    return clean


def _call_ai(base: str, key: str, content: str, history: list, system_hint: str, image_url: str = None) -> str:
    """
    POST /ai/chat
    Body: { style, content, model, history, url }
    history = [ {role, content}, ... ]
    """
    url = f"{base}/ai/chat"
    params = {"apikey": key} if key else None
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "TXABot/2.0",
    }

    # Inject system prompt vào đầu history, nhưng vẫn giữ đúng schema API.
    full_history = _sanitize_history_for_api([
        {"role": "user",      "content": SYSTEM_PROMPT + system_hint},
        {"role": "assistant", "content": "Oke, mình hiểu rồi. Mình sẽ giữ đúng vai vế và phong cách nhé!"},
    ] + history)

    payload = {
        "style":   "chat",
        "model":   "online",
        "content": content,
        "history": full_history,
    }

    # Thêm image_url nếu có
    if image_url:
        payload["url"] = image_url

    r = requests.post(url, json=payload, params=params, headers=headers, timeout=API_TIMEOUT_SECONDS)
    
    if r.status_code == 401:
        raise Exception(f"API Key hết hạn hoặc không hợp lệ!\nAPI URL: {url}\nAPI Key: {key[:8]}...")

    if not r.ok:
        raise requests.HTTPError(
            f"{r.status_code} {r.reason}: {r.text[:300]}",
            response=r
        )
    data = r.json()

    # Normalize response — API có thể trả về nhiều format
    reply = (
        data.get("reply")
        or data.get("content")
        or data.get("message")
        or data.get("response")
        or data.get("text")
        or (data.get("data") or {}).get("reply")
        or (data.get("data") or {}).get("content")
        or ""
    )
    return reply.strip()

# ─── COMMAND HANDLER ────────────────────────────────────────────────────────────

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    from zlapi.models import Message, ThreadType

    prefix = getattr(bot, 'prefix', '*')
    parts   = message_text.strip().split(None, 1)
    cmd     = parts[0].lstrip("*!./").lower() if parts else ""
    content = parts[1].strip() if len(parts) > 1 else ""

    # ── Xử lý lệnh on/off (chỉ admin) ──────────────────────────────────────
    if content.lower() == "on":
        if not is_admin(bot, author_id):
            bot.replyMessage(
                Message(text="❌ Bạn không phải admin bot!"),
                message_object, thread_id, thread_type
            )
        else:
            response = handle_chat_on(bot, thread_id)
            bot.replyMessage(Message(text=response), message_object, thread_id, thread_type)
        return

    if content.lower() == "off":
        if not is_admin(bot, author_id):
            bot.replyMessage(
                Message(text="❌ Bạn không phải admin bot!"),
                message_object, thread_id, thread_type
            )
        else:
            response = handle_chat_off(bot, thread_id)
            bot.replyMessage(Message(text=response), message_object, thread_id, thread_type)
        return

    # ── Kiểm tra xem chat đã được bật chưa ─────────────────────────────────
    settings = read_settings(bot.uid)
    if not (settings.get("chat", {}).get(thread_id, False)):
        return

    # ── Rate limiting ───────────────────────────────────────────────────────
    current_time = datetime.now()
    if author_id in last_message_times:
        time_diff = current_time - last_message_times[author_id]
        if time_diff < timedelta(seconds=RATE_LIMIT_SECONDS):
            bot.replyMessage(
                Message(text=f"Ơi {get_user_name_by_id(bot, author_id)}, từ từ thôi! TXABOT đây không phải siêu máy tính chạy max tốc độ đâu nha! �"),
                message_object, thread_id, thread_type
            )
            return
    last_message_times[author_id] = current_time

    # ── Trích xuất link ảnh nếu có gửi kèm ảnh hoặc reply ảnh ───────────────
    image_url = None
    if message_object.msgType == "chat.photo":
        img_url = message_object.content.href.replace("\\/", "/")
        image_url = urllib.parse.unquote(img_url)
    elif message_object.quote:
        attach = message_object.quote.attach
        if attach:
            try:
                attach_data = json.loads(attach)
                image_url = attach_data.get('hdUrl') or attach_data.get('href')
            except Exception:
                pass

    # ── Xử lý nội dung chat ─────────────────────────────────────────────────
    query_text = content
    if not query_text and image_url:
        query_text = "Mô tả hình ảnh này giúp mình"

    if not query_text:
        bot.replyMessage(
            Message(text="⚠️ Vui lòng nhập nội dung cần trò chuyện. Ví dụ: *chat xin chào"),
            message_object, thread_id, thread_type
        )
        return

    # ── Gọi AI với các tính năng mới ─────────────────────────────────────────
    base, key = _read_api_config()
    if not key:
        bot.replyMessage(
            Message(text="⚠️ Chưa cấu hình kairobot_api_key trong txa.json!"),
            message_object, thread_id, thread_type
        )
        return

    tid_str = str(thread_id)

    # ── 1. Detect vai vế ──────────────────────────────────────────────────
    role = _detect_role(query_text, tid_str)

    # ── 2. Lấy điểm thân thiết ───────────────────────────────────────────
    intimacy = _get_intimacy(tid_str)

    # ── 3. Build system hint ──────────────────────────────────────────────
    system_hint = _build_role_hint(role, intimacy)

    # ── 4. Lấy history context ────────────────────────────────────────────
    ctx_history = _get_context_history(tid_str)

    # ── 5. Gọi AI ─────────────────────────────────────────────────────────
    try:
        reply = _call_ai(base, key, query_text, ctx_history, system_hint, image_url)
    except requests.Timeout:
        bot.replyMessage(
            Message(text="⏳ AI đang bận, thử lại sau ít giây nha~"),
            message_object, thread_id, thread_type
        )
        return
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            bot.replyMessage(
                Message(text=f"❌ Lỗi xác thực API!\n📍 API URL: {base}/ai/chat\n🔑 API Key: {key[:8]}...\n\nVui lòng kiểm tra lại API Key!"),
                message_object, thread_id, thread_type
            )
        else:
            bot.replyMessage(
                Message(text=f"❌ Lỗi AI: {e}"),
                message_object, thread_id, thread_type
            )
        return

    if not reply:
        bot.replyMessage(
            Message(text="🤔 AI trả về rỗng, thử lại xem~"),
            message_object, thread_id, thread_type
        )
        return

    # ── 6. Lưu vào history ────────────────────────────────────────────────
    _append_history(tid_str, "user",      query_text)
    _append_history(tid_str, "assistant", reply)

    # ── 7. Tăng điểm thân thiết ──────────────────────────────────────────
    # +2 nếu nội dung dài (chat nghiêm túc), +1 bình thường
    points = 2 if len(query_text) > 50 else 1
    _add_intimacy(tid_str, points)

    # ── 8. Gửi reply ─────────────────────────────────────────────────────
    bot.replyMessage(Message(text=reply), message_object, thread_id, thread_type)


# ─── LISTENER: Auto-chat khi tag bot hoặc reply bot ──────────────────────────
# (Không cần prefix lệnh — bot tự respond khi được mention)

def listener(bot, message_object, author_id, thread_id, thread_type, message_text):
    """
    Auto-trigger khi:
    - User reply vào tin nhắn của bot với prefix 'learn'
    - User mention tên bot với prefix 'learn'
    Không cần gõ *chat
    """
    from zlapi.models import Message, ThreadType

    # Đảm bảo message_text là string
    if not message_text:
        return
    if not isinstance(message_text, str):
        message_text = str(message_text)
    if not message_text.strip():
        return

    # ── Kiểm tra xem chat đã được bật chưa ─────────────────────────────────
    settings = read_settings(bot.uid)
    if not (settings.get("chat", {}).get(thread_id, False)):
        return

    # Kiểm tra mention tên bot hoặc reply vào tin nhắn của bot.
    bot_name = getattr(bot, "_username", "txa").lower()
    prefix = getattr(bot, "prefix", "*")
    normalized = message_text.strip()

    # Không hijack các lệnh đã có prefix, tránh trường hợp tên bot nằm trong lệnh khác.
    if normalized.lower().startswith(prefix):
        return

    is_reply_to_bot = bool(getattr(message_object, "quote", None))
    is_mention = False
    if bot_name:
        is_mention = re.search(rf"(^|\W){re.escape(bot_name)}(\W|$)", normalized.lower()) is not None

    if not is_reply_to_bot and not is_mention:
        return

    # CHỈ trigger khi có prefix 'learn' ở đầu tin nhắn
    if not normalized.lower().startswith("learn"):
        return

    # Bỏ 'learn' và mention name ra khỏi content.
    clean = normalized[5:].strip()  # Bỏ 'learn' (5 ký tự)
    clean = re.sub(re.escape(bot_name), "", clean, flags=re.IGNORECASE).strip() if bot_name else clean
    if clean:
        txa_command(bot, message_object, thread_id, thread_type, author_id, "chat " + clean)
