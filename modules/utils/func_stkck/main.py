import os
import requests
import urllib.parse
import uuid
import threading
from core.bot_sys import is_admin, read_settings, write_settings, get_user_name_by_id
from zlapi.models import Message, Mention

# Thông tin tài khoản ngân hàng mặc định
DEFAULT_BANK = "Techcombank"
DEFAULT_STK = "2923252311"
DEFAULT_NAME = "TANG XUAN ANH"

def parse_amount(amount_str):
    amount_str = amount_str.lower().replace(",", "").replace(".", "").strip()
    multiplier = 1
    if amount_str.endswith("k"):
        multiplier = 1000
        amount_str = amount_str[:-1]
    elif amount_str.endswith("m") or amount_str.endswith("tr"):
        multiplier = 1000000
        if amount_str.endswith("tr"):
            amount_str = amount_str[:-2]
        else:
            amount_str = amount_str[:-1]
    try:
        return int(float(amount_str) * multiplier)
    except ValueError:
        return None

def handle_stkck_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "stkck" not in settings:
        settings["stkck"] = {}
    settings["stkck"][thread_id] = True
    write_settings(bot.uid, settings)
    return f"🚦 Lệnh {bot.prefix}bank đã được BẬT trong nhóm này ✅"

def handle_stkck_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "stkck" in settings and thread_id in settings["stkck"]:
        settings["stkck"][thread_id] = False
        write_settings(bot.uid, settings)
        return f"🚦 Lệnh {bot.prefix}bank đã TẮT trong nhóm này ✅"
    return "🚦 Nhóm chưa có thông tin cấu hình bank để tắt 🤗"

