import sys
import os
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import inspect
import importlib
import io
import json
import logging
import random
import modules.txacommand as txacommand
import signal
import sys
import os
import re
import subprocess
import tempfile
import time
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from colorama import Style, init
from PIL import Image, ImageDraw, ImageOps, ImageFont, ImageFilter, ImageEnhance
import pyfiglet
from core.bot_sys import *
from zlapi import *
from zlapi.models import *
import threading
from zlapi import ZaloAPI
from queue import Queue
from fbchat.models import ThreadType
from zlapi.models import Message, ThreadType
from tempfile import NamedTemporaryFile
import glob
import pytz
from io import BytesIO
from datetime import datetime
import requests

logger = logging.getLogger("txabot")

message_count = {}
message_threshold = {}  # Lưu ngưỡng cho mỗi thread
def send_random_sticker(bot, thread_id, thread_type):
    if not os.path.exists('sticker.json'):
        return
    try:
        with open('sticker.json', 'r', encoding='utf-8') as file:
            stickers = json.load(file)
    except Exception as e:
        logger.error(f"Error reading sticker.json: {e}")
        return
            
    if not stickers:
        return
        
    sticker = random.choice(stickers)
    bot.sendSticker(sticker['stickerType'], sticker['stickerId'], sticker['cateId'], thread_id, thread_type)

def auto_stk(bot, message_object, author_id, thread_id, thread_type, message_text):
    # Không đếm tin nhắn không phải text (sticker, ảnh, v.v.)
    if not message_text or not isinstance(message_text, str) or message_text.strip() == "":
        return
        
    settings = read_settings(bot.uid)
    if settings.get('auto_sticker', {}).get(thread_id, False) and thread_id in settings.get('allowed_thread_ids', []):
        if thread_id not in message_count:
            message_count[thread_id] = 0
        if thread_id not in message_threshold:
            message_threshold[thread_id] = random.randint(10, 11)  # Random ngưỡng lần đầu
            
        message_count[thread_id] += 1
        if message_count[thread_id] >= message_threshold[thread_id]:
            send_random_sticker(bot, thread_id, thread_type)
            message_count[thread_id] = 0
            message_threshold[thread_id] = random.randint(10, 11)  # Random ngưỡng mới

current_word = None
wrong_attempts = 0
correct_attempts = 0
timeout_thread = None
timeout_duration = 30
current_player = None
used_words = set()
game_active = False
leaderboard = {}
leaderboard_file = "leaderboard.json"
words = []

def load_words():
    global words
    try:
        with open('words.txt', 'r', encoding='utf-8') as file:
            words = [line.strip() for line in file if line.strip()]
        return words
    except FileNotFoundError:
        words = []
        return words

words = load_words()

def load_leaderboard(uid):
    global leaderboard
    data_file_path = f"{uid}_{leaderboard_file}"
    try:
        with open(data_file_path, 'r', encoding='utf-8') as f:
            leaderboard = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        leaderboard = {}

def save_leaderboard(uid):
    data_file_path = f"{uid}_{leaderboard_file}"
    try:
        with open(data_file_path, 'w', encoding='utf-8') as f:
            json.dump(leaderboard, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving leaderboard: {e}")

def save_word_to_file(word):
    try:
        with open('words.txt', 'a', encoding='utf-8') as file:
            file.write(f"\n{word}")
        if word not in words:
            words.append(word)
    except Exception as e:
        print(f"Error saving word: {e}")

def remove_word_from_file(word):
    global words
    if word in words:
        try:
            with open('words.txt', 'r', encoding='utf-8') as file:
                lines = file.readlines()
            with open('words.txt', 'w', encoding='utf-8') as file:
                for line in lines:
                    if line.strip() != word:
                        file.write(line)
            words = load_words()
            return True
        except Exception as e:
            print(f"Error removing word: {e}")
    return False

def reset_game():
    global current_word, wrong_attempts, correct_attempts, timeout_thread, current_player, used_words, game_active
    if timeout_thread and timeout_thread.is_alive():
        timeout_thread.cancel()
    
    current_word = None
    wrong_attempts = 0
    correct_attempts = 0
    timeout_thread = None
    current_player = None
    used_words.clear()
    game_active = False

def handle_timeout(bot, message_object, thread_id, thread_type):
    global game_active
    if not game_active:
        return
    if random.random() > 0.3:
        bot.sendReaction(message_object, "😢", thread_id, thread_type)
    bot.sendReaction(message_object, "TBOT FAILED ❌", thread_id, thread_type)
    bot.replyMessage(Message(text="➜ ❌ Bạn đã hết thời gian trả lời! Trò chơi kết thúc."), 
                    message_object, thread_id=thread_id, thread_type=thread_type)
    reset_game()

def start_timeout(bot, message_object, thread_id, thread_type):
    global timeout_thread, game_active
    if timeout_thread and timeout_thread.is_alive():
        timeout_thread.cancel()
    game_active = True
    timeout_thread = threading.Timer(timeout_duration, lambda: handle_timeout(bot, message_object, thread_id, thread_type))
    timeout_thread.start()

def fetch_webpage(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching webpage: {str(e)}")
        return None

def get_wikipedia_info(search_term):
    base_url = "https://vi.wikipedia.org/wiki/"
    search_url = base_url + search_term.replace(" ", "_")
    
    page_content = fetch_webpage(search_url)
    if not page_content:
        return {"Lỗi": "Không thể lấy thông tin từ Wikipedia."}

    soup = BeautifulSoup(page_content, "html.parser")
    image_url = "Không tìm thấy ảnh"
    infobox = soup.find("table", {"class": "infobox"})
    
    if infobox:
        image_tag = infobox.find("img")
        if image_tag and "src" in image_tag.attrs:
            image_url = "https:" + image_tag["src"]

    info = {}
    if infobox:
        rows = infobox.find_all("tr")
        for row in rows:
            header = row.find("th")
            data = row.find("td")
            if header and data:
                links = data.find_all("a", href=True)
                if links:
                    info[header.text.strip()] = [f"https://vi.wikipedia.org{link['href']}" for link in links]
                else:
                    info[header.text.strip()] = data.text.strip()

    paragraphs = soup.find_all("p")
    content = "\n\n".join([p.text.strip() for p in paragraphs[:2] if p.text.strip()])

    return {
        "Hình ảnh": image_url,
        "Thông tin": info,
        "Mô tả": content
    }

def _read_kairobot_config():
    try:
        config_path = os.path.join(os.path.dirname(__file__), "txa.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            bot_data = (config.get("data") or [{}])[0]
            base_url = bot_data.get("kairobot_base_url") or os.getenv("KAIROBOT_BASE_URL") or "https://kairobot.qzz.io"
            api_key = bot_data.get("kairobot_api_key") or bot_data.get("apikey") or os.getenv("KAIROBOT_APIKEY") or ""
            return base_url.rstrip("/"), api_key.strip()
    except Exception:
        pass
    return "https://kairobot.qzz.io", ""

def check_word(player_word, last_part):
    if not player_word or not last_part:
        return False
    if player_word.split()[0] != last_part:
        return False

    # Check via word-chain API first
    base_url, api_key = _read_kairobot_config()
    if api_key:
        try:
            url = f"{base_url}/games/word-chain"
            resp = requests.get(url, params={"apikey": api_key, "word": player_word}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") is not False:
                    if player_word not in words:
                        save_word_to_file(player_word)
                    return True
        except Exception as api_err:
            print(f"[WordChain API] Fallback due to error: {api_err}")

    # Fallback to local dictionary and Wikipedia
    if player_word in words:
        return True
    wiki_info = get_wikipedia_info(player_word)
    if "Lỗi" not in wiki_info and wiki_info["Mô tả"]:
        save_word_to_file(player_word)
        return True
    return False

def update_leaderboard(bot, user_id, user_name, words_used):
    global leaderboard
    load_leaderboard(bot.uid)
    
    if user_id not in leaderboard:
        leaderboard[user_id] = {"name": user_name, "score": 0, "correct_answers": 0}
    
    leaderboard[user_id]["score"] += words_used
    leaderboard[user_id]["correct_answers"] += words_used
    leaderboard[user_id]["name"] = user_name
    
    save_leaderboard(bot.uid)
    return leaderboard[user_id]

def get_user_rank(bot, user_id):
    load_leaderboard(bot.uid)
    if not leaderboard or user_id not in leaderboard:
        return None
    
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1]["score"], reverse=True)
    for rank, (uid, _) in enumerate(sorted_leaderboard, 1):
        if uid == user_id:
            return rank
    return None

def handle_victory(bot, message_object, author_id, thread_id, thread_type):
    user_name = get_user_name_by_id(bot, author_id)
    words_used = correct_attempts
    user_data = update_leaderboard(bot, author_id, user_name, words_used)
    user_rank = get_user_rank(bot, author_id)
    
    message = f"🚦 {user_name}\n"
    message += "🎈 Xin chúc mừng bạn đã chiến thắng!\n"
    message += f"💯 Khích lệ: +{words_used} 🍫\n"
    message += f"🏅 Thành tích: {words_used} từ\n"
    
    if user_rank and user_rank <= 10:
        medal_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
        medal = medal_emojis.get(user_rank, f"{user_rank}️⃣")
        message += f"🎉 Bạn đã lập kỷ lục mới đứng {medal} trong BXH!"
    
    bot.replyMessage(Message(text=message, mention=Mention(author_id, length=len(user_name), offset=3)), 
                    message_object, thread_id=thread_id, thread_type=thread_type)
    reset_game()

def handle_defeat(bot, message_object, author_id, thread_id, thread_type):
    user_name = get_user_name_by_id(bot, author_id)
    correct_answers = correct_attempts
    
    if correct_answers > 0:
        user_data = update_leaderboard(bot, author_id, user_name, correct_answers)
        user_rank = get_user_rank(bot, author_id)
    else:
        user_rank = None
    
    message = f"🚦 {user_name}\n"
    message += "😢 Bạn đã sai quá nhiều lần. Thua rồi!\n"
    message += f"🎖️ Thành tích: {correct_answers} từ\n"
    
    if user_rank and user_rank <= 10:
        medal_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
        medal = medal_emojis.get(user_rank, f"{user_rank}️⃣")
        message += f"🎉 Bạn đã lập kỷ lục mới đứng {medal} trong BXH!"
    
    bot.replyMessage(Message(text=message, mention=Mention(author_id, length=len(user_name), offset=3)), 
                    message_object, thread_id=thread_id, thread_type=thread_type)
    reset_game()

def handle_wrong_attempt(bot, message_object, thread_id, thread_type):
    global wrong_attempts
    wrong_attempts += 1
    for _ in range(wrong_attempts):
        if random.random() > 0.3:
            bot.sendReaction(message_object, "😢", thread_id, thread_type)
        bot.sendReaction(message_object, "TBOT FAILED ❌", thread_id, thread_type)
    if wrong_attempts >= 3:
        handle_defeat(bot, message_object, current_player, thread_id, thread_type)
        return True
    return False

def get_leaderboard_display(bot):
    load_leaderboard(bot.uid)
    
    if not leaderboard:
        return "🚦 BXH 🏅 Top Game Nối Từ:\n➜ Chưa có dữ liệu xếp hạng!"
    
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1]["score"], reverse=True)
    
    display_text = "🚦 BXH 🏅 Top 10 Game Nối Từ:\n"
    medals = ["🥇", "🥈", "🥉"] + [f"{i}️⃣" for i in range(4, 11)]
    
    for i, (user_id, data) in enumerate(sorted_leaderboard[:10], 1):
        medal = medals[i-1]
        name = data["name"]
        score = data["score"]
        display_text += f"➜ {medal} {name} - {score} từ\n"
    
    return display_text.strip()

def nt_bxh(bot, message_object, thread_id, thread_type):
    display_text = get_leaderboard_display(bot)
    bot.replyMessage(Message(text=display_text), 
                    message_object, thread_id=thread_id, thread_type=thread_type)

def process_valid_word(bot, message_object, author_id, thread_id, thread_type, player_word):
    global current_word, wrong_attempts, correct_attempts, used_words
    player_last_part = player_word.split()[-1]
    used_words.add(player_word)
    
    next_word = next(
        (word for word in words 
         if word.split()[0] == player_last_part
         and word not in used_words 
         and len(word.split()) == 2),
        None
    )
    
    if next_word:
        current_word = next_word
        used_words.add(next_word)
        wrong_attempts = 0
        correct_attempts += 1
        
        for _ in range(correct_attempts):
            if random.random() > 0.3:
                bot.sendReaction(message_object, "❤️", thread_id, thread_type)
            bot.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
        
        response = f"{get_user_name_by_id(bot, author_id)} {next_word}"
        start_timeout(bot, message_object, thread_id, thread_type)
        bot.replyMessage(Message(text=response, mention=Mention(author_id, length=len(f"{get_user_name_by_id(bot, author_id)}"), offset=0)), 
                       message_object, thread_id=thread_id, thread_type=thread_type)
    else:
        handle_victory(bot, message_object, author_id, thread_id, thread_type)

def start_new_game(bot, message_object, author_id, thread_id, thread_type):
    global current_word, current_player, used_words, game_active
    if not words:
        bot.replyMessage(Message(text="➜ ❌ File words.txt không chứa từ nào!"), 
                       message_object, thread_id=thread_id, thread_type=thread_type)
        return
    current_word = random.choice(words)
    used_words.add(current_word)
    current_player = author_id
    game_active = True
    response = f"➜ Từ khởi đầu: '{current_word}'\n"
    start_timeout(bot, message_object, thread_id, thread_type)
    bot.replyMessage(Message(text=response), message_object,
                   thread_id=thread_id, thread_type=thread_type)

def nt_check(bot, message_object, author_id, thread_id, thread_type, message):
    parts = message.strip().split()
    if len(parts) < 3 or parts[1].lower() != "check":
        bot.replyMessage(Message(text="➜ Cú pháp không đúng! Sử dụng: /nt check <từ>"), 
                        message_object, thread_id=thread_id, thread_type=thread_type)
        return
    
    search_term = " ".join(parts[2:])
    wiki_info = get_wikipedia_info(search_term)
    
    if "Lỗi" in wiki_info or not wiki_info["Mô tả"]:
        response = f"➜ Từ '{search_term}' không được tìm thấy trên Wikipedia hoặc không có nghĩa rõ ràng."
    else:
        response = (
            f"➜ Kết quả cho '{search_term}':\n"
            f"📝 Mô tả: {wiki_info['Mô tả'][:200]}...\n"
            f"🖼️ Hình ảnh: {wiki_info['Hình ảnh']}\n"
            f"🔗 Link: https://vi.wikipedia.org/wiki/{search_term.replace(' ', '_')}"
        )
        if search_term not in words:
            save_word_to_file(search_term)
            response += f"\n✅ Đã thêm '{search_term}' vào danh sách từ vựng!"

    bot.replyMessage(Message(text=response), message_object, 
                    thread_id=thread_id, thread_type=thread_type)

def nt_add(bot, message_object, author_id, thread_id, thread_type, message):
    parts = message.strip().split()
    if len(parts) < 3 or parts[1].lower() != "add":
        bot.replyMessage(Message(text="➜ Cú pháp không đúng! Sử dụng: /nt add <từ>"), 
                        message_object, thread_id=thread_id, thread_type=thread_type)
        return
    
    new_word = " ".join(parts[2:])
    if new_word in words:
        response = f"🚦 {get_user_name_by_id(bot, author_id)} Từ '{new_word}' đã tồn tại trong từ điển! ⚠️"
    else:
        save_word_to_file(new_word)
        response = f"🚦 {get_user_name_by_id(bot, author_id)} Đã thêm từ '{new_word}' vào từ điển thành công! ✅"
    
    bot.replyMessage(Message(text=response, mention=Mention(author_id, length=len(f"{get_user_name_by_id(bot, author_id)}"), offset=3)), 
                    message_object, thread_id=thread_id, thread_type=thread_type)

def nt_del(bot, message_object, author_id, thread_id, thread_type, message):
    parts = message.strip().split()
    if len(parts) < 3 or parts[1].lower() != "del":
        bot.replyMessage(Message(text="➜ Cú pháp không đúng! Sử dụng: /nt del <từ>"), 
                        message_object, thread_id=thread_id, thread_type=thread_type)
        return
    
    word_to_remove = " ".join(parts[2:])
    if remove_word_from_file(word_to_remove):
        response = f"🚦 Đã xóa từ '{word_to_remove}' khỏi từ điển ✅"
    else:
        response = f"➜ Từ '{word_to_remove}' không có trong từ điển 🤧"
    
    bot.replyMessage(Message(text=response), message_object, 
                    thread_id=thread_id, thread_type=thread_type)

def nt_go(bot, message_object, author_id, thread_id, thread_type, message):
    global current_word, wrong_attempts, current_player, used_words, game_active
    message_text = message.strip()
    
    if message_text.startswith(f"{bot.prefix}nt bxh"):
        return nt_bxh(bot, message_object, thread_id, thread_type)
    elif message_text.startswith(f"{bot.prefix}nt check"):
        return nt_check(bot, message_object, author_id, thread_id, thread_type, message)
    elif message_text.startswith(f"{bot.prefix}nt add"):
        return nt_add(bot, message_object, author_id, thread_id, thread_type, message)
    elif message_text.startswith(f"{bot.prefix}nt del"):
        return nt_del(bot, message_object, author_id, thread_id, thread_type, message)
    elif message_text == f"{bot.prefix}nt":
        return show_menu(bot, message_object, message, author_id, thread_id, thread_type)

    if not game_active or current_player is None:
        return start_new_game(bot, message_object, author_id, thread_id, thread_type)
    
    if game_active and author_id != current_player:
        return

    if author_id != current_player:
        return
    
    player_word = message_text.replace(f"{bot.prefix}nt", "").strip()
    if len(player_word.split()) != 2:
        if handle_wrong_attempt(bot, message_object, thread_id, thread_type):
            return
        start_timeout(bot, message_object, thread_id, thread_type)
        return
    
    if player_word in used_words:
        if handle_wrong_attempt(bot, message_object, thread_id, thread_type):
            return
        start_timeout(bot, message_object, thread_id, thread_type)
        return
    
    last_part = current_word.split()[-1]
    if not check_word(player_word, last_part):
        if handle_wrong_attempt(bot, message_object, thread_id, thread_type):
            return
        start_timeout(bot, message_object, thread_id, thread_type)
        return
    
    if timeout_thread and timeout_thread.is_alive():
        timeout_thread.cancel()
    
    process_valid_word(bot, message_object, author_id, thread_id, thread_type, player_word)

def show_menu(bot, message_object, message, author_id, thread_id, thread_type):
    content = message.strip().split()
    message_text = message.strip()
    if message_text.startswith(f"{bot.prefix}nt"):
        if len(content) == 1:
            menu_nt = {
                f"{bot.prefix}nt go": "🔠 Bắt đầu game",
                f"{bot.prefix}nt check [từ vựng]": "✅ Kiểm tra ý nghĩa từ vựng",
                f"{bot.prefix}nt bxh": "🏆 Top 10 BXH",
                f"{bot.prefix}nt add [từ vựng]": "✚ Thêm từ vựng (BMT)",
                f"{bot.prefix}nt del [từ vựng]": "🗑️ Xóa từ vựng"
            }
            temp_image_path, menu_message = create_menu_nt_image(menu_nt, bot, author_id)
            bot.sendLocalImage(
                temp_image_path, thread_id=thread_id, thread_type=thread_type,
                message=Message(text=menu_message), height=500, width=1280
            )
            os.remove(temp_image_path)
            return

