# -*- coding: UTF-8 -*-
"""
Module: capcut.py
Lệnh: cap, capcut, capdl
- cap <từ khóa>           → Tìm ảnh/video CapCut template
- cap img <từ khóa>       → Tìm ảnh
- capdl <link>            → Tải video CapCut không watermark
"""

import os
import sys
import requests

sys.dont_write_bytecode = True

from PIL import Image
from modules.shared.cards import (
    create_search_card,
    create_download_card,
    create_help_card,
)

# ─── METADATA ─────────────────────────────────────────────────────────────────
txa = {
    "name": "CapCut Search & Download",
    "desc": {
        "cap": "Tìm kiếm ảnh/video CapCut",
        "capcut": "Tìm kiếm ảnh/video CapCut",
        "capdl": "Tải video CapCut không watermark",
        "capsearch": "Tìm kiếm ảnh/video CapCut"
    },
    "author": "TXA",
    "command": ["cap", "capcut", "capdl", "capsearch"]
}

# ─── CONFIG ───────────────────────────────────────────────────────────────────

def _get_api(bot):
    cfg  = getattr(bot, "_txa_config", None) or {}
    base = cfg.get("kairobot_base_url", "https://kairobot.qzz.io").rstrip("/")
    key  = cfg.get("kairobot_api_key", "")
    return base, key


def _api_headers(key: str) -> dict:
    return {
        "x-api-key": key,
        "User-Agent": "TXABot/2.0",
    }

# ─── FORMATTER ────────────────────────────────────────────────────────────────

def _fmt_num(n) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n) if n else "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _build_search_card(item: dict, index: int, ctype: str = "video") -> str:
    """
    Build card từ 1 kết quả search CapCut.
    API response fields (kairobot /capcut/search):
    title, author/creator, cover, url/share_url,
    use_count/like_count/view_count (tuỳ API)
    """
    title    = (item.get("title") or item.get("name") or item.get("text") or "").strip()
    title    = title[:80] + "…" if len(title) > 80 else title

    author   = item.get("author") or item.get("creator") or item.get("username") or "?"
    views    = _fmt_num(item.get("view_count") or item.get("use_count") or item.get("playCount") or 0)
    likes    = _fmt_num(item.get("like_count") or item.get("diggCount") or 0)
    uses     = _fmt_num(item.get("use_count") or item.get("used_count") or 0)

    share_url = (
        item.get("share_url")
        or item.get("url")
        or item.get("link")
        or item.get("webUrl")
        or ""
    )

    icon = "🎬" if ctype == "video" else "🖼️"

    lines = [
        f"{'═'*30}",
        f"{icon} [{index}] {title or '(Không có tiêu đề)'}",
        f"✏️ {author}",
    ]

    stats = []
    if views != "0": stats.append(f"👁️ {views}")
    if likes != "0": stats.append(f"❤️ {likes}")
    if uses  != "0": stats.append(f"🔁 {uses}")
    if stats:
        lines.append("  ".join(stats))

    if share_url:
        lines.append(f"🔗 {share_url}")

    return "\n".join(lines)


def _build_download_card(data: dict) -> str:
    title  = (data.get("title") or data.get("desc") or "").strip()
    title  = title[:100] + "…" if len(title) > 100 else title
    author = data.get("author") or data.get("creator") or data.get("username") or "?"

    return "\n".join([
        "╔═══════════════════════╗",
        "║  🎞️  CapCut Download   ║",
        "╚═══════════════════════╝",
        f"📝 {title or '(Không có tiêu đề)'}",
        f"✏️ {author}",
        "✅ Video không watermark đang gửi…",
    ])

# ─── API CALLS ────────────────────────────────────────────────────────────────

def _search_capcut(base: str, key: str, query: str, media_type: int = 1, count: int = 5):
    """
    GET /capcut/search?query=...&type=1
    type: 1 = video, 2 = ảnh
    count không phải param chính thức nhưng thêm phòng trường hợp
    """
    url = f"{base}/capcut/search"
    params = {"query": query, "type": media_type, "count": count}
    r = requests.get(url, params=params, headers=_api_headers(key), timeout=20)
    r.raise_for_status()
    return r.json()


def _download_capcut(base: str, key: str, link: str):
    """GET /capcut/download?url=..."""
    url = f"{base}/capcut/download"
    r = requests.get(url, params={"url": link}, headers=_api_headers(key), timeout=30)
    r.raise_for_status()
    return r.json()

