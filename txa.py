import sys
import os
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

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

logger = logging.getLogger("txabot")

message_count = {}
def send_random_sticker(bot, thread_id, thread_type):
    with open('auto_sticker.json', 'r', encoding='utf-8') as file:
        stickers = json.load(file)
    sticker = random.choice(stickers)
    bot.sendSticker(sticker['stickerType'], sticker['stickerId'], sticker['cateId'], thread_id, thread_type)

def auto_stk(bot, message_object, author_id, thread_id, thread_type):
    settings = read_settings(bot.uid)
    if settings.get('auto_sticker', {}).get(thread_id, False) and thread_id in settings.get('allowed_thread_ids', []):
        if thread_id not in message_count:
            message_count[thread_id] = 0
        message_count[thread_id] += 1
        if message_count[thread_id] >= random.randint(10,11):
            send_random_sticker(bot, thread_id, thread_type)
            message_count[thread_id] = 0

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
    bot.sendReaction(message_object, "❌", thread_id, thread_type)
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

def check_word(player_word, last_part):
    if not player_word or not last_part:
        return False
    if player_word in words and player_word.split()[0] == last_part:
        return True
    wiki_info = get_wikipedia_info(player_word)
    if "Lỗi" not in wiki_info and wiki_info["Mô tả"]:
        if player_word.split()[0] == last_part:
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
        bot.sendReaction(message_object, "❌", thread_id, thread_type)
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
            bot.sendReaction(message_object, "✅", thread_id, thread_type)
        
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
        return user_info.zaloName or user_info.displayName
    except Exception as e:
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
            
            bot.sendReaction(message_object, random.choice(reaction), thread_id, thread_type)
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
                
            print("="*50)
            print(f"🎉 TỔNG KẾT: Thành công: {txacommand.success_count} | Thất bại: {txacommand.fail_count}")
            print(f"👉 Đã nạp thành công {len(self.commands)} lệnh gọi!")
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"❌ Lỗi nghiêm trọng khi load modules: {e}")

    def execute(self, command_name, message_text, message_object, thread_id, thread_type, author_id):
        handler = self.commands.get(command_name)
        if not handler:
            return False
            
        try:
            import inspect
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
                    
            handler(*args)
            return True
        except Exception as e:
            print(f"Lỗi khi thực thi lệnh '{command_name}': {e}")
            import traceback
            traceback.print_exc()
            try:
                self.client.sendMessage(f"❌ Lỗi khi thực thi lệnh '{command_name}': {e}", thread_id, thread_type)
            except Exception as send_err:
                print(f"[ERROR] couldn't send error message: {send_err}")
            return True

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
        self.version ="1.0"
        self.date_update ='05-06-26'
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
        self._log_bot_message(message, thread_id, thread_type)
        return super().sendMessage(message, thread_id, thread_type, mark_message, ttl)

    def replyMessage(self, message, replyMsg, thread_id, thread_type, ttl=0):
        if isinstance(message, str):
            message = Message(text=message)
        self._log_bot_message(message, thread_id, thread_type)
        return super().replyMessage(message, replyMsg, thread_id, thread_type, ttl)

    def send(self, message, thread_id, thread_type=ThreadType.USER, mark_message=None, ttl=0):
        if isinstance(message, str):
            message = Message(text=message)
        self._log_bot_message(message, thread_id, thread_type)
        return super().send(message, thread_id, thread_type, mark_message, ttl)

    def _log_bot_message(self, message, thread_id, thread_type):
        try:
            import random
            colors = [
                "#FF5733", "#33FF57", "#3357FF", "#F3FF33", "#FF33F3",
                "#33FFF3", "#FF5733", "#5733FF", "#33FFA5", "#FF8C33"
            ]
            selected_colors = random.sample(colors, 8)
            
            def hex_to_ansi(hex_color):
                hex_color = hex_color.lstrip('#')
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return f"\033[38;2;{r};{g};{b}m"
            
            current_time = time.strftime("%H:%M:%S - %d/%m/%Y", time.localtime())
            message_text = message.text if hasattr(message, 'text') else str(message)
            
            print(f"\n{hex_to_ansi(selected_colors[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
            if thread_type == ThreadType.USER:
                print(f"{hex_to_ansi(selected_colors[1])}{Style.BRIGHT}🤖 BOT GỬI TIN NHẮN RIÊNG TƯ{Style.RESET_ALL}")
            else:
                print(f"{hex_to_ansi(selected_colors[1])}{Style.BRIGHT}🤖 BOT GỬI TIN NHẮN NHÓM{Style.RESET_ALL}")
            print(f"{hex_to_ansi(selected_colors[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
            print(f"{hex_to_ansi(selected_colors[2])}{Style.BRIGHT}│- Nội dung: {message_text}{Style.RESET_ALL}")
            if thread_type == ThreadType.GROUP:
                try:
                    group_info = self.fetchGroupInfo(thread_id)
                    group_name = group_info.gridInfoMap.get(thread_id, {}).get('name', 'Không rõ')
                    print(f"{hex_to_ansi(selected_colors[3])}{Style.BRIGHT}│- ID nhóm: {group_name} ({thread_id}){Style.RESET_ALL}")
                except Exception:
                    print(f"{hex_to_ansi(selected_colors[3])}{Style.BRIGHT}│- ID nhóm: {thread_id}{Style.RESET_ALL}")
            else:
                try:
                    user_info = self.fetchUserInfo(thread_id)
                    user_name = user_info.changed_profiles.get(thread_id, {}).get('zaloName', 'Không rõ')
                    print(f"{hex_to_ansi(selected_colors[3])}{Style.BRIGHT}│- Đến người dùng: {user_name} ({thread_id}){Style.RESET_ALL}")
                except Exception:
                    print(f"{hex_to_ansi(selected_colors[3])}{Style.BRIGHT}│- Đến UID: {thread_id}{Style.RESET_ALL}")
            print(f"{hex_to_ansi(selected_colors[4])}{Style.BRIGHT}│- Thời gian: {current_time}{Style.RESET_ALL}")
            print(f"{hex_to_ansi(selected_colors[0])}{Style.BRIGHT}{'='*60}\n{Style.RESET_ALL}")
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
                
                if modified:
                    settings["approved_users"] = approved_users
                    settings["approved_users_expiry"] = approved_expiry
                    settings["image_approved_users"] = image_approved
                    settings["image_approved_users_expiry"] = image_expiry
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
                for mention in message_object.mentions:
                    target_uid = mention.get('uid')
                    if not target_uid:
                        continue
                    history = self.message_history.get(thread_id, [])
                    found_msg = None
                    for m in reversed(history):
                        if m['msgId'] == message_object.msgId:
                            continue
                        if m['author_id'] == target_uid:
                            found_msg = m
                            break
                    
                    if found_msg:
                        try:
                            self.deleteGroupMsg(found_msg['msgId'], target_uid, found_msg['cliMsgId'], thread_id)
                            deleted_any = True
                            history.remove(found_msg)
                        except Exception as e:
                            print(f"[ERROR] deleteGroupMsg mention error: {e}")
            
            else:
                history = self.message_history.get(thread_id, [])
                found_msg = None
                for m in reversed(history):
                    if m['msgId'] == message_object.msgId:
                        continue
                    found_msg = m
                    break
                
                if found_msg:
                    try:
                        self.deleteGroupMsg(found_msg['msgId'], found_msg['author_id'], found_msg['cliMsgId'], thread_id)
                        deleted_any = True
                        history.remove(found_msg)
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
            settings = read_settings(self.uid)
            allowed_thread_ids = settings.get('allowed_thread_ids', [])
            admin_bot = settings.get("admin_bot", [])
            approved_users = settings.get("approved_users", [])
            banned_users = settings.get("banned_users", [])
            chat_user = (thread_type == ThreadType.USER)
            is_main_bot = self.is_main_bot
            prefix = self.prefix
            allowed_thread_ids = get_allowed_thread_ids(self)

            message_text = message.text if isinstance(message, Message) else str(message)
            # Clean leading mentions (like @Tbot) and whitespace
            message_text = re.sub(r'^@[\S]+[\s]*', '', message_text).lstrip()
            message_lower = message_text.lower()

            if author_id == self.uid or author_id in banned_users:
                return



            if thread_id not in self.message_history:
                self.message_history[thread_id] = []
            self.message_history[thread_id].append({
                "msgId": message_object.msgId,
                "cliMsgId": message_object.cliMsgId,
                "author_id": author_id,
                "text": message_text
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

            is_bot_on_cmd = (
                message_lower.startswith(f"{prefix}bot on") or 
                message_lower.startswith(f"{prefix}group on")
            )
            
            is_user_approved = (author_id in admin_bot or author_id in approved_users)
            
            if thread_type == ThreadType.GROUP:
                is_allowed = (
                    (thread_id in allowed_thread_ids and is_user_approved) or 
                    (is_bot_on_cmd and (author_id in admin_bot or is_group_admin_or_creator(self, author_id, thread_id)))
                )
            else:
                is_allowed = is_user_approved

            # Add friendly reply when bot is mentioned but not a command
            has_mention = (message_object.mentions and len(message_object.mentions) > 0) or (message_text and '@' in message_text)
            if has_mention and not message_text.startswith(prefix) and is_allowed:
                try:
                    user_name = get_user_name_by_id(self, author_id)
                    replies = [
                        f"Xin chào {user_name}! 🌸 Tôi là {self.me_name}!\nGõ {prefix}help để xem danh sách lệnh nhé!",
                        f"Chào {user_name}! 😊 Có gì tôi có thể giúp bạn? Gõ {prefix}help để biết thêm!",
                        f"Hi {user_name}! 🚗 Bạn cần giúp gì? Gõ {prefix}help để xem danh sách lệnh!"
                    ]
                    reply_text = random.choice(replies)
                    self.replyMessage(Message(text=reply_text), message_object, thread_id, thread_type)
                except Exception as e:
                    print(f"[ERROR] Error sending mention reply: {e}")
                return

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

            # Log tin nhắn nhóm chưa được phép (không có lệnh prefix)
            if not is_allowed and thread_type == ThreadType.GROUP:
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
                    print(f"{hex_to_ansi(_c[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
                    print(f"{hex_to_ansi(_c[1])}{Style.BRIGHT}💬 TIN NHẮN NHÓM (GROUP MESSAGE){Style.RESET_ALL}")
                    print(f"{hex_to_ansi(_c[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
                    print(f"{hex_to_ansi(_c[1])}{Style.BRIGHT}│- Message: {message_text}{Style.RESET_ALL}")
                    print(f"{hex_to_ansi(_c[2])}{Style.BRIGHT}│- ID NGƯỜI DÙNG: {author_id}{Style.RESET_ALL}")
                    print(f"{hex_to_ansi(_c[6])}{Style.BRIGHT}│- TÊN NGƯỜI DÙNG: {_author_name}{Style.RESET_ALL}")
                    print(f"{hex_to_ansi(_c[3])}{Style.BRIGHT}│- ID NHÓM: {thread_id}{Style.RESET_ALL}")
                    print(f"{hex_to_ansi(_c[4])}{Style.BRIGHT}│- TÊN NHÓM: {_group_name}{Style.RESET_ALL}")
                    print(f"{hex_to_ansi(_c[5])}{Style.BRIGHT}│- TRẠNG THÁI NHÓM: ❌ CHƯA KÍCH HOẠT{Style.RESET_ALL}")
                    print(f"{hex_to_ansi(_c[7])}{Style.BRIGHT}│- THỜI GIAN NHẬN ĐƯỢC: {_t}{Style.RESET_ALL}")
                    print(f"{hex_to_ansi(_c[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
                except Exception:
                    pass
                return

            if thread_id in allowed_thread_ids and thread_type == ThreadType.GROUP and not is_admin(self, author_id):
                handle_check_profanity(self, author_id, thread_id, message_object, thread_type, message)
            
            author_info = self.fetchUserInfo(author_id).changed_profiles.get(author_id, {})
            author_name = author_info.get('zaloName', 'đéo xác định')
            current_time = time.strftime("%H:%M:%S - %d/%m/%Y", time.localtime())
            colors_selected = random.sample(colors, 8)
            
            # Beautiful logging for private messages
            if thread_type == ThreadType.USER:
                print(f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[1])}{Style.BRIGHT}🔒 TIN NHẮN RIÊNG TƯ (PRIVATE MESSAGE){Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[2])}{Style.BRIGHT}│- Message: {message_text}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[3])}{Style.BRIGHT}│- ID NGƯỜI DÙNG: {author_id}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[6])}{Style.BRIGHT}│- TÊN NGƯỜI DÙNG: {author_name}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[4])}{Style.BRIGHT}│- TRẠNG THÁI: {'✅ ĐƯỢC PHÉP' if (author_id in admin_bot or author_id in approved_users) else '❌ KHÔNG ĐƯỢC PHÉP'}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[7])}{Style.BRIGHT}│- THỜI GIAN: {current_time}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
            else:
                try:
                    group_info_log = self.fetchGroupInfo(thread_id)
                    group_name = group_info_log.gridInfoMap.get(thread_id, {}).get('name', 'N/A')
                except Exception:
                    group_name = 'N/A'
                is_allowed_status = thread_id in allowed_thread_ids
                print(f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[1])}{Style.BRIGHT}💬 TIN NHẮN NHÓM (GROUP MESSAGE){Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[1])}{Style.BRIGHT}│- Message: {message_text}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[2])}{Style.BRIGHT}│- ID NGƯỜI DÙNG: {author_id}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[6])}{Style.BRIGHT}│- TÊN NGƯỜI DÙNG: {author_name}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[3])}{Style.BRIGHT}│- ID NHÓM: {thread_id}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[4])}{Style.BRIGHT}│- TÊN NHÓM: {group_name}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[5])}{Style.BRIGHT}│- TRẠNG THÁI NHÓM: {'✅ ĐƯỢC PHÉP' if is_allowed_status else '❌ CHƯA KÍCH HOẠT'}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[7])}{Style.BRIGHT}│- THỜI GIAN NHẬN ĐƯỢC: {current_time}{Style.RESET_ALL}")
                print(f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
            
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

            # Parse commands starting with prefix
            if message_text.startswith(prefix):
                cmd_parts = message_text[len(prefix):].split(" ")
                cmd_name = cmd_parts[0].lower()
                
                # Check custom inline command overrides (group on / off)
                if cmd_name == "group" and len(cmd_parts) > 1:
                    sub_action = cmd_parts[1].lower()
                    if sub_action == "on":
                        response = bot_on_group(self, thread_id)
                        self.sendReaction(message_object, "✅", thread_id, thread_type)
                        self.replyMessage(Message(text=response), message_object, thread_id, thread_type)
                        return
                    elif sub_action == "off":
                        response = bot_off_group(self, thread_id)
                        self.sendReaction(message_object, "✅", thread_id, thread_type)
                        self.replyMessage(Message(text=response), message_object, thread_id, thread_type)
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
                        self.sendReaction(message_object, "⏳", thread_id, thread_type)
                        self.updateAutoDeleteChat(ttl=ttl_ms, threadId=thread_id, isGroup=True)
                        self.sendReaction(message_object, "✅", thread_id, thread_type)
                        self.replyMessage(Message(text=f"✅ Đã thiết lập tin nhắn tự xóa của nhóm thành: {time_str}."), message_object, thread_id, thread_type)
                    except Exception as e:
                        self.sendReaction(message_object, "❌", thread_id, thread_type)
                        self.replyMessage(Message(text=f"❌ Thất bại khi cài đặt tin nhắn tự xóa: {str(e)}"), message_object, thread_id, thread_type)
                    return

                # Check approval for image commands
                cmd_info = txacommand.loaded_commands.get(cmd_name)
                if cmd_info and cmd_info.get('module_path', '').startswith("modules.images."):
                    is_user_admin = is_admin(self, author_id)
                    settings = read_settings(self.uid)
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

                # Check dynamic commands logic
                executed = self.command_handler.execute(cmd_name, message_text, message_object, thread_id, thread_type, author_id)
                if executed:
                    # Let auto sticker run as a post-hook
                    auto_stk(self, message_object, author_id, thread_id, thread_type)
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
                    tim_kiem_yanhh3d(self, message_object, author_id, thread_id, thread_type, message_lower, message_text)
                    return

            # Check general auto hooks
            auto_stk(self, message_object, author_id, thread_id, thread_type)
            
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
        logging.error(f"Lỗi khi lưu username và author_id vào config.json: {e}")

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