def create_gradient_colors(num_colors: int) -> List[Tuple[int, int, int]]:
    return [(random.randint(80, 220), random.randint(80, 220), random.randint(80, 220)) 
            for _ in range(num_colors)]

def interpolate_colors(colors: List[Tuple[int, int, int]], text_length: int, change_every: int) -> List[Tuple[int, int, int]]:
    gradient = []
    num_segments = len(colors) - 1
    steps_per_segment = max((text_length // change_every) + 1, 1)

    for i in range(num_segments):
        for j in range(steps_per_segment):
            if len(gradient) < text_length:
                ratio = j / steps_per_segment
                interpolated_color = (
                    int(colors[i][0] * (1 - ratio) + colors[i + 1][0] * ratio),
                    int(colors[i][1] * (1 - ratio) + colors[i + 1][1] * ratio),
                    int(colors[i][2] * (1 - ratio) + colors[i + 1][2] * ratio)
                )
                gradient.append(interpolated_color)

    while len(gradient) < text_length:
        gradient.append(colors[-1])
    return gradient[:text_length]

def is_emoji(character: str) -> bool:
    return character in emoji.EMOJI_DATA

def draw_text_with_emoji(draw: ImageDraw.Draw, text: str, position: Tuple[int, int],
                         font: ImageFont.FreeTypeFont, emoji_font: ImageFont.FreeTypeFont,
                         gradient_colors: List[Tuple[int, int, int]]) -> int:
    current_x = position[0]
    y = position[1]
    gradient = interpolate_colors(gradient_colors, len(text), 1)
    
    for i, char in enumerate(text):
        try:
            selected_font = emoji_font if is_emoji(char) else font
            font_size = selected_font.size
            offset_y = y - (font_size // 4) if is_emoji(char) else y
            
            draw.text((current_x, offset_y), char, 
                     fill=tuple(gradient[i]), 
                     font=selected_font)
            
            try:
                text_width = selected_font.getlength(char)
            except AttributeError:
                text_bbox = draw.textbbox((0, 0), char, font=selected_font)
                text_width = text_bbox[2] - text_bbox[0]
                if text_width == 0 and char == " ":
                    text_width = selected_font.size // 3
            current_x += text_width + (2 if is_emoji(char) else 0)
            
        except Exception as e:
            print(f"Lỗi khi vẽ ký tự '{char}': {e}")
            continue
    
    return current_x

def create_menu_nt_image(command_names, bot, author_id, nt_status=True):
    avatar_url = bot.fetchUserInfo(author_id).changed_profiles.get(author_id).avatar
    current_page_commands = list(command_names.items())
    numbered_commands = [f"{name}: {desc}" for name, desc in current_page_commands]
    menu_message = f"{get_user_name_by_id(bot, author_id)}\n" + "\n".join(numbered_commands)

    background_dir = "background"
    background_path = random.choice([os.path.join(background_dir, f) 
                                   for f in os.listdir(background_dir) 
                                   if f.endswith(('.png', '.jpg'))])
    image = Image.open(background_path).convert("RGBA").resize((1280, 500))
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    rect_x0, rect_y0, rect_x1, rect_y1 = (1280 - 1100) // 2, (500 - 300) // 2, \
                                        (1280 - 1100) // 2 + 1100, (500 - 300) // 2 + 300
    draw.rounded_rectangle([rect_x0, rect_y0, rect_x1, rect_y1], radius=50, 
                         fill=(255, 255, 255, 200))

    if avatar_url:
        try:
            avatar_image = Image.open(BytesIO(requests.get(avatar_url).content)).convert("RGBA").resize((100, 100))
            gradient_size = 110
            gradient_colors = create_gradient_colors(7)
            gradient_overlay = Image.new("RGBA", (gradient_size, gradient_size), (0, 0, 0, 0))
            gradient_draw = ImageDraw.Draw(gradient_overlay)
            
            for i, color in enumerate(gradient_colors):
                gradient_draw.ellipse((i, i, gradient_size - i, gradient_size - i), 
                                    outline=color, width=1)
            
            mask = Image.new("L", avatar_image.size, 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 100, 100), fill=255)
            gradient_overlay.paste(avatar_image, (5, 5), mask)
            overlay.paste(gradient_overlay, (rect_x0 + 20, rect_y0 + 100), gradient_overlay)
        except Exception as e:
            print(f"Lỗi khi xử lý avatar: {e}")

    text_hi = f"Hi, {get_user_name_by_id(bot, author_id)}"
    text_welcome = f"🎊 Chào mừng đến với menu 🔠 game nối từ"
    text_nt_status = f"{bot.prefix}nt on/off: bật/tắt tính năng"
    text_bot_ready = f"♥️ bot sẵn sàng phục vụ"
    text_bot_info = f"🤖 Bot: {get_user_name_by_id(bot, bot.uid)} 💻 version {bot.version} 🗓️ update {bot.date_update}"

    font_path = "font/arial unicode ms.otf"
    emoji_font_path = "font/NotoEmoji-Bold.ttf"
    
    font_hi = ImageFont.truetype(font_path, size=50) if os.path.exists(font_path) else ImageFont.load_default()
    font_welcome = ImageFont.truetype(font_path, size=35) if os.path.exists(font_path) else ImageFont.load_default()
    font_nt = ImageFont.truetype(font_path, size=40) if os.path.exists(font_path) else ImageFont.load_default()
    emoji_font = ImageFont.truetype(emoji_font_path, size=35) if os.path.exists(emoji_font_path) else ImageFont.load_default()

    total_height = 300
    line_spacing = total_height // 5
    center_x = 1280 // 2

    y_pos = rect_y0 + 10
    draw_text_with_emoji(draw, text_hi, (center_x - 200, y_pos),
                        font_hi, emoji_font, create_gradient_colors(5))
    
    y_pos += line_spacing
    draw_text_with_emoji(draw, text_welcome, (center_x - 370, y_pos), 
                        font_welcome, emoji_font, create_gradient_colors(5))
    
    y_pos += line_spacing
    draw_text_with_emoji(draw, text_nt_status, (center_x - 250, y_pos), 
                        font_nt, emoji_font, create_gradient_colors(5))
    
    y_pos += line_spacing
    draw_text_with_emoji(draw, text_bot_ready, (center_x - 250, y_pos), 
                        font_welcome, emoji_font, create_gradient_colors(5))
    
    y_pos += line_spacing - 10
    draw_text_with_emoji(draw, text_bot_info, (center_x - 460, y_pos), 
                        font_welcome, emoji_font, create_gradient_colors(7))

    final_image = Image.alpha_composite(image, overlay)
    temp_image_path = "nt_menu.png"
    final_image.save(temp_image_path)
    
    return temp_image_path, menu_message

user_selection_data = {}
session = requests.Session()
BACKGROUND_PATH = "background/"
CACHE_PATH = "modules/cache/"
OUTPUT_IMAGE_PATH = os.path.join(CACHE_PATH, "donghua.png")

def get_dominant_color(image_path):
    try:
        if not os.path.exists(image_path):
            print(f"File ảnh không tồn tại: {image_path}")
            return (0, 0, 0)

        img = Image.open(image_path).convert("RGB")
        img = img.resize((150, 150), Image.Resampling.LANCZOS)
        pixels = img.getdata()

        if not pixels:
            print(f"Không thể lấy dữ liệu pixel từ ảnh: {image_path}")
            return (0, 0, 0)

        r, g, b = 0, 0, 0
        for pixel in pixels:
            r += pixel[0]
            g += pixel[1]
            b += pixel[2]
        total = len(pixels)
        if total == 0:
            return (0, 0, 0)
        r, g, b = r // total, g // total, b // total
        return (r, g, b)

    except Exception as e:
        print(f"Lỗi khi phân tích màu nổi bật: {e}")
        return (0, 0, 0)

def get_contrasting_color(base_color, alpha=255):
    r, g, b = base_color[:3]
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return (255, 255, 255, alpha) if luminance < 0.5 else (0, 0, 0, alpha)

def random_contrast_color(base_color):
    r, g, b, _ = base_color
    box_luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    
    if box_luminance > 0.5:
        r = random.randint(0, 50)
        g = random.randint(0, 50)
        b = random.randint(0, 50)
    else:
        r = random.randint(200, 255)
        g = random.randint(200, 255)
        b = random.randint(200, 255)
    
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    s = min(1.0, s + 0.9)
    v = min(1.0, v + 0.7)
    
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    
    text_luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    if abs(text_luminance - box_luminance) < 0.3:
        if box_luminance > 0.5:
            r, g, b = colorsys.hsv_to_rgb(h, s, min(1.0, v * 0.4))
        else:
            r, g, b = colorsys.hsv_to_rgb(h, s, min(1.0, v * 1.7))
    
    return (int(r * 255), int(g * 255), int(b * 255), 255)

def download_avatar(avatar_url, save_path=os.path.join(CACHE_PATH, "user_avatar.png")):
    if not avatar_url:
        return None
    try:
        resp = requests.get(avatar_url, stream=True, timeout=5)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            return save_path
    except Exception as e:
        print(f"❌ Lỗi tải avatar: {e}")
    return None

def generate_menu_image(bot, author_id, thread_id, thread_type):
    images = glob.glob(os.path.join(BACKGROUND_PATH, "*.jpg")) + \
             glob.glob(os.path.join(BACKGROUND_PATH, "*.png")) + \
             glob.glob(os.path.join(BACKGROUND_PATH, "*.jpeg"))
    if not images:
        print("❌ Không tìm thấy ảnh trong thư mục background/")
        return None

    image_path = random.choice(images)

    try:
        size = (1920, 600)
        final_size = (1280, 380)
        bg_image = Image.open(image_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=7))
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        dominant_color = get_dominant_color(image_path)
        r, g, b = dominant_color
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

        box_colors = [
            (255, 20, 147, 90),
            (128, 0, 128, 90),
            (0, 100, 0, 90),
            (0, 0, 139, 90),
            (184, 134, 11, 90),
            (138, 3, 3, 90),
            (0, 0, 0, 90)
        ]

        box_color = random.choice(box_colors)

        box_x1, box_y1 = 90, 60
        box_x2, box_y2 = size[0] - 90, size[1] - 60
        draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=75, fill=box_color)

        font_arial_path = "font/arial unicode ms.otf"
        font_emoji_path = "font/NotoEmoji-Bold.ttf"
        
        try:
            font_text_large = ImageFont.truetype(font_arial_path, size=76)
            font_text_big = ImageFont.truetype(font_arial_path, size=68)
            font_text_small = ImageFont.truetype(font_arial_path, size=64)
            font_text_bot = ImageFont.truetype(font_arial_path, size=58)
            font_time = ImageFont.truetype(font_arial_path, size=56)
            font_icon = ImageFont.truetype(font_emoji_path, size=60)
            font_icon_large = ImageFont.truetype(font_emoji_path, size=175)
            font_name = ImageFont.truetype(font_emoji_path, size=60)
        except Exception as e:
            print(f"❌ Lỗi tải font: {e}")
            font_text_large = ImageFont.load_default(size=76)
            font_text_big = ImageFont.load_default(size=68)
            font_text_small = ImageFont.load_default(size=64)
            font_text_bot = ImageFont.load_default(size=58)
            font_time = ImageFont.load_default(size=56)
            font_icon = ImageFont.load_default(size=60)
            font_icon_large = ImageFont.load_default(size=175)
            font_name = ImageFont.load_default(size=60)

        def draw_text_with_shadow(draw, position, text, font, fill, shadow_color=(0, 0, 0, 250), shadow_offset=(2, 2)):
            x, y = position
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_color)
            draw.text((x, y), text, font=font, fill=fill)

        vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        vietnam_now = datetime.now(vietnam_tz)
        hour = vietnam_now.hour
        formatted_time = vietnam_now.strftime("%H:%M")
        time_icon = "🌤️" if 6 <= hour < 18 else "🌙"
        time_text = f" {formatted_time}"
        time_x = box_x2 - 250
        time_y = box_y1 + 10
        
        box_rgb = box_color[:3]
        box_luminance = (0.299 * box_rgb[0] + 0.587 * box_rgb[1] + 0.114 * box_rgb[2]) / 255
        last_lines_color = (255, 255, 255, 220) if box_luminance < 0.5 else (0, 0, 0, 220)

        time_color = last_lines_color

        if time_x >= 0 and time_y >= 0 and time_x < size[0] and time_y < size[1]:
            try:
                icon_x = time_x - 75
                icon_color = random_contrast_color(box_color)
                draw_text_with_shadow(draw, (icon_x, time_y - 8), time_icon, font_icon, icon_color)
                draw.text((time_x, time_y), time_text, font=font_time, fill=time_color)
            except Exception as e:
                print(f"❌ Lỗi vẽ thời gian lên ảnh: {e}")
                draw_text_with_shadow(draw, (time_x - 75, time_y - 8), "⏰", font_icon, (255, 255, 255, 255))
                draw.text((time_x, time_y), " ??;??", font=font_time, fill=time_color)

        user_info = bot.fetchUserInfo(author_id) if author_id else None
        user_name = "Unknown"
        if user_info and hasattr(user_info, 'changed_profiles') and author_id in user_info.changed_profiles:
            user = user_info.changed_profiles[author_id]
            user_name = getattr(user, 'name', None) or getattr(user, 'displayName', None) or f"ID_{author_id}"

        greeting_name = "Chủ Nhân" if is_admin(bot, author_id) else user_name

        emoji_colors = {
            "🎵": random_contrast_color(box_color),
            "😁": random_contrast_color(box_color),
            "🖤": random_contrast_color(box_color),
            "💞": random_contrast_color(box_color),
            "🤖": random_contrast_color(box_color),
            "💻": random_contrast_color(box_color),
            "📅": random_contrast_color(box_color),
            "🎧": random_contrast_color(box_color),
            "🌙": random_contrast_color(box_color),
            "🌤️": (200, 150, 255, 255)
        }

        text_lines = [
            f"Hi, {greeting_name}",
            f"💞 Chào mừng đến menu HH3D donghua 🐉",
            f"{bot.prefix}donghua on/off: 🚀 Bật/Tắt tính năng",
            "😁 Bot Sẵn Sàng Phục 🖤",
            f"🤖Bot: {bot.me_name} 💻Version: {bot.version} 📅Update {bot.date_update}"
        ]

        color1 = random_contrast_color(box_color)
        color2 = random_contrast_color(box_color)
        while color1 == color2:
            color2 = random_contrast_color(box_color)
        text_colors = [
            color1,
            color2,
            last_lines_color,
            last_lines_color,
            last_lines_color
        ]

        text_fonts = [
            font_text_large,
            font_text_big,
            font_text_bot,
            font_text_bot,
            font_text_small
        ]

        line_spacing = 85
        start_y = box_y1 + 10

        avatar_url = user_info.changed_profiles[author_id].avatar if user_info and hasattr(user_info, 'changed_profiles') and author_id in user_info.changed_profiles else None
        avatar_path = download_avatar(avatar_url)
        if avatar_path and os.path.exists(avatar_path):
            avatar_size = 200
            try:
                avatar_img = Image.open(avatar_path).convert("RGBA").resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
                border_size = avatar_size + 10
                rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
                draw_border = ImageDraw.Draw(rainbow_border)
                steps = 360
                for i in range(steps):
                    import colorsys
                    h = i / steps
                    r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
                    draw_border.arc([(0, 0), (border_size-1, border_size-1)], start=i, end=i + (360 / steps), fill=(int(r * 255), int(g * 255), int(b * 255), 255), width=5)
                avatar_y = (box_y1 + box_y2 - avatar_size) // 2
                overlay.paste(rainbow_border, (box_x1 + 40, avatar_y), rainbow_border)
                overlay.paste(avatar_img, (box_x1 + 45, avatar_y + 5), mask)
            except Exception as e:
                print(f"❌ Lỗi xử lý avatar: {e}")
                draw.text((box_x1 + 60, (box_y1 + box_y2) // 2 - 140), "🐳", font=font_icon, fill=(0, 139, 139, 255))
        else:
            draw.text((box_x1 + 60, (box_y1 + box_y2) // 2 - 140), "🐳", font=font_icon, fill=(0, 139, 139, 255))

        current_line_idx = 0
        for i, line in enumerate(text_lines):
            if not line:
                current_line_idx += 1
                continue

            parts = []
            current_part = ""
            for char in line:
                if ord(char) > 0xFFFF:
                    if current_part:
                        parts.append(current_part)
                        current_part = ""
                    parts.append(char)
                else:
                    current_part += char
            if current_part:
                parts.append(current_part)

            total_width = 0
            part_widths = []
            current_font = font_text_bot if i == 4 else text_fonts[i]
            for part in parts:
                font_to_use = font_icon if any(ord(c) > 0xFFFF for c in part) else current_font
                width = draw.textbbox((0, 0), part, font=font_to_use)[2]
                part_widths.append(width)
                total_width += width

            max_width = box_x2 - box_x1 - 300
            if total_width > max_width:
                font_size = int(current_font.getbbox("A")[3] * max_width / total_width * 0.9)
                if font_size < 60:
                    font_size = 60
                try:
                    current_font = ImageFont.truetype(font_arial_path, size=font_size) if os.path.exists(font_arial_path) else ImageFont.load_default(size=font_size)
                except Exception as e:
                    print(f"❌ Lỗi điều chỉnh font size: {e}")
                    current_font = ImageFont.load_default(size=font_size)
                total_width = 0
                part_widths = []
                for part in parts:
                    font_to_use = font_icon if any(ord(c) > 0xFFFF for c in part) else current_font
                    width = draw.textbbox((0, 0), part, font=font_to_use)[2]
                    part_widths.append(width)
                    total_width += width

            text_x = (box_x1 + box_x2 - total_width) // 2
            text_y = start_y + current_line_idx * line_spacing + (current_font.getbbox("A")[3] // 2)

            current_x = text_x
            for part, width in zip(parts, part_widths):
                if any(ord(c) > 0xFFFF for c in part):
                    emoji_color = emoji_colors.get(part, random_contrast_color(box_color))
                    draw_text_with_shadow(draw, (current_x, text_y), part, font_icon, emoji_color)
                    if part == "🤖" and i == 4:
                        draw_text_with_shadow(draw, (current_x, text_y - 5), part, font_icon, emoji_color)
                else:
                    if i < 2:
                        draw_text_with_shadow(draw, (current_x, text_y), part, current_font, text_colors[i])
                    else:
                        draw.text((current_x, text_y), part, font=current_font, fill=text_colors[i])
                current_x += width
            current_line_idx += 1

        right_icons = ["🐉", "🐳", "🐲"]
        right_icon = random.choice(right_icons)
        icon_right_x = box_x2 - 225
        icon_right_y = (box_y1 + box_y2 - 180) // 2
        draw_text_with_shadow(draw, (icon_right_x, icon_right_y), right_icon, font_icon_large, emoji_colors.get(right_icon, (80, 80, 80, 255)))

        final_image = Image.alpha_composite(bg_image, overlay)
        final_image = final_image.resize(final_size, Image.Resampling.LANCZOS)
        os.makedirs(os.path.dirname(OUTPUT_IMAGE_PATH), exist_ok=True)
        final_image.save(OUTPUT_IMAGE_PATH, "PNG", quality=95)
        print(f"✅ Ảnh menu đã được lưu: {OUTPUT_IMAGE_PATH}")
        return OUTPUT_IMAGE_PATH

    except Exception as e:
        print(f"❌ Lỗi xử lý ảnh menu: {e}")
        return None

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        name = user_info.zaloName or user_info.displayName or ""
        # Xóa suffix trong ngoặc đơn ở cuối tên: "Nguyễn A (Biệt danh)" → "Nguyễn A"
        name = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
        return name or "Unknown User"
    except Exception:
        return "Unknown User"
    
def tim_kiem_yanhh3d(bot, message_object, author_id, thread_id, thread_type, message_lower, message):
    try:
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            response = (
                f"{get_user_name_by_id(bot, author_id)}\n"
                f"{bot.prefix}donghua [từ khóa]: .\n"
                f"{bot.prefix}donghua bxh: .\n"
                f"💞 Ví dụ: {bot.prefix}donghua tu tutien  ✅\n"
            )
            os.makedirs(CACHE_PATH, exist_ok=True)
    
            image_path = generate_menu_image(bot, author_id, thread_id, thread_type)
            if not image_path:
                bot.sendMessage("❌ Không thể tạo ảnh menu!", thread_id, thread_type)
                return

            reaction = [
                "❌", "🤧", "🐞", "😊", "🔥", "👍", "💖", "🚀",
                "😍", "😂", "😢", "😎", "🙌", "💪", "🌟", "🍀",
                "🎉", "🦁", "🌈", "🍎", "⚡", "🔔", "🎸", "🍕",
                "🏆", "📚", "🦋", "🌍", "⛄", "🎁", "💡", "🐾",
                "😺", "🐶", "🐳", "🦄", "🌸", "🍉", "🍔", "🎄",
                "🎃", "👻", "☃️", "🌴", "🏀", "⚽", "🎾", "🏈",
                "🚗", "✈️", "🚢", "🌙", "☀️", "⭐", "⛅", "☔",
                "⌛", "⏰", "💎", "💸", "📷", "🎥", "🎤", "🎧",
                "🍫", "🍰", "🍩", "☕", "🍵", "🍷", "🍹", "🥐",
                "🐘", "🦒", "🐍", "🦜", "🐢", "🦀", "🐙", "🦈",
                "🍓", "🍋", "🍑", "🥥", "🥐", "🥪", "🍝", "🍣",
                "🎲", "🎯", "🎱", "🎮", "🎰", "🧩", "🧸", "🎡",
                "🏰", "🗽", "🗼", "🏔️", "🏝️", "🏜️", "🌋", "⛲",
                "📱", "💻", "🖥️", "🖨️", "⌨️", "🖱️", "📡", "🔋",
                "🔍", "🔎", "🔑", "🔒", "🔓", "📩", "📬", "📮",
                "💢", "💥", "💫", "💦", "💤", "🚬", "💣", "🔫",
                "🩺", "💉", "🩹", "🧬", "🔬", "🔭", "🧪", "🧫",
                "🧳", "🎒", "👓", "🕶️", "👔", "👗", "👠", "🧢",
                "🦷", "🦴", "👀", "👅", "👄", "👶", "👩", "👨",
                "🚶", "🏃", "💃", "🕺", "🧘", "🏄", "🏊", "🚴",
                "🍄", "🌾", "🌻", "🌵", "🌿", "🍂", "🍁", "🌊",
                "🛠️", "🔧", "🔨", "⚙️", "🪚", "🪓", "🧰", "⚖️",
                "🧲", "🪞", "🪑", "🛋️", "🛏️", "🪟", "🚪", "🧹"
            ]
            
            if random.random() > 0.3:
                bot.sendReaction(message_object, random.choice(reaction), thread_id, thread_type)
            bot.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
            bot.sendLocalImage(
                imagePath=image_path,
                message=Message(text=response, mention=Mention(author_id, length=len(f"{get_user_name_by_id(bot, author_id)}"), offset=0)),
                thread_id=thread_id,
                thread_type=thread_type,
                width=1920,
                height=600,
                ttl=240000
            )
            
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"❌ Lỗi khi xóa ảnh: {e}")
            return

        tu_khoa = parts[1].strip().lower()
        if tu_khoa == "bxh":
            send_bxh(bot, thread_id, thread_type, message_object, author_id)
            return

        url = "https://yanhh3d.vip/ajax/search/suggest"
        params = {"ajaxSearch": "1", "keysearch": tu_khoa}
        headers = {"User-Agent": "Mozilla/5.0"}
        response = session.get(url, params=params, headers=headers)
        data = response.json()
        html_data = data.get("data", "")
        soup = BeautifulSoup(html_data, "html.parser")
        items = soup.find_all("a")

        if not items:
            bot.replyMessage(
                Message(text="❌ Không tìm thấy kết quả nào."),
                message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
            )
            return

        danh_sach = []
        for a_tag in items:
            title = a_tag.get("title")
            ep_span = a_tag.find("span", class_="ep-search")
            so_tap = ep_span.get_text(strip=True) if ep_span else "Không rõ"
            url_phim = a_tag.get('href')
            img_tag = a_tag.find("img")
            avatar_url = img_tag.get("src") if img_tag else ""
            danh_sach.append((title, so_tap, url_phim, avatar_url)) 

        user_selection_data[author_id] = {
            "state": "waiting_for",
            "next_step": "handle_user_selection",
            "danh_sach": danh_sach
        }

        set_timeout(author_id, bot, message_object, thread_id, thread_type)

        danh_sach_text = "\n".join(
            [f"➜ {i}. {title} ({so_tap})" for i, (title, so_tap, _, _) in enumerate(danh_sach, 1)]
        )

        custom_message = (
            f"🚦{get_user_name_by_id(bot, author_id)}\n"
            f"🔎 Danh sách phim hoạt hình 3D '{tu_khoa}' tìm được\n"
            f"🧮 Tổng cộng: {len(danh_sach)} phim\n"
            "🌀 Nguồn: yanhh3d.tv\n\n"
            f"{danh_sach_text}\n"
            "🎯 Mời bạn nhập số tương ứng để chọn phim (30s)\n"
            "🚦 Nhập 0 để hủy chọn"
        )

        anh_path = ve_anh_danh_sach(danh_sach, tu_khoa)
        bot.sendLocalImage(
            imagePath=anh_path,
            thread_id=thread_id,
            thread_type=thread_type,
            message=Message(text=custom_message),
            height=440,
            width=1365,
            ttl=30000
        )
        os.remove(anh_path)

        if message == "0":
            bot.replyMessage(
                Message(text="❌ Bạn đã hủy lựa chọn."),
                message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
            )
            user_selection_data.pop(author_id, None)  
            return

    except Exception as e:
        bot.replyMessage(
            Message(text=f"❌ Đã xảy ra lỗi khi tìm kiếm: {str(e)}"),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
        )

def set_timeout(author_id, bot, message_object, thread_id, thread_type):
    def cancel_selection():
        if author_id in user_selection_data and user_selection_data[author_id]["state"] == "waiting_for":
            del user_selection_data[author_id]
            bot.replyMessage(
                Message(text="⏰ Hết thời gian phản hồi. Vui lòng thử lại từ đầu."),
                message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
            )
    timer = threading.Timer(30.0, cancel_selection)
    timer.start()

def ve_anh_danh_sach(danh_sach, tu_khoa):
    width = 1365
    item_height = 130
    padding = 20
    row_count = (len(danh_sach) + 1) // 2
    height = padding * 2 + row_count * item_height

    bg_path = random.choice([f for f in os.listdir("background") if f.endswith(('.jpg', '.png'))])
    bg_image = Image.open(f"background/" + bg_path).resize((width, height))
    img = ImageEnhance.Brightness(bg_image).enhance(0.3)
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("font/arial unicode ms.otf", 36)
        font_item = ImageFont.truetype("font/arial unicode ms.otf", 28)
        font_small = ImageFont.truetype("font/arial unicode ms.otf", 24)
    except:
        font_title = font_item = font_small = ImageFont.load_default()

    def draw_circle_avatar(pos, avatar_url, size=90):
        try:
            response = requests.get(avatar_url)
            avatar = Image.open(BytesIO(response.content)).resize((size, size)).convert("RGBA")
        except:
            avatar = Image.new("RGBA", (size, size), (255, 255, 255, 255))

        mask = Image.new("L", (size, size), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, size, size), fill=255)

        border = Image.new("RGBA", (size + 10, size + 10), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border)
        border_draw.ellipse((0, 0, size + 10, size + 10), fill=(255, 0, 255, 255))
        border.paste(avatar, (5, 5), mask=mask)
        img.paste(border, pos, mask=border)

    for i, (title, so_tap, url_phim, avatar_url) in enumerate(danh_sach):
        row = i // 2
        col = i % 2
        x = padding + col * (width // 2)
        y = padding + row * item_height

        draw.rounded_rectangle((x, y, x + width // 2 - padding, y + item_height - 10), radius=20, fill=(0, 0, 0, 100))
        draw_circle_avatar((x + 10, y + 10), avatar_url)
        draw.text((x + 110, y + 10), title, font=font_item, fill=(200, 150, 255))
        draw.text((x + 110, y + 50), so_tap, font=font_small, fill=(255, 255, 255))
        draw.text((x + 110, y + 80), "yanhh3d.vip", font=font_small, fill=(200, 200, 200))
        draw.text((x + width // 2 - 60, y + 10), str(i + 1), font=font_item, fill=(180, 180, 180))

    with NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        img.save(tmp.name)
        return tmp.name

def handle_user_selection(bot, message_object, author_id, thread_id, thread_type, message):
    try:
        user_data = user_selection_data.get(author_id)
        if not user_data or user_data.get("next_step") != "handle_user_selection":
            return

        danh_sach = user_data.get('danh_sach', [])

        if message.strip() == "0":
            bot.replyMessage(
                Message(text="❌ Bạn đã hủy lựa chọn."),
                message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
            )
            user_selection_data.pop(author_id, None)
            return

        if not message.isdigit():
            bot.replyMessage(
                Message(text="❌ Vui lòng nhập số hợp lệ tương ứng với phim."),
                message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
            )
            return

        chon = int(message)
        if chon < 1 or chon > len(danh_sach):
            bot.replyMessage(
                Message(text="❌ Lựa chọn không hợp lệ. Vui lòng nhập số trong danh sách."),
                message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
            )
            return

        lua_chon = danh_sach[chon - 1]
        ten_phim, tap, url_phim = lua_chon[:3]

        user_selection_data[author_id] = {
            "state": "waiting_for",
            "next_step": "handle_episode_selection",
            "url_phim": url_phim,
            "ten_phim": ten_phim,
            "tap": tap
        }

        set_timeout(author_id, bot, message_object, thread_id, thread_type)

        bot.replyMessage(
            Message(text=f"🍿 Bạn đã chọn: {ten_phim}\n🔖 Danh sách tập: [{tap}]\n\nVui lòng nhập số tập bạn muốn xem.\n🚦 Nhập 0 để hủy chọn"),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000
        )

    except Exception as e:
        bot.replyMessage(
            Message(text=f"❌ Đã xảy ra lỗi: {str(e)}"),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
        )

def handle_episode_selection(bot, message_object, author_id, thread_id, thread_type, message):
    try:
        user_data = user_selection_data.get(author_id)
        if message == "0":
            bot.replyMessage(
                Message(text="❌ Bạn đã hủy lựa chọn."),
                message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
            )
            user_selection_data.pop(author_id, None) 
            return
       
        try:
            chon_tap = int(message)
            url_phim = user_data["url_phim"]
            ten_phim = user_data["ten_phim"]
            tap= user_data["tap"]
            max_tap = 27
            if chon_tap > max_tap and chon_tap < 1:
                bot.replyMessage(
                    Message(text=f"❌ Tập phim không hợp lệ. Vui lòng chọn lại từ 1 đến {max_tap}."), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                return
            url_tap = f"{url_phim.strip('/')}/tap-{chon_tap}"

            bot.replyMessage(
                Message(text=f"🍿 Bạn đã chọn tập {chon_tap} của phim '{ten_phim}'.\n🎥 URL: {url_tap}"),
                message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
            )

            get_fb_source(bot, url_tap, message_object, thread_id, thread_type)
            user_selection_data.pop(author_id, None)
        except ValueError:
           pass
    except Exception as e:
        bot.replyMessage(
            Message(text=f"❌ Đã xảy ra lỗi: {str(e)}"),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
        )

def get_fb_source(bot, url_tap, message_object, thread_id, thread_type):
    try:
        response = session.get(url_tap)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        og_image = soup.find("meta", property="og:image")
        thumbnail_url = og_image["content"] if og_image else "https://default-thumbnail-url.com/thumbnail.jpg"
        
        scripts = soup.find_all('script')

        for script in scripts:
            script_content = script.string
            if not script_content:
                continue

            checklink_matches = re.findall(r'\$checkLink\d+\s*=\s*"([^"]+)"', script_content)
            for link in checklink_matches:
                if "yanhh3d" in link:
                    process_yanhh3d(bot, link, message_object, thread_id, thread_type, thumbnail_url)
                    return

        bot.replyMessage(
            Message(text="❌ lỗi rồi."),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
        )

    except Exception as e:
        bot.replyMessage(
            Message(text=f"❌ Lỗi khi xử lý: {str(e)}"),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
        )

def process_yanhh3d(bot, url, message_object, thread_id, thread_type, thumbnail_url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(url, headers=headers)
        match = re.search(r'var cccc = "(https://[^"]+\.mp4[^"]*)"', response.text)
        if match:
            video_url = match.group(1)
            download_video(bot, video_url, thumbnail_url, message_object, thread_id, thread_type)
        else:
            pass
    except Exception as e:
        bot.replyMessage(
            Message(text=f"❌ Lỗi khi truy cập link: {str(e)}"),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
        )

def download_video(bot, video_url, thumbnail_url, message_object, thread_id, thread_type):
    try:
        duration = 100
        final_duration = 600 if duration > 600 else duration

        bot.sendRemoteVideo(
            videoUrl=video_url,
            thumbnailUrl=thumbnail_url,  
            duration=final_duration,
            thread_id=thread_id,
            thread_type=thread_type,
            width=1280,
            height=720,
            message=Message(text=""),
            ttl=1000000
        )

    except Exception as e:
        bot.replyMessage(
            Message(text=f"❌ Lỗi khi gửi video: {str(e)}"),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000
        )

def upload_to_uguuu(file_path):
    try:
        print(f"➜   Đang upload file lên GoFile: {file_path}")
        
        with open(file_path, 'rb') as file:
            files = {'file': file}
            response = requests.post("https://store1.gofile.io/uploadFile", files=files)

        print(f"➜   Phản hồi từ GoFile: {response.text}")
        result = response.json()
        
        if result["status"] == "ok":
            uploaded_url = result["data"]["downloadPage"]
            print(f"➜   Upload thành công: {uploaded_url}")
            return uploaded_url
        else:
            print("➜   Upload thất bại:", result.get("message"))
            return None

    except Exception as e:
        print(f"➜   Lỗi khi upload file lên GoFile: {e}")
        return None

def ve_anh_bxh(items):
    width = 1365
    item_height = 130
    padding = 20
    row_count = (len(items) + 1) // 2
    height = padding * 2 + row_count * item_height

    bg_path = random.choice([f for f in os.listdir("background") if f.endswith(('.jpg', '.png'))])
    bg_image = Image.open(f"background/{bg_path}").resize((width, height))
    img = ImageEnhance.Brightness(bg_image).enhance(0.3)
    draw = ImageDraw.Draw(img)

    try:
        font_item = ImageFont.truetype("font/arial unicode ms.otf", 28)
        font_small = ImageFont.truetype("font/arial unicode ms.otf", 24)
    except:
        font_item = font_small = ImageFont.load_default()

    for i, item in enumerate(items):
        rank = item['rank']
        name = item['name']
        episode = item['episode']
        avatar_url = item['avatar_url']

        row = i // 2
        col = i % 2
        x = padding + col * (width // 2)
        y = padding + row * item_height

        draw.rounded_rectangle((x, y, x + width // 2 - padding, y + item_height - 10), radius=20, fill=(0, 0, 0, 100))

        try:
            response = requests.get(avatar_url)
            avatar = Image.open(BytesIO(response.content)).resize((90, 90)).convert("RGBA")
        except:
            avatar = Image.new("RGBA", (90, 90), (255, 255, 255, 255))

        mask = Image.new("L", (90, 90), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, 90, 90), fill=255)

        border = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border)
        border_draw.ellipse((0, 0, 100, 100), fill=(255, 0, 255, 255))
        border.paste(avatar, (5, 5), mask=mask)

        img.paste(border, (x + 10, y + 10), mask=border)
        draw.text((x + 110, y + 10), f"{rank}. {name}", font=font_item, fill=(200, 150, 255))
        draw.text((x + 110, y + 50), episode, font=font_small, fill=(255, 255, 255))
        draw.text((x + width // 2 - 60, y + 10), str(rank), font=font_item, fill=(180, 180, 180))

    with NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        img.save(tmp.name)
        return tmp.name

def send_bxh(bot, thread_id, thread_type, message_object, author_id):
    try:
        url = "https://yanhh3d.vip/moi-cap-nhat"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        ranking_section = soup.select_one("#top-viewed-day")
        items = ranking_section.select("li.item-top") if ranking_section else []
        if not items:
            bot.replyMessage(
                Message(text="❌ Không tìm thấy BXH nào."),
                message_object, thread_id=thread_id, thread_type=thread_type
            )
            return

        bxh_list = []
        for item in items:
            rank = item.select_one(".film-number span").text.strip() if item.select_one(".film-number span") else ""
            name = item.select_one(".film-name a").text.strip() if item.select_one(".film-name a") else ""
            episode = item.select_one(".fd-infor span").text.strip() if item.select_one(".fd-infor span") else ""
            link = item.select_one(".film-name a")["href"] if item.select_one(".film-name a") else ""
            img_tag = item.select_one("img")
            avatar_url = img_tag["data-src"] if img_tag and img_tag.has_attr("data-src") else img_tag["src"] if img_tag and img_tag.has_attr("src") else ""
            
            bxh_list.append({
                'rank': rank,
                'name': name,
                'episode': episode,
                'link': link,
                'avatar_url': avatar_url
            })

        user_name = get_user_name_by_id(bot, author_id)
        text_bxh = f"🚦{user_name}\n🚦Top {len(bxh_list)} bảng xếp hạng phim hoạt hình 3D cập nhật mới nhất\n📅 Vào lúc: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n🌀Nguồn: yanhh3d.vip\n\n"

        for item in bxh_list:
            text_bxh += f"{item['rank']}. {item['name']} ({item['episode']})\n🔗 {item['link']}\n"

        image_path = ve_anh_bxh(bxh_list[:10])
        bot.sendLocalImage(
            imagePath=image_path,
            thread_id=thread_id,
            thread_type=thread_type,
            message=Message(text=text_bxh),
            height=440,
            width=1365,
            ttl=1200000
        )
        os.remove(image_path)

    except Exception as e:
        bot.replyMessage(
            Message(text=f"❌ Lỗi khi lấy BXH: {str(e)}"),
            message_object, thread_id=thread_id, thread_type=thread_type
        )

init(autoreset=True)
colors = [
    "FF9900", "FFFF33", "33FFFF", "FF99FF", "FF3366", 
    "FFFF66", "FF00FF", "66FF99", "00CCFF", "FF0099", 
    "FF0066", "0033FF", "FF9999", "00FF66", "00FFFF", 
    "CCFFFF", "8F00FF", "FF00CC", "FF0000", "FF1100", 
    "FF3300"
]

# Lock để tránh log đè nhau từ nhiều thread
_console_lock = threading.Lock()

def hex_to_ansi(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'\033[38;2;{r};{g};{b}m'

text = "TXABOT"
xb = pyfiglet.figlet_format(text)
print(xb)

# Dynamic Command Handler logic inside txa.py
class DynamicCommandHandler:
    def __init__(self, client):
        self.client = client
        self.commands = {}
        self.load_commands()
        
    def load_commands(self):
        print("\n" + "="*50)
        print("🔍 ĐANG LOAD CÁC MODULES LỆNH DYNAMIC...")
        print("="*50)
        
        try:
            txacommand.load_modules()
            
            # Print load status of each module, one line per module
            for item in txacommand.load_summary:
                if item['status'] == 'SUCCESS':
                    print(f"🟢 [Thành công] {item['module']}")
                else:
                    print(f"🔴 [Thất bại] {item['module']} - Lý do: {item['reason']}")
            
            # Update self.commands with the loaded functions
            for cmd, cmd_info in txacommand.loaded_commands.items():
                self.commands[cmd] = cmd_info['function']
                
            total_super = 0
            total_admin = 0
            total_silver = 0
            total_all = 0
            for cmd, cmd_info in txacommand.loaded_commands.items():
                t_per = cmd_info.get('t-per', 'all')
                if t_per in ['super-admin', 'super']:
                    total_super += 1
                elif t_per == 'admin':
                    total_admin += 1
                elif t_per in ['s-admin', 's-ad']:
                    total_silver += 1
                else:
                    total_all += 1
                    
            def get_display_width(text):
                import unicodedata
                import emoji
                normalized_text = unicodedata.normalize('NFC', text)
                width = 0
                for char in normalized_text:
                    category = unicodedata.category(char)
                    if category.startswith('M'):
                        continue
                    if char in emoji.EMOJI_DATA:
                        width += 2
                    elif unicodedata.east_asian_width(char) in ('W', 'F', 'A'):
                        width += 2
                    elif ord(char) > 0xFFFF:
                        width += 2
                    else:
                        width += 1
                return width

            def pad_to_width(text, target_width):
                curr_width = get_display_width(text)
                padding = target_width - curr_width
                if padding > 0:
                    return text + " " * padding
                return text

            print("="*50)
            print(f"🎉 TỔNG KẾT: Thành công: {txacommand.success_count} | Thất bại: {txacommand.fail_count}")
            print(f"👉 Đã nạp thành công {len(self.commands)} lệnh gọi!")
            print("="*50)
            print(f"📊 THỐNG KÊ PHÂN QUYỀN LỆNH (CHỈ TÍNH LỆNH LOAD THÀNH CÔNG):")
            print(f"┌──────────────────────────────┬─────────────┐")
            print(f"│ Phân loại quyền              │ Số lượng    │")
            print(f"├──────────────────────────────┼─────────────┤")
            print(f"│ {pad_to_width('👑 Super Admin (super)', 28)} │ {pad_to_width(str(total_super), 11)} │")
            print(f"│ {pad_to_width('🛡 Admin Bot (admin)', 28)} │ {pad_to_width(str(total_admin), 11)} │")
            print(f"│ {pad_to_width('🥈 Key Bạc (s-ad)', 28)} │ {pad_to_width(str(total_silver), 11)} │")
            print(f"│ {pad_to_width('👥 Thành viên (all)', 28)} │ {pad_to_width(str(total_all), 11)} │")
            print(f"├──────────────────────────────┼─────────────┤")
            print(f"│ {pad_to_width('🌟 Tổng số lệnh', 28)} │ {pad_to_width(str(len(txacommand.loaded_commands)), 11)} │")
            print(f"└──────────────────────────────┴─────────────┘")
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"❌ Lỗi nghiêm trọng khi load modules: {e}")

    def execute(self, command_name, message_text, message_object, thread_id, thread_type, author_id):
        handler = self.commands.get(command_name)
        if not handler:
            return False
            
        cmd_info = txacommand.loaded_commands.get(command_name)
        if cmd_info:
            t_per = cmd_info.get('t-per', 'all')
            if t_per != 'all':
                settings = read_settings(self.client.uid)
                admin_bot = settings.get("admin_bot", [])
                high_level_admins = settings.get("high_level_admins", [])
                silver_users = settings.get("silver_users", [])
                
                is_super_admin = (author_id == self.client.uid) or (author_id in high_level_admins)
                is_admin_bot = is_super_admin or (author_id in admin_bot)
                is_silver = is_admin_bot or (author_id in silver_users)
                
                if t_per in ['super-admin', 'super']:
                    if not is_super_admin:
                        try:
                            self.client.sendReaction(message_object, "❌", thread_id, thread_type)
                            self.client.replyMessage(
                                Message(text="❌ Bạn không có quyền sử dụng lệnh này (Chỉ dành cho Super Admin Bot). 🤧"),
                                message_object, thread_id, thread_type
                            )
                        except Exception as err:
                            print(f"[DynamicCommandHandler] Lỗi gửi phản hồi quyền: {err}")
                        return True
                elif t_per == 'admin':
                    if not is_admin_bot:
                        try:
                            self.client.sendReaction(message_object, "❌", thread_id, thread_type)
                            self.client.replyMessage(
                                Message(text="❌ Bạn không có quyền sử dụng lệnh này (Chỉ dành cho Admin Bot). 🤧"),
                                message_object, thread_id, thread_type
                            )
                        except Exception as err:
                            print(f"[DynamicCommandHandler] Lỗi gửi phản hồi quyền: {err}")
                        return True
                elif t_per in ['s-admin', 's-ad']:
                    if not is_silver:
                        try:
                            self.client.sendReaction(message_object, "❌", thread_id, thread_type)
                            self.client.replyMessage(
                                Message(text="❌ Bạn không có quyền sử dụng lệnh này (Chỉ dành cho Key Bạc). 🤧"),
                                message_object, thread_id, thread_type
                            )
                        except Exception as err:
                            print(f"[DynamicCommandHandler] Lỗi gửi phản hồi quyền: {err}")
                        return True

        try:
            if random.random() > 0.3:
                self.client.sendReaction(message_object, "⏳", thread_id, thread_type)
            self.client.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
        except Exception as react_err:
            print(f"[DynamicCommandHandler] Lỗi gửi waiting reaction: {react_err}")
            
        try:
            sig = inspect.signature(handler)
            args_map = {
                'self': self.client,
                'client': self.client,
                'bot': self.client,
                'message': message_text,
                'message_text': message_text,
                'message_lower': message_text.lower(),
                'message_object': message_object,
                'thread_id': thread_id,
                'thread_type': thread_type,
                'author_id': author_id
            }
            
            args = []
            for param_name in sig.parameters:
                if param_name in args_map:
                    args.append(args_map[param_name])
                else:
                    args.append(None)
                    
            result = handler(*args)
            
            if result is False:
                try:
                    self.client.sendReaction(message_object, "/-remove", thread_id, thread_type, reactionType=-1)
                except Exception as react_err:
                    print(f"[DynamicCommandHandler] Lỗi xóa reaction: {react_err}")
                return True
                
            if result == "no_reaction":
                return True
                
            try:
                success_reactions = ["👍", "❤️", "😆", "😮", "🎉", "🔥", "🤩", "✅"]
                if random.random() > 0.3:
                    self.client.sendReaction(message_object, random.choice(success_reactions), thread_id, thread_type)
                self.client.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
            except Exception as react_err:
                print(f"[DynamicCommandHandler] Lỗi gửi success reaction: {react_err}")
                
            return True
        except Exception as e:
            print(f"Lỗi khi thực thi lệnh '{command_name}': {e}")
            import traceback
            traceback.print_exc()
            
            try:
                if random.random() > 0.3:
                    self.client.sendReaction(message_object, "❌", thread_id, thread_type)
                self.client.sendReaction(message_object, "TBOT FAILED ❌", thread_id, thread_type)
            except Exception as react_err:
                print(f"[DynamicCommandHandler] Lỗi gửi fail reaction: {react_err}")
                
            try:
                self.client.sendMessage(f"❌ Lỗi khi thực thi lệnh '{command_name}': {e}", thread_id, thread_type)
            except Exception as send_err:
                print(f"[ERROR] couldn't send error message: {send_err}")
            return True

def create_fancy_text_style(segments):
    """
    Tạo text và style JSON cho tin nhắn Zalo với nhiều hiệu ứng.
    segments: list[dict] mỗi dict có 'text' và 'styles' (list các st string).
    """
    full_text = "".join(s["text"] for s in segments)
    style_list = []
    offset = 0
    for seg in segments:
        text = seg["text"]
        length = len(text)
        for st in seg.get("styles", []):
            style_list.append({"start": offset, "len": length, "st": st})
        offset += length
    return full_text, json.dumps({"styles": style_list, "ver": 0})


class bot(ZaloAPI):
    def __init__(self, api_key, secret_key, imei=None, session_cookies=None, prefix='', is_main_bot=None):
        super().__init__(api_key, secret_key, imei, session_cookies)
        self.start_time = time.time()  # Track uptime
        self.is_main_bot = is_main_bot
        self.prefix = prefix
        self.imei = imei
        self.session_cookies = session_cookies
        self.secret_key = secret_key
        self.api_key = api_key
        self.group_info_cache = {}
        self.last_sms_times = {}
        handle_bot_admin(self)
        load_pending_states(self)
        self.Group = False
        self.is_spamming = False
        self.spam_thread = None
        self.spam_lock = threading.Lock()
        self.spam_content = ""
        self.link_removal_enabled = False
        self.banned_word_removal_enabled = False
        self.message_queue = Queue()
        self.worker_thread = threading.Thread
        self.users = {}
        self.promotion_active = False
        self.promotion_discount = 0.5
        self.current_color = "#BBDF32"
        self.current_size = "15"
        self.hidden_accounts = set()
        self.hidden_notifications = {}
        self.data_file = {}
        self.list_group = []
        self.loan_allowed = {}
        self.previous_members = {}
        self.latest_member = {}
        self.last_check_time = {}
        self.pending_login_requests = {}
        self.message_counts = {}
        self.command_usage_count = {}
        self.used_codes = {}
        self.allowed_groups = set()
        self.stop_event = threading.Event()
        self.message_history = {}
        self.last_admin_notify = {}
        self.version ="1.1"
        self.date_update ='07-06-26'
        # Automatically update Zalo profile display name if it's not "TXA Bot"
        try:
            profile = self.fetchAccountInfo().profile
            current_name = profile.get("displayName") or profile.get("zaloName") or "Bot"
            if current_name != "TXA Bot":
                dob = profile.get("dob") or profile.get("sdob") or "2000-01-01"
                gender = profile.get("gender", 0)
                self.changeAccountSetting(name="TXA Bot", dob=dob, gender=gender)
                logging.info(f"Đã đổi tên Zalo từ '{current_name}' sang 'TXA Bot'")
                self.me_name = "TXA Bot"
            else:
                self.me_name = current_name
        except Exception as e:
            logging.error(f"Lỗi khi kiểm tra/đổi tên Zalo: {e}")
            self.me_name = "TXA Bot"
        # Notify after restart
        try:
            if os.path.exists('restart_target.json'):
                with open('restart_target.json', 'r', encoding='utf-8') as f:
                    restart_data = json.load(f)
                target_thread_id = restart_data.get('thread_id')
                target_thread_type_str = restart_data.get('thread_type', '')
                target_thread_type = ThreadType.GROUP if 'GROUP' in target_thread_type_str else ThreadType.USER
                if target_thread_id:
                    restart_msg = "🚀 TXA Bot đã khởi động lại thành công!\n⚡ Hệ thống đã sẵn sàng hoạt động."
                    line1_len = len("🚀 TXA Bot đã khởi động lại thành công!\n")
                    line2_len = len("⚡ Hệ thống đã sẵn sàng hoạt động.")
                    total_len = line1_len + line2_len
                    restart_style = MultiMsgStyle([
                        MessageStyle(style="color", color="00e5ff", offset=0, length=line1_len, auto_format=False),
                        MessageStyle(style="bold", offset=0, length=line1_len, auto_format=False),
                        MessageStyle(style="italic", offset=0, length=line1_len, auto_format=False),
                        MessageStyle(style="color", color="ffd700", offset=line1_len, length=line2_len, auto_format=False),
                        MessageStyle(style="bold", offset=line1_len, length=line2_len, auto_format=False),
                        MessageStyle(style="underline", offset=line1_len, length=line2_len, auto_format=False),
                    ])
                    self.send(Message(text=restart_msg, style=restart_style), target_thread_id, target_thread_type)
                os.remove('restart_target.json')
        except Exception as e:
            print(f"[DEBUG] Restart notify error: {e}")
        self.group_info_cache = {}
        all_group = self.fetchAllGroups()
        allowed_thread_ids = list(all_group.gridVerMap.keys())
        initialize_group_info(self, allowed_thread_ids)
        start_member_check_thread(self,allowed_thread_ids)

        try:
            from modules.bot.func_autosend.main import start_autosend_thread
            autosend_settings = read_settings(self.uid).get("autosend", {})
            if any(autosend_settings.values()):
                start_autosend_thread(self)
        except Exception as e:
            logging.error(f"Lỗi khởi động autosend thread: {e}")
        
        # Khởi động luồng quét hết hạn quyền sử dụng chạy nền
        threading.Thread(target=self.expiry_cleanup_loop, daemon=True).start()
        
        # Load commands handler
        self.command_handler = DynamicCommandHandler(self)

    def sendMessage(self, message, thread_id, thread_type, mark_message=None, ttl=0):
        if isinstance(message, str):
            message = Message(text=message)
        self.log_bot_message(message, thread_id, thread_type)
        result = super().sendMessage(message, thread_id, thread_type, mark_message, ttl)
        self._schedule_ttl_delete(result, thread_id, thread_type, ttl)
        return result

    def replyMessage(self, message, replyMsg, thread_id, thread_type, ttl=0):
        if isinstance(message, str):
            message = Message(text=message)
        self.log_bot_message(message, thread_id, thread_type)
        result = super().replyMessage(message, replyMsg, thread_id, thread_type, ttl)
        self._schedule_ttl_delete(result, thread_id, thread_type, ttl)
        return result

    def send(self, message, thread_id, thread_type=ThreadType.USER, mark_message=None, ttl=0):
        if isinstance(message, str):
            message = Message(text=message)
        self.log_bot_message(message, thread_id, thread_type)
        result = super().send(message, thread_id, thread_type, mark_message, ttl)
        self._schedule_ttl_delete(result, thread_id, thread_type, ttl)
        return result

    def sendReaction(self, messageObject, reactionIcon, thread_id, thread_type, reactionType=75):
        self.log_bot_message(f"🎭 [THẢ CẢM XÚC] {reactionIcon}", thread_id, thread_type)
        return super().sendReaction(messageObject, reactionIcon, thread_id, thread_type, reactionType)

    def sendMultiReaction(self, reactionObj, reactionIcon, thread_id, thread_type, reactionType=75):
        self.log_bot_message(f"🎭 [THẢ CẢM XÚC HÀNG LOẠT] {reactionIcon}", thread_id, thread_type)
        return super().sendMultiReaction(reactionObj, reactionIcon, thread_id, thread_type, reactionType)

    def sendLocalImage(self, imagePath, thread_id, thread_type, width=2560, height=2560, message=None, custom_payload=None, ttl=0):
        msg_text = message.text if isinstance(message, Message) else message or ''
        self.log_bot_message(f"🖼️ [GỬI ẢNH] {msg_text} (Đường dẫn: {imagePath})", thread_id, thread_type)
        result = super().sendLocalImage(imagePath, thread_id, thread_type, width, height, message, custom_payload, ttl)
        self._schedule_ttl_delete(result, thread_id, thread_type, ttl)
        return result

    def sendMultiLocalImage(self, imagePathList, thread_id, thread_type, width=2560, height=2560, message=None, ttl=0):
        msg_text = message.text if isinstance(message, Message) else message or ''
        self.log_bot_message(f"🖼️ [GỬI NHIỀU ẢNH] {msg_text} (Danh sách: {imagePathList})", thread_id, thread_type)
        result = super().sendMultiLocalImage(imagePathList, thread_id, thread_type, width, height, message, ttl)
        self._schedule_ttl_delete(result, thread_id, thread_type, ttl)
        return result

    def sendLocalVideo(self, filePath, thread_id, thread_type, message=None, ttl=0):
        msg_text = message.text if isinstance(message, Message) else message or ''
        self.log_bot_message(f"🎥 [GỬI VIDEO LOCAL] {msg_text} (Đường dẫn: {filePath})", thread_id, thread_type)
        
        if not os.path.exists(filePath):
            raise Exception(f"Video file not found: {filePath}")
            
        # 1. Extract video metadata using ffprobe
        duration = 10000 # default 10s
        width = 1280
        height = 720
        try:
            probe_cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                filePath
            ]
            res = subprocess.run(probe_cmd, capture_output=True, text=True)
            if res.returncode == 0:
                probe_data = json.loads(res.stdout)
                if "format" in probe_data and "duration" in probe_data["format"]:
                    duration = int(float(probe_data["format"]["duration"]) * 1000)
                for stream in probe_data.get("streams", []):
                    if stream.get("codec_type") == "video":
                        width = int(stream.get("width", width))
                        height = int(stream.get("height", height))
                        if "duration" in stream:
                            duration = int(float(stream["duration"]) * 1000)
                        break
        except Exception as probe_err:
            logging.error(f"Error extracting video metadata with ffprobe: {probe_err}")
            
        # 2. Transcode audio stream to AAC for iOS compatibility
        fd_out, temp_out_path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd_out)
        
        transcoded = False
        try:
            cmd = [
                "ffmpeg", "-y",
                "-threads", "0",
                "-i", filePath,
                "-c:v", "copy",
                "-c:a", "aac",
                "-movflags", "+faststart",
                temp_out_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0 and os.path.exists(temp_out_path) and os.path.getsize(temp_out_path) > 0:
                transcoded = True
        except Exception as trans_err:
            logging.error(f"Error transcoding video audio: {trans_err}")
            
        upload_path = temp_out_path if transcoded else filePath
        
        try:
            # 3. Upload to Zalo CDN via photo_original upload endpoint
            file_size = os.path.getsize(upload_path)
            file_name = os.path.basename(filePath)
            
            if thread_type == ThreadType.GROUP:
                url = "https://tt-files-wpa.chat.zalo.me/api/group/photo_original/upload"
                upload_type = 11
                to_key = "grid"
            else:
                url = "https://tt-files-wpa.chat.zalo.me/api/message/photo_original/upload"
                upload_type = 2
                to_key = "toid"
                
            with open(upload_path, "rb") as f:
                files = [("chunkContent", f)]
                params = {
                    "params": self._encode({
                        "totalChunk": 1,
                        "fileName": file_name,
                        "clientId": int(time.time() * 1000),
                        "totalSize": file_size,
                        "imei": self.imei,
                        "isE2EE": 0,
                        "jxl": 0,
                        "chunkId": 1,
                        to_key: str(thread_id)
                    }),
                    "zpw_ver": 685,
                    "zpw_type": 30,
                    "type": upload_type
                }
                
                response = self._post(url, params=params, files=files)
                res_data = response.json()
                if res_data.get("error_code") != 0:
                    raise Exception(f"Upload to Zalo CDN failed: {res_data}")
                    
                decoded = self._decode(res_data["data"])
                if decoded.get("error_code") != 0:
                    raise Exception(f"Decode Zalo CDN upload response failed: {decoded}")
                    
                uploaded_url = decoded["data"]["normalUrl"]
                
            # 4. Send video using Zalo remote video message
            thumbnail_url = "https://f66-zpg-r.zdn.vn/jxl/8107149848477004187/d08a4d364d8cf9d2a09d.jxl"
            
            result = super().sendRemoteVideo(
                videoUrl=uploaded_url,
                thumbnailUrl=thumbnail_url,
                duration=duration,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                message=message,
                ttl=ttl
            )
            self._schedule_ttl_delete(result, thread_id, thread_type, ttl)
            return result
            
        finally:
            try:
                if os.path.exists(temp_out_path):
                    os.remove(temp_out_path)
            except Exception:
                pass

    def sendRemoteVideo(self, videoUrl, thumbnailUrl, duration, thread_id, thread_type, width=1280, height=720, message=None, ttl=0):
        msg_text = message.text if isinstance(message, Message) else message or ''
        self.log_bot_message(f"🎥 [GỬI VIDEO REMOTE] {msg_text}\nURL video: {videoUrl}", thread_id, thread_type)
        
        # Intercept external URLs to upload them to Zalo CDN first for iOS audio compatibility
        if videoUrl.startswith("http") and "zdn.vn" not in videoUrl and "zalo.me" not in videoUrl:
            
            fd, temp_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)
            
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                response = requests.get(videoUrl, headers=headers, stream=True)
                response.raise_for_status()
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                # Send the downloaded local video
                result = self.sendLocalVideo(temp_path, thread_id, thread_type, message, ttl)
                return result
            except Exception as e:
                logging.error(f"Failed to auto-process and send remote video via Zalo CDN: {e}. Falling back to direct URL sending.")
                result = super().sendRemoteVideo(videoUrl, thumbnailUrl, duration, thread_id, thread_type, width, height, message, ttl)
                self._schedule_ttl_delete(result, thread_id, thread_type, ttl)
                return result
            finally:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception:
                    pass
        else:
            result = super().sendRemoteVideo(videoUrl, thumbnailUrl, duration, thread_id, thread_type, width, height, message, ttl)
            self._schedule_ttl_delete(result, thread_id, thread_type, ttl)
            return result


    def sendSticker(self, stickerType, stickerId, cateId, thread_id, thread_type, ttl=0):
        self.log_bot_message(f"✨ [GỬI STICKER] ID: {stickerId}, Cate: {cateId}", thread_id, thread_type)
        result = super().sendSticker(stickerType, stickerId, cateId, thread_id, thread_type, ttl)
        self._schedule_ttl_delete(result, thread_id, thread_type, ttl)
        return result

    def sendLink(self, linkUrl, title, thread_id, thread_type, thumbnailUrl=None, domainUrl=None, desc=None, message=None, ttl=0):
        self.log_bot_message(f"🔗 [GỬI LINK] Tiêu đề: {title}\nURL: {linkUrl}", thread_id, thread_type)
        result = super().sendLink(linkUrl, title, thread_id, thread_type, thumbnailUrl, domainUrl, desc, message, ttl)
        self._schedule_ttl_delete(result, thread_id, thread_type, ttl)
        return result

    def _schedule_ttl_delete(self, result, thread_id, thread_type, ttl):
        try:
            ttl = int(ttl or 0)
        except Exception:
            ttl = 0
        if ttl <= 0:
            return

        targets = self._extract_sent_messages(result)
        if not targets:
            print(f"[TTL] Không lấy được msgId/cliMsgId từ response để tự xóa sau {ttl}ms")
            return

        def delete_target(target):
            msg_id = target.get("msgId")
            cli_msg_id = target.get("cliMsgId")
            owner_id = target.get("ownerId") or target.get("uidFrom") or target.get("senderId") or self.uid
            if not msg_id or not cli_msg_id:
                return
            try:
                if thread_type == ThreadType.GROUP:
                    self.deleteGroupMsg(msg_id, owner_id, cli_msg_id, thread_id)
                else:
                    self.undoMessage(msg_id, cli_msg_id, thread_id, thread_type)
                print(f"[TTL] Đã tự xóa tin nhắn {msg_id} sau {ttl}ms")
            except Exception as e:
                print(f"[TTL] Không thể tự xóa tin nhắn {msg_id}: {e}")

        for target in targets:
            timer = threading.Timer(ttl / 1000.0, delete_target, args=(target,))
            timer.daemon = True
            timer.start()

    def _extract_sent_messages(self, result):
        items = []

        def as_plain(obj):
            if obj is None:
                return None
            if hasattr(obj, "toDict"):
                try:
                    return obj.toDict()
                except Exception:
                    pass
            if isinstance(obj, dict):
                return obj
            if isinstance(obj, (list, tuple)):
                return list(obj)
            if hasattr(obj, "__dict__"):
                return dict(obj.__dict__)
            return None

        def walk(obj):
            plain = as_plain(obj)
            if isinstance(plain, list):
                for item in plain:
                    walk(item)
                return
            if not isinstance(plain, dict):
                return

            msg_id = (
                plain.get("globalMsgId") or plain.get("msgId") or plain.get("msg_id")
                or plain.get("gMsgID") or plain.get("message_id")
            )
            cli_msg_id = (
                plain.get("cliMsgId") or plain.get("cli_msg_id") or plain.get("clientMsgId")
                or plain.get("cMsgID") or plain.get("clientId")
            )
            if msg_id and cli_msg_id:
                items.append({
                    "msgId": str(msg_id),
                    "cliMsgId": str(cli_msg_id),
                    "ownerId": plain.get("ownerId"),
                    "uidFrom": plain.get("uidFrom"),
                    "senderId": plain.get("senderId"),
                })

            for key in plain.keys():
                child = plain[key]
                if isinstance(child, str):
                    try:
                        child = json.loads(child)
                    except Exception:
                        continue
                walk(child)

        walk(result)
        unique = []
        seen = set()
        for item in items:
            key = (item["msgId"], item["cliMsgId"])
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def log_send_success(self, thread_id, thread_type, content_type="unknown", slot=None):
        """Log khi gửi nội dung thành công"""
        try:
            current_time = time.strftime("%H:%M:%S - %d/%m/%Y", time.localtime())
            selected_colors = random.sample(colors, 8)
            
            if slot is None:
                slot = time.strftime("%H:%M")
            
            if thread_type == ThreadType.GROUP:
                try:
                    group_info_log = self.fetchGroupInfo(thread_id)
                    group_name = group_info_log.gridInfoMap.get(thread_id, {}).get('name', 'N/A')
                except Exception:
                    group_name = 'N/A'
                print(f"\n{hex_to_ansi(selected_colors[0])}{Style.BRIGHT}✅ Đã gửi nội dung đến {group_name} ({thread_id}) (type: {content_type}, slot: {slot}){Style.RESET_ALL}")
            else:
                try:
                    user_info_log = self.fetchUserInfo(thread_id)
                    user_name = user_info_log.changed_profiles.get(thread_id, {}).get('zaloName', 'N/A')
                except Exception:
                    user_name = 'N/A'
                print(f"\n{hex_to_ansi(selected_colors[0])}{Style.BRIGHT}✅ Đã gửi nội dung đến {user_name} ({thread_id}) (type: {content_type}, slot: {slot}){Style.RESET_ALL}")
        except Exception as e:
            print(f"[ERROR] Không thể in log gửi thành công: {e}")

    def log_autosend(self, thread_id, thread_type, slot=None):
        """Log khi autosend đúng khung giờ"""
        try:
            if slot is None:
                slot = time.strftime("%H:%M")
            
            selected_colors = random.sample(colors, 8)
            
            if thread_type == ThreadType.GROUP:
                try:
                    group_info_log = self.fetchGroupInfo(thread_id)
                    group_name = group_info_log.gridInfoMap.get(thread_id, {}).get('name', 'N/A')
                except Exception:
                    group_name = 'N/A'
                print(f"\n{hex_to_ansi(selected_colors[0])}{Style.BRIGHT}🕒 Autosend đến đúng khung giờ: {slot} cho nhóm {group_name} ({thread_id}){Style.RESET_ALL}")
            else:
                try:
                    user_info_log = self.fetchUserInfo(thread_id)
                    user_name = user_info_log.changed_profiles.get(thread_id, {}).get('zaloName', 'N/A')
                except Exception:
                    user_name = 'N/A'
                print(f"\n{hex_to_ansi(selected_colors[0])}{Style.BRIGHT}🕒 Autosend đến đúng khung giờ: {slot} cho người dùng {user_name} ({thread_id}){Style.RESET_ALL}")
        except Exception as e:
            print(f"[ERROR] Không thể in log autosend: {e}")

    def log_bot_message(self, message, thread_id, thread_type):
        try:
            message_text = message.text if hasattr(message, 'text') else str(message)
            current_time = time.strftime("%H:%M:%S - %d/%m/%Y", time.localtime())
            selected_colors = random.sample(colors, 8)

            lines = []
            lines.append(f"\n{hex_to_ansi(selected_colors[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
            if thread_type == ThreadType.USER:
                lines.append(f"{hex_to_ansi(selected_colors[1])}{Style.BRIGHT}🔒 BOT GỬI TIN NHẮN RIÊNG TƯ{Style.RESET_ALL}")
            else:
                lines.append(f"{hex_to_ansi(selected_colors[1])}{Style.BRIGHT}💬 BOT GỬI TIN NHẮN NHÓM{Style.RESET_ALL}")
            lines.append(f"{hex_to_ansi(selected_colors[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
            lines.append(f"{hex_to_ansi(selected_colors[1])}{Style.BRIGHT}│- Message: {message_text}{Style.RESET_ALL}")
            if thread_type == ThreadType.GROUP:
                try:
                    group_info_log = self.fetchGroupInfo(thread_id)
                    group_name = group_info_log.gridInfoMap.get(thread_id, {}).get('name', 'N/A')
                except Exception:
                    group_name = 'N/A'
                lines.append(f"{hex_to_ansi(selected_colors[3])}{Style.BRIGHT}│- ID nhóm: {thread_id}{Style.RESET_ALL}")
                lines.append(f"{hex_to_ansi(selected_colors[4])}{Style.BRIGHT}│- Tên nhóm: {group_name}{Style.RESET_ALL}")
                lines.append(f"{hex_to_ansi(selected_colors[5])}{Style.BRIGHT}│- Thời gian: {current_time}{Style.RESET_ALL}")
            else:
                try:
                    user_info_log = self.fetchUserInfo(thread_id)
                    user_name = user_info_log.changed_profiles.get(thread_id, {}).get('zaloName', 'N/A')
                except Exception:
                    user_name = 'N/A'
                lines.append(f"{hex_to_ansi(selected_colors[3])}{Style.BRIGHT}│- Đến người dùng: {thread_id}{Style.RESET_ALL}")
                lines.append(f"{hex_to_ansi(selected_colors[4])}{Style.BRIGHT}│- Tên người dùng: {user_name}{Style.RESET_ALL}")
                lines.append(f"{hex_to_ansi(selected_colors[5])}{Style.BRIGHT}│- Thời gian: {current_time}{Style.RESET_ALL}")
            lines.append(f"{hex_to_ansi(selected_colors[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
            with _console_lock:
                print("\n".join(lines))
        except Exception as e:
            print(f"[ERROR] Không thể in log tin nhắn bot: {e}")

    def expiry_cleanup_loop(self):
        while not self.stop_event.is_set():
            try:
                settings = read_settings(self.uid)
                current_time = time.time()
                modified = False
                
                # 1. Quét hết hạn approved_users
                approved_users = settings.get("approved_users", [])
                approved_expiry = settings.get("approved_users_expiry", {})
                
                uids_to_remove = []
                for uid, expiry in list(approved_expiry.items()):
                    if expiry is not None and current_time >= expiry:
                        uids_to_remove.append(uid)
                
                for uid in uids_to_remove:
                    if uid in approved_users:
                        approved_users.remove(uid)
                    approved_expiry.pop(uid, None)
                    modified = True
                    try:
                        inbox_text = "⚠️ Quyền sử dụng TXA Bot của bạn đã hết hạn. Vui lòng liên hệ Admin để gia hạn! 🌸"
                        self.send(Message(text=inbox_text), thread_id=uid, thread_type=ThreadType.USER)
                        print(f"🤖 [Hết hạn] Đã thu hồi quyền sử dụng Bot chung của UID {uid} do hết thời hạn.")
                    except Exception as e:
                        print(f"[ERROR] Không thể inbox báo hết hạn cho {uid}: {e}")
                
                # 2. Quét hết hạn image_approved_users
                image_approved = settings.get("image_approved_users", [])
                image_expiry = settings.get("image_approved_users_expiry", {})
                
                img_uids_to_remove = []
                for uid, expiry in list(image_expiry.items()):
                    if expiry is not None and current_time >= expiry:
                        img_uids_to_remove.append(uid)
                        
                for uid in img_uids_to_remove:
                    if uid in image_approved:
                        image_approved.remove(uid)
                    image_expiry.pop(uid, None)
                    modified = True
                    try:
                        inbox_text = "⚠️ Quyền sử dụng các lệnh kho ảnh của bạn trên TXA Bot đã hết hạn."
                        self.send(Message(text=inbox_text), thread_id=uid, thread_type=ThreadType.USER)
                        print(f"🤖 [Hết hạn] Đã thu hồi quyền sử dụng Kho ảnh của UID {uid} do hết thời hạn.")
                    except Exception as e:
                        print(f"[ERROR] Không thể inbox báo hết hạn kho ảnh cho {uid}: {e}")
                
                # 3. Quét hết hạn nude_approved_users
                nude_approved = settings.get("nude_approved_users", [])
                nude_expiry = settings.get("nude_approved_users_expiry", {})
                
                nude_uids_to_remove = []
                for uid, expiry in list(nude_expiry.items()):
                    if expiry is not None and current_time >= expiry:
                        nude_uids_to_remove.append(uid)
                        
                for uid in nude_uids_to_remove:
                    if uid in nude_approved:
                        nude_approved.remove(uid)
                    nude_expiry.pop(uid, None)
                    modified = True
                    try:
                        inbox_text = "⚠️ Quyền sử dụng các lệnh ảnh nude/nhạy cảm (girlnude, girllon) của bạn trên TXA Bot đã hết hạn."
                        self.send(Message(text=inbox_text), thread_id=uid, thread_type=ThreadType.USER)
                        print(f"🤖 [Hết hạn] Đã thu hồi quyền sử dụng lệnh Nude của UID {uid} do hết thời hạn.")
                    except Exception as e:
                        print(f"[ERROR] Không thể inbox báo hết hạn lệnh Nude cho {uid}: {e}")
                
                # 4. Quét hết hạn silver_users
                silver_users = settings.get("silver_users", [])
                silver_expiry = settings.get("silver_users_expiry", {})
                
                silver_uids_to_remove = []
                for uid, expiry in list(silver_expiry.items()):
                    if expiry is not None and current_time >= expiry:
                        silver_uids_to_remove.append(uid)
                        
                for uid in silver_uids_to_remove:
                    if uid in silver_users:
                        silver_users.remove(uid)
                    silver_expiry.pop(uid, None)
                    modified = True
                    try:
                        inbox_text = "⚠️ Quyền Key Bạc của bạn trên TXA Bot đã hết hạn."
                        self.send(Message(text=inbox_text), thread_id=uid, thread_type=ThreadType.USER)
                        print(f"🤖 [Hết hạn] Đã thu hồi quyền Key Bạc của UID {uid} do hết thời hạn.")
                    except Exception as e:
                        print(f"[ERROR] Không thể inbox báo hết hạn Key Bạc cho {uid}: {e}")
                
                if modified:
                    settings["approved_users"] = approved_users
                    settings["approved_users_expiry"] = approved_expiry
                    settings["image_approved_users"] = image_approved
                    settings["image_approved_users_expiry"] = image_expiry
                    settings["nude_approved_users"] = nude_approved
                    settings["nude_approved_users_expiry"] = nude_expiry
                    settings["silver_users"] = silver_users
                    settings["silver_users_expiry"] = silver_expiry
                    write_settings(self.uid, settings)
                    
            except Exception as e:
                print(f"[ERROR] Lỗi trong loop quét hết hạn quyền: {e}")
            
            time.sleep(5)

    def onEvent(self, event_data, event_type):
        try:
            handle_event(self, event_data, event_type)
        except Exception as e:
            logger.error(f"🚦 Lỗi khi xử lý sự kiện: {e}")

    def handle_delete_msg(self, message_object, author_id, thread_id, thread_type, message_text):
        try:
            settings = read_settings(self.uid)
            admin_bot = settings.get("admin_bot", [])
            
            is_bot_adm = author_id in admin_bot
            is_grp_adm = False
            if thread_type == ThreadType.GROUP:
                is_grp_adm = is_group_admin_or_creator(self, author_id, thread_id)
                
            if not (is_bot_adm or is_grp_adm):
                err_msg = self.replyMessage(Message(text="❌ Bạn không có quyền sử dụng lệnh xóa tin nhắn!"), message_object, thread_id, thread_type)
                def delay_cleanup():
                    time.sleep(5)
                    try:
                        self.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
                    except:
                        pass
                    try:
                        self.deleteGroupMsg(err_msg.get('msgId'), self.uid, err_msg.get('cliMsgId'), thread_id)
                    except:
                        pass
                threading.Thread(target=delay_cleanup, daemon=True).start()
                return

            deleted_any = False
            if message_object.quote:
                q = message_object.quote
                try:
                    self.deleteGroupMsg(q.globalMsgId, q.ownerId, q.cliMsgId, thread_id)
                    deleted_any = True
                except Exception as e:
                    print(f"[ERROR] deleteGroupMsg quote error: {e}")
                    
            elif message_object.mentions:
                # Format: !del @name [number]
                # Count means delete that many recent messages from the mentioned user.
                parts = message_text.split()
                num_to_delete = 1  # Default: delete 1 message
                for p in parts:
                    try:
                        n = int(p)
                        if 1 <= n <= 100:
                            num_to_delete = n
                            break
                    except ValueError:
                        continue
                
                recent_messages = []
                try:
                    group_data = self.getRecentGroup(thread_id)
                    if hasattr(group_data, "groupMsgs"):
                        recent_messages = group_data.groupMsgs or []
                    elif isinstance(group_data, dict):
                        recent_messages = group_data.get("groupMsgs", []) or []
                except Exception as e:
                    print(f"[ERROR] getRecentGroup delete mention error: {e}")

                for mention in message_object.mentions:
                    target_uid = mention.get('uid')
                    if not target_uid:
                        continue

                    msgs_to_delete = []
                    target_uid_str = str(target_uid)

                    for m in reversed(recent_messages):
                        msg_id = str(m.get('msgId', ''))
                        uid_from = str(m.get('uidFrom', ''))
                        if msg_id == str(message_object.msgId):
                            continue
                        if uid_from == target_uid_str:
                            msgs_to_delete.append({
                                "msgId": m.get('msgId'),
                                "cliMsgId": m.get('cliMsgId'),
                                "author_id": target_uid_str
                            })
                            if len(msgs_to_delete) >= num_to_delete:
                                break

                    if len(msgs_to_delete) < num_to_delete:
                        history = self.message_history.get(thread_id, [])
                        known_ids = {str(m.get('msgId', '')) for m in msgs_to_delete}
                        for m in reversed(history):
                            msg_id = str(m.get('msgId', ''))
                            if msg_id == str(message_object.msgId) or msg_id in known_ids:
                                continue
                            if str(m.get('author_id', '')) == target_uid_str:
                                msgs_to_delete.append(m)
                                known_ids.add(msg_id)
                                if len(msgs_to_delete) >= num_to_delete:
                                    break

                    for found_msg in msgs_to_delete:
                        try:
                            self.deleteGroupMsg(found_msg['msgId'], found_msg['author_id'], found_msg['cliMsgId'], thread_id)
                            deleted_any = True
                        except Exception as e:
                            print(f"[ERROR] deleteGroupMsg mention error: {e}")
            
            else:
                recent_messages = []
                if thread_type == ThreadType.GROUP:
                    try:
                        group_data = self.getRecentGroup(thread_id)
                        if hasattr(group_data, "groupMsgs"):
                            recent_messages = group_data.groupMsgs or []
                        elif isinstance(group_data, dict):
                            recent_messages = group_data.get("groupMsgs", []) or []
                    except Exception as e:
                        print(f"[ERROR] getRecentGroup error in last message deletion: {e}")
                
                found_msg = None
                for m in reversed(recent_messages):
                    msg_id = str(m.get('msgId', ''))
                    if msg_id == str(message_object.msgId):
                        continue
                    found_msg = {
                        "msgId": m.get('msgId'),
                        "cliMsgId": m.get('cliMsgId'),
                        "author_id": str(m.get('uidFrom', ''))
                    }
                    break
                
                if not found_msg:
                    history = self.message_history.get(thread_id, [])
                    for m in reversed(history):
                        if str(m['msgId']) == str(message_object.msgId):
                            continue
                        found_msg = m
                        break
                
                if found_msg:
                    try:
                        self.deleteGroupMsg(found_msg['msgId'], found_msg['author_id'], found_msg['cliMsgId'], thread_id)
                        deleted_any = True
                        try:
                            history = self.message_history.get(thread_id, [])
                            for m in history:
                                if str(m.get('msgId')) == str(found_msg['msgId']):
                                    history.remove(m)
                                    break
                        except:
                            pass
                    except Exception as e:
                        print(f"[ERROR] deleteGroupMsg last message error: {e}")

            try:
                self.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
            except Exception as e:
                print(f"[ERROR] delete cmd msg error: {e}")
                
            if not deleted_any and thread_type == ThreadType.GROUP:
                warn = self.replyMessage(Message(text="⚠️ Không tìm thấy tin nhắn gần đây để xóa hoặc Bot không có quyền xóa!"), message_object, thread_id, thread_type)
                def delay_cleanup_warn():
                    time.sleep(5)
                    try:
                        self.deleteGroupMsg(warn.get('msgId'), self.uid, warn.get('cliMsgId'), thread_id)
                    except:
                        pass
                threading.Thread(target=delay_cleanup_warn, daemon=True).start()

        except Exception as e:
            print(f"[ERROR] handle_delete_msg general error: {e}")

    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        try:
            # Check if this is a reaction event
            if isinstance(message, dict) and "rIcon" in message:
                try:
                    r_icon = message.get("rIcon", "")
                    r_author_name = get_user_name_by_id(self, author_id)
                    r_time = time.strftime("%H:%M:%S - %d/%m/%Y", time.localtime())
                    r_colors = random.sample(colors, 8)

                    r_lines = []
                    r_lines.append(f"\n{hex_to_ansi(r_colors[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
                    if thread_type == ThreadType.USER:
                        r_lines.append(f"{hex_to_ansi(r_colors[1])}{Style.BRIGHT}🎭 PHẢN ỨNG TIN NHẮN RIÊNG TƯ (PRIVATE REACTION){Style.RESET_ALL}")
                    else:
                        r_lines.append(f"{hex_to_ansi(r_colors[1])}{Style.BRIGHT}🎭 PHẢN ỨNG TIN NHẮN NHÓM (GROUP REACTION){Style.RESET_ALL}")
                    r_lines.append(f"{hex_to_ansi(r_colors[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
                    r_lines.append(f"{hex_to_ansi(r_colors[2])}{Style.BRIGHT}│- Biểu tượng: {r_icon}{Style.RESET_ALL}")
                    r_lines.append(f"{hex_to_ansi(r_colors[3])}{Style.BRIGHT}│- ID người phản ứng: {author_id}{Style.RESET_ALL}")
                    r_lines.append(f"{hex_to_ansi(r_colors[6])}{Style.BRIGHT}│- Tên người phản ứng: {r_author_name}{Style.RESET_ALL}")
                    if thread_type == ThreadType.GROUP:
                        try:
                            g_info = self.fetchGroupInfo(thread_id)
                            g_name = g_info.gridInfoMap.get(thread_id, {}).get('name', 'N/A')
                        except:
                            g_name = 'N/A'
                        r_lines.append(f"{hex_to_ansi(r_colors[4])}{Style.BRIGHT}│- Tên nhóm: {g_name} ({thread_id}){Style.RESET_ALL}")
                    r_lines.append(f"{hex_to_ansi(r_colors[5])}{Style.BRIGHT}│- Thời gian: {r_time}{Style.RESET_ALL}")
                    r_lines.append(f"{hex_to_ansi(r_colors[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
                    with _console_lock:
                        print("\n".join(r_lines))
                except Exception as log_err:
                    print(f"[ERROR] Lỗi khi in log phản ứng: {log_err}")
                return

            settings = read_settings(self.uid)
            allowed_thread_ids = settings.get('allowed_thread_ids', [])
            admin_bot = settings.get("admin_bot", [])
            approved_users = settings.get("approved_users", [])
            banned_users = settings.get("banned_users", [])
            chat_user = (thread_type == ThreadType.USER)
            is_main_bot = self.is_main_bot
            prefix = self.prefix
            allowed_thread_ids = get_allowed_thread_ids(self)

            # DEBUG TIKTOK
            try:
                msg_str = str(message)
                msg_obj_str = str(message_object)
                if "tiktok" in msg_str.lower() or "tiktok" in msg_obj_str.lower():
                    with open("debug_tiktok.txt", "a", encoding="utf-8") as f:
                        f.write(f"\n=== TIKTOK MSG AT {time.strftime('%H:%M:%S - %d/%m/%Y')} ===\n")
                        f.write(f"Type of message: {type(message)}\n")
                        f.write(f"message content representation: {msg_str}\n")
                        f.write(f"message content keys/dict: {getattr(message, '__dict__', None) if hasattr(message, '__dict__') else message}\n")
                        f.write(f"message_object representation: {msg_obj_str}\n")
                        f.write(f"message_object keys/dict: {getattr(message_object, '__dict__', None) if hasattr(message_object, '__dict__') else message_object}\n")
                        f.write(f"================================================\n")
            except Exception as debug_err:
                print(f"[DEBUG] Error writing debug_tiktok.txt: {debug_err}")

            # Use get_content_message from core.bot_sys to get proper text content
            message_text = get_content_message(message_object)

            # Clean leading mentions (like @name) and whitespace
            message_text = re.sub(r'^@[\S]+[\s]*', '', message_text).lstrip()
            message_lower = message_text.lower()

            # Call all loaded listeners (auto hooks)
            try:
                for listener_data in txacommand.loaded_listeners:
                    listener_fn = listener_data.get('function')
                    if callable(listener_fn):
                        try:
                            listener_fn(self, message_object, author_id, thread_id, thread_type, message_text)
                        except Exception as listener_err:
                            print(f"[ERROR] Listener {listener_data.get('name')} ({listener_data.get('module_path')} error: {listener_err}")
            except Exception as e:
                print(f"[ERROR] Error calling listeners: {e}")

            if author_id in banned_users:
                return

            if author_id == self.uid:
                # log_bot_message trong sendMessage/replyMessage/send đã in rồi → bỏ qua
                if not message_text.startswith(prefix):
                    return



            if thread_id not in self.message_history:
                self.message_history[thread_id] = []
            self.message_history[thread_id].append({
                "msgId": message_object.msgId,
                "cliMsgId": message_object.cliMsgId,
                "author_id": author_id,
                "text": message_text,
                "msgType": getattr(message_object, "msgType", "webchat")
            })
            if len(self.message_history[thread_id]) > 100:
                self.message_history[thread_id].pop(0)

            is_delete_command = False
            for kw in ["!del", "!xoa", "!delete", ".del", ".xoa", ".delete"]:
                if kw in message_lower.split():
                    is_delete_command = True
                    break
            
            if is_delete_command:
                self.handle_delete_msg(message_object, author_id, thread_id, thread_type, message_text)
                return

            # Check if currently muted
            muted_users = settings.get('muted_users', [])
            current_time = int(time.time())
            is_muted = False
            for muted_user in muted_users:
                if muted_user['author_id'] == author_id and muted_user['thread_id'] == thread_id:
                    if muted_user['muted_until'] == float('inf') or current_time < muted_user['muted_until']:
                        is_muted = True
                        break
            
            if is_muted:
                safe_delete_message(self, message_object, author_id, thread_id)
                return

            if thread_type == ThreadType.GROUP and not is_admin(self, author_id):
                handle_check_profanity(self, author_id, thread_id, message_object, thread_type, message)

            is_bot_on_cmd = (
                message_lower.startswith(f"{prefix}bot on") or 
                message_lower.startswith(f"{prefix}group on")
            )
            
            silver_users = settings.get("silver_users", [])
            is_user_approved = (author_id in admin_bot or author_id in approved_users or author_id in silver_users)
            
            if thread_type == ThreadType.GROUP:
                is_allowed = (
                    (thread_id in allowed_thread_ids and is_user_approved) or 
                    (is_bot_on_cmd and (author_id in admin_bot or is_group_admin_or_creator(self, author_id, thread_id)))
                )
            else:
                is_allowed = is_user_approved

            # Add friendly reply when bot is mentioned but not a command (DISABLED)
            # has_mention = (message_object.mentions and len(message_object.mentions) > 0) or (message_text and '@' in message_text)
            # if has_mention and not message_text.startswith(prefix) and is_allowed:
            #     try:
            #         user_name = get_user_name_by_id(self, author_id)
            #         replies = [
            #             f"Xin chào {user_name}! 🌸 Tôi là {self.me_name}!\nGõ {prefix}help để xem danh sách lệnh nhé!",
            #             f"Chào {user_name}! 😊 Có gì tôi có thể giúp bạn? Gõ {prefix}help để biết thêm!",
            #             f"Hi {user_name}! 🚗 Bạn cần giúp gì? Gõ {prefix}help để xem danh sách lệnh!"
            #         ]
            #         reply_text = random.choice(replies)
            #         self.replyMessage(Message(text=reply_text), message_object, thread_id, thread_type)
            #     except Exception as e:
            #         print(f"[ERROR] Error sending mention reply: {e}")
            #     return

            if not is_allowed:
                if message_text.startswith(prefix):
                    admin_names = []
                    for aid in admin_bot:
                        admin_names.append(f"Admin (ID: {aid})")
                    admin_info = ", ".join(admin_names) if admin_names else "Admin BOT"
                    
                    if thread_type == ThreadType.USER:
                        warning_text = (
                            f"⚠️ Bạn chưa được phép sử dụng BOT trong tin nhắn riêng tư!\n"
                            f"➜ Vui lòng liên hệ {admin_info} để được duyệt. 🌸\n"
                            f"💡 (Hiện tại đang miễn phí trải nghiệm, sau này sẽ có tính phí dịch vụ nhé! 🌸)"
                        )
                    else:
                        if thread_id not in allowed_thread_ids:
                            warning_text = (
                                f"⚠️ Nhóm này chưa được kích hoạt sử dụng BOT!\n"
                                f"➜ Vui lòng liên hệ {admin_info} để được mở quyền sử dụng. 🌸\n"
                                f"💡 (Hiện tại đang miễn phí trải nghiệm, sau này sẽ có tính phí dịch vụ nhé! 🌸)"
                            )
                        else:
                            warning_text = (
                                f"⚠️ Bạn chưa được phép sử dụng BOT!\n"
                                f"➜ Vui lòng liên hệ {admin_info} để được duyệt quyền sử dụng. 🌸\n"
                                f"💡 (Hiện tại đang miễn phí trải nghiệm, sau này sẽ có tính phí dịch vụ nhé! 🌸)"
                            )
                    warning_msg = self.replyMessage(Message(text=warning_text), message_object, thread_id, thread_type)
                    
                    if thread_type == ThreadType.GROUP:
                        try:
                            w_msg_id = None
                            w_cli_msg_id = None
                            if warning_msg:
                                if isinstance(warning_msg, dict):
                                    w_msg_id = warning_msg.get('msgId') or warning_msg.get('messageId') or warning_msg.get('msg_id')
                                    w_cli_msg_id = warning_msg.get('cliMsgId') or warning_msg.get('clientMsgId') or warning_msg.get('cli_msg_id')
                                else:
                                    w_msg_id = getattr(warning_msg, 'msgId', None) or getattr(warning_msg, 'messageId', None) or getattr(warning_msg, 'msg_id', None)
                                    w_cli_msg_id = getattr(warning_msg, 'cliMsgId', None) or getattr(warning_msg, 'clientMsgId', None) or getattr(warning_msg, 'cli_msg_id', None)
                                    if not w_msg_id and hasattr(warning_msg, 'get'):
                                        w_msg_id = warning_msg.get('msgId') or warning_msg.get('messageId')
                                    if not w_cli_msg_id and hasattr(warning_msg, 'get'):
                                        w_cli_msg_id = warning_msg.get('cliMsgId') or warning_msg.get('clientMsgId')
                            
                            u_msg_id = message_object.msgId if hasattr(message_object, 'msgId') else message_object.get('msgId') if isinstance(message_object, dict) else None
                            u_cli_msg_id = message_object.cliMsgId if hasattr(message_object, 'cliMsgId') else message_object.get('cliMsgId') if isinstance(message_object, dict) else None
                            
                            if w_msg_id and w_cli_msg_id and u_msg_id and u_cli_msg_id:
                                settings = read_settings(self.uid)
                                pending_cleanups = settings.setdefault("pending_cleanups", {})
                                # Đảm bảo key lưu là string
                                author_key = str(author_id)
                                user_cleanups = pending_cleanups.setdefault(author_key, [])
                                user_cleanups.append({
                                    "thread_id": thread_id,
                                    "user_msg_id": u_msg_id,
                                    "user_cli_msg_id": u_cli_msg_id,
                                    "warning_msg_id": w_msg_id,
                                    "warning_cli_msg_id": w_cli_msg_id
                                })
                                settings["pending_cleanups"] = pending_cleanups
                                write_settings(self.uid, settings)
                        except Exception as e:
                            print(f"[ERROR] Không thể lưu tin nhắn chờ dọn dẹp: {e}")
                    
                    # Gửi tin nhắn riêng (Inbox) báo cho Admin biết có người muốn dùng bot
                    if author_id != self.uid and author_id not in admin_bot:
                        current_time_sec = time.time()
                        last_notify = self.last_admin_notify.setdefault((author_id, 'bot'), 0)
                        if current_time_sec - last_notify >= 300: # 5 phút cooldown
                            try:
                                req_name = get_user_name_by_id(self, author_id)
                                context = "tin nhắn riêng tư"
                                if thread_type == ThreadType.GROUP:
                                    try:
                                        g_info = self.fetchGroupInfo(thread_id)
                                        context = f"nhóm '{g_info.gridInfoMap.get(thread_id, {}).get('name', 'N/A')}'"
                                    except:
                                        context = "nhóm chat"
                                
                                if not os.path.exists("cache"):
                                    os.makedirs("cache")
                                pending_file = "cache/pending_bot_approvals.txt"
                                pending_uids = []
                                if os.path.exists(pending_file):
                                    with open(pending_file, "r", encoding="utf-8") as f:
                                        pending_uids = [line.strip() for line in f if line.strip()]
                                
                                if str(author_id) not in pending_uids:
                                    pending_uids.append(str(author_id))
                                    with open(pending_file, "w", encoding="utf-8") as f:
                                        for p_uid in pending_uids:
                                            f.write(f"{p_uid}\n")
                                
                                for p_uid in pending_uids:
                                    if p_uid not in PENDING_BOT_STATE:
                                        PENDING_BOT_STATE.append(p_uid)
                                if str(author_id) not in PENDING_BOT_STATE:
                                    PENDING_BOT_STATE.append(str(author_id))
                                
                                if len(PENDING_BOT_STATE) >= 2:
                                    img_path = generate_pending_approvals_image("⏳ DANH SÁCH CHỜ DUYỆT BOT", PENDING_BOT_STATE, self)
                                    if img_path and os.path.exists(img_path):
                                        with Image.open(img_path) as img:
                                            w, h = img.size
                                        for admin_id in admin_bot:
                                            if admin_id != self.uid:
                                                self.sendLocalImage(
                                                    imagePath=img_path,
                                                    thread_id=admin_id,
                                                    thread_type=ThreadType.USER,
                                                    width=w,
                                                    height=h,
                                                    message=Message(text=f"🔔 Có {len(pending_uids)} yêu cầu duyệt dùng bot đang chờ!\n💡 Gõ `{prefix}bot approved add yes` để duyệt tất cả.")
                                                )
                                        os.remove(img_path)
                                    else:
                                        notify_text = f"🔔 [DANH SÁCH DUYỆT BOT ĐANG CHỜ]\n"
                                        for p_uid in pending_uids:
                                            notify_text += f"➜ {get_user_name_by_id(self, p_uid)} ({p_uid})\n"
                                        notify_text += f"💡 Gõ `{prefix}bot approved add yes` để duyệt tất cả."
                                        for admin_id in admin_bot:
                                            if admin_id != self.uid:
                                                self.send(Message(text=notify_text), thread_id=admin_id, thread_type=ThreadType.USER)
                                else:
                                    notify_text = (
                                        f"🔔 [YÊU CẦU DUYỆT BOT]\n"
                                        f"➜ Người dùng: {req_name}\n"
                                        f"➜ UID: {author_id}\n"
                                        f"➜ Muốn sử dụng BOT tại: {context}\n"
                                        f"➜ Lệnh đã gõ: {message_text}\n"
                                        f"💡 Gõ `{prefix}bot approved add {author_id}` để duyệt quyền."
                                    )
                                    for admin_id in admin_bot:
                                        if admin_id != self.uid:
                                            self.send(Message(text=notify_text), thread_id=admin_id, thread_type=ThreadType.USER)
                                self.last_admin_notify[(author_id, 'bot')] = current_time_sec
                            except Exception as e:
                                print(f"[ERROR] Không thể gửi thông báo yêu cầu duyệt bot cho Admin: {e}")

            # Nhóm chưa kích hoạt: tắt log cho user thường, chỉ giữ log nếu Admin BOT nhắn.
            if not is_allowed and thread_type == ThreadType.GROUP and author_id != self.uid:
                if author_id not in admin_bot:
                    return

                try:
                    _author_info = self.fetchUserInfo(author_id).changed_profiles.get(author_id, {})
                    _author_name = _author_info.get('zaloName', 'N/A')
                    _group_name = 'N/A'
                    try:
                        _g = self.fetchGroupInfo(thread_id)
                        _group_name = _g.gridInfoMap.get(thread_id, {}).get('name', 'N/A')
                    except Exception:
                        pass
                    _t = time.strftime("%H:%M:%S - %d/%m/%Y", time.localtime())
                    _c = random.sample(colors, 8)
                    lines = [
                        f"{hex_to_ansi(_c[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}",
                        f"{hex_to_ansi(_c[1])}{Style.BRIGHT}💬 TIN NHẮN NHÓM (GROUP MESSAGE) - ADMIN BOT / NHÓM CHƯA KÍCH HOẠT{Style.RESET_ALL}",
                        f"{hex_to_ansi(_c[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}",
                        f"{hex_to_ansi(_c[1])}{Style.BRIGHT}│- Message: {message_text}{Style.RESET_ALL}",
                        f"{hex_to_ansi(_c[2])}{Style.BRIGHT}│- ID NGƯỜI DÙNG: {author_id} (ADMIN BOT){Style.RESET_ALL}",
                        f"{hex_to_ansi(_c[6])}{Style.BRIGHT}│- TÊN NGƯỜI DÙNG: {_author_name}{Style.RESET_ALL}",
                        f"{hex_to_ansi(_c[3])}{Style.BRIGHT}│- ID NHÓM: {thread_id}{Style.RESET_ALL}",
                        f"{hex_to_ansi(_c[4])}{Style.BRIGHT}│- TÊN NHÓM: {_group_name}{Style.RESET_ALL}",
                        f"{hex_to_ansi(_c[5])}{Style.BRIGHT}│- TRẠNG THÁI NHÓM: ❌ CHƯA KÍCH HOẠT (vẫn log vì người gửi là Admin BOT){Style.RESET_ALL}",
                        f"{hex_to_ansi(_c[7])}{Style.BRIGHT}│- THỜI GIAN NHẬN ĐƯỢC: {_t}{Style.RESET_ALL}",
                        f"{hex_to_ansi(_c[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}"
                    ]
                    with _console_lock:
                        print("\n".join(lines))
                except Exception:
                    pass
                return

            # handle_check_profanity đã được di chuyển lên trước để chạy độc lập với bot on/off
            
            author_info = self.fetchUserInfo(author_id).changed_profiles.get(author_id, {})
            author_name = author_info.get('zaloName', 'đéo xác định')
            current_time = time.strftime("%H:%M:%S - %d/%m/%Y", time.localtime())
            colors_selected = random.sample(colors, 8)
            
            # Beautiful logging for private messages
            if author_id != self.uid:
                if thread_type == ThreadType.USER:
                    lines = [
                        f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[1])}{Style.BRIGHT}🔒 TIN NHẮN RIÊNG TƯ (PRIVATE MESSAGE){Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[2])}{Style.BRIGHT}│- Message: {message_text}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[3])}{Style.BRIGHT}│- ID NGƯỜI DÙNG: {author_id}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[6])}{Style.BRIGHT}│- TÊN NGƯỜI DÙNG: {author_name}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[4])}{Style.BRIGHT}│- TRẠNG THÁI: {'✅ ĐƯỢC PHÉP' if (author_id in admin_bot or author_id in approved_users) else '❌ KHÔNG ĐƯỢC PHÉP'}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[7])}{Style.BRIGHT}│- THỜI GIAN: {current_time}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}"
                    ]
                    with _console_lock:
                        print("\n".join(lines))
                else:
                    try:
                        group_info_log = self.fetchGroupInfo(thread_id)
                        group_name = group_info_log.gridInfoMap.get(thread_id, {}).get('name', 'N/A')
                    except Exception:
                        group_name = 'N/A'
                    is_allowed_status = thread_id in allowed_thread_ids
                    lines = [
                        f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[1])}{Style.BRIGHT}💬 TIN NHẮN NHÓM (GROUP MESSAGE){Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[1])}{Style.BRIGHT}│- Message: {message_text}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[2])}{Style.BRIGHT}│- ID NGƯỜI DÙNG: {author_id}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[6])}{Style.BRIGHT}│- TÊN NGƯỜI DÙNG: {author_name}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[3])}{Style.BRIGHT}│- ID NHÓM: {thread_id}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[4])}{Style.BRIGHT}│- TÊN NHÓM: {group_name}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[5])}{Style.BRIGHT}│- TRẠNG THÁI NHÓM: {'✅ ĐƯỢC PHÉP' if is_allowed_status else '❌ CHƯA KÍCH HOẠT'}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[7])}{Style.BRIGHT}│- THỜI GIAN NHẬN ĐƯỢC: {current_time}{Style.RESET_ALL}",
                        f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}"
                    ]
                    with _console_lock:
                        print("\n".join(lines))
            
            # Admin control of music features for groups (private chat only)
            if thread_type == ThreadType.USER and author_id in admin_bot and (
                message_lower.startswith(f"{prefix}music") or 
                message_lower.startswith(f"{prefix}nhac") or
                message_lower.startswith(f"{prefix}nct on") or
                message_lower.startswith(f"{prefix}nct off") or
                message_lower.startswith(f"{prefix}mp3 on") or
                message_lower.startswith(f"{prefix}mp3 off") or
                message_lower.startswith(f"{prefix}scl on") or
                message_lower.startswith(f"{prefix}scl off")
            ):
                parts = message_text.split()
                if len(parts) >= 3:
                    command_prefix = parts[0].lower()[len(prefix):]
                    action = parts[1].lower()
                    target = parts[2].strip()
                    
                    target_group_id = None
                    if "zalo.me/" in target:
                        url_match = re.search(r'https?://zalo\.me/[^\s]+', target)
                        url = url_match.group(0) if url_match else target
                        try:
                            group_info = self.checkGroup(url)
                            target_group_id = group_info.get('groupId')
                        except Exception as e:
                            print(f"[ERROR] Resolving group link: {e}")
                    else:
                        target_group_id = target
                        
                    if not target_group_id:
                        self.replyMessage(Message(text="❌ Không thể tìm thấy Group ID!"), message_object, thread_id, thread_type)
                    else:
                        settings = read_settings(self.uid)
                        
                        if command_prefix in ["music", "nhac"]:
                            music_enabled_groups = settings.setdefault("music_enabled_groups", [])
                            nct_enabled_groups = settings.setdefault("nct_enabled_groups", [])
                            mp3_enabled_groups = settings.setdefault("mp3_enabled_groups", [])
                            scl_disabled_groups = settings.setdefault("scl_disabled_groups", [])
                            
                            if action == "on":
                                if target_group_id not in music_enabled_groups:
                                    music_enabled_groups.append(target_group_id)
                                if target_group_id not in nct_enabled_groups:
                                    nct_enabled_groups.append(target_group_id)
                                if target_group_id not in mp3_enabled_groups:
                                    mp3_enabled_groups.append(target_group_id)
                                if target_group_id in scl_disabled_groups:
                                    scl_disabled_groups.remove(target_group_id)
                                msg_text = "tất cả tính năng nhạc (ZingMP3, NCT, SoundCloud)"
                            else:
                                if target_group_id in music_enabled_groups:
                                    music_enabled_groups.remove(target_group_id)
                                if target_group_id in nct_enabled_groups:
                                    nct_enabled_groups.remove(target_group_id)
                                if target_group_id in mp3_enabled_groups:
                                    mp3_enabled_groups.remove(target_group_id)
                                if target_group_id not in scl_disabled_groups:
                                    scl_disabled_groups.append(target_group_id)
                                msg_text = "tất cả tính năng nhạc"
                                
                        elif command_prefix == "nct":
                            nct_enabled_groups = settings.setdefault("nct_enabled_groups", [])
                            if action == "on":
                                if target_group_id not in nct_enabled_groups:
                                    nct_enabled_groups.append(target_group_id)
                                msg_text = "nghe nhạc NhacCuaTui (NCT)"
                            else:
                                if target_group_id in nct_enabled_groups:
                                    nct_enabled_groups.remove(target_group_id)
                                music_enabled_groups = settings.setdefault("music_enabled_groups", [])
                                if target_group_id in music_enabled_groups:
                                    music_enabled_groups.remove(target_group_id)
                                msg_text = "nghe nhạc NhacCuaTui (NCT)"
                                
                        elif command_prefix == "mp3":
                            mp3_enabled_groups = settings.setdefault("mp3_enabled_groups", [])
                            if action == "on":
                                if target_group_id not in mp3_enabled_groups:
                                    mp3_enabled_groups.append(target_group_id)
                                msg_text = "nghe nhạc ZingMP3"
                            else:
                                if target_group_id in mp3_enabled_groups:
                                    mp3_enabled_groups.remove(target_group_id)
                                music_enabled_groups = settings.setdefault("music_enabled_groups", [])
                                if target_group_id in music_enabled_groups:
                                    music_enabled_groups.remove(target_group_id)
                                msg_text = "nghe nhạc ZingMP3"
                                
                        elif command_prefix == "scl":
                            scl_disabled_groups = settings.setdefault("scl_disabled_groups", [])
                            if action == "on":
                                if target_group_id in scl_disabled_groups:
                                    scl_disabled_groups.remove(target_group_id)
                                msg_text = "nghe nhạc SoundCloud"
                            else:
                                if target_group_id not in scl_disabled_groups:
                                    scl_disabled_groups.append(target_group_id)
                                msg_text = "nghe nhạc SoundCloud"
                                
                        write_settings(self.uid, settings)
                        
                        group_name_resolved = "N/A"
                        try:
                            g_info = self.fetchGroupInfo(target_group_id).gridInfoMap.get(target_group_id)
                            if g_info:
                                group_name_resolved = g_info.name
                        except:
                            pass
                            
                        status_str = "bật" if action == "on" else "tắt"
                        icon_str = "✅" if action == "on" else "🛑"
                        self.replyMessage(Message(text=f"{icon_str} Đã {status_str} {msg_text} cho nhóm:\n➜ Tên: {group_name_resolved}\n➜ ID: {target_group_id}"), message_object, thread_id, thread_type)
                else:
                    self.replyMessage(Message(text="⚠️ Sai cú pháp! Vui lòng dùng:\n➜ .music <on/off> <link_group/group_id> hoặc .nct/mp3/scl <on/off> <link_group/group_id>"), message_object, thread_id, thread_type)
                return

            # Intercept word chain game active states only if allowed
            if is_allowed and current_word is not None and not message_text.startswith(prefix):
                if game_active and author_id == current_player:
                    nt_go(self, message_object, author_id, thread_id, thread_type, message_lower)
                    return

            # Intercept custom message choices (donghua search selections) only if allowed
            if is_allowed and author_id in user_selection_data and message.strip().isdigit() and user_selection_data.get(author_id)['next_step'] == "handle_user_selection":
                handle_user_selection(self, message_object, author_id, thread_id, thread_type, message)
                return
            elif is_allowed and author_id in user_selection_data and message.strip().isdigit() and user_selection_data.get(author_id)['next_step'] == "handle_episode_selection":
                handle_episode_selection(self, message_object, author_id, thread_id, thread_type, message)
                return

            # For unapproved private messages, send a warning even if no prefix
            if not is_allowed and thread_type == ThreadType.USER:
                # Send the same warning as for command
                admin_names = []
                for aid in admin_bot:
                    admin_names.append(f"Admin (ID: {aid})")
                admin_info = ", ".join(admin_names) if admin_names else "Admin BOT"
                
                warning_text = (
                    f"⚠️ Bạn chưa được phép sử dụng BOT trong tin nhắn riêng tư!\n"
                    f"➜ Vui lòng liên hệ {admin_info} để được duyệt. 🌸\n"
                    f"💡 (Hiện tại đang miễn phí trải nghiệm, sau này sẽ có tính phí dịch vụ nhé! 🌸)"
                )
                try:
                    self.replyMessage(Message(text=warning_text), message_object, thread_id, thread_type)
                except Exception as e:
                    print(f"[ERROR] Error sending unapproved PM warning: {e}")
                return

            # Kiểm tra nếu tin nhắn là số và người dùng có state nhạc
            if message_text.strip().isdigit() and author_id in USER_MUSIC_STATES:
                state = USER_MUSIC_STATES[author_id]
                source = state.get('source')
                if source:
                    # Gọi execute với command name tương ứng
                    cmd_name = None
                    if source == 'scl':
                        cmd_name = 'scl'
                    elif source == 'zingmp3':
                        cmd_name = 'mp3'
                    elif source == 'nct':
                        cmd_name = 'nct'
                        
                    if cmd_name:
                        # Gọi execute, nó sẽ handle tất cả tham số
                        executed = self.command_handler.execute(cmd_name, message_text, message_object, thread_id, thread_type, author_id)
                        if executed:
                            return

            # Parse commands starting with prefix
            is_cmd = False
            used_prefix = None
            if prefix and message_text.startswith(prefix) and len(message_text) > len(prefix):
                rem_text = message_text[len(prefix):].strip()
                if rem_text:
                    is_cmd = True
                    used_prefix = prefix

            if is_cmd:
                cmd_parts = message_text[len(used_prefix):].split(" ")
                cmd_name = cmd_parts[0].lower()
                
                # Hàng đợi lệnh nhạc (Music Command Queue)
                if cmd_name in ["mp3", "zingmp3", "scl", "nhac", "nct", "nhaccuatui"]:
                    is_selection = len(cmd_parts) == 2 and cmd_parts[1].isdigit()
                    if not is_selection:
                        if author_id in USER_MUSIC_STATES:
                            state = USER_MUSIC_STATES[author_id]
                            if time.time() - state.get('time_of_search', 0) <= 120:
                                try:
                                    self.sendReaction(message_object, "⏳", thread_id, thread_type)
                                except Exception as rx_err:
                                    print(f"Lỗi thả reaction ⏳: {rx_err}")
                                
                                queue_list = USER_MUSIC_QUEUES.setdefault(author_id, [])
                                queue_list.append({
                                    "message_text": message_text,
                                    "message_object": message_object,
                                    "thread_id": thread_id,
                                    "thread_type": thread_type
                                })
                                return
                
                # Check custom inline command overrides (group on / off)
                if cmd_name == "group" and len(cmd_parts) > 1:
                    sub_action = cmd_parts[1].lower()
                    if sub_action == "on":
                        response = bot_on_group(self, thread_id)
                        if random.random() > 0.3:
                            self.sendReaction(message_object, "❤️", thread_id, thread_type)
                        self.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
                        self.replyMessage(Message(text=response), message_object, thread_id, thread_type)
                        return
                    elif sub_action == "off":
                        response = bot_off_group(self, thread_id)
                        if random.random() > 0.3:
                            self.sendReaction(message_object, "❤️", thread_id, thread_type)
                        self.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
                        self.replyMessage(Message(text=response), message_object, thread_id, thread_type)
                        return

                # Configure user platform/device for voice message compatibility (M4A vs MP3)
                if cmd_name in ["device", "platform"]:
                    if len(cmd_parts) < 2:
                        self.replyMessage(Message(text=(
                            f"📱 Cấu hình thiết bị nhận nhạc (Giảm thời gian chờ convert):\n"
                            f"👉 Cú pháp: {prefix}device <ios / android / pc>\n"
                            f"💡 Mặc định: ios\n"
                            f"💡 Android/PC: Không cần convert, nhưng có thể hok nghe được trên ios!"
                        )), message_object, thread_id, thread_type)
                        return

                    plat = cmd_parts[1].lower().strip()
                    if plat not in ["ios", "android", "pc"]:
                        self.replyMessage(Message(text="⚠️ Thiết bị không hợp lệ! Vui lòng chọn: ios, android, hoặc pc."), message_object, thread_id, thread_type)
                        return

                    settings = read_settings(self.uid)
                    if "user_platforms" not in settings:
                        settings["user_platforms"] = {}
                    
                    settings["user_platforms"][author_id] = plat
                    write_settings(self.uid, settings)

                    self.replyMessage(Message(text=f"✅ Đã cấu hình thiết bị của bạn là: {plat.upper()}.\n"
                                                   f"{( '🎵 Bot sẽ gửi file MP3 trực tiếp (Không cần chờ convert!)' if plat != 'ios' else '🎵 Bot sẽ convert sang M4A cho bạn.' )}"), 
                                      message_object, thread_id, thread_type)
                    return

                # Inline autodelete / ttl configuration
                if cmd_name in ["autodelete", "ttl"]:
                    if thread_type != ThreadType.GROUP:
                        self.replyMessage(Message(text="⚠️ Lệnh này chỉ hoạt động trong nhóm chat!"), message_object, thread_id, thread_type)
                        return

                    is_admin_bot = author_id in admin_bot
                    is_group_admin = is_group_admin_or_creator(self, author_id, thread_id)
                    if not (is_admin_bot or is_group_admin):
                        self.replyMessage(Message(text="❌ Bạn không có quyền quản trị nhóm hoặc Admin Bot để thực hiện lệnh này!"), message_object, thread_id, thread_type)
                        return

                    if len(cmd_parts) < 2:
                        self.replyMessage(Message(text=(
                            f"⚠️ Vui lòng nhập thời gian tự xóa!\n"
                            f"👉 Cú pháp: {prefix}ttl <thời_gian>\n"
                            f"👉 Các mốc thời gian hợp lệ:\n"
                            f"- 0 hoặc off (Tắt tự xóa)\n"
                            f"- 1d hoặc 1 (Tự xóa sau 1 ngày)\n"
                            f"- 7d hoặc 7 (Tự xóa sau 7 ngày)\n"
                            f"- 14d hoặc 14 (Tự xóa sau 14 ngày)\n"
                            f"- 30d hoặc 30 (Tự xóa sau 30 ngày)"
                        )), message_object, thread_id, thread_type)
                        return

                    time_arg = cmd_parts[1].lower().strip()
                    ttl_ms = None
                    time_str = ""

                    if time_arg in ["0", "off", "tắt"]:
                        ttl_ms = 0
                        time_str = "Tắt tự xóa"
                    elif time_arg in ["1d", "1", "1 ngày", "24h"]:
                        ttl_ms = 86400000
                        time_str = "1 ngày (24 giờ)"
                    elif time_arg in ["7d", "7", "7 ngày"]:
                        ttl_ms = 604800000
                        time_str = "7 ngày"
                    elif time_arg in ["14d", "14", "14 ngày"]:
                        ttl_ms = 1209600000
                        time_str = "14 ngày"
                    elif time_arg in ["30d", "30", "30 ngày"]:
                        ttl_ms = 2592000000
                        time_str = "30 ngày"
                    else:
                        self.replyMessage(Message(text="⚠️ Thời gian tự xóa không hợp lệ! Vui lòng chọn: 0, 1d, 7d, 14d hoặc 30d."), message_object, thread_id, thread_type)
                        return

                    try:
                        if random.random() > 0.3:
                            self.sendReaction(message_object, "👍", thread_id, thread_type)
                        self.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
                        self.updateAutoDeleteChat(ttl=ttl_ms, threadId=thread_id, isGroup=True)
                        if random.random() > 0.3:
                            self.sendReaction(message_object, "❤️", thread_id, thread_type)
                        self.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
                        self.replyMessage(Message(text=f"✅ Đã thiết lập tin nhắn tự xóa của nhóm thành: {time_str}."), message_object, thread_id, thread_type)
                    except Exception as e:
                        if random.random() > 0.3:
                            self.sendReaction(message_object, "😢", thread_id, thread_type)
                        self.sendReaction(message_object, "TBOT FAILED ❌", thread_id, thread_type)
                        self.replyMessage(Message(text=f"❌ Thất bại khi cài đặt tin nhắn tự xóa: {str(e)}"), message_object, thread_id, thread_type)
                    return

                # Check approval for image and video commands
                cmd_info = txacommand.loaded_commands.get(cmd_name)
                is_media_cmd = cmd_info and (
                    cmd_info.get('module_path', '').startswith("modules.images.") or 
                    cmd_info.get('module_path', '').startswith("modules.videos.")
                )
                if is_media_cmd:
                    is_user_admin = is_admin(self, author_id)
                    settings = read_settings(self.uid)
                    
                    # 1. Master switch check (nằm trên tất cả)
                    media_commands_active = settings.get("media_commands_active", True)
                    if not media_commands_active and not is_user_admin:
                        self.replyMessage(
                            Message(text="⚠️ Tính năng sử dụng các lệnh kho ảnh/video hiện đang bị Admin tắt!"),
                            message_object, thread_id, thread_type
                        )
                        return
                        
                    approved_users = settings.get("image_approved_users", [])
                    
                    if not is_user_admin and author_id not in approved_users:
                        # User is not approved and not admin
                        admin_bot = settings.get("admin_bot", [])
                        admin_id = admin_bot[0] if admin_bot else self.uid
                        admin_name = get_user_name_by_id(self, admin_id)
                        
                        warning_text = (
                            f"⚠️ Bạn chưa được phép sử dụng các lệnh kho ảnh!\n"
                            f"➜ Vui lòng liên hệ Admin {admin_name} để được duyệt. 🌸\n"
                            f"💡 (Hiện tại đang miễn phí trải nghiệm, sau này sẽ có tính phí dịch vụ nhé! 🌸)"
                        )
                        offset = warning_text.find(admin_name)
                        length = len(admin_name)
                        mention = Mention(uid=admin_id, length=length, offset=offset)
                        
                        warning_msg = self.replyMessage(Message(text=warning_text, mention=mention), message_object, thread_id, thread_type)
                        
                        if thread_type == ThreadType.GROUP:
                            try:
                                w_msg_id = None
                                w_cli_msg_id = None
                                if warning_msg:
                                    if isinstance(warning_msg, dict):
                                        w_msg_id = warning_msg.get('msgId') or warning_msg.get('messageId') or warning_msg.get('msg_id')
                                        w_cli_msg_id = warning_msg.get('cliMsgId') or warning_msg.get('clientMsgId') or warning_msg.get('cli_msg_id')
                                    else:
                                        w_msg_id = getattr(warning_msg, 'msgId', None) or getattr(warning_msg, 'messageId', None) or getattr(warning_msg, 'msg_id', None)
                                        w_cli_msg_id = getattr(warning_msg, 'cliMsgId', None) or getattr(warning_msg, 'clientMsgId', None) or getattr(warning_msg, 'cli_msg_id', None)
                                        if not w_msg_id and hasattr(warning_msg, 'get'):
                                            w_msg_id = warning_msg.get('msgId') or warning_msg.get('messageId')
                                        if not w_cli_msg_id and hasattr(warning_msg, 'get'):
                                            w_cli_msg_id = warning_msg.get('cliMsgId') or warning_msg.get('clientMsgId')
                                
                                u_msg_id = message_object.msgId if hasattr(message_object, 'msgId') else message_object.get('msgId') if isinstance(message_object, dict) else None
                                u_cli_msg_id = message_object.cliMsgId if hasattr(message_object, 'cliMsgId') else message_object.get('cliMsgId') if isinstance(message_object, dict) else None
                                
                                if w_msg_id and w_cli_msg_id and u_msg_id and u_cli_msg_id:
                                    settings = read_settings(self.uid)
                                    pending_cleanups = settings.setdefault("pending_cleanups", {})
                                    # Đảm bảo key lưu là string
                                    author_key = str(author_id)
                                    user_cleanups = pending_cleanups.setdefault(author_key, [])
                                    user_cleanups.append({
                                        "thread_id": thread_id,
                                        "user_msg_id": u_msg_id,
                                        "user_cli_msg_id": u_cli_msg_id,
                                        "warning_msg_id": w_msg_id,
                                        "warning_cli_msg_id": w_cli_msg_id
                                    })
                                    settings["pending_cleanups"] = pending_cleanups
                                    write_settings(self.uid, settings)
                            except Exception as e:
                                print(f"[ERROR] Không thể lưu tin nhắn chờ dọn dẹp: {e}")
                        
                        # Gửi tin nhắn riêng (Inbox) báo cho Admin biết có người muốn dùng kho ảnh
                        if author_id != self.uid:
                            current_time_sec = time.time()
                            last_notify = self.last_admin_notify.setdefault((author_id, 'image'), 0)
                            if current_time_sec - last_notify >= 300: # 5 phút cooldown
                                try:
                                    req_name = get_user_name_by_id(self, author_id)
                                    context = "tin nhắn riêng tư"
                                    if thread_type == ThreadType.GROUP:
                                        try:
                                            g_info = self.fetchGroupInfo(thread_id)
                                            context = f"nhóm '{g_info.gridInfoMap.get(thread_id, {}).get('name', 'N/A')}'"
                                        except:
                                            context = "nhóm chat"
                                    
                                    if not os.path.exists("cache"):
                                        os.makedirs("cache")
                                    pending_file = "cache/pending_image_approvals.txt"
                                    pending_uids = []
                                    if os.path.exists(pending_file):
                                        with open(pending_file, "r", encoding="utf-8") as f:
                                            pending_uids = [line.strip() for line in f if line.strip()]
                                    
                                    if str(author_id) not in pending_uids:
                                        pending_uids.append(str(author_id))
                                        with open(pending_file, "w", encoding="utf-8") as f:
                                            for p_uid in pending_uids:
                                                f.write(f"{p_uid}\n")
                                    
                                    for p_uid in pending_uids:
                                        if p_uid not in PENDING_IMAGE_STATE:
                                            PENDING_IMAGE_STATE.append(p_uid)
                                    if str(author_id) not in PENDING_IMAGE_STATE:
                                        PENDING_IMAGE_STATE.append(str(author_id))
                                    
                                    if len(PENDING_IMAGE_STATE) >= 2:
                                        img_path = generate_pending_approvals_image("🌸 DANH SÁCH CHỜ DUYỆT KHO ẢNH", PENDING_IMAGE_STATE, self)
                                        if img_path and os.path.exists(img_path):
                                            with Image.open(img_path) as img:
                                                w, h = img.size
                                            for admin_id in admin_bot:
                                                if admin_id != self.uid:
                                                    self.sendLocalImage(
                                                        imagePath=img_path,
                                                        thread_id=admin_id,
                                                        thread_type=ThreadType.USER,
                                                        width=w,
                                                        height=h,
                                                        message=Message(text=f"🔔 Có {len(pending_uids)} yêu cầu duyệt kho ảnh đang chờ!\n💡 Gõ `!duyet yes` để duyệt tất cả.")
                                                    )
                                            os.remove(img_path)
                                        else:
                                            notify_text = f"🔔 [DANH SÁCH DUYỆT KHO ẢNH ĐANG CHỜ]\n"
                                            for p_uid in pending_uids:
                                                notify_text += f"➜ {get_user_name_by_id(self, p_uid)} ({p_uid})\n"
                                            notify_text += f"💡 Gõ `!duyet yes` để duyệt tất cả."
                                            for admin_id in admin_bot:
                                                if admin_id != self.uid:
                                                    self.send(Message(text=notify_text), thread_id=admin_id, thread_type=ThreadType.USER)
                                    else:
                                        notify_text = (
                                            f"🔔 [YÊU CẦU DUYỆT KHO ẢNH]\n"
                                            f"➜ Người dùng: {req_name}\n"
                                            f"➜ UID: {author_id}\n"
                                            f"➜ Muốn dùng lệnh kho ảnh `{cmd_name}` tại: {context}\n"
                                            f"💡 Gõ `{prefix}duyet {author_id}` để duyệt quyền kho ảnh."
                                        )
                                        for admin_id in admin_bot:
                                            if admin_id != self.uid:
                                                self.send(Message(text=notify_text), thread_id=admin_id, thread_type=ThreadType.USER)
                                    self.last_admin_notify[(author_id, 'image')] = current_time_sec
                                except Exception as e:
                                    print(f"[ERROR] Không thể gửi thông báo yêu cầu duyệt ảnh cho Admin: {e}")
                        return

                    # Kiểm tra quyền cho các lệnh nude (girlnude, girllon)
                    if cmd_name in ["girlnude", "girllon"] and not is_user_admin:
                        nude_approved = settings.get("nude_approved_users", [])
                        if author_id not in nude_approved:
                            bank_info = settings.get("bank_info", {})
                            bank = bank_info.get("bank", "Techcombank")
                            stk = bank_info.get("stk", "2923252311")
                            name = bank_info.get("name", "TANG XUAN ANH")
                            
                            description = f"Duyet nude {author_id}"
                            
                            import urllib.parse
                            encoded_name = urllib.parse.quote(name)
                            encoded_desc = urllib.parse.quote(description)
                            
                            qr_url = f"https://img.vietqr.io/image/{bank}-{stk}-compact2.png?accountName={encoded_name}&amount=50000&addInfo={encoded_desc}"
                            
                            temp_dir = "modules/cache"
                            os.makedirs(temp_dir, exist_ok=True)
                            temp_path = os.path.join(temp_dir, f"nude_qr_{author_id}.png")
                            
                            try:
                                import requests
                                res = requests.get(qr_url, timeout=15)
                                res.raise_for_status()
                                with open(temp_path, "wb") as f:
                                    f.write(res.content)
                                    
                                caption_text = (
                                    "⚠️ Quyền sử dụng các lệnh ảnh nude/nhạy cảm (girlnude, girllon) yêu cầu trả phí (50k/ngày).\n"
                                    "🏦 Bạn vui lòng chuyển khoản theo mã QR bên dưới, sau đó liên hệ Admin kèm theo ảnh chụp giao dịch (bill chuyển khoản) để kích hoạt quyền nhé! 🌸"
                                )
                                
                                # Gửi ảnh QR qua tin nhắn riêng (inbox)
                                self.sendLocalImage(
                                    imagePath=temp_path,
                                    thread_id=author_id,
                                    thread_type=ThreadType.USER,
                                    message=Message(text=caption_text),
                                    ttl=0
                                )
                                
                                # Phản hồi trong nhóm
                                self.replyMessage(
                                    Message(text="⚠️ Bé đã gửi thông tin chuyển khoản 50k/ngày vào tin nhắn riêng (inbox) của bạn. Hãy kiểm tra inbox, sau đó liên hệ Admin kèm theo ảnh giao dịch để kích hoạt nhé! 🌸"),
                                    message_object, thread_id, thread_type
                                )
                            except Exception as private_err:
                                print(f"[ERROR] Failing to send private QR to {author_id}: {private_err}")
                                self.replyMessage(
                                    Message(text="⚠️ Không thể gửi tin nhắn riêng cho bạn. Vui lòng nhắn tin/kết bạn trước với bot để nhận thông tin chuyển khoản! 🌸"),
                                    message_object, thread_id, thread_type
                                )
                            finally:
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)
                            return

                # Check dynamic commands logic
                executed = self.command_handler.execute(cmd_name, message_text, message_object, thread_id, thread_type, author_id)
                if executed:
                    # Let auto sticker run as a post-hook
                    auto_stk(self, message_object, author_id, thread_id, thread_type, message_text)
                    return
                
                # Check custom checks for music options disabled checks
                if cmd_name in ["scl", "ns", "mp3", "zingmp3", "nct", "nhaccuatui"]:
                    if thread_type == ThreadType.GROUP:
                        # Music config disabled notification logic
                        settings = read_settings(self.uid)
                        if cmd_name in ["scl", "ns"]:
                            scl_disabled_groups = settings.setdefault("scl_disabled_groups", [])
                            if thread_id in scl_disabled_groups:
                                admin_names = [f"Admin (ID: {aid})" for aid in admin_bot]
                                admin_info = ", ".join(admin_names) if admin_names else "Admin BOT"
                                self.replyMessage(Message(text=f"⚠️ Nhóm này đã bị Admin BOT tắt tính năng nghe nhạc SoundCloud!\n➜ Vui lòng liên hệ {admin_info} để được mở lại. 🎵"), message_object, thread_id, thread_type)
                                return
                        elif cmd_name in ["mp3", "zingmp3"]:
                            music_enabled_groups = settings.setdefault("music_enabled_groups", [])
                            mp3_enabled_groups = settings.setdefault("mp3_enabled_groups", [])
                            if thread_id not in music_enabled_groups and thread_id not in mp3_enabled_groups:
                                admin_names = [f"Admin (ID: {aid})" for aid in admin_bot]
                                admin_info = ", ".join(admin_names) if admin_names else "Admin BOT"
                                self.replyMessage(Message(text=f"⚠️ Nhóm này chưa được Admin BOT kích hoạt tính năng nghe nhạc ZingMP3!\n➜ Vui lòng liên hệ {admin_info} để được mở tính năng nghe nhạc. 🎵"), message_object, thread_id, thread_type)
                                return
                        elif cmd_name in ["nct", "nhaccuatui"]:
                            music_enabled_groups = settings.setdefault("music_enabled_groups", [])
                            nct_enabled_groups = settings.setdefault("nct_enabled_groups", [])
                            if thread_id not in music_enabled_groups and thread_id not in nct_enabled_groups:
                                admin_names = [f"Admin (ID: {aid})" for aid in admin_bot]
                                admin_info = ", ".join(admin_names) if admin_names else "Admin BOT"
                                self.replyMessage(Message(text=f"⚠️ Nhóm này chưa được Admin BOT kích hoạt tính năng nghe nhạc NhacCuaTui (NCT)!\n➜ Vui lòng liên hệ {admin_info} để được mở tính năng nghe nhạc. 🎵"), message_object, thread_id, thread_type)
                                return

                # Check if it was a donghua query
                if cmd_name == "donghua":
                    try:
                        if random.random() > 0.3:
                            self.sendReaction(message_object, "⏳", thread_id, thread_type)
                        self.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
                    except Exception as react_err:
                        print(f"[Main] Lỗi gửi waiting reaction cho donghua: {react_err}")
                    
                    try:
                        tim_kiem_yanhh3d(self, message_object, author_id, thread_id, thread_type, message_lower, message_text)
                        try:
                            success_reactions = ["👍", "❤️", "😆", "😮", "🎉", "🔥", "🤩", "✅"]
                            if random.random() > 0.3:
                                self.sendReaction(message_object, random.choice(success_reactions), thread_id, thread_type)
                            self.sendReaction(message_object, "TBOT ✅", thread_id, thread_type)
                        except Exception as react_err:
                            print(f"[Main] Lỗi gửi success reaction cho donghua: {react_err}")
                    except Exception as e:
                        print(f"Lỗi khi thực thi lệnh 'donghua': {e}")
                        try:
                            if random.random() > 0.3:
                                self.sendReaction(message_object, "❌", thread_id, thread_type)
                            self.sendReaction(message_object, "TBOT FAILED ❌", thread_id, thread_type)
                        except Exception as react_err:
                            print(f"[Main] Lỗi gửi fail reaction cho donghua: {react_err}")
                        try:
                            self.sendMessage(f"❌ Lỗi khi thực thi lệnh 'donghua': {e}", thread_id, thread_type)
                        except Exception as send_err:
                            print(f"[ERROR] couldn't send error message: {send_err}")
                    return

                # If none of the above hardcoded commands returned, and it wasn't a dynamic command
                try:
                    self.sendReaction(message_object, "❌", thread_id, thread_type)
                    self.sendReaction(message_object, "TBOT FAILED ❌", thread_id, thread_type)
                except Exception as react_err:
                    print(f"[Main] Lỗi gửi reaction cho lệnh không hợp lệ: {react_err}")
                
                self.replyMessage(
                    Message(text=f"➜ Lệnh [{used_prefix}{cmd_name}] không được hỗ trợ hoặc gõ sai cú pháp 🤧\n➜ Gõ {used_prefix}bot hoặc {used_prefix}help để xem danh sách lệnh! ✅"),
                    message_object, thread_id, thread_type, ttl=9000
                )
                return

            # Check general auto hooks
            auto_stk(self, message_object, author_id, thread_id, thread_type, message_text)
            
        except Exception as e:
            print(f"[MAIN] Lỗi trong main: {e}")

