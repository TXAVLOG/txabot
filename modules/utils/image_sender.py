import os
import random
import requests
import time
from pathlib import Path
from zlapi.models import Message

class ImageSender:
    def __init__(self, data_dir=None):
        if data_dir:
            self.data_dir = data_dir
        else:
            self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data-send")
        
        self.config = {
            "girl": {
                "file": "girl.txt",
                "text": "z_thinh_girl.txt",
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
            }
        }
    
    def get_image_urls(self, type_name):
        """Đọc URLs từ file txt"""
        if type_name not in self.config:
            return None
        
        file_path = os.path.join(self.data_dir, self.config[type_name]["file"])
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        return urls
    
    def get_text(self, type_name):
        """Đọc caption từ file txt"""
        if type_name not in self.config or "text" not in self.config[type_name]:
            return ""
        
        file_path = os.path.join(self.data_dir, "Text", self.config[type_name]["text"])
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
    
    def send_image(self, bot, message_object, thread_id, thread_type, author_id, type_name):
        """Gửi ảnh hoặc video tới chat"""
        urls = self.get_image_urls(type_name)
        if not urls or len(urls) == 0:
            return "❌ Không tìm thấy dữ liệu!"
        
        # Nếu là video (bắt đầu bằng 'vd')
        if type_name.startswith("vd"):
            url = None
            max_attempts = 10
            for attempt in range(max_attempts):
                candidate_url = random.choice(urls)
                try:
                    res = requests.head(candidate_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
                    if res.status_code == 200:
                        url = candidate_url
                        break
                except:
                    pass
            if not url:
                url = random.choice(urls)
            
            # Lấy caption
            text = self.get_text(type_name)
            if text:
                try:
                    author_info = bot.fetchUserInfo(author_id).changed_profiles.get(author_id, {})
                    author_name = author_info.get('zaloName', 'User')
                    caption = f"[ {author_name} ] {text}"
                except:
                    caption = text
            else:
                caption = ""
                
            ttl = self.config[type_name].get("ttl", 300000)
            thumbnail_url = "https://f66-zpg-r.zdn.vn/jxl/8107149848477004187/d08a4d364d8cf9d2a09d.jxl"
            
            try:
                bot.sendRemoteVideo(
                    videoUrl=url,
                    thumbnailUrl=thumbnail_url,
                    duration="1000000",
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=1080,
                    height=1920,
                    message=Message(text=caption),
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
            # Lấy caption
            text = self.get_text(type_name)
            if text:
                # Lấy tên người dùng
                try:
                    author_info = bot.fetchUserInfo(author_id).changed_profiles.get(author_id, {})
                    author_name = author_info.get('zaloName', 'User')
                    caption = f"[ {author_name} ] {text}"
                except:
                    caption = text
            else:
                caption = ""
            
            # Gửi ảnh
            ttl = self.config[type_name].get("ttl", 300000)
            bot.sendLocalImage(
                temp_file,
                thread_id=thread_id,
                thread_type=thread_type,
                message=Message(text=caption),
                ttl=ttl
            )
            
            return None
        finally:
            # Xóa temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        return "❌ Lỗi khi gửi ảnh!"
