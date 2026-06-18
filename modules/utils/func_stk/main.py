# -*- coding: UTF-8 -*-
"""
Module: sticker.py
Lệnh: sticker, pixel
Fix: Gửi qua send_custom_sticker với pStickerType=1 → Zalo nhận diện là STICKER thật
     (có nút lưu sticker, nhãn sticker trong popup)
"""

import os
import sys
import tempfile
import requests
import json
from io import BytesIO
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont

sys.dont_write_bytecode = True

# ─── METADATA ─────────────────────────────────────────────────────────────────
txa = {
    "name": "Sticker & Pixel Art",
    "desc": {
        "sticker": "Tạo sticker từ ảnh reply",
        "pixel": "Tạo ảnh pixel art từ ảnh reply",
        "stk": "Tạo sticker từ ảnh reply",
        "pxl": "Tạo ảnh pixel art từ ảnh reply"
    },
    "author": "TXA",
    "command": ["sticker", "pixel", "stk", "pxl"]
}

# ─── HELPER ───────────────────────────────────────────────────────────────────

def _get_image_url_from_message(message_object):
    """Lấy URL ảnh từ tin nhắn reply hoặc tin nhắn hiện tại."""
    # Kiểm tra quote / reply
    quote = getattr(message_object, "quote", None)
    if quote:
        q_attach = getattr(quote, "attach", None)
        if q_attach:
            if isinstance(q_attach, str):
                try:
                    q_attach = json.loads(q_attach)
                except Exception:
                    pass
            if isinstance(q_attach, dict):
                for key in ("hdUrl", "oriUrl", "normalUrl", "href"):
                    if q_attach.get(key):
                        return q_attach[key]
        q_href = getattr(quote, "href", None) or getattr(quote, "attach_href", None)
        if q_href:
            return q_href

    # Tin nhắn hiện tại
    attach = getattr(message_object, "attach", None)
    if attach:
        if isinstance(attach, str):
            try:
                attach = json.loads(attach)
            except Exception:
                pass
        if isinstance(attach, dict):
            for key in ("hdUrl", "oriUrl", "normalUrl", "href"):
                if attach.get(key):
                    return attach[key]

    return None


def _download_image(url: str, session=None) -> Image.Image | None:
    try:
        getter = session.get if session else requests.get
        r = getter(url, timeout=15)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGBA")
    except Exception as e:
        print(f"[sticker] Lỗi tải ảnh: {e}")
        return None


def _make_sticker_image(img: Image.Image, size: int = 512) -> Image.Image:
    """
    Chuẩn bị ảnh sticker:
    - Resize về square (512×512) giữ tỷ lệ, padding transparent
    - Giữ kênh Alpha nếu có, nếu không tự remove bg đơn giản
    """
    img = img.convert("RGBA")

    # Resize giữ tỷ lệ
    img.thumbnail((size, size), Image.LANCZOS)

    # Canvas trong suốt
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    offset = ((size - img.width) // 2, (size - img.height) // 2)
    canvas.paste(img, offset, img)
    return canvas


def _make_pixel_art(img: Image.Image, pixel_size: int = 16, size: int = 512) -> Image.Image:
    """
    Chuyển ảnh thành pixel art style:
    - Giảm độ phân giải xuống grid nhỏ rồi scale lên lại
    - Tăng saturation + contrast cho vibe retro
    """
    img = img.convert("RGBA")

    # Tính grid dimensions giữ tỷ lệ
    aspect = img.width / img.height
    if aspect >= 1:
        grid_w = pixel_size
        grid_h = max(1, int(pixel_size / aspect))
    else:
        grid_h = pixel_size
        grid_w = max(1, int(pixel_size * aspect))

    # Pixelate: resize nhỏ → scale lên
    small = img.resize((grid_w, grid_h), Image.NEAREST)
    pixelated = small.resize((size, size), Image.NEAREST)

    # Tăng saturation và contrast
    rgb = pixelated.convert("RGB")
    rgb = ImageEnhance.Color(rgb).enhance(1.8)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.3)

    # Ghép lại alpha
    r, g, b = rgb.split()
    _, _, _, a = pixelated.split()
    result = Image.merge("RGBA", (r, g, b, a))
    return result


def _image_to_webp_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="WEBP", lossless=True, quality=90)
    return buf.getvalue()


def _image_to_png_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _upload_to_tmpfiles(data: bytes, filename: str) -> str | None:
    """Upload file lên tmpfiles.org để lấy public URL."""
    try:
        resp = requests.post(
            "https://tmpfiles.org/api/v1/upload",
            files={"file": (filename, data, "image/webp")},
            timeout=20,
        )
        resp.raise_for_status()
        j = resp.json()
        # tmpfiles trả về {"status":"success","data":{"url":"https://tmpfiles.org/XXXXX/file.webp"}}
        raw_url = j.get("data", {}).get("url", "")
        # Chuyển sang direct download link
        direct = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
        return direct if direct.startswith("http") else None
    except Exception as e:
        print(f"[sticker] Upload tmpfiles lỗi: {e}")
        return None


