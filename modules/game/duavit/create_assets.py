
from PIL import Image, ImageDraw, ImageFont
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

def create_waiting_image():
    img = Image.new('RGB', (400, 300), color='#4CAF50')
    draw = ImageDraw.Draw(img)
    try:
        font_emoji = ImageFont.truetype(os.path.join(ASSETS_DIR, 'NotoEmoji-Bold.ttf'), 40)
        font_text = ImageFont.truetype(os.path.join(ASSETS_DIR, 'arial.ttf'), 35)
    except:
        font_emoji = ImageFont.load_default()
        font_text = ImageFont.load_default()
    
    text = "⏳ Đang chờ..."
    emoji_len = draw.textlength("⏳", font=font_emoji)
    text_len = draw.textlength(text[1:], font=font_text)
    total_len = emoji_len + text_len
    x = (400 - total_len) / 2
    draw.text((x, 120), "⏳", fill='white', font=font_emoji)
    draw.text((x + emoji_len, 120), " Đang chờ...", fill='white', font=font_text)
    img.save(os.path.join(ASSETS_DIR, 'waiting.png'))

def create_duck_image():
    img = Image.new('RGB', (200, 200), color='#FFD700')
    draw = ImageDraw.Draw(img)
    try:
        font_emoji = ImageFont.truetype(os.path.join(ASSETS_DIR, 'NotoEmoji-Bold.ttf'), 100)
    except:
        font_emoji = ImageFont.load_default()
    text = "🦆"
    text_len = draw.textlength(text, font=font_emoji)
    x = (200 - text_len) / 2
    draw.text((x, 50), text, fill='white', font=font_emoji)
    img.save(os.path.join(ASSETS_DIR, 'duck.png'))

def create_duck_race_gif():
    frames = []
    for i in range(5):
        img = Image.new('RGB', (400, 300), color='#87CEEB')
        draw = ImageDraw.Draw(img)
        try:
            font_emoji = ImageFont.truetype(os.path.join(ASSETS_DIR, 'NotoEmoji-Bold.ttf'), 30)
            font_text = ImageFont.truetype(os.path.join(ASSETS_DIR, 'arial.ttf'), 28)
        except:
            font_emoji = ImageFont.load_default()
            font_text = ImageFont.load_default()
        
        text = f"🦆 Đua vịt... {i+1}"
        emoji_len = draw.textlength("🦆", font=font_emoji)
        text_len = draw.textlength(text[1:], font=font_text)
        total_len = emoji_len + text_len
        x = (400 - total_len) / 2
        draw.text((x, 120), "🦆", fill='white', font=font_emoji)
        draw.text((x + emoji_len, 120), f" Đua vịt... {i+1}", fill='white', font=font_text)
        frames.append(img)
    frames[0].save(os.path.join(ASSETS_DIR, 'duck_race.gif'), 
                   save_all=True, append_images=frames[1:], duration=500, loop=0)

if __name__ == "__main__":
    create_waiting_image()
    create_duck_image()
    create_duck_race_gif()
    print("Assets created successfully!")
