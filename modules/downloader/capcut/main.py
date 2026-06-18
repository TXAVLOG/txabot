# -*- coding: UTF-8 -*-
"""
Module: capcut.py
Lệnh: cap, capcut, capdl, capsearch, capedit, capfeed, capuser, capposts
- cap <từ khóa>           → Tìm video template CapCut
- cap img <từ khóa>       → Tìm ảnh template CapCut
- capdl <link>            → Tải video CapCut không watermark
- capedit <link/id> [ảnh] → Chỉnh sửa template CapCut bằng cách thay thế ảnh
- capfeed [danh_mục]      → Lấy danh sách template CapCut theo danh mục
- capuser <profile_url>   → Lấy thông tin creator CapCut
- capposts <profile_url>  → Lấy danh sách mẫu của creator CapCut
"""

import os
import sys
import json
import requests
from PIL import Image
from zlapi.models import Message

sys.dont_write_bytecode = True

from modules.shared.cards import (
    create_search_card,
    create_download_card,
    create_profile_card,
    create_help_card,
)

# ─── METADATA ─────────────────────────────────────────────────────────────────
txa = {
    "name": "CapCut Lovable Integration",
    "desc": {
        "cap": "Tìm kiếm video template CapCut",
        "capcut": "Tìm kiếm video template CapCut",
        "capdl": "Tải video CapCut không watermark",
        "capsearch": "Tìm kiếm video template CapCut",
        "capedit": "Thay thế ảnh và render template CapCut",
        "capfeed": "Lấy danh sách mẫu theo danh mục CapCut",
        "capuser": "Xem thông tin creator CapCut",
        "capposts": "Lấy danh sách mẫu của creator CapCut"
    },
    "author": "TXA",
    "command": ["cap", "capcut", "capdl", "capsearch", "capedit", "capfeed", "capuser", "capposts"]
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


def _map_template_item(item: dict) -> dict:
    """
    Ánh xạ các trường từ Lovable API response sang định dạng canvas card yêu cầu.
    """
    author_val = item.get("author") or "?"
    if isinstance(author_val, dict):
        author = author_val.get("name") or author_val.get("username") or "?"
    else:
        author = str(author_val)

    usage_count = item.get("usage_count") or item.get("use_count") or item.get("used_count") or 0
    play_count = item.get("play_count") or item.get("playCount") or (int(usage_count) * 8) or 0

    return {
        "title": item.get("title") or item.get("desc") or "",
        "author": author,
        "cover": item.get("cover_url") or item.get("cover") or "",
        "url": item.get("template_url") or item.get("url") or f"https://www.capcut.com/template-detail/{item.get('template_id')}",
        "like_count": item.get("like_count") or 0,
        "use_count": usage_count,
        "play_count": play_count,
    }


def _build_search_card(item: dict, index: int, ctype: str = "video") -> str:
    title = (item.get("title") or "").strip()
    title = title[:80] + "…" if len(title) > 80 else title

    author = item.get("author") or "?"
    views = _fmt_num(item.get("play_count") or 0)
    likes = _fmt_num(item.get("like_count") or 0)
    uses = _fmt_num(item.get("use_count") or 0)
    share_url = item.get("url") or ""

    icon = "🎬" if ctype == "video" else "🖼️"

    lines = [
        f"{'═'*30}",
        f"{icon} [{index}] {title or '(Không có tiêu đề)'}",
        f"✏️ {author}",
    ]

    stats = []
    if views != "0": stats.append(f"👁️ {views}")
    if likes != "0": stats.append(f"❤️ {likes}")
    if uses != "0": stats.append(f"🔁 {uses}")
    if stats:
        lines.append("  ".join(stats))

    if share_url:
        lines.append(f"🔗 {share_url}")

    return "\n".join(lines)


def _build_download_card(data: dict) -> str:
    title  = (data.get("title") or data.get("desc") or "").strip()
    title  = title[:100] + "…" if len(title) > 100 else title
    author = data.get("author") or "?"

    return "\n".join([
        "╔═══════════════════════╗",
        "║  🎞️  CapCut Download   ║",
        "╚═══════════════════════╝",
        f"📝 {title or '(Không có tiêu đề)'}",
        f"✏️ {author}",
        "✅ Video không watermark đang gửi…",
    ])

# ─── COMMAND HANDLER ──────────────────────────────────────────────────────────

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    parts = message_text.strip().split(None, 1)
    cmd   = parts[0].lstrip("*!./,").lower() if parts else ""
    arg   = parts[1].strip() if len(parts) > 1 else ""

    # ── DOWNLOAD MODE (capdl) ───────────────────────────────────────────────
    if cmd == "capdl":
        if not arg or not arg.startswith("http"):
            bot.replyMessage(
                Message(text=(
                    f"🎞️ Dùng: {prefix}capdl <link CapCut>\n"
                    f"Ví dụ: {prefix}capdl https://www.capcut.com/template-detail/7544395522975534397"
                )),
                message_object, thread_id, thread_type
            )
            return

        bot.replyMessage(Message(text="⏳ Đang tải video CapCut từ API…"), message_object, thread_id, thread_type)

        try:
            url = "https://apiwebfree.lovable.app/api/capcut-download"
            r = requests.get(url, params={"url": arg}, timeout=30)
            res = r.json()
        except Exception as e:
            bot.replyMessage(Message(text=f"❌ Lỗi kết nối API: {e}"), message_object, thread_id, thread_type)
            return

        if not res.get("success", False):
            err = res.get("error") or "Không thể tải video từ link này"
            bot.replyMessage(Message(text=f"❌ Lỗi API: {err}"), message_object, thread_id, thread_type)
            return

        # Tạo card preview
        card_text = _build_download_card(res)
        
        # Tiền xử lý duration để tránh lỗi Pillow
        duration_val = res.get("duration") or 0
        if isinstance(duration_val, str):
            duration_val = duration_val.strip().lower()
            if duration_val.endswith("s"):
                duration_val = duration_val[:-1]
            try:
                res["duration"] = int(duration_val)
            except ValueError:
                res["duration"] = 0

        image_path = create_download_card(res, brand="capcut", size=None)
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
                except:
                    pass
        else:
            bot.replyMessage(Message(text=card_text), message_object, thread_id, thread_type)

        video_url = res.get("video_url") or res.get("url")
        cover_url = res.get("cover") or res.get("thumb") or ""

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

    # ── EDIT TEMPLATE MODE (capedit) ─────────────────────────────────────────
    elif cmd == "capedit":
        if not arg:
            bot.replyMessage(
                Message(text=(
                    f"🎞️ Dùng: {prefix}capedit <template_url/id> [ảnh1,ảnh2,...]\n"
                    f"Ví dụ: {prefix}capedit https://www.capcut.com/templates/7179578535193890049 https://example.com/p1.jpg,https://example.com/p2.jpg"
                )),
                message_object, thread_id, thread_type
            )
            return

        parts_arg = arg.split(None, 1)
        template_val = parts_arg[0].strip()
        images_val = parts_arg[1].strip() if len(parts_arg) > 1 else ""

        bot.replyMessage(Message(text="⏳ Đang chỉnh sửa template CapCut…"), message_object, thread_id, thread_type)

        try:
            url = "https://apiwebfree.lovable.app/api/capcut-edit"
            params = {"template": template_val}
            if images_val:
                params["images"] = images_val

            r = requests.get(url, params=params, timeout=45)
            res = r.json()
        except Exception as e:
            bot.replyMessage(Message(text=f"❌ Lỗi API: {e}"), message_object, thread_id, thread_type)
            return

        if not res.get("success", False):
            err = res.get("error") or res.get("message") or "Lỗi thay thế ảnh"
            if "login" in err.lower() or "check login" in err.lower():
                bot.replyMessage(Message(text="⚠️ Tính năng chỉnh sửa template CapCut hiện đang bảo trì máy chủ. Vui lòng thử lại sau! 🛠️"), message_object, thread_id, thread_type)
            else:
                bot.replyMessage(Message(text=f"❌ Thất bại: {err}"), message_object, thread_id, thread_type)
            return

        video_url = res.get("video_url") or res.get("url") or res.get("video")
        if video_url:
            bot.replyMessage(Message(text="✅ Đã render thành công! Đang gửi video…"), message_object, thread_id, thread_type)
            try:
                bot.sendRemoteVideo(
                    videoUrl=video_url,
                    thumbnailUrl="",
                    duration=0,
                    thread_id=thread_id,
                    thread_type=thread_type,
                )
            except Exception:
                bot.replyMessage(Message(text=f"⚠️ Không gửi trực tiếp được video.\n🔗 {video_url}"), message_object, thread_id, thread_type)
        else:
            bot.replyMessage(Message(text=f"✅ Phản hồi API:\n{json.dumps(res, indent=2, ensure_ascii=False)}"), message_object, thread_id, thread_type)
        return

    # ── CATEGORY FEED MODE (capfeed) ──────────────────────────────────────────
    elif cmd == "capfeed":
        category_id = "10020"
        count = 5
        
        if arg:
            sub_parts = arg.split()
            if len(sub_parts) >= 1:
                category_id = sub_parts[0]
            if len(sub_parts) >= 2:
                try:
                    count = int(sub_parts[1])
                except:
                    pass

        bot.replyMessage(Message(text=f"⏳ Đang tải feed danh mục {category_id}…"), message_object, thread_id, thread_type)

        try:
            url = "https://apiwebfree.lovable.app/api/capcut-feed"
            params = {"action": "templates", "category_id": category_id, "count": count, "cursor": 0}
            r = requests.get(url, params=params, timeout=25)
            res = r.json()
        except Exception as e:
            bot.replyMessage(Message(text=f"❌ Lỗi API: {e}"), message_object, thread_id, thread_type)
            return

        if not res.get("success", False):
            err = res.get("error") or "Không thể tải danh mục"
            bot.replyMessage(Message(text=f"❌ Lỗi: {err}"), message_object, thread_id, thread_type)
            return

        templates = res.get("templates") or []
        if not templates:
            bot.replyMessage(Message(text="😔 Danh mục này hiện trống."), message_object, thread_id, thread_type)
            return

        mapped_items = [_map_template_item(t) for t in templates]

        image_path = create_search_card(
            mapped_items,
            header_title=f"CapCut Feed: {category_id}",
            footer_text=f"💡 Dùng {prefix}capdl <link> để tải video no-WM",
            brand="capcut",
            content_type="video",
            size=None,
        )

        text_fallback = (
            f"🎬 CapCut Feed: {category_id}\n"
            + "\n".join([_build_search_card(item, i + 1, "video") for i, item in enumerate(mapped_items[:5])])
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
                except:
                    pass
        else:
            bot.replyMessage(Message(text=text_fallback), message_object, thread_id, thread_type)
        return

    # ── CREATOR INFO MODE (capuser) ───────────────────────────────────────────
    elif cmd == "capuser":
        if not arg:
            bot.replyMessage(Message(text=f"🎞️ Dùng: {prefix}capuser <profile_url_hoặc_share_link>\nVí dụ: {prefix}capuser https://mobile.capcutshare.com/sv2/ZSHbMe9t3/"), message_object, thread_id, thread_type)
            return

        bot.replyMessage(Message(text="⏳ Đang tải thông tin creator…"), message_object, thread_id, thread_type)

        try:
            url = "https://apiwebfree.lovable.app/api/capcut-user-info"
            r = requests.get(url, params={"url": arg}, timeout=25)
            res = r.json()
        except Exception as e:
            bot.replyMessage(Message(text=f"❌ Lỗi API: {e}"), message_object, thread_id, thread_type)
            return

        if not res.get("success", False):
            err = res.get("error") or "Không tìm thấy creator này"
            bot.replyMessage(Message(text=f"❌ Lỗi: {err}"), message_object, thread_id, thread_type)
            return

        user = res.get("user") or {}
        name = user.get("name") or "Không rõ"
        uid = user.get("uid") or "?"
        unique_id = user.get("unique_id") or "?"
        avatar = user.get("avatar_url") or ""
        desc = user.get("description") or "Không có tiểu sử"
        templates_count = user.get("template_count") or 0
        likes_count = user.get("like_count") or 0

        info_text = (
            f"👤 Creator: {name} (@{unique_id})\n"
            f"🆔 UID: {uid}\n"
            f"📝 Tiểu sử: {desc}\n"
            f"🎬 Số mẫu: {templates_count}\n"
            f"❤️ Lượt thích: {likes_count}\n"
            f"🔗 Profile: {user.get('profile_url') or ''}"
        )

        profile_data = {
            "nickname": name,
            "unique_id": unique_id,
            "signature": desc,
            "follower_count": 0,
            "following_count": 0,
            "heart_count": likes_count,
            "video_count": templates_count,
            "avatar": avatar,
            "verified": user.get("is_creator", False)
        }

        image_path = create_profile_card(profile_data, brand="capcut", size=None)

        if image_path and os.path.exists(image_path):
            try:
                with Image.open(image_path) as img:
                    w, h = img.size
                bot.sendLocalImage(
                    image_path,
                    message=Message(text=info_text),
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=w,
                    height=h,
                )
            except Exception:
                bot.replyMessage(Message(text=info_text), message_object, thread_id, thread_type)
            finally:
                try:
                    os.remove(image_path)
                except:
                    pass
        else:
            bot.replyMessage(Message(text=info_text), message_object, thread_id, thread_type)
        return

    # ── CREATOR POSTS MODE (capposts) ─────────────────────────────────────────
    elif cmd == "capposts":
        if not arg:
            bot.replyMessage(Message(text=f"🎞️ Dùng: {prefix}capposts <profile_url> [count]\nVí dụ: {prefix}capposts https://www.capcut.com/profile/IvVnCmom5BKO5CQc-TxNM1p2VfDQEdzrBayMrPvsKhY 5"), message_object, thread_id, thread_type)
            return

        parts_arg = arg.split()
        profile_url = parts_arg[0]
        count = 5
        if len(parts_arg) > 1:
            try:
                count = int(parts_arg[1])
            except ValueError:
                pass

        bot.replyMessage(Message(text="⏳ Đang tải các mẫu của creator…"), message_object, thread_id, thread_type)

        try:
            url = "https://apiwebfree.lovable.app/api/capcut-user-posts"
            params = {"url": profile_url, "count": count, "cursor": 0}
            r = requests.get(url, params=params, timeout=25)
            res = r.json()
        except Exception as e:
            bot.replyMessage(Message(text=f"❌ Lỗi API: {e}"), message_object, thread_id, thread_type)
            return

        if not res.get("success", False):
            err = res.get("error") or "Không thể lấy danh sách mẫu"
            bot.replyMessage(Message(text=f"❌ Lỗi: {err}"), message_object, thread_id, thread_type)
            return

        templates = res.get("templates") or []
        if not templates:
            bot.replyMessage(Message(text="😔 Creator này chưa đăng mẫu nào."), message_object, thread_id, thread_type)
            return

        mapped_items = [_map_template_item(t) for t in templates]

        image_path = create_search_card(
            mapped_items,
            header_title=f"Creator Mẫu: {res.get('public_id') or 'Profile'}",
            footer_text=f"💡 Dùng {prefix}capdl <link> để tải video no-WM",
            brand="capcut",
            content_type="video",
            size=None,
        )

        text_fallback = (
            f"🎬 Creator Mẫu:\n"
            + "\n".join([_build_search_card(item, i + 1, "video") for i, item in enumerate(mapped_items[:5])])
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
                except:
                    pass
        else:
            bot.replyMessage(Message(text=text_fallback), message_object, thread_id, thread_type)
        return

    # ── TEMPLATE SEARCH MODE (cap / capcut / capsearch) ──────────────────────
    if not arg:
        help_path = create_help_card(
            brand="capcut",
            commands=[
                (f"{prefix}cap <từ khóa>", "Tìm video mẫu"),
                (f"{prefix}cap img <từ khóa>", "Tìm ảnh mẫu"),
                (f"{prefix}capdl <link>", "Tải video không watermark"),
                (f"{prefix}capedit <link> [ảnh]", "Thay thế ảnh vào mẫu"),
                (f"{prefix}capfeed [mã_dm]", "Xem mẫu theo danh mục"),
                (f"{prefix}capuser <profile_url>", "Xem thông tin creator"),
                (f"{prefix}capposts <profile_url>", "Xem mẫu của creator"),
            ],
            size=None,
        )
        if help_path and os.path.exists(help_path):
            try:
                with Image.open(help_path) as img:
                    w, h = img.size
                bot.sendLocalImage(
                    help_path,
                    message=Message(text="🎞️ Hướng dẫn sử dụng CapCut"),
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
                except:
                    pass
        else:
            bot.replyMessage(
                Message(text=(
                    "🎞️ Lệnh CapCut hỗ trợ:\n"
                    f"  {prefix}cap <từ khóa>      → Tìm video mẫu\n"
                    f"  {prefix}cap img <từ khóa>  → Tìm ảnh mẫu\n"
                    f"  {prefix}capdl <link>       → Tải video sạch\n"
                    f"  {prefix}capedit <link> [ảnh] → Thay ảnh vào mẫu\n"
                    f"  {prefix}capfeed [dm]       → Mẫu theo danh mục\n"
                    f"  {prefix}capuser <url>      → Xem creator\n"
                    f"  {prefix}capposts <url>     → Các mẫu của creator"
                )),
                message_object, thread_id, thread_type
            )
        return

    # Xác định loại tìm kiếm (ảnh hoặc video)
    media_type = "video"
    keywords = arg
    if arg.lower().startswith(("img ", "image ", "ảnh ", "photo ")):
        media_type = "image"
        keywords = arg.split(None, 1)[1] if " " in arg else arg

    ctype_label = "ảnh" if media_type == "image" else "video"
    bot.replyMessage(
        Message(text=f"🔍 Đang tìm mẫu CapCut {ctype_label}: **{keywords}**…"),
        message_object, thread_id, thread_type
    )

    try:
        url = "https://apiwebfree.lovable.app/api/capcut-search"
        params = {"q": keywords, "type": media_type, "count": 5, "cursor": 0}
        r = requests.get(url, params=params, timeout=25)
        res = r.json()
    except Exception as e:
        bot.replyMessage(Message(text=f"❌ Lỗi tìm kiếm: {e}"), message_object, thread_id, thread_type)
        return

    if not res.get("success", False):
        bot.replyMessage(Message(text="❌ Lỗi khi tìm kiếm mẫu trên API"), message_object, thread_id, thread_type)
        return

    templates = res.get("templates") or []
    if not templates:
        bot.replyMessage(Message(text=f"😔 Không tìm thấy kết quả cho: **{keywords}**"), message_object, thread_id, thread_type)
        return

    mapped_items = [_map_template_item(t) for t in templates]

    header_text = f"🔍 CapCut {ctype_label}: {keywords}"
    footer_text = f"💡 Dùng {prefix}capdl <link> để tải video no-WM"

    image_path = create_search_card(
        mapped_items,
        header_title=f"CapCut {ctype_label}: {keywords}",
        footer_text=footer_text,
        brand="capcut",
        content_type=media_type,
        size=None,
    )

    text_fallback = (
        f"{header_text}\n"
        + "\n".join([_build_search_card(item, i + 1, media_type) for i, item in enumerate(mapped_items[:5])])
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
            except:
                pass
    else:
        bot.replyMessage(Message(text=text_fallback), message_object, thread_id, thread_type)
