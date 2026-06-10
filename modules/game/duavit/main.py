
import os
import random
import time
from PIL import Image, ImageDraw, ImageFont
from zlapi.models import Message, Mention

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
DUCK_BASE_IMAGE = os.path.join(ASSETS_DIR, 'duck.png')
WAITING_IMAGE = os.path.join(ASSETS_DIR, 'waiting.png')
DUCK_RACE_GIF = os.path.join(ASSETS_DIR, 'duck_race.gif')
FONT_PATH = os.path.join(BASE_DIR, '../../../font/arial.ttf')

# Game constants
NUM_DUCKS = 10
DUCKS = [f"🦆 {i+1}" for i in range(NUM_DUCKS)]


def create_duck_image(duck_number, output_path):
    try:
        if os.path.exists(DUCK_BASE_IMAGE):
            base_image = Image.open(DUCK_BASE_IMAGE)
        else:
            base_image = Image.new('RGB', (200, 200), color='#FFD700')
        draw = ImageDraw.Draw(base_image)
        try:
            # Try both font paths
            font = ImageFont.truetype(FONT_PATH, 50)
        except:
            try:
                font = ImageFont.truetype(os.path.join(ASSETS_DIR, 'arial.ttf'), 50)
            except:
                font = ImageFont.load_default()
        text_position = (base_image.width // 2 - 20, base_image.height // 2 - 20)
        draw.text(text_position, duck_number, fill='red', font=font)
        base_image.save(output_path)
    except Exception as e:
        print(f"[ERROR] Lỗi khi tạo ảnh vịt chiến thắng: {e}")

def start_duck_race(bot, thread_id, thread_type, author_id, duck_number):
    try:
        player_choice = f"🦆 {duck_number}"
        
        if player_choice not in DUCKS:
            bot.send(
                Message(text=f"❌ Vịt bạn chọn không hợp lệ! Vui lòng chọn số vịt từ 1 đến {NUM_DUCKS}."),
                thread_id,
                thread_type
            )
            return

        # Show waiting first
        waiting_msg = bot.send(
            Message(text="🦆 Cuộc đua vịt sắp bắt đầu! Vui lòng chờ..."),
            thread_id,
            thread_type
        )
        if os.path.exists(WAITING_IMAGE):
            bot.sendLocalImage(WAITING_IMAGE, thread_id=thread_id, thread_type=thread_type)
        time.sleep(3)
        bot.send(Message(text="🏁 Cuộc đua vịt bắt đầu!"), thread_id, thread_type)

        if os.path.exists(DUCK_RACE_GIF):
            bot.sendLocalImage(DUCK_RACE_GIF, thread_id=thread_id, thread_type=thread_type)

        time.sleep(10)
        
        winner_duck = random.choice(DUCKS)
        winner_num = winner_duck.split()[1]
        race_image_path = os.path.join(BASE_DIR, 'winner_duck.png')
        create_duck_image(winner_num, race_image_path)

        if player_choice == winner_duck:
            response_text = f"🎉 Chúc mừng bạn! Vịt của bạn ({player_choice}) đã chiến thắng!"
        else:
            response_text = f"😢 Rất tiếc, vịt của bạn ({player_choice}) đã thua. Vịt thắng cuộc là {winner_duck}."
        
        bot.send(Message(text=response_text), thread_id, thread_type)
        
        if os.path.exists(race_image_path):
            bot.sendLocalImage(
                race_image_path,
                message=Message(text=f"Vịt thắng cuộc: {winner_duck}"),
                thread_id=thread_id,
                thread_type=thread_type
            )
            try:
                os.remove(race_image_path)
            except:
                pass

    except Exception as e:
        print(f"[ERROR] Lỗi khi bắt đầu đua vịt: {e}")
        bot.send(
            Message(text=f"Đã xảy ra lỗi khi bắt đầu đua vịt: {e}"),
            thread_id,
            thread_type
        )


def handle_duavit_command(bot, message_object, thread_id, thread_type, author_id, message):
    prefix = getattr(bot, 'prefix', '.')
    content = message.strip().split()
    
    if len(content) < 2:
        help_text = (
            f"🦆 Hướng dẫn chơi Đua Vịt!\n"
            f"➜ {prefix}duavit [số vịt] - Bắt đầu cuộc đua vịt\n"
            f"➜ Ví dụ: {prefix}duavit 3"
        )
        bot.send(
            Message(text=help_text),
            thread_id,
            thread_type
        )
        return
    
    duck_num_str = content[1]
    if not duck_num_str.isdigit():
        bot.send(
            Message(text="❌ Số vịt phải là số! Vui lòng nhập lại!"),
            thread_id,
            thread_type
        )
        return
    
    duck_num = int(duck_num_str)
    if duck_num < 1 or duck_num > NUM_DUCKS:
        bot.send(
            Message(text=f"❌ Vui lòng chọn số vịt từ 1 đến {NUM_DUCKS}!"),
            thread_id,
            thread_type
        )
        return
    
    start_duck_race(bot, thread_id, thread_type, author_id, duck_num)


txa = {
    "name": "DuaVit",
    "desc": {
        "duavit": "Đua vịt vui vẻ!"
    },
    "author": "TXA",
    "command": ["duavit"]
}


def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    handle_duavit_command(bot, message_object, thread_id, thread_type, author_id, message_text)
