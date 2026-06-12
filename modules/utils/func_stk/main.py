import requests
import subprocess
import json
import urllib.parse
import os
import time
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
from zlapi.models import Message, MultiMsgStyle, MessageStyle
from core.bot_sys import is_admin, read_settings, write_settings, create_rotating_webp, upload_file

# --- HÀM PHỤ TRỢ LƯU TRỮ STICKER ---
def load_saved_stickers():
    file_path = "stickers.txt"
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except Exception as e:
        print(f"[func_stk] Error loading stickers.txt: {e}")
        return []

def save_stickers(stickers_list):
    file_path = "stickers.txt"
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(stickers_list, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"[func_stk] Error saving stickers.txt: {e}")
        return False

# --- HÀM VẼ DANH SÁCH STICKER ---
def generate_sticker_list_image(stickers, page=1, total_pages=1, is_search=False):
    try:
        scale = 2  # Vẽ độ phân giải cao cho ảnh nét hơn
        width = 600 * scale
        row_height = 90 * scale
        padding = 20 * scale
        thumb_size = 70 * scale
        
        header_height = 80 * scale
        footer_height = 60 * scale
        
        img_height = header_height + len(stickers) * row_height + footer_height
        
        # Tạo canvas nền tối hiện đại
        image = Image.new("RGBA", (width, img_height), (30, 30, 30, 255))
        draw = ImageDraw.Draw(image)
        
        # Load font chữ hỗ trợ Unicode
        font_path = "font/arial unicode ms.otf"
        font_path_bold = "font/arial unicode ms bold.otf"
        try:
            font_title = ImageFont.truetype(font_path_bold, 24 * scale)
            font_text = ImageFont.truetype(font_path_bold, 20 * scale)
            font_sub = ImageFont.truetype(font_path, 14 * scale)
            font_num = ImageFont.truetype(font_path_bold, 22 * scale)
        except Exception:
            try:
                font_title = ImageFont.truetype("arial.ttf", 24 * scale)
                font_text = ImageFont.truetype("arial.ttf", 20 * scale)
                font_sub = ImageFont.truetype("arial.ttf", 14 * scale)
                font_num = ImageFont.truetype("arial.ttf", 22 * scale)
            except Exception:
                font_title = font_text = font_sub = font_num = ImageFont.load_default()
            
        # Vẽ Header tiêu đề
        title_text = "🔍 KẾT QUẢ TÌM KIẾM STICKER" if is_search else "🎨 DANH SÁCH STICKER ĐÃ LƯU"
        draw.text((padding, 25 * scale), title_text, fill=(0, 255, 180, 255), font=font_title)
        
        # Vẽ từng sticker trong danh sách
        for idx, stk in enumerate(stickers):
            y_offset = header_height + idx * row_height
            
            # Vẽ hộp nền hàng (bo góc 12px)
            draw.rounded_rectangle(
                [padding, y_offset, width - padding, y_offset + row_height - 10 * scale],
                radius=12 * scale,
                fill=(45, 45, 45, 255)
            )
            
            # Lấy số thứ tự thực tế để gửi (original index nếu là tìm kiếm, hoặc tính theo trang nếu là list)
            actual_num = stk.get("original_index") if is_search else (page - 1) * 10 + idx + 1
            
            # Vẽ số thứ tự
            num_str = f"#{actual_num}"
            draw.text((padding + 15 * scale, y_offset + 22 * scale), num_str, fill=(255, 200, 50, 255), font=font_num)
            
            # Tạo ảnh thumbnail mặc định (màu xám)
            thumb_img = Image.new("RGBA", (thumb_size, thumb_size), (60, 60, 60, 255))
            url = stk.get("staticImgUrl") or stk.get("animationImgUrl")
            if url:
                try:
                    res = requests.get(url, timeout=5)
                    temp_img = Image.open(BytesIO(res.content)).convert("RGBA")
                    thumb_img = ImageOps.fit(temp_img, (thumb_size, thumb_size), centering=(0.5, 0.5))
                    
                    # Bo góc thumbnail 10px
                    mask = Image.new("L", (thumb_size, thumb_size), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.rounded_rectangle((0, 0, thumb_size, thumb_size), radius=10 * scale, fill=255)
                    thumb_img.putalpha(mask)
                except Exception as e:
                    print(f"[func_stk] Error loading thumb for drawing: {e}")
                    
            # Dán thumbnail lên canvas
            thumb_x = padding + 80 * scale
            thumb_y = y_offset + (row_height - 10 * scale - thumb_size) // 2
            image.paste(thumb_img, (thumb_x, thumb_y), thumb_img.split()[3] if len(thumb_img.split()) == 4 else None)
            
            # Vẽ Tên sticker
            name_x = thumb_x + thumb_size + 15 * scale
            name_y = y_offset + 12 * scale
            draw.text((name_x, name_y), stk["name"], fill=(255, 255, 255, 255), font=font_text)
            
            # Vẽ Loại sticker (Đĩa xoay, Pixel Art hoặc Thường)
            stk_type = stk.get("type", "normal")
            type_label = "[💿 Đĩa Xoay]" if stk_type == "disc" else "[👾 Pixel Art]" if stk_type == "pixel" else "[🖼️ Sticker Thường]"
            type_color = (255, 105, 180, 255) if stk_type == "disc" else (100, 200, 255, 255) if stk_type == "pixel" else (180, 180, 180, 255)
            draw.text((name_x, name_y + 25 * scale), type_label, fill=type_color, font=font_sub)
            
        # Vẽ Footer thông tin trang
        footer_y = img_height - footer_height + 15 * scale
        if is_search:
            footer_text = f"Tìm thấy {len(stickers)} kết quả | Gõ -stk <số> để gửi nhanh sticker mong muốn!"
        else:
            footer_text = f"Trang {page}/{total_pages} | Gõ -stk list <trang> để xem trang khác | Gõ -stk <số> để gửi"
        draw.text((padding, footer_y), footer_text, fill=(150, 150, 150, 255), font=font_sub)
        
        # Lưu ảnh ra thư mục cache
        cache_dir = "modules/cache/"
        os.makedirs(cache_dir, exist_ok=True)
        out_path = os.path.join(cache_dir, f"stk_list_p{page}_{int(time.time())}.png")
        image.convert("RGB").save(out_path, format="JPEG", quality=95)
        return out_path
    except Exception as e:
        print(f"[func_stk] Error drawing sticker list image: {e}")
        return None

# --- HÀM CHUYỂN MP4 SANG WEBP (HỖ TRỢ PIXEL ART) ---
def convert_mp4_to_webp_and_upload(video_url, is_pixel_mode=False):
    try:
        response = requests.get(video_url, stream=True, timeout=15)
        response.raise_for_status()
        temp_mp4 = "temp_video.mp4"
        temp_webp = "temp_sticker.webp"
        with open(temp_mp4, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        # Bộ lọc FFmpeg pixelated: Giảm độ phân giải xuống 48px rồi phóng to lại 512px bằng láng giềng gần nhất (neighbor)
        filter_str = "scale=48:-2,scale=512:-2:flags=neighbor" if is_pixel_mode else "scale=512:-2"
        
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_mp4,
            "-vf", filter_str,
            "-c:v", "libwebp_anim",
            "-loop", "0",
            "-r", "15",
            "-an",
            "-lossless", "0",
            "-q:v", "75",
            "-loglevel", "error",
            temp_webp
        ], check=True, capture_output=True, text=True)

        webp_url = upload_file(temp_webp, "image/webp")
        
        # Xóa tệp tạm
        for file in [temp_mp4, temp_webp]:
            if os.path.exists(file):
                os.remove(file)

        if webp_url:
            print(f"[func_stk] Converted and uploaded video: {webp_url}")
            return webp_url
        return None
    except Exception as e:
        print(f"[func_stk] Lỗi khi chuyển MP4 sang WebP: {e}")
        return None