def _send_as_zalo_sticker(bot, static_url: str, anim_url: str, thread_id, thread_type, reply_id=None):
    """
    Gửi ảnh qua send_custom_sticker — pStickerType=1 trong payload
    → Zalo client nhận diện là STICKER thật (có nút lưu, nhãn sticker).
    """
    try:
        bot.send_custom_sticker(
            staticImgUrl=static_url,
            animationImgUrl=anim_url,
            thread_id=thread_id,
            thread_type=thread_type,
            reply=reply_id,
            width=512,
            height=512,
        )
        return True
    except Exception as e:
        print(f"[sticker] send_custom_sticker lỗi: {e}")
        return False


# ─── COMMAND HANDLER ──────────────────────────────────────────────────────────

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    from zlapi.models import Message, ThreadType

    parts    = message_text.strip().split()
    cmd      = parts[0].lstrip("*!./,").lower() if parts else ""
    is_pixel = cmd in ("pixel", "pxl")

    # ── Lấy URL ảnh ──────────────────────────────────────────────────────
    img_url = _get_image_url_from_message(message_object)

    # Nếu không có reply, thử lấy URL từ text
    if not img_url and len(parts) > 1:
        candidate = parts[1]
        if candidate.startswith("http"):
            img_url = candidate

    if not img_url:
        emoji = "🎨" if is_pixel else "🖼️"
        tip   = "pixel art" if is_pixel else "sticker"
        bot.replyMessage(
            Message(text=f"{emoji} Reply vào một ảnh để tạo {tip}!\nVí dụ: Reply ảnh + gõ `*{'pixel' if is_pixel else 'sticker'}`"),
            message_object, thread_id, thread_type
        )
        return

    # ── Thông báo đang xử lý ─────────────────────────────────────────────
    action = "🎮 Đang tạo pixel art..." if is_pixel else "✨ Đang tạo sticker..."
    bot.replyMessage(Message(text=action), message_object, thread_id, thread_type)

    # ── Download ảnh gốc ─────────────────────────────────────────────────
    session = getattr(bot._state, "_session", None)
    img = _download_image(img_url, session)

    if not img:
        bot.replyMessage(
            Message(text="❌ Không tải được ảnh. Thử lại với ảnh khác nhé!"),
            message_object, thread_id, thread_type
        )
        return

    # ── Xử lý ảnh ───────────────────────────────────────────────────────
    try:
        if is_pixel:
            # Lấy pixel_size từ arg nếu có (vd: *pixel 8)
            pixel_size = 16
            if len(parts) > 1 and parts[1].isdigit():
                pixel_size = max(4, min(64, int(parts[1])))
            elif len(parts) > 2 and parts[2].isdigit():
                pixel_size = max(4, min(64, int(parts[2])))
            sticker_img = _make_pixel_art(img, pixel_size=pixel_size)
        else:
            sticker_img = _make_sticker_image(img)
    except Exception as e:
        bot.replyMessage(
            Message(text=f"❌ Lỗi xử lý ảnh: {e}"),
            message_object, thread_id, thread_type
        )
        return

    # ── Convert → WebP (animated sticker endpoint cần webp) ──────────────
    webp_data = _image_to_webp_bytes(sticker_img)
    png_data  = _image_to_png_bytes(sticker_img)

    # ── Upload lên host công khai ─────────────────────────────────────────
    webp_url = _upload_to_tmpfiles(webp_data, "sticker.webp")
    png_url  = _upload_to_tmpfiles(png_data,  "sticker.png")

    if not webp_url or not png_url:
        # Fallback: thử dùng chính img_url gốc nếu đã là Zalo CDN
        if "zalo.me" in img_url or "zadn.vn" in img_url or "zdn.vn" in img_url:
            webp_url = img_url
            png_url  = img_url
        else:
            bot.replyMessage(
                Message(text="❌ Không thể upload ảnh lên host. Vui lòng thử lại!"),
                message_object, thread_id, thread_type
            )
            return

    # ── Lấy reply ID nếu có ──────────────────────────────────────────────
    reply_id = None
    quote = getattr(message_object, "quote", None)
    if quote:
        reply_id = getattr(quote, "globalMsgId", None) or getattr(quote, "msgId", None)

    # ── Gửi sticker ──────────────────────────────────────────────────────
    ok = _send_as_zalo_sticker(bot, png_url, webp_url, thread_id, thread_type, reply_id)

    if not ok:
        # Fallback: gửi ảnh thường nếu custom sticker thất bại
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(png_data)
            tmp.close()
            bot.sendLocalImage(
                imagePath=tmp.name,
                thread_id=thread_id,
                thread_type=thread_type,
                message=Message(text="⚠️ Sticker endpoint thất bại, gửi ảnh thường"),
            )
            os.unlink(tmp.name)
        except Exception as fe:
            print(f"[sticker] fallback sendLocalImage lỗi: {fe}")
            bot.replyMessage(
                Message(text="❌ Gửi sticker thất bại. Thử lại sau!"),
                message_object, thread_id, thread_type
            )