CONFIG_FILE = "txa.json"
lock = threading.Lock()

def save_json(filename: str, data: Dict) -> None:
    with lock:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Lỗi khi lưu dữ liệu vào {filename}: {e}")
            raise

def load_json(filename: str) -> Dict:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"Không tìm thấy tệp {filename}. Tạo dữ liệu mặc định")
        default_data = {"data": []}
        save_json(filename, default_data)
        return default_data
    except json.JSONDecodeError:
        logging.error(f"Không thể giải mã JSON từ {filename}")
        default_data = {"data": []}
        save_json(filename, default_data)
        return default_data
    except Exception as e:
        logging.error(f"Lỗi không xác định khi đọc {filename}: {e}")
        return {"data": []}

def save_username_to_config(username: str, author_id: str) -> None:
    try:
        with lock:
            data = load_json(CONFIG_FILE)
            
            if "data" not in data:
                data["data"] = []
                
            existing_user = next((user for user in data["data"] if user.get('username') == username), None)
            if not existing_user:
                data["data"].append({
                    "username": username,
                    "author_id": author_id,
                    "status": True
                })
                save_json(CONFIG_FILE, data)
                logging.info(f"Đã lưu {username} vào config")
    except Exception as e:
        logging.error(f"Lỗi khi lưu username và author_id vào txa.json: {e}")