# ─── COMMAND HANDLER ──────────────────────────────────────────────────────────

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    from zlapi.models import Message

    parts = message_text.strip().split(None, 1)
    cmd   = parts[0].lstrip("*!./").lower() if parts else ""
    arg   = parts[1].strip() if len(parts) > 1 else ""

    base, key = _get_api(bot)

    if not key:
        bot.replyMessage(
            Message(text="⚠️ Chưa cấu hình kairobot_api_key trong txa.json!"),
            message_object, thread_id, thread_type
        )
        return

    # ── DOWNLOAD MODE ─────────────────────────────────────────────────────
    if cmd == "capdl":
        if not arg or not arg.startswith("http"):
            bot.replyMessage(
                Message(text=(
                    "🎞️ Dùng: *capdl <link CapCut>\n"
                    "Ví dụ: *capdl https://www.capcut.com/t/Zs8PoABbX/"
                )),
                message_object, thread_id, thread_type
            )
            return

        bot.replyMessage(Message(text="⏳ Đang tải video CapCut…"), message_object, thread_id, thread_type)

        try:
            resp = _download_capcut(base, key, arg)
        except Exception as e:
            bot.replyMessage(
                Message(text=f"❌ Lỗi API: {e}"),
                message_object, thread_id, thread_type
            )
            return

        data = resp.get("data") or resp
        card_text = _build_download_card(data)

        image_path = create_download_card(data, brand="capcut", size=None)
        if image_path and os.path.exists(image_path):
            try:
                with Image.open(image_path) as img:
                    w, h = img.size
                bot.sendLocalImage(
                    image_path,
                    message=Message(text=card_text),
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=w,
                    height=h,
                )
            except Exception:
                bot.replyMessage(Message(text=card_text), message_object, thread_id, thread_type)
            finally:
                try:
                    os.remove(image_path)
                except Exception:
                    pass
        else:
            bot.replyMessage(Message(text=card_text), message_object, thread_id, thread_type)

        video_url = (
            data.get("video_url_no_watermark")
            or data.get("video_no_wm")
            or data.get("video")
            or data.get("url")
            or resp.get("url")
        )
        cover_url = data.get("cover") or data.get("thumb") or ""

        if video_url:
            try:
                bot.sendRemoteVideo(
                    videoUrl=video_url,
                    thumbnailUrl=cover_url,
                    duration=0,
                    thread_id=thread_id,
                    thread_type=thread_type,
                )
            except Exception:
                bot.replyMessage(
                    Message(text=f"⚠️ Không gửi được trực tiếp.\n🔗 {video_url}"),
                    message_object, thread_id, thread_type
                )
        return

    # ── SEARCH MODE ───────────────────────────────────────────────────────
    if not arg:
        help_path = create_help_card(
            brand="capcut",
            commands=[
                ("cap <từ khóa>", "Tìm video template"),
                ("cap img <từ khóa>", "Tìm ảnh"),
                ("capdl <link>", "Tải video no-WM"),
                ("capsearch <từ khóa>", "Tìm ảnh/video"),
            ],
            size=None,
        )
        if help_path and os.path.exists(help_path):
            try:
                with Image.open(help_path) as img:
                    w, h = img.size
                bot.sendLocalImage(
                    help_path,
                    message=Message(text="🎞️ Hướng dẫn CapCut"),
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=w,
                    height=h,
                )
            except Exception:
                pass
            finally:
                try:
                    os.remove(help_path)
                except Exception:
                    pass
        else:
            bot.replyMessage(
                Message(text=(
                    "🎞️ CapCut Search\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "📌 Lệnh:\n"
                    "  *cap <từ khóa>        → Tìm video template\n"
                    "  *cap img <từ khóa>    → Tìm ảnh\n"
                    "  *capdl <link>         → Tải video no-WM\n"
                )),
                message_object, thread_id, thread_type
            )
        return

    # Phát hiện search ảnh: type=2
    media_type = 1  # mặc định video
    keywords   = arg
    if arg.lower().startswith(("img ", "image ", "ảnh ", "photo ")):
        media_type = 2
        keywords   = arg.split(None, 1)[1] if " " in arg else arg

    ctype_label = "ảnh" if media_type == 2 else "video"
    bot.replyMessage(
        Message(text=f"🔍 Đang tìm CapCut {ctype_label}: **{keywords}**…"),
        message_object, thread_id, thread_type
    )

    try:
        resp = _search_capcut(base, key, keywords, media_type, count=5)
    except Exception as e:
        bot.replyMessage(
            Message(text=f"❌ Lỗi tìm kiếm: {e}"),
            message_object, thread_id, thread_type
        )
        return

    items = (
        resp if isinstance(resp, list)
        else resp.get("data") or resp.get("results") or resp.get("items") or []
    )

    if not items:
        bot.replyMessage(
            Message(text=f"😔 Không tìm thấy kết quả cho: **{keywords}**"),
            message_object, thread_id, thread_type
        )
        return

    # Build output card image
    icon   = "🖼️" if media_type == 2 else "🎬"
    header_text = f"{icon} CapCut {ctype_label}: {keywords}"
    footer_text = "💡 Dùng *capdl <link> để tải video no-WM"

    image_path = create_search_card(
        items,
        header_title=f"CapCut {ctype_label}: {keywords}",
        footer_text=footer_text,
        brand="capcut",
        content_type=ctype_label,
        size=None,
    )

    text_fallback = (
        f"{header_text}\n"
        + "\n".join([_build_search_card(item, i + 1, ctype_label) for i, item in enumerate(items[:5])])
        + f"\n{footer_text}"
    )

    if image_path and os.path.exists(image_path):
        try:
            with Image.open(image_path) as img:
                w, h = img.size
            bot.sendLocalImage(
                image_path,
                message=Message(text=text_fallback),
                thread_id=thread_id,
                thread_type=thread_type,
                width=w,
                height=h,
            )
        except Exception:
            bot.replyMessage(Message(text=text_fallback), message_object, thread_id, thread_type)
        finally:
            try:
                os.remove(image_path)
            except Exception:
                pass
    else:
        bot.replyMessage(Message(text=text_fallback), message_object, thread_id, thread_type)
