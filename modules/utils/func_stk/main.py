import requests
import subprocess
import json
import urllib.parse
import os
from io import BytesIO
from PIL import Image, ImageDraw
from zlapi.models import Message, MultiMsgStyle, MessageStyle
from zlapi._threads import ThreadType
from core.bot_sys import is_admin, read_settings, write_settings

def handle_stk_command(message, message_object, thread_id, thread_type, author_id, client):
    if message_object.quote:
        attach = message_object.quote.attach
        if attach:
            try:
                attach_data = json.loads(attach)
            except json.JSONDecodeError:
                client.sendMessage(
                    Message(text="❌ Dữ liệu ảnh không hợp lệ."),
                    thread_id=thread_id,
                    thread_type=thread_type
                )
                return

            file_url = attach_data.get('hdUrl') or attach_data.get('href')
            if not file_url:
                client.sendMessage(
                    Message(text="❌ Không tìm thấy URL ảnh."),
                    thread_id=thread_id,
                    thread_type=thread_type
                )
                return

            file_url = file_url.replace("\\/", "/")
            file_url = urllib.parse.unquote(file_url)

            # Handle JXL by replacing with JPG
            if "jxl" in file_url:
                file_url = file_url.replace("jxl", "jpg")

            file_type = get_file_type(file_url)
            if file_type == "video":
                webp_url = convert_mp4_to_webp_and_upload(file_url)
                if webp_url:
                    client.send_custom_sticker(
                        animationImgUrl=webp_url,
                        staticImgUrl=webp_url,
                        thread_id=thread_id,
                        thread_type=thread_type,
                        width=None,
                        height=None
                    )
                    send_response(client, thread_id, thread_type, "✅ Đã tạo Sticker video thành công!", ttl=30000)
                    print("✅ Sticker video đã tạo xong và gửi thành công!")
                else:
                    send_response(client, thread_id, thread_type, "❌ Không thể tạo sticker video!")
                    print("❌ Không thể tạo sticker video!")
            elif file_type == "image":
                try:
                    response = requests.get(file_url, stream=True, timeout=15)
                    response.raise_for_status()
                    # Validate Content-Type
                    content_type = response.headers.get("Content-Type", "").lower()
                    if not content_type.startswith("image/"):
                        print(f"❌ Không phải file ảnh, Content-Type: {content_type}")
                        client.sendMessage(
                            Message(text="❌ File không phải là ảnh hợp lệ."),
                            thread_id=thread_id,
                            thread_type=thread_type
                        )
                        return

                    # Process image with Pillow
                    img = Image.open(BytesIO(response.content)).convert("RGBA")
                    temp_webp = "temp_sticker.webp"
                    width, height = img.size
                    # Resize while maintaining aspect ratio
                    img = img.resize((512, int(512 * height / width)), Image.LANCZOS)
                    width, height = img.size
                    mask = Image.new("L", (width, height), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.rounded_rectangle((0, 0, width, height), radius=50, fill=255)
                    img.putalpha(mask)
                    img.save(temp_webp, format="WEBP", quality=75, lossless=False)

                    # Upload to Catbox
                    with open(temp_webp, "rb") as f:
                        files = {'fileToUpload': ('sticker.webp', f, 'image/webp')}
                        upload_response = requests.post("https://catbox.moe/user/api.php", files=files, data={"reqtype": "fileupload"})
                    
                    # Clean up
                    if os.path.exists(temp_webp):
                        os.remove(temp_webp)

                    if upload_response.status_code == 200:
                        webp_url = upload_response.text.strip() + "?creator=khangapi"
                        client.send_custom_sticker(
                            animationImgUrl=webp_url,
                            staticImgUrl=webp_url,
                            thread_id=thread_id,
                            thread_type=thread_type,
                            reply=message_object,
                            width=None,
                            height=None
                        )
                        send_message = "✅ Đã tạo Sticker ảnh thành công!"
                        style = MultiMsgStyle([
                            MessageStyle(offset=0, length=len(send_message), style="font", size="6", auto_format=False),
                            MessageStyle(offset=0, length=len(send_message), style="bold", auto_format=False)
                        ])
                        styled_message = Message(text=send_message, style=style)
                        client.replyMessage(styled_message, message_object, thread_id, thread_type, ttl=80000)
                        print(f"✅ Converted and uploaded image: {webp_url}")
                    else:
                        print(f"❌ Upload failed: {upload_response.text}")
                        client.sendMessage(
                            Message(text="❌ Không thể tải sticker lên!"),
                            thread_id=thread_id,
                            thread_type=thread_type
                        )
                except Exception as e:
                    print(f"❌ Lỗi khi chuyển ảnh sang WebP: {e}")
                    client.sendMessage(
                        Message(text=f"❌ Lỗi khi tạo sticker: {str(e)}"),
                        thread_id=thread_id,
                        thread_type=thread_type
                    )
            else:
                send_response(client, thread_id, thread_type, "❌ Loại file không hỗ trợ!")
                print("❌ Loại file không hỗ trợ!")
        else:
            send_response(client, thread_id, thread_type, "❌ Không có file nào được reply!")
    else:
        send_response(client, thread_id, thread_type, "❌ Hãy reply vào ảnh hoặc video cần tạo sticker!")

def get_file_type(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        content_type = response.headers.get("Content-Type", "").lower()
        if "image" in content_type:
            return "image"
        elif "video" in content_type:
            return "video"
        return "unknown"
    except requests.RequestException as e:
        print(f"❌ Lỗi xác định loại file: {e}")
        return "unknown"

def convert_mp4_to_webp_and_upload(video_url):
    try:
        # Download the MP4
        response = requests.get(video_url, stream=True, timeout=15)
        response.raise_for_status()
        temp_mp4 = "temp_video.mp4"
        temp_webp = "temp_sticker.webp"
        with open(temp_mp4, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        # Convert MP4 to animated WebP using FFmpeg
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_mp4,
            "-vf", "scale=512:-2",
            "-c:v", "libwebp_anim",
            "-loop", "0",
            "-r", "15",
            "-an",
            "-lossless", "0",
            "-q:v", "75",
            "-loglevel", "error",
            temp_webp
        ], check=True, capture_output=True, text=True)

        # Upload to Catbox
        with open(temp_webp, "rb") as f:
            files = {'fileToUpload': ('sticker.webp', f, 'image/webp')}
            upload_response = requests.post("https://catbox.moe/user/api.php", files=files, data={"reqtype": "fileupload"})
        
        # Clean up
        for file in [temp_mp4, temp_webp]:
            if os.path.exists(file):
                os.remove(file)

        if upload_response.status_code == 200:
            webp_url = upload_response.text.strip() + "?creator=khangapi"
            print(f"✅ Converted and uploaded video: {webp_url}")
            return webp_url
        print(f"❌ Upload failed: {upload_response.text}")
        return None
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error: {e.stderr}")
        return None
    except Exception as e:
        print(f"❌ Lỗi khi chuyển MP4 sang WebP: {e}")
        return None

def send_response(client, thread_id, thread_type, text, ttl=10000):
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=len(text), style="font", size="10", auto_format=False),
        MessageStyle(offset=0, length=len(text), style="bold", auto_format=False)
    ])
    styled_message = Message(text=text, style=style)
    client.sendMessage(styled_message, thread_id, thread_type, ttl=ttl)