def get_file_type(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        content_type = response.headers.get("Content-Type", "").lower()
        if "image" in content_type:
            return "image"
        elif "video" in content_type:
            return "video"
        return "unknown"
    except Exception as e:
        print(f"[func_stk] Lỗi xác định loại file: {e}")
        return "unknown"

def send_response(client, thread_id, thread_type, text, ttl=10000):
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=len(text), style="font", size="10", auto_format=False),
        MessageStyle(offset=0, length=len(text), style="bold", auto_format=False)
    ])
    styled_message = Message(text=text, style=style)
    client.sendMessage(styled_message, thread_id, thread_type, ttl=ttl)

# --- HÀM XỬ LÝ LỆNH CHÍNH ---
def handle_stk_command(message, message_object, thread_id, thread_type, author_id, client):
    prefix = getattr(client, 'prefix', '.')
    if message.startswith(prefix):
        clean_msg = message[len(prefix):]
    else:
        clean_msg = message
    parts = clean_msg.strip().split()
    cmd = parts[0].lower() if parts else ""
    args = parts[1:]
    
    is_pixel_mode = (cmd == 'stkpx')
    is_disc_mode = (cmd == 'stkd') or any(arg in ['disc', 'dia', 'xoay', 'nhac', 'music'] for arg in args)

    # ----------------- LUỒNG B: KHÔNG REPLY TIN NHẮN (QUẢN LÝ / GỬI LẠI STICKER) -----------------
    if not message_object.quote:
        stickers = load_saved_stickers()
        
        # 1. Lệnh xem danh sách: -stk list [trang]
        if args and args[0].lower() == "list":
            page = 1
            if len(args) > 1 and args[1].isdigit():
                page = int(args[1])
                
            if not stickers:
                client.sendMessage(
                    Message(text="🚦 Hiện tại chưa có sticker tự chế nào được lưu cả. Hãy reply một ảnh/video bằng lệnh `-stk [tên]` để tạo và lưu nhé!"),
                    thread_id=thread_id,
                    thread_type=thread_type
                )
                return
                
            total_stickers = len(stickers)
            total_pages = (total_stickers + 9) // 10
            if page < 1 or page > total_pages:
                send_response(client, thread_id, thread_type, f"❌ Số trang không hợp lệ (1-{total_pages})!")
                return
                
            start_idx = (page - 1) * 10
            end_idx = min(start_idx + 10, total_stickers)
            page_stickers = stickers[start_idx:end_idx]
            
            send_response(client, thread_id, thread_type, f"⏳ Bé đang vẽ ảnh danh sách sticker (Trang {page}/{total_pages})...", ttl=15000)
            list_img_path = generate_sticker_list_image(page_stickers, page, total_pages)
            if list_img_path and os.path.exists(list_img_path):
                try:
                    with Image.open(list_img_path) as img:
                         w, h = img.size
                    client.sendLocalImage(list_img_path, thread_id, thread_type, width=w, height=h, ttl=300000)
                    os.remove(list_img_path)
                except Exception as e:
                    print(f"Error sending list image: {e}")
            else:
                client.sendMessage(Message(text="❌ Lỗi khi vẽ ảnh danh sách!"), thread_id=thread_id, thread_type=thread_type)
            return

        # 2. Lệnh tìm kiếm sticker: -stk find <tên>
        elif args and args[0].lower() == "find":
            if len(args) < 2:
                send_response(client, thread_id, thread_type, "💡 Hãy nhập từ khóa tìm kiếm! Ví dụ: `-stk find mèo`")
                return
            
            query = " ".join(args[1:]).lower()
            matched_stickers = []
            for idx, stk in enumerate(stickers):
                if query in stk["name"].lower():
                    stk_copy = stk.copy()
                    stk_copy["original_index"] = idx + 1
                    matched_stickers.append(stk_copy)
                    
            if not matched_stickers:
                client.sendMessage(
                    Message(text=f"🔍 Không tìm thấy sticker nào có tên chứa: '{query}' 🤧"),
                    thread_id=thread_id,
                    thread_type=thread_type
                )
                return
                
            # Góp ý người dùng: Nếu chỉ có duy nhất 1 kết quả -> gửi thẳng sticker đó luôn!
            if len(matched_stickers) == 1:
                stk = matched_stickers[0]
                send_response(client, thread_id, thread_type, f"🎯 Tìm thấy sticker '{stk['name']}'. Tiến hành gửi thẳng...", ttl=8000)
                client.send_custom_sticker(
                    staticImgUrl=stk["animationImgUrl"],
                    animationImgUrl=stk["animationImgUrl"],
                    thread_id=thread_id,
                    thread_type=thread_type,
                    reply=message_object,
                    width=512,
                    height=512
                )
                return
                
            # Nếu có nhiều hơn 1 kết quả -> vẽ ảnh kết quả tìm kiếm
            send_response(client, thread_id, thread_type, f"🔍 Tìm thấy {len(matched_stickers)} sticker phù hợp. Đang vẽ danh sách...", ttl=15000)
            list_img_path = generate_sticker_list_image(matched_stickers, page=1, total_pages=1, is_search=True)
            if list_img_path and os.path.exists(list_img_path):
                try:
                    with Image.open(list_img_path) as img:
                         w, h = img.size
                    client.sendLocalImage(list_img_path, thread_id, thread_type, width=w, height=h, ttl=300000)
                    os.remove(list_img_path)
                except Exception as e:
                    print(f"Error sending search image: {e}")
            else:
                client.sendMessage(Message(text="❌ Lỗi khi vẽ ảnh kết quả tìm kiếm!"), thread_id=thread_id, thread_type=thread_type)
            return

        # 3. Lệnh xóa sticker: -stk delete <số hoặc tên>
        elif args and args[0].lower() in ["delete", "xoa"]:
            if len(args) < 2:
                send_response(client, thread_id, thread_type, "💡 Hãy nhập số thứ tự hoặc tên sticker cần xóa! Ví dụ: `-stk delete 1`")
                return
                
            target = " ".join(args[1:])
            deleted_stk = None
            
            # Xóa theo số thứ tự
            if target.isdigit():
                idx = int(target) - 1
                if 0 <= idx < len(stickers):
                    deleted_stk = stickers.pop(idx)
            
            # Xóa theo tên
            if not deleted_stk:
                for i, stk in enumerate(stickers):
                    if stk["name"].lower() == target.lower():
                        deleted_stk = stickers.pop(i)
                        break
                        
            if deleted_stk:
                save_stickers(stickers)
                client.sendMessage(
                    Message(text=f"🗑️ Đã xóa thành công sticker '{deleted_stk['name']}' ({deleted_stk.get('type', 'normal')}) khỏi bộ nhớ!"),
                    thread_id=thread_id,
                    thread_type=thread_type
                )
            else:
                client.sendMessage(
                    Message(text=f"❌ Không tìm thấy sticker '{target}' trong danh sách để xóa!"),
                    thread_id=thread_id,
                    thread_type=thread_type
                )
            return

        # 4. Gửi sticker nhanh bằng số thứ tự: -stk <số>
        elif parts and parts[0].isdigit():
            num = int(parts[0])
            idx = num - 1
            if 0 <= idx < len(stickers):
                stk = stickers[idx]
                client.send_custom_sticker(
                    staticImgUrl=stk["animationImgUrl"],
                    animationImgUrl=stk["animationImgUrl"],
                    thread_id=thread_id,
                    thread_type=thread_type,
                    reply=message_object,
                    width=512,
                    height=512
                )
            else:
                send_response(client, thread_id, thread_type, f"❌ Số thứ tự sticker không tồn tại (1-{len(stickers)})!")
            return
            
        elif args and args[0].isdigit():
            num = int(args[0])
            idx = num - 1
            if 0 <= idx < len(stickers):
                stk = stickers[idx]
                client.send_custom_sticker(
                    staticImgUrl=stk["animationImgUrl"],
                    animationImgUrl=stk["animationImgUrl"],
                    thread_id=thread_id,
                    thread_type=thread_type,
                    reply=message_object,
                    width=512,
                    height=512
                )
            else:
                send_response(client, thread_id, thread_type, f"❌ Số thứ tự sticker không tồn tại (1-{len(stickers)})!")
            return

        # 5. Menu Hướng dẫn
        send_response(
            client, thread_id, thread_type,
            f"🎨 HƯỚNG DẪN QUẢN LÝ STICKER:\n"
            f"- `{prefix}stk list [trang]`: Xem các sticker đã lưu bằng hình ảnh\n"
            f"- `{prefix}stk <số>`: Gửi nhanh sticker số đó\n"
            f"- `{prefix}stk find <tên>`: Tìm sticker (gửi thẳng nếu chỉ có 1 kết quả)\n"
            f"- `{prefix}stk delete <số/tên>`: Xóa sticker khỏi danh sách\n\n"
            f"💡 HƯỚNG DẪN TẠO STICKER (Reply ảnh/video):\n"
            f"- `{prefix}stk [tên]`: Tạo sticker thường\n"
            f"- `{prefix}stkd [tên]`: Tạo sticker đĩa xoay\n"
            f"- `{prefix}stkpx [tên]`: Tạo sticker pixel art"
        )
        return

    # ----------------- LUỒNG A: CÓ REPLY TIN NHẮN (TẠO STICKER MỚI) -----------------
    attach = message_object.quote.attach
    if not attach:
        send_response(client, thread_id, thread_type, "❌ Hãy reply vào một tin nhắn chứa hình ảnh hoặc video để tạo sticker!")
        return

    try:
        attach_data = json.loads(attach)
    except json.JSONDecodeError:
        send_response(client, thread_id, thread_type, "❌ Dữ liệu tin nhắn reply không hợp lệ!")
        return

    file_url = attach_data.get('hdUrl') or attach_data.get('href')
    if not file_url:
        send_response(client, thread_id, thread_type, "❌ Không tìm thấy đường dẫn tệp tin reply!")
        return

    file_url = file_url.replace("\\/", "/").replace("&amp;", "&")
    file_url = urllib.parse.unquote(file_url)

    if "jxl" in file_url:
        file_url = file_url.replace("jxl", "jpg")

    # Lấy danh sách hiện tại để tính tên mặc định
    stickers_list = load_saved_stickers()
    
    # Lọc bỏ các từ khóa chế độ để lấy tên sticker thực tế
    name_parts = [arg for arg in args if arg not in ['disc', 'dia', 'xoay', 'nhac', 'music']]
    
    # Góp ý người dùng: nếu trống tên thì mặc định đặt là txa_{len(stickers_list) + 1}
    default_name = f"txa_{len(stickers_list) + 1}"
    stk_name = " ".join(name_parts) if name_parts else default_name

    file_type = get_file_type(file_url)
    
    if file_type == "video":
        send_response(client, thread_id, thread_type, "⏳ Bé đang tạo sticker video cho bạn, chờ tí nhé...", ttl=30000)
        webp_url = convert_mp4_to_webp_and_upload(file_url, is_pixel_mode=is_pixel_mode)
        if webp_url:
            client.send_custom_sticker(
                staticImgUrl=webp_url,
                animationImgUrl=webp_url,
                thread_id=thread_id,
                thread_type=thread_type,
                reply=message_object,
                width=512,
                height=512
            )
            # Lưu vào file stickers.txt
            new_stk = {
                "name": stk_name,
                "staticImgUrl": webp_url,
                "animationImgUrl": webp_url,
                "type": "pixel" if is_pixel_mode else "normal",
                "authorId": author_id,
                "timestamp": int(time.time())
            }
            stickers_list.append(new_stk)
            save_stickers(stickers_list)
            
            send_response(client, thread_id, thread_type, f"✅ Đã tạo & lưu thành công Sticker video '{stk_name}'!", ttl=30000)
        else:
            send_response(client, thread_id, thread_type, "❌ Không thể tạo sticker video!")

    elif file_type == "image":
        if is_disc_mode:
            try:
                send_response(client, thread_id, thread_type, "⏳ Bé đang tạo sticker đĩa xoay cho bạn, chờ tí nhé...", ttl=30000)
                res = create_rotating_webp(file_url)
                if not res:
                    send_response(client, thread_id, thread_type, "❌ Không thể tạo sticker đĩa xoay!")
                    return
                    
                static_path, animated_path = res
                webp_url = upload_file(animated_path, "image/webp")
                
                for path in [static_path, animated_path]:
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except:
                            pass
                            
                if not webp_url:
                    send_response(client, thread_id, thread_type, "❌ Lỗi khi tải sticker lên server!")
                    return
                    
                client.send_custom_sticker(
                    staticImgUrl=webp_url,
                    animationImgUrl=webp_url,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    reply=message_object,
                    width=512,
                    height=512
                )
                
                # Lưu vào file stickers.txt
                new_stk = {
                    "name": stk_name,
                    "staticImgUrl": webp_url,
                    "animationImgUrl": webp_url,
                    "type": "disc",
                    "authorId": author_id,
                    "timestamp": int(time.time())
                }
                stickers_list.append(new_stk)
                save_stickers(stickers_list)
                
                send_response(client, thread_id, thread_type, f"✅ Đã tạo & lưu thành công Sticker đĩa xoay '{stk_name}'!", ttl=30000)
            except Exception as e:
                print(f"[func_stk] Lỗi tạo sticker đĩa xoay: {e}")
                send_response(client, thread_id, thread_type, f"❌ Lỗi khi tạo sticker: {str(e)}")
                
        else:
            try:
                send_response(client, thread_id, thread_type, f"⏳ Bé đang tạo sticker{' pixel art' if is_pixel_mode else ''} cho bạn, chờ tí nhé...", ttl=30000)
                response = requests.get(file_url, stream=True, timeout=15)
                response.raise_for_status()
                
                img = Image.open(BytesIO(response.content)).convert("RGBA")
                temp_webp = "temp_sticker.webp"
                width, height = img.size
                
                if is_pixel_mode:
                    # Thuật toán Pixel Art: Scale nhỏ xuống 48px rồi phóng to lại 512px bằng lân cận gần nhất (NEAREST)
                    pixel_size = 48
                    new_h = int(pixel_size * height / width)
                    img_small = img.resize((pixel_size, new_h), Image.Resampling.NEAREST)
                    img = img_small.resize((512, int(512 * new_h / pixel_size)), Image.Resampling.NEAREST)
                else:
                    img = img.resize((512, int(512 * height / width)), Image.LANCZOS)
                    
                width, height = img.size
                mask = Image.new("L", (width, height), 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle((0, 0, width, height), radius=50, fill=255)
                img.putalpha(mask)
                img.save(temp_webp, format="WEBP", quality=75, lossless=False)
                
                webp_url = upload_file(temp_webp, "image/webp")
                if os.path.exists(temp_webp):
                    os.remove(temp_webp)
                    
                if webp_url:
                    client.send_custom_sticker(
                        staticImgUrl=webp_url,
                        animationImgUrl=webp_url,
                        thread_id=thread_id,
                        thread_type=thread_type,
                        reply=message_object,
                        width=512,
                        height=512
                    )
                    
                    # Lưu vào file stickers.txt
                    new_stk = {
                        "name": stk_name,
                        "staticImgUrl": webp_url,
                        "animationImgUrl": webp_url,
                        "type": "pixel" if is_pixel_mode else "normal",
                        "authorId": author_id,
                        "timestamp": int(time.time())
                    }
                    stickers_list.append(new_stk)
                    save_stickers(stickers_list)
                    
                    send_response(client, thread_id, thread_type, f"✅ Đã tạo & lưu thành công Sticker '{stk_name}'!", ttl=30000)
                else:
                    send_response(client, thread_id, thread_type, "❌ Không thể tải sticker lên server!")
            except Exception as e:
                print(f"[func_stk] Lỗi khi tạo sticker thường: {e}")
                send_response(client, thread_id, thread_type, f"❌ Lỗi khi tạo sticker: {str(e)}")
    else:
        send_response(client, thread_id, thread_type, "❌ Loại file đính kèm này không được hỗ trợ!")

# --- HÀM CHO TÍNH NĂNG AUTO STICKER ---
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

# --- CONFIG THÔNG TIN LỆNH ---
txa = {
    "name": "pro_stk",
    "desc": {
        "stk": "Tạo, lưu và quản lý sticker cá nhân",
        "autostk": "Tự động gửi sticker",
        "stkd": "Tạo sticker đĩa nhạc xoay từ ảnh và lưu lại",
        "stkpx": "Tạo sticker pixel art từ ảnh/video và lưu lại"
    },
    "author": "TXA",
    "command": ['stk', 'autostk', 'stkd', 'stkpx']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'stk': handle_stk_command,
        'stkd': handle_stk_command,
        'stkpx': handle_stk_command,
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