def handle_bank_command(message, message_object, thread_id, thread_type, author_id, client):
    def run():
        try:
            settings = read_settings(client.uid)
            prefix = getattr(client, 'prefix', '.')
            clean_msg = message[len(prefix):] if message.startswith(prefix) else message
            parts = clean_msg.strip().split()
            
            if not parts:
                return
                
            cmd = parts[0].lower()
            args = parts[1:]
            
            # Check Admin configuration commands
            if args and args[0].lower() == "on":
                if not is_admin(client, author_id):
                    client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), message_object, thread_id, thread_type)
                    return
                response = handle_stkck_on(client, thread_id)
                client.replyMessage(Message(text=response), message_object, thread_id, thread_type)
                return
            elif args and args[0].lower() == "off":
                if not is_admin(client, author_id):
                    client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), message_object, thread_id, thread_type)
                    return
                response = handle_stkck_off(client, thread_id)
                client.replyMessage(Message(text=response), message_object, thread_id, thread_type)
                return
            
            # Check custom configuration commands for Bank Details
            if args and args[0].lower() == "set":
                if not is_admin(client, author_id):
                    client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), message_object, thread_id, thread_type)
                    return
                if len(args) < 4:
                    client.replyMessage(
                        Message(text=f"❌ Sai cú pháp! Sử dụng: {prefix}{cmd} set <stk> <tên_ngân_hàng> <tên_chủ_khoản>"),
                        message_object, thread_id, thread_type
                    )
                    return
                stk = args[1]
                bank = args[2]
                name = " ".join(args[3:]).strip('\'"')
                
                if "bank_info" not in settings:
                    settings["bank_info"] = {}
                settings["bank_info"]["stk"] = stk
                settings["bank_info"]["bank"] = bank
                settings["bank_info"]["name"] = name
                write_settings(client.uid, settings)
                
                client.replyMessage(
                    Message(text=f"✅ Đã cấu hình tài khoản nhận tiền thành công:\n🏦 Ngân hàng: {bank.upper()}\n🔑 Số tài khoản: {stk}\n👤 Chủ tài khoản: {name.upper()}"),
                    message_object, thread_id, thread_type
                )
                return
                
            # If set bank details individually
            if args and args[0].lower() in ["setstk", "setbank", "setname"]:
                if not is_admin(client, author_id):
                    client.replyMessage(Message(text="❌ Bạn không phải admin bot!"), message_object, thread_id, thread_type)
                    return
                if len(args) < 2:
                    client.replyMessage(Message(text=f"❌ Thiếu tham số cấu hình!"), message_object, thread_id, thread_type)
                    return
                
                sub = args[0].lower()
                val = " ".join(args[1:]).strip('\'"')
                if "bank_info" not in settings:
                    settings["bank_info"] = {}
                
                if sub == "setstk":
                    settings["bank_info"]["stk"] = val
                    label = "Số tài khoản"
                elif sub == "setbank":
                    settings["bank_info"]["bank"] = val
                    label = "Tên ngân hàng"
                else:
                    settings["bank_info"]["name"] = val
                    label = "Tên chủ tài khoản"
                    
                write_settings(client.uid, settings)
                client.replyMessage(Message(text=f"✅ Đã cập nhật {label} thành công!"), message_object, thread_id, thread_type)
                return
            
            # Standard execution (checking if enabled)
            if not settings.get("stkck", {}).get(thread_id, False):
                return
                
            # Load current bank details
            bank_info = settings.get("bank_info", {})
            bank = bank_info.get("bank", DEFAULT_BANK)
            stk = bank_info.get("stk", DEFAULT_STK)
            name = bank_info.get("name", DEFAULT_NAME)
            
            # Parse amount and description
            amount = None
            description = ""
            
            if args:
                first_arg = args[0]
                parsed = parse_amount(first_arg)
                if parsed is not None:
                    amount = parsed
                    description = " ".join(args[1:])
                else:
                    description = " ".join(args)
            
            # Generate VietQR Code Image
            encoded_name = urllib.parse.quote(name)
            encoded_desc = urllib.parse.quote(description) if description else ""
            
            qr_url = f"https://img.vietqr.io/image/{bank}-{stk}-compact2.png?accountName={encoded_name}"
            if amount is not None:
                qr_url += f"&amount={amount}"
            if description:
                qr_url += f"&addInfo={encoded_desc}"
                
            # Download image locally
            temp_dir = "modules/cache"
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, f"bank_qr_{uuid.uuid4().hex}.png")
            
            try:
                res = requests.get(qr_url, timeout=15)
                res.raise_for_status()
                with open(temp_path, "wb") as f:
                    f.write(res.content)
            except Exception as download_err:
                client.replyMessage(Message(text=f"❌ Lỗi tải mã QR từ VietQR: {download_err}"), message_object, thread_id, thread_type)
                return
                
            amount_txt = f"{amount:,} VNĐ" if amount is not None else "Tùy tâm"
            desc_txt = description if description else "Chuyển khoản"
            
            caption = (
                "💳 THÔNG TIN CHUYỂN KHOẢN 💳\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🏦 Ngân hàng: {bank.upper()}\n"
                f"🔑 Số tài khoản: {stk}\n"
                f"👤 Chủ tài khoản: {name.upper()}\n"
                f"💰 Số tiền: {amount_txt}\n"
                f"📝 Nội dung: {desc_txt}\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "⚠️ Quét mã QR bên dưới để chuyển khoản nhanh."
            )
            
            client.sendLocalImage(
                imagePath=temp_path,
                thread_id=thread_id,
                thread_type=thread_type,
                message=Message(text=caption),
                ttl=0
            )
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        except Exception as e:
            print(f"[func_stkck] Error: {e}")
            client.replyMessage(Message(text=f"❌ Lỗi hệ thống: {e}"), message_object, thread_id, thread_type)
            
    thread = threading.Thread(target=run)
    thread.start()

txa = {
    "name": "pro_stkck",
    "desc": "Tạo mã QR chuyển khoản và thông tin tài khoản ngân hàng. Bật/tắt bằng lệnh on/off.",
    "author": "TXA",
    "command": ['bank']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'bank': handle_bank_command
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
