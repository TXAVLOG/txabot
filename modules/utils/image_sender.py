import os
import random
import requests
import time
from pathlib import Path
from urllib.parse import urlparse
from zlapi.models import Message

REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
}

def normalize_url(raw_url):
    if raw_url is None:
        return ""
    url = str(raw_url).strip().strip('"').strip("'").strip()
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("www."):
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return url

def url_is_reachable(url):
    try:
        response = requests.head(url, headers=REQUEST_HEADERS, timeout=5, allow_redirects=True)
        if 200 <= response.status_code < 400:
            return True
        if response.status_code in (401, 403, 405):
            return True
    except requests.RequestException:
        pass

    try:
        headers = dict(REQUEST_HEADERS)
        headers["Range"] = "bytes=0-0"
        response = requests.get(url, headers=headers, timeout=7, stream=True, allow_redirects=True)
        try:
            if 200 <= response.status_code < 400 or response.status_code in (401, 403):
                return True
            return False
        finally:
            response.close()
    except requests.RequestException:
        return True

def choose_reachable_url(urls):
    candidates = [url for url in (normalize_url(item) for item in urls) if url]
    random.shuffle(candidates)
    for url in candidates:
        if url_is_reachable(url):
            return url
    return candidates[0] if candidates else ""

class ImageSender:
    def __init__(self, data_dir=None):
        if data_dir:
            self.data_dir = data_dir
        else:
            self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data-send")
        
        self.local_images_dir = os.path.join(os.path.dirname(__file__), "..", "local-images")
        
        self.config = {
            "girl": {
                "file": "girl.txt",
                "text": "z_thinh_girl.txt",
                "local_dir": "girl",
                "ttl": 300000
            },
            "zGirl": {
                "file": "zGirl.txt",
                "text": "z_thinh_girl.txt",
                "ttl": 300000
            },
            "cosplay": {
                "file": "cosplay.txt",
                "text": "z_thinh_cosplay.txt",
                "ttl": 300000
            },
            "anime": {
                "file": "anime.txt",
                "text": "z_thinh_anime.txt",
                "ttl": 300000
            },
            "boy": {
                "file": "boy.txt",
                "text": "z_thinh_boy.txt",
                "ttl": 300000
            },
            "boy6mui": {
                "file": "boy6mui.txt",
                "ttl": 300000
            },
            "girlsexy": {
                "file": "girlsexy.txt",
                "ttl": 180000
            },
            "girlnguc": {
                "file": "girlnguc.txt",
                "ttl": 180000
            },
            "girlnude": {
                "file": "girlnude.txt",
                "ttl": 180000
            },
            "girllon": {
                "file": "girllon.txt",
                "ttl": 180000
            },
            "vdgirl": {
                "file": "vdgirl.txt",
                "local_dir": "vdgirl",
                "ttl": 300000
            },
            "vdcos": {
                "file": "vdcos.txt",
                "ttl": 300000
            },
            "vdanime": {
                "file": "vdanime.txt",
                "ttl": 300000
            },
            "vdsexy": {
                "file": "vdsexy.txt",
                "ttl": 180000
            },
            "anhgai": {
                "file": "anhgai.txt",
                "text": "z_thinh_girl.txt",
                "ttl": 300000
            },
            "imgsexy": {
                "file": "imgsexy.txt",
                "ttl": 180000
            },
            "vdchill": {
                "file": "vdchill.txt",
                "ttl": 300000
            },
            "vdgai": {
                "file": "vdgai.txt",
                "ttl": 300000
            }
        }
    
    def get_image_urls(self, type_name):
        """Đọc URLs từ file txt"""
        if type_name not in self.config:
            return None
        
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data-send")
        file_path = os.path.join(data_dir, self.config[type_name]["file"])
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [url for url in (normalize_url(line) for line in f) if url]
        
        return urls
    
    def get_text(self, type_name):
        """Đọc caption từ file txt"""
        if type_name not in self.config or "text" not in self.config[type_name]:
            return ""
        
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data-send")
        file_path = os.path.join(data_dir, "Text", self.config[type_name]["text"])
        if not os.path.exists(file_path):
            return ""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            texts = [line.strip() for line in f if line.strip()]
        
        selected_text = random.choice(texts) if texts else ""
        return selected_text.replace('\\n', '\n')
    
    def download_image(self, url, save_path, timeout=10):
        """Download ảnh từ URL"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site'
        }
        
        if 'imgur.com' in url:
            headers['Referer'] = 'https://imgur.com/'
        elif 'flickr.com' in url or 'staticflickr.com' in url:
            headers['Referer'] = 'https://www.flickr.com/'
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=timeout, stream=True)
                response.raise_for_status()
                
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Check file size
                file_size = os.path.getsize(save_path)
                if file_size < 1024:  # < 1KB
                    os.remove(save_path)
                    raise Exception("File quá nhỏ")
                
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    raise e
        
        return False
    
    def get_local_files(self, type_name):
        """Lấy danh sách file local"""
        if type_name not in self.config or "local_dir" not in self.config[type_name]:
            return []
        
        local_dir = os.path.join(self.local_images_dir, self.config[type_name]["local_dir"])
        if not os.path.exists(local_dir):
            return []
        
        # Lấy tất cả file ảnh/video
        extensions = [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".avi", ".mov", ".mkv"]
        files = []
        for file in os.listdir(local_dir):
            if os.path.splitext(file)[1].lower() in extensions:
                files.append(os.path.join(local_dir, file))
        
        return files
    
    def send_image(self, bot, message_object=None, thread_id=None, thread_type=None, author_id=None, type_name=None, custom_caption=""):
        """Gửi ảnh hoặc video tới chat"""
        
        # Lấy caption trước
        if custom_caption:
            caption = custom_caption
        else:
            text = self.get_text(type_name)
            if text:
                try:
                    if author_id:
                        author_info = bot.fetchUserInfo(author_id).changed_profiles.get(author_id, {})
                        author_name = author_info.get('zaloName', 'User')
                        caption = f"[ {author_name} ] {text}"
                    else:
                        caption = text
                except:
                    caption = text
            else:
                caption = ""
        
        msg_payload = caption if isinstance(caption, Message) else Message(text=caption)
        ttl = self.config[type_name].get("ttl", 300000)
        
        # Kiểm tra file local trước
        local_files = self.get_local_files(type_name)
        
        if local_files:
            # Chọn ngẫu nhiên file local
            selected_file = random.choice(local_files)
            
            # Nếu là video
            if type_name.startswith("vd"):
                try:
                    bot.sendLocalVideo(
                        selected_file,
                        thread_id=thread_id,
                        thread_type=thread_type,
                        message=msg_payload,
                        ttl=ttl
                    )
                    return None
                except Exception as e:
                    # Nếu lỗi, thử dùng URL
                    pass
            else:
                # Gửi ảnh local
                try:
                    if message_object:
                        bot.sendLocalImage(
                            selected_file,
                            thread_id=thread_id,
                            thread_type=thread_type,
                            message=msg_payload,
                            ttl=ttl
                        )
                    else:
                        bot.sendLocalImage(
                            selected_file,
                            thread_id=thread_id,
                            thread_type=thread_type,
                            message=msg_payload,
                            ttl=ttl
                        )
                    return None
                except Exception as e:
                    # Nếu lỗi, thử dùng URL
                    pass
        
        # Nếu không có file local hoặc lỗi, dùng URL cũ
        urls = self.get_image_urls(type_name)
        if not urls or len(urls) == 0:
            return "❌ Không tìm thấy dữ liệu!"
        
        # Nếu là video (bắt đầu bằng 'vd')
        if type_name.startswith("vd"):
            url = choose_reachable_url(urls)
            if not url:
                return "❌ Không tìm thấy URL video hợp lệ!"
            
            thumbnail_url = "https://i.imgur.com/wudT3ID.jpeg"
            
            try:
                bot.sendRemoteVideo(
                    videoUrl=url,
                    thumbnailUrl=thumbnail_url,
                    duration="1000000",
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=1080,
                    height=1920,
                    message=msg_payload,
                    ttl=ttl
                )
                return None
            except Exception as e:
                return f"❌ Lỗi khi gửi video: {e}"
        
        # Tạo temp file
        temp_dir = os.path.join(os.path.dirname(__file__), "..", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, f"{type_name}_{int(time.time())}.jpg")
        
        # Thử download ảnh
        max_attempts = 30
        for attempt in range(max_attempts):
            url = random.choice(urls)
            try:
                self.download_image(url, temp_file, timeout=5)
                break
            except:
                continue
        else:
            return "❌ Không thể tải ảnh. Vui lòng thử lại sau!"
        
        try:
            # Gửi ảnh
            if message_object:
                bot.sendLocalImage(
                    temp_file,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    message=msg_payload,
                    ttl=ttl
                )
            else:
                bot.sendLocalImage(
                    temp_file,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    message=msg_payload,
                    ttl=ttl
                )
            
            return None
        finally:
            # Xóa temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        return "❌ Lỗi khi gửi ảnh!"
