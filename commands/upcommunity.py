import json
import time
import requests
from zlapi.models import Message
# pyrefly: ignore [missing-import]
from logging_utils import Logging

logger = Logging()

class UpCommunityHandler:
    def __init__(self, client):
        self.client = client
    
    def handle_upcommunity_command(self, message, message_object, thread_id, thread_type, author_id):
        # Check if user is admin
        if author_id != self.client.ADMIN:
            self.client.replyMessage(
                Message(text="Bạn không có quyền sử dụng lệnh này."),
                message_object,
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=5000
            )
            return
        
        # Parse command
        parts = message.split()
        if len(parts) < 2:
            self.client.replyMessage(
                Message(text="Cú pháp: ..upcommunity <group_id>\nHoặc: ..upcommunity (sử dụng group hiện tại)"),
                message_object,
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=5000
            )
            return
        
        # Get group ID from command or use current thread_id
        group_id = parts[1] if len(parts) > 1 and parts[1] != thread_id else thread_id
        
        # Get bot configuration
        try:
            config = self.load_main_bot_config()
            cookies = config.get("session_cookies", {})
            imei = config.get("imei", "")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.client.replyMessage(
                Message(text=f"Lỗi khi tải cấu hình: {e}"),
                message_object,
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=5000
            )
            return
        
        # Send reaction
        try:
            self.client.sendReaction(message_object, "⏳", thread_id, thread_type)
        except Exception as e:
            logger.error(f"Error sending reaction: {e}")
        
        # Call upgrade API
        result = self.upgrade_community(group_id, cookies, imei)
        
        # Send result
        if result.get("success"):
            try:
                self.client.sendReaction(message_object, "✅", thread_id, thread_type)
            except Exception as e:
                logger.error(f"Error sending success reaction: {e}")
            
            self.client.replyMessage(
                Message(text=f"✅ Thành công! Nhóm {group_id} đã được nâng cấp lên Cộng đồng."),
                message_object,
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=10000
            )
        else:
            try:
                self.client.sendReaction(message_object, "❌", thread_id, thread_type)
            except Exception as e:
                logger.error(f"Error sending fail reaction: {e}")
            
            error_msg = result.get("error", "Lỗi không xác định")
            self.client.replyMessage(
                Message(text=f"❌ Thất bại! {error_msg}"),
                message_object,
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=10000
            )
    
    def load_main_bot_config(self):
        """Load main bot configuration from txa.json"""
        CONFIG_FILE = "txa.json"
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for bot in data["data"]:
            if bot.get("is_main_bot"):
                return bot
        raise ValueError("Không tìm thấy main bot!")
    
    def upgrade_community(self, group_id: str, cookies: dict, imei: str):
        """Upgrade Zalo group to community using API"""
        headers = {
            "User-Agent"  : "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/91.0.4472.120 Mobile Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin"      : "https://chat.zalo.me",
            "Referer"     : "https://chat.zalo.me/",
        }

        params = {
            "zpw_ver" : 685,
            "zpw_type": 30,
        }

        ts = int(time.time() * 1000)
        payload = {
            "params": json.dumps({
                "grid": str(group_id),
                "imei": imei,
                "ts"  : ts,
            }, separators=(',', ':')),
        }

        logger.info(f"Gọi API upgrade community cho group {group_id}")

        try:
            res = requests.post(
                "https://tt-group-wpa.chat.zalo.me/api/group/upgrade/community",
                params=params, 
                data=payload, 
                headers=headers, 
                cookies=cookies, 
                timeout=15,
            )

            logger.info(f"API Response Status: {res.status_code}")
            logger.info(f"API Response Body: {res.text[:500]}")

            result = res.json()
            err_code = result.get("error_code", -1)
            err_msg = result.get("error_message", "")
            
            if err_code == 0:
                return {"success": True}
            else:
                return {"success": False, "error": f"error_code={err_code}, message={err_msg}"}
                
        except Exception as e:
            logger.error(f"Lỗi khi gọi API upgrade community: {e}")
            return {"success": False, "error": str(e)}
