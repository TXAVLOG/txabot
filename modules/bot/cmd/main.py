# -*- coding: UTF-8 -*-
import os
import json
import time
from zlapi.models import Message
import modules.txacommand as txacommand
from core.bot_sys import read_settings

# Metadata
txa = {
    "name": "Command Manager",
    "desc": "Quản lý hệ thống lệnh, tìm kiếm lệnh và gán alias động.",
    "author": "TXA",
    "command": "cmd"
}

ALIASES_FILE = r"c:\Users\TXA3099\Desktop\Bot\txabot\aliases.json"

def _load_aliases():
    if os.path.exists(ALIASES_FILE):
        try:
            with open(ALIASES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[CMD MANAGER] Error loading aliases: {e}")
    return {}

def _save_aliases(aliases):
    try:
        with open(ALIASES_FILE, "w", encoding="utf-8") as f:
            json.dump(aliases, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[CMD MANAGER] Error saving aliases: {e}")
        return False

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, "prefix", ".")
    parts = message_text.strip().split()
    
    # ── HELP / LIST ─────────────────────────────────────────────────────────
    if len(parts) < 2:
        help_msg = (
            "⚙️ HỆ THỐNG QUẢN LÝ LỆNH\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔎 Tìm lệnh: {prefix}cmd find [từ khóa]\n"
            f"☘️ Chi tiết lệnh: {prefix}cmd [tên lệnh]\n"
            f"📋 Thêm alias: {prefix}cmd alias [lệnh gốc] [alias mới] (Admin)\n"
            f"🗑️ Xóa alias: {prefix}cmd unalias [alias] (Admin)\n"
            f"📌 Xem danh sách alias: {prefix}cmd list"
        )
        bot.replyMessage(Message(text=help_msg), message_object, thread_id, thread_type)
        return

    subcmd = parts[1].lower()

    # ── LIST ALIASES ────────────────────────────────────────────────────────
    if subcmd == "list":
        aliases = _load_aliases()
        if not aliases:
            bot.replyMessage(Message(text="📋 Hiện chưa có alias nào được cấu hình."), message_object, thread_id, thread_type)
            return
            
        list_lines = ["📋 DANH SÁCH ALIAS LỆNH:"]
        for alias, original in sorted(aliases.items()):
            list_lines.append(f"• {prefix}{alias} ➜ {prefix}{original}")
        bot.replyMessage(Message(text="\n".join(list_lines)), message_object, thread_id, thread_type)
        return

    # ── FIND COMMANDS ────────────────────────────────────────────────────────
    if subcmd == "find":
        if len(parts) < 3:
            bot.replyMessage(Message(text=f"❌ Dùng: {prefix}cmd find [từ khóa]"), message_object, thread_id, thread_type)
            return
        query = " ".join(parts[2:]).lower()
        
        matches = []
        # Search loaded commands
        for cmd_name, cmd_info in txacommand.loaded_commands.items():
            name = cmd_info.get("name", "").lower()
            desc = cmd_info.get("desc", "").lower()
            
            # Match query
            if query in cmd_name or query in name or query in desc:
                # Avoid duplicates in output if multi alias
                if cmd_name not in [m[0] for m in matches]:
                    matches.append((cmd_name, cmd_info))
                    
        if not matches:
            bot.replyMessage(Message(text=f"😔 Không tìm thấy lệnh nào chứa từ khóa: '{query}'"), message_object, thread_id, thread_type)
            return
            
        result_lines = [f"🔎 KẾT QUẢ TÌM LỆNH CHO '{query}':"]
        for cmd_name, cmd_info in sorted(matches, key=lambda x: x[0]):
            t_per = cmd_info.get("t-per", "all")
            per_icon = "👑" if t_per == "super" or t_per == "super-admin" else "🛡" if t_per == "admin" else "🥈" if t_per == "s-ad" or t_per == "s-admin" else "👥"
            desc = cmd_info.get("desc", "Không có mô tả")
            if isinstance(desc, dict):
                desc = desc.get(cmd_name, "Không có mô tả")
            result_lines.append(f"• {prefix}{cmd_name} [{per_icon} {t_per}] : {desc}")
            
        bot.replyMessage(Message(text="\n".join(result_lines)), message_object, thread_id, thread_type)
        return

    # ── ALIAS OPERATION (Admin Only) ─────────────────────────────────────────
    if subcmd == "alias":
        # Check permissions
        settings = read_settings(bot.uid)
        admin_bot = settings.get("admin_bot", [])
        high_level_admins = settings.get("high_level_admins", [])
        is_admin = (author_id == bot.uid) or (author_id in high_level_admins) or (author_id in admin_bot)
        
        if not is_admin:
            bot.replyMessage(Message(text="❌ Bạn không có quyền quản trị để gán alias."), message_object, thread_id, thread_type)
            return
            
        if len(parts) < 4:
            bot.replyMessage(Message(text=f"❌ Dùng: {prefix}cmd alias [lệnh gốc] [alias mới]"), message_object, thread_id, thread_type)
            return
            
        original_cmd = parts[2].lower()
        new_alias = parts[3].lower()
        
        # Verify original command exists
        if original_cmd not in txacommand.loaded_commands:
            bot.replyMessage(Message(text=f"❌ Lệnh gốc '{original_cmd}' không tồn tại."), message_object, thread_id, thread_type)
            return
            
        # Verify new alias doesn't clash with existing core commands
        if new_alias in txacommand.loaded_commands:
            bot.replyMessage(Message(text=f"❌ Không thể dùng '{new_alias}' làm alias vì nó trùng với một lệnh hệ thống."), message_object, thread_id, thread_type)
            return
            
        aliases = _load_aliases()
        aliases[new_alias] = original_cmd
        if _save_aliases(aliases):
            bot.replyMessage(Message(text=f"✅ Đã gán alias thành công:\n👉 {prefix}{new_alias} ➜ {prefix}{original_cmd}"), message_object, thread_id, thread_type)
        else:
            bot.replyMessage(Message(text="❌ Lỗi khi lưu file cấu hình alias."), message_object, thread_id, thread_type)
        return

    # ── UNALIAS OPERATION (Admin Only) ───────────────────────────────────────
    if subcmd == "unalias":
        settings = read_settings(bot.uid)
        admin_bot = settings.get("admin_bot", [])
        high_level_admins = settings.get("high_level_admins", [])
        is_admin = (author_id == bot.uid) or (author_id in high_level_admins) or (author_id in admin_bot)
        
        if not is_admin:
            bot.replyMessage(Message(text="❌ Bạn không có quyền quản trị để xóa alias."), message_object, thread_id, thread_type)
            return
            
        if len(parts) < 3:
            bot.replyMessage(Message(text=f"❌ Dùng: {prefix}cmd unalias [alias]"), message_object, thread_id, thread_type)
            return
            
        alias_to_remove = parts[2].lower()
        
        aliases = _load_aliases()
        if alias_to_remove not in aliases:
            bot.replyMessage(Message(text=f"❌ Alias '{alias_to_remove}' không tồn tại."), message_object, thread_id, thread_type)
            return
            
        original_cmd = aliases.pop(alias_to_remove)
        if _save_aliases(aliases):
            bot.replyMessage(Message(text=f"🗑️ Đã xóa alias '{alias_to_remove}' (trỏ tới '{original_cmd}') thành công."), message_object, thread_id, thread_type)
        else:
            bot.replyMessage(Message(text="❌ Lỗi khi lưu file cấu hình alias."), message_object, thread_id, thread_type)
        return

    # ── VIEW COMMAND DETAILS ──────────────────────────────────────────────────
    # If subcmd is not a known command manager subcommand, look for the command details
    target_cmd = subcmd
    aliases = _load_aliases()
    
    # Resolve alias if queried
    if target_cmd in aliases:
        target_cmd = aliases[target_cmd]
        
    if target_cmd in txacommand.loaded_commands:
        cmd_info = txacommand.loaded_commands[target_cmd]
        t_per = cmd_info.get("t-per", "all")
        per_icon = "👑" if t_per == "super" or t_per == "super-admin" else "🛡" if t_per == "admin" else "🥈" if t_per == "s-ad" or t_per == "s-admin" else "👥"
        
        desc = cmd_info.get("desc", "Không có mô tả")
        if isinstance(desc, dict):
            desc = desc.get(target_cmd, "Không có mô tả")
            
        # Get all aliases pointing to this command
        cmd_aliases = [alias for alias, original in aliases.items() if original == target_cmd]
        alias_str = ", ".join([f"{prefix}{a}" for a in cmd_aliases]) if cmd_aliases else "Không có"
        
        detail_msg = (
            f"☘️ THÔNG TIN CHI TIẾT LỆNH: {prefix}{target_cmd}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"📛 Tên hiển thị: {cmd_info.get('name', 'N/A')}\n"
            f"📝 Mô tả: {desc}\n"
            f"🔑 Phân quyền: {per_icon} {t_per}\n"
            f"👤 Tác giả: {cmd_info.get('author', 'N/A')}\n"
            f"📋 Phím tắt/Alias: {alias_str}"
        )
        bot.replyMessage(Message(text=detail_msg), message_object, thread_id, thread_type)
    else:
        bot.replyMessage(Message(text=f"❌ Lệnh hoặc subcommand '{subcmd}' không tồn tại trong hệ thống."), message_object, thread_id, thread_type)
