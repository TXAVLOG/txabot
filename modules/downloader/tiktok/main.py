# -*- coding: UTF-8 -*-
"""
Module: tiktok.py
Lệnh: tt, tiktok, ttdl
- tt <từ khóa>          → Tìm kiếm video/ảnh TikTok, gửi card info đẹp
- ttdl <link>           → Tải video TikTok không watermark
"""

import sys
import os
import tempfile
import requests

sys.dont_write_bytecode = True

# ─── METADATA ─────────────────────────────────────────────────────────────────
txa = {
    "name": "TikTok Search & Download",
    "desc": {
        "tt": "Tìm kiếm video/ảnh TikTok",
        "tiktok": "Tìm kiếm video/ảnh TikTok",
        "ttdl": "Tải video TikTok không watermark",
        "tksearch": "Tìm kiếm video/ảnh TikTok"
    },
    "author": "TXA",
    "command": ["tt", "tiktok", "ttdl", "tksearch"]
}

# ─── CONFIG ───────────────────────────────────────────────────────────────────

def _get_api(bot):
    cfg = getattr(bot, "_txa_config", None) or {}
    base = cfg.get("kairobot_base_url", "https://kairobot.qzz.io").rstrip("/")
    key  = cfg.get("kairobot_api_key", "")
    return base, key


def _api_headers(key: str) -> dict:
    return {
        "x-api-key": key,
        "User-Agent": "TXABot/2.0",
    }

# ─── CARD BUILDER ─────────────────────────────────────────────────────────────

def _num_fmt(n) -> str:
    """Format số đẹp: 1234567 → 1.2M"""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n) if n else "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _build_search_card(item: dict, index: int) -> str:
    """
    Tạo text card info từ 1 kết quả TikTok search.
    item keys từ SearchTiktokDto response (thực tế kairobot trả về):
    title/desc, author/nickname, diggCount, commentCount, playCount, shareCount,
    cover (URL ảnh), video_url, type (video/image)
    """
    title    = (item.get("title") or item.get("desc") or item.get("text") or "").strip()
    title    = title[:80] + "…" if len(title) > 80 else title

    author   = item.get("author") or item.get("nickname") or item.get("unique_id") or "?"
    likes    = _num_fmt(item.get("diggCount") or item.get("like_count") or 0)
    comments = _num_fmt(item.get("commentCount") or item.get("comment_count") or 0)
    plays    = _num_fmt(item.get("playCount") or item.get("play_count") or 0)
    shares   = _num_fmt(item.get("shareCount") or item.get("share_count") or 0)
    ctype    = (item.get("type") or "video").lower()
    icon     = "🎬" if ctype == "video" else "🖼️"

    link = (
        item.get("video_url")
        or item.get("share_url")
        or item.get("url")
        or item.get("webVideoUrl")
        or ""
    )

    lines = [
        f"{'━'*32}",
        f"{icon} [{index}] {title or '(Không có tiêu đề)'}",
        f"👤 @{author}",
        f"❤️ {likes}  💬 {comments}  ▶️ {plays}  🔁 {shares}",
    ]
    if link:
        lines.append(f"🔗 {link}")

    return "\n".join(lines)


def _build_download_card(data: dict) -> str:
    """Card thông tin video sau khi tải."""
    title  = (data.get("title") or data.get("desc") or "").strip()
    title  = title[:100] + "…" if len(title) > 100 else title
    author = data.get("author") or data.get("nickname") or data.get("unique_id") or "?"
    dur    = data.get("duration") or 0
    dur_s  = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "?"
    likes  = _num_fmt(data.get("diggCount") or data.get("like_count") or 0)

    return "\n".join([
        "╔══════════════════════╗",
        "║  🎵  TikTok Download  ║",
        "╚══════════════════════╝",
        f"📝 {title or '(Không có tiêu đề)'}",
        f"👤 @{author}",
        f"⏱️ {dur_s}  ❤️ {likes}",
        "✅ Video không watermark đang gửi…",
    ])

# ─── SEARCH ───────────────────────────────────────────────────────────────────

def _search_tiktok(base: str, key: str, keywords: str, content_type: str = "video", count: int = 5):
    """
    GET /tiktok/search?keywords=...&type=video&count=5
    type: "video" | "image"
    """
    url = f"{base}/tiktok/search"
    params = {
        "keywords": keywords,
        "type": content_type,
        "count": count,
        "cursor": 0,
    }
    r = requests.get(url, params=params, headers=_api_headers(key), timeout=20)
    r.raise_for_status()
    return r.json()

