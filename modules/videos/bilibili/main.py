# -*- coding: utf-8 -*-
import requests
from zlapi.models import Message, MultiMsgStyle, MessageStyle

txa = {
    "name": "bilibili",
    "desc": {
        "bili": "Tìm kiếm video trên Bilibili TV",
        "bilibili": "Tìm kiếm video trên Bilibili TV"
    },
    "author": "TXA",
    "command": ["bili", "bilibili"],
    "t-per": "all"
}

API_URL = "https://apiwebfree.lovable.app/api/bilibili-search"
DEFAULT_PAGE_SIZE = 5
MAX_PAGE_SIZE = 10

FONT_SIZE = "9"

def _sty(text, color="#e8eaf6"):
    h = len(text.split("\n")[0]) + 1
    return MultiMsgStyle([
        MessageStyle(offset=0, length=len(text), style="font", size=FONT_SIZE, auto_format=False),
        MessageStyle(offset=0, length=h, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=h, style="bold", auto_format=False),
    ])

def search_bilibili(keyword, page=1, page_size=5, sort=0, duration_type=0):
    """Tìm kiếm video Bilibili qua API."""
    try:
        params = {
            "keyword": keyword,
            "page": page,
            "pageSize": page_size,
            "sort": sort,
            "durationType": duration_type
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        resp = requests.get(API_URL, params=params, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and data.get("data"):
                return data["data"]
        return None
    except Exception as e:
        print(f"[BILIBILI] Lỗi API: {e}")
        return None

def txa_command(client, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(client, "prefix", ".")

    # Parse command
    parts = message_text.strip().split(maxsplit=1)
    if not parts:
        return

    cmd_raw = parts[0]
    cmd = cmd_raw[len(prefix):].strip().lower() if cmd_raw.startswith(prefix) else cmd_raw.strip().lower()

    if cmd not in ("bili", "bilibili"):
        return

    args_str = parts[1].strip() if len(parts) > 1 else ""

    # Không có keyword
    if not args_str:
        help_msg = (
            f"🎬 BILIBILI SEARCH\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📌 Cú pháp:\n"
            f"  {prefix}bili <từ khóa>\n"
            f"  {prefix}bili <từ khóa> -p <trang>\n"
            f"  {prefix}bili <từ khóa> -n <số kết quả>\n\n"
            f"📋 Ví dụ:\n"
            f"  {prefix}bili one piece\n"
            f"  {prefix}bili naruto -p 2\n"
            f"  {prefix}bili dragon ball -n 3"
        )
        client.replyMessage(
            Message(text=help_msg, style=_sty(help_msg, "#F7B503")),
            message_object, thread_id, thread_type, ttl=30000
        )
        return

    # Parse tham số -p (page) và -n (số kết quả)
    page = 1
    count = DEFAULT_PAGE_SIZE
    keyword = args_str

    arg_parts = args_str.split()
    filtered = []
    i = 0
    while i < len(arg_parts):
        if arg_parts[i] == "-p" and i + 1 < len(arg_parts) and arg_parts[i + 1].isdigit():
            page = max(1, int(arg_parts[i + 1]))
            i += 2
        elif arg_parts[i] == "-n" and i + 1 < len(arg_parts) and arg_parts[i + 1].isdigit():
            count = min(MAX_PAGE_SIZE, max(1, int(arg_parts[i + 1])))
            i += 2
        else:
            filtered.append(arg_parts[i])
            i += 1

    keyword = " ".join(filtered).strip()
    if not keyword:
        keyword = args_str.split("-")[0].strip()

    # Gửi thông báo đang tìm
    loading_msg = f"🔍 Đang tìm \"{keyword}\" trên Bilibili..."
    client.replyMessage(
        Message(text=loading_msg, style=_sty(loading_msg, "#F7B503")),
        message_object, thread_id, thread_type, ttl=8000
    )

    # Gọi API
    result = search_bilibili(keyword, page=page, page_size=count)

    if not result:
        err_msg = f"❌ Không tìm thấy kết quả cho \"{keyword}\"\n💡 Thử từ khóa khác hoặc kiểm tra lại!"
        client.replyMessage(
            Message(text=err_msg, style=_sty(err_msg, "#DB342E")),
            message_object, thread_id, thread_type, ttl=20000
        )
        return

    videos = [v for v in result.get("results", []) if v.get("url")]
    total = result.get("total", 0)
    has_more = result.get("hasMore", False)
    cur_page = result.get("page", page)

    if not videos:
        err_msg = f"❌ Không có video nào cho \"{keyword}\" (trang {page})\n💡 Thử trang khác: {prefix}bili {keyword} -p 2"
        client.replyMessage(
            Message(text=err_msg, style=_sty(err_msg, "#DB342E")),
            message_object, thread_id, thread_type, ttl=20000
        )
        return

    # Build kết quả
    lines = [
        f"🎬 KẾT QUẢ BILIBILI: \"{keyword}\"",
        f"📄 Trang {cur_page} | 🎯 Tìm thấy {total} video",
        "━━━━━━━━━━━━━━━━━━━━━━"
    ]

    for i, v in enumerate(videos[:count], 1):
        title = v.get("title", "Không rõ")
        url = v.get("url", "")
        duration = v.get("duration", "?")
        views = v.get("views", "?")
        author = v.get("author", {}).get("nickname", "Ẩn danh")

        # Cắt title nếu quá dài
        if len(title) > 60:
            title = title[:57] + "..."

        lines.append(f"\n{i}. 🎞 {title}")
        lines.append(f"   ⏱ {duration}  👁 {views}")
        lines.append(f"   👤 {author}")
        lines.append(f"   🔗 {url}")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━")
    if has_more:
        lines.append(f"➡️ Trang tiếp: {prefix}bili {keyword} -p {cur_page + 1}")
    else:
        lines.append(f"✅ Đây là trang cuối cùng")

    msg = "\n".join(lines)
    client.replyMessage(
        Message(text=msg, style=_sty(msg, "#00B4D8")),
        message_object, thread_id, thread_type, ttl=120000
    )