def run_bot(
    imei: str,
    session_cookies: Dict,
    prefix: str,
    is_main_bot: bool,
    username: Optional[str] = None,
    author_id: Optional[str] = None,
    status: Optional[bool] = None
) -> None:
    try:
        if status is False:
            logging.info(f"Bot {username} bị vô hiệu hóa (status: {status})")
            return

        if not isinstance(session_cookies, dict) or not session_cookies:
            logging.error(f"Cookie phiên không hợp lệ cho {username}")
            return

        prefix = prefix if prefix else "None"
        
        client = bot('</>', '</>', imei=imei, session_cookies=session_cookies, 
                    prefix=prefix, is_main_bot=is_main_bot)

        if username and author_id:
            save_username_to_config(username, author_id)

        bot_type = "chính" if is_main_bot else "phụ"
        logging.info(f"Khởi động bot {bot_type} - Tên: {username}, prefix: {prefix}")
        
        client.listen(run_forever=True, delay=0, thread=True)

    except KeyboardInterrupt:
        logging.info(f"Bot {username} đã nhận tín hiệu Ctrl+C, đang dừng...")
    except Exception as e:
        logging.error(f"Lỗi khi chạy bot {username}: {e}")

def start_threads(data: List[Dict]) -> None:
    threads = []

    for item in data:
        try:
            imei = item.get("imei", "Unknown_IMEI")
            session_cookies = item.get("session_cookies", {})
            prefix = item.get("prefix", "")
            is_main_bot = item.get("is_main_bot", False)
            username = item.get("username")
            author_id = item.get("author_id")
            status = item.get("status", True)

            if not username or not author_id:
                logging.warning(f"Thiếu username hoặc author_id trong config: {item}")
                continue

            thread = threading.Thread(
                target=run_bot,
                args=(imei, session_cookies, prefix, is_main_bot, username, author_id, status),
                daemon=True
            )
            threads.append(thread)
            thread.start()

        except Exception as e:
            logging.error(f"Lỗi khi tạo thread cho bot {username}: {e}")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        logging.info("\n🛑 Nhận tín hiệu Ctrl+C, đang tắt bot...")
        os._exit(0)

def signal_handler(sig, frame):
    logging.info("\n🛑 Nhận tín hiệu Ctrl+C, đang tắt bot an toàn...")
    os._exit(0)

def main():
    # Kiểm tra và tự động cài đặt FFmpeg nếu thiếu
    from core.ffmpeg_installer import check_and_install_ffmpeg
    check_and_install_ffmpeg()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        data = load_json(CONFIG_FILE)
        
        if "data" not in data:
            logging.error("Không tìm thấy trường 'data' trong JSON")
            return
            
        if not data["data"]:
            logging.warning("Không có dữ liệu bot nào trong config")
            return
            
        start_threads(data["data"])
        
    except Exception as e:
        logging.error(f"Lỗi trong quá trình khởi động: {e}")

if __name__ == "__main__":
    main()