# ─── DOWNLOAD ─────────────────────────────────────────────────────────────────

def _download_tiktok(base: str, key: str, video_url: str):
    """GET /tiktok/download?url=..."""
    url = f"{base}/tiktok/download"
    r = requests.get(url, params={"url": video_url}, headers=_api_headers(key), timeout=30)
    r.raise_for_status()
    return r.json()

# ─── COMMAND HANDLER ──────────────────────────────────────────────────────────

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    from zlapi.models import Message, ThreadType

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
    if cmd == "ttdl":
        if not arg or not arg.startswith("http"):
            bot.replyMessage(
                Message(text="🎬 Dùng: *ttdl <link TikTok>\nVí dụ: *ttdl https://www.tiktok.com/@user/video/xxx"),
                message_object, thread_id, thread_type
            )
            return

        bot.replyMessage(Message(text="⏳ Đang tải video TikTok…"), message_object, thread_id, thread_type)

        try:
            data = _download_tiktok(base, key, arg)
        except Exception as e:
            bot.replyMessage(
                Message(text=f"❌ Lỗi API: {e}"),
                message_object, thread_id, thread_type
            )
            return

        # Lấy video URL không watermark
        video_dl = (
            data.get("video_url_no_watermark")
            or data.get("video")
            or data.get("url")
            or (data.get("data") or {}).get("video_url_no_watermark")
            or (data.get("data") or {}).get("video")
        )

        card = _build_download_card(data.get("data") or data)
        bot.replyMessage(Message(text=card), message_object, thread_id, thread_type)

        if video_dl:
            try:
                bot.sendRemoteVideo(
                    videoUrl=video_dl,
                    thumbnailUrl=(data.get("data") or data).get("cover") or "",
                    duration=int((data.get("data") or data).get("duration") or 0),
                    thread_id=thread_id,
                    thread_type=thread_type,
                )
            except Exception as ve:
                bot.replyMessage(
                    Message(text=f"⚠️ Không gửi được video trực tiếp.\n🔗 Link tải: {video_dl}"),
                    message_object, thread_id, thread_type
                )
        return

    # ── SEARCH MODE ───────────────────────────────────────────────────────
    if not arg:
        bot.replyMessage(
            Message(text=(
                "🎵 TikTok Search\n"
                "━━━━━━━━━━━━━━━━\n"
                "📌 Lệnh:\n"
                "  *tt <từ khóa>          → Tìm video\n"
                "  *tt img <từ khóa>      → Tìm ảnh\n"
                "  *ttdl <link>           → Tải video no-WM\n"
            )),
            message_object, thread_id, thread_type
        )
        return

    # Phát hiện search ảnh
    content_type = "video"
    keywords = arg
    if arg.lower().startswith(("img ", "image ", "ảnh ", "photo ")):
        content_type = "image"
        keywords = arg.split(None, 1)[1] if " " in arg else arg

    bot.replyMessage(
        Message(text=f"🔍 Đang tìm TikTok {content_type}: **{keywords}**…"),
        message_object, thread_id, thread_type
    )

    try:
        resp = _search_tiktok(base, key, keywords, content_type, count=5)
    except Exception as e:
        bot.replyMessage(
            Message(text=f"❌ Lỗi tìm kiếm: {e}"),
            message_object, thread_id, thread_type
        )
        return

    # Normalize response
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

    # Build cards
    icon = "🎬" if content_type == "video" else "🖼️"
    header = (
        f"{icon} Kết quả TikTok: **{keywords}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    cards = [_build_search_card(item, i + 1) for i, item in enumerate(items[:5])]
    footer = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 Dùng *ttdl <link> để tải video"

    full_text = header + "\n".join(cards) + footer
    bot.replyMessage(Message(text=full_text), message_object, thread_id, thread_type)

    # Gửi thêm thumbnail ảnh cover (chỉ 1 ảnh đại diện để không spam)
    cover_url = None
    for item in items[:3]:
        cover_url = item.get("cover") or item.get("origin_cover") or item.get("thumb")
        if cover_url and cover_url.startswith("http"):
            break

    if cover_url:
        try:
            bot.sendRemoteImage(
                cover_url,
                thumbnailUrl=cover_url,
                thread_id=thread_id,
                thread_type=thread_type,
                message=Message(text=f"🖼️ Cover: {items[0].get('title','')[:50]}"),
            )
        except Exception:
            pass