def handle_autostk_on(client, thread_id):
    settings = read_settings(client.uid)
    if "auto_sticker" not in settings:
        settings["auto_sticker"] = {}
    settings["auto_sticker"][thread_id] = True
    write_settings(client.uid, settings)
    return f"🚦 Tính năng rải sticker auto đã được BẬT trong nhóm này ✅"

def handle_autostk_off(client, thread_id):
    settings = read_settings(client.uid)
    if "auto_sticker" in settings and thread_id in settings["auto_sticker"]:
        settings["auto_sticker"][thread_id] = False
        write_settings(client.uid, settings)
        return f"🚦 Tính năng rải sticker auto đã được TẮT trong nhóm này ✅"
    return "🚦 Nhóm chưa có thông tin cấu hình auto sticker để tắt 🤗"

def handle_autostk_command(message, message_object, thread_id, thread_type, author_id, client):
    prefix = getattr(client, 'prefix', '.')
    parts = message.replace(f"{prefix}autostk", "").strip().split()
    if not parts:
        send_response(client, thread_id, thread_type, f"💡 Hướng dẫn:\n- {prefix}autostk on: Bật rải sticker auto\n- {prefix}autostk off: Tắt rải sticker auto")
        return
    
    sub_cmd = parts[0].lower()
    if sub_cmd == "on":
        if not is_admin(client, author_id):
            send_response(client, thread_id, thread_type, "❌ Bạn không phải admin bot!")
            return
        response = handle_autostk_on(client, thread_id)
        send_response(client, thread_id, thread_type, response)
    elif sub_cmd == "off":
        if not is_admin(client, author_id):
            send_response(client, thread_id, thread_type, "❌ Bạn không phải admin bot!")
            return
        response = handle_autostk_off(client, thread_id)
        send_response(client, thread_id, thread_type, response)
    else:
        send_response(client, thread_id, thread_type, f"💡 Hướng dẫn:\n- {prefix}autostk on: Bật rải sticker auto\n- {prefix}autostk off: Tắt rải sticker auto")



txa = {
    "name": "pro_stk",
    "desc": {
        "stk": "Tạo sticker từ ảnh",
        "autostk": "Tự động gửi sticker"
    },
    "author": "TXA",
    "command": ['stk', 'autostk']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'stk': handle_stk_command,
        'autostk': handle_autostk_command
    }
    
    func = dispatch_map.get(cmd)
    if func:
        import inspect
        sig = inspect.signature(func)
        args_map = {
            'bot': bot,
            'client': bot,
            'message_object': message_object,
            'thread_id': thread_id,
            'thread_type': thread_type,
            'author_id': author_id,
            'message': message_text,
            'message_text': message_text,
            'message_lower': message_text.lower()
        }
        args = []
        for param_name in sig.parameters:
            if param_name in args_map:
                args.append(args_map[param_name])
            else:
                args.append(None)
        func(*args)
