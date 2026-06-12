import colorsys
from datetime import datetime
import glob
import os
import random
import threading
import subprocess
import time
from bs4 import BeautifulSoup
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import pytz
import requests
from io import BytesIO
from core.bot_sys import get_user_name_by_id, is_admin, read_settings, write_settings, convert_to_m4a
from zlapi.models import *

BACKGROUND_PATH = "background/"
CACHE_PATH = "modules/cache/"
OUTPUT_IMAGE_PATH = os.path.join(CACHE_PATH, "news.png")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

URL_VNEXPRESS = "https://vnexpress.net/"
URL_TUOITRE = "https://tuoitre.vn/"
URL_ZINGNEWS = "https://zingnews.vn/"
URL_DANTRI = "https://dantri.com.vn/tin-moi-nhat.htm"
URL_VOV = "https://vov.vn/"
URL_THETHAO247 = "https://thethao247.vn/"
URL_CAFEF = "https://cafef.vn/"

def handle_news_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "news" not in settings:
        settings["news"] = {}
    settings["news"][thread_id] = True
    write_settings(bot.uid, settings)
    return f"🚦Lệnh {bot.prefix}news đã được Bật 🚀 trong nhóm này ✅"

def handle_news_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "news" in settings and thread_id in settings["news"]:
        settings["news"][thread_id] = False
        write_settings(bot.uid, settings)
        return f"🚦Lệnh {bot.prefix}news đã Tắt ⭕️ trong nhóm này ✅"
    return "🚦Nhóm chưa có thông tin cấu hình news để ⭕️ Tắt 🤗"

def news(bot, message_object, author_id, thread_id, thread_type, command):
    def send_news_response():
        try:
            settings = read_settings(bot.uid)
    
            user_message = command.replace(f"{bot.prefix}news ", "").strip().lower()
            if user_message == "on":
                if not is_admin(bot, author_id):  
                    response = "❌Bạn không phải admin bot!"
                else:
                    response = handle_news_on(bot, thread_id)
                bot.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
                return
            elif user_message == "off":
                if not is_admin(bot, author_id):  
                    response = "❌Bạn không phải admin bot!"
                else:
                    response = handle_news_off(bot, thread_id)
                bot.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
                return
            
            if not (settings.get("news", {}).get(thread_id, False)):
                return
            
            elif user_message == "list":
                response = (
                    "🚦 Danh sách nguồn tin tức hỗ trợ:\n"
                    "➜ 1. cafef\n"
                    "➜ 2. dantri\n"
                    "➜ 3. thethao247\n"
                    "➜ 4. tuoitre\n"
                    "➜ 5. vnexpress\n"
                    f"➜ 6. zingnews\n"
                    "➜ 7. vov\n"
                    f"📌 Sử dụng: {bot.prefix}news [số lượng] [tên nguồn] hoặc {bot.prefix}news [số lượng] tổng hợp"
                )
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                return

            bot_prefix = f"{bot.prefix}news"
            parts = command.split()
            if len(parts) == 1:
                response = (
                    f"{get_user_name_by_id(bot, author_id)}\n"
                    f"➜ {bot_prefix} [số lượng]: Lấy tin ngẫu nhiên từ tất cả các nguồn (tối đa 5 tin).\n"
                    f"➜ {bot_prefix} [số lượng] [tên nguồn]: Lấy tin từ nguồn cụ thể.\n"
                    f"➜ {bot_prefix} [số lượng] tổng hợp: Lấy tin ngẫu nhiên từ tất cả các nguồn.\n"
                    f"➜ {bot_prefix} list: Xem danh sách nguồn tin tức hiện tại.\n"
                    "🤖 BOT luôn sẵn sàng phục vụ bạn! 🌸"
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
                return  # Thêm return để tránh lỗi tiếp tục xử lý

            try:
                num_articles = int(parts[1])
                if num_articles <= 0 or num_articles > 5:
                    raise ValueError
            except ValueError:
                response = "➜ ❌ Vui lòng nhập số lượng tin hợp lệ (số nguyên dương, tối đa 5)."
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                return

            # Danh sách nguồn tin tức (chỉ giữ các nguồn đã có hàm)
            news_sources = {
                "vnexpress": get_news_vnexpress,
                "tuoitre": get_news_tuoitre,
                "zingnews": get_news_zingnews,
                "dantri": get_news_dantri,
                "vov": get_news_vov,
                "thethao247": get_news_thethao247,
                "cafef": get_news_cafef
            }

            # Ánh xạ tên nguồn nhân hóa cho voice
            source_names_humanized = {
                "vnexpress": "VNExpress chấm net",
                "tuoitre": "Tuổi Trẻ chấm VN",
                "zingnews": "Zing News chấm VN",
                "dantri": "Dân Trí chấm com chấm VN",
                "vov": "VOV chấm VN",
                "thethao247": "Thể Thao Hai Bốn Bảy chấm VN",
                "cafef": "CafeF chấm VN"
            }

            articles = []
            sent_links = set()
            source_name = None

            # Xử lý nguồn tin tức
            if len(parts) >= 3:
                source_name = parts[2].lower()
                if source_name in news_sources:
                    try:
                        news = news_sources[source_name]()
                        if news:
                            unique_articles = [article for article in news if article['link'] not in sent_links]
                            if len(unique_articles) >= num_articles:
                                articles = random.sample(unique_articles, num_articles)
                            else:
                                articles = unique_articles
                            sent_links.update(article['link'] for article in articles)
                    except Exception as e:
                        print(f"Lỗi khi lấy tin từ nguồn {source_name}: {e}")
                elif source_name == "tổng hợp":
                    for source in news_sources.values():
                        if len(articles) >= num_articles:
                            break
                        try:
                            news = source()
                            if news:
                                unique_articles = [article for article in news if article['link'] not in sent_links]
                            if unique_articles:
                                random_article = random.choice(unique_articles)
                                articles.append(random_article)
                                sent_links.add(random_article['link'])
                        except Exception as e:
                            print(f"Lỗi khi lấy tin từ nguồn {source.__name__}: {e}")
                else:
                    response = f"➜ ❌ Nguồn '{source_name}' không hợp lệ. Xem danh sách bằng '{bot_prefix} list'."
                    bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                    return
            else:
                for source in news_sources.values():
                    if len(articles) >= num_articles:
                        break
                    try:
                        news = source()
                        if news:
                            unique_articles = [article for article in news if article['link'] not in sent_links]
                            if unique_articles:
                                random_article = random.choice(unique_articles)
                                articles.append(random_article)
                                sent_links.add(random_article['link'])
                    except Exception as e:
                        print(f"Lỗi khi lấy tin từ nguồn {source.__name__}: {e}")

            if len(articles) < num_articles:
                response = f"➜ ❌ Chỉ lấy được {len(articles)} tin tức từ nguồn."
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
            else:
                if source_name in news_sources:
                    summary_text = f"Tin tức từ {source_names_humanized[source_name]} hôm nay:\n"
                else:
                    summary_text = "Tin tức tổng hợp hôm nay:\n"

                for i, article in enumerate(articles, 1):
                    title = article.get('title', 'Không có tiêu đề')
                    description = article.get('description', 'Không có mô tả.')
                    link = article.get('link', '#')
                    thumbnail = article.get('thumbnail', None)

                    detailed_message = (
                        f"📰 [Tin {i}: {title}]\n"
                        f"📝 Mô tả: {description}\n"
                    )
                    bot.sendLink(
                        link,
                        title=title,
                        thread_id=thread_id,
                        thread_type=thread_type,
                        message=Message(text=detailed_message),
                        ttl=100000
                    )
                    summary_text += f"Tin {i}: {title}.\n"
                    time.sleep(2)

                try:
                    print("Bắt đầu tạo voice clip...")
                    mp3_file_path = create_voice_clip(summary_text)
                    if mp3_file_path and os.path.exists(mp3_file_path):

                        m4a_file = convert_to_m4a(mp3_file_path)
                        uploaded_url = upload_to_uguu(m4a_file)
                        if uploaded_url:
                            bot.sendRemoteVoice(
                                uploaded_url,
                                thread_id,
                                thread_type,
                                fileSize=os.path.getsize(m4a_file),
                                ttl=100000
                            )
                        if m4a_file != mp3_file_path:
                            try:
                                os.remove(m4a_file)
                            except:
                                pass
                        try:
                            os.remove(mp3_file_path)
                        except:
                            pass
                except Exception as e:
                    print(f"Lỗi khi xử lý voice: {e}")
                    bot.replyMessage(Message(text="➜ ❌ Không thể tạo hoặc gửi voice clip."), message_object, thread_id=thread_id, thread_type=thread_type)

        except Exception as e:
            print(f"Error: {e}")
            bot.replyMessage(Message(text="➜ 🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type)

    thread = threading.Thread(target=send_news_response)
    thread.start()

def get_news_vnexpress():
    try:
        response = requests.get(URL_VNEXPRESS, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select("article.item-news")[:5]:
            title_element = item.select_one("h3.title-news a")
            desc_element = item.select_one("p.description a")
            thumb_element = item.select_one("img")
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": title_element["href"].strip() if title_element else "#",
                "description": desc_element.text.strip() if desc_element else "Không có mô tả.",
                "thumbnail": thumb_element["data-src"] if thumb_element and "data-src" in thumb_element.attrs else None
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ VNExpress: {e}")
        return []

def get_news_tuoitre():
    try:
        response = requests.get(URL_TUOITRE, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select(".box-category-item")[:5]:
            title_element = item.select_one("h3 a")
            desc_element = item.select_one(".box-category-lead")
            thumb_element = item.select_one("img")
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": "https://tuoitre.vn" + title_element["href"].strip() if title_element else "#",
                "description": desc_element.text.strip() if desc_element else "Không có mô tả.",
                "thumbnail": thumb_element["src"] if thumb_element and "src" in thumb_element.attrs else None
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ Tuổi Trẻ: {e}")
        return []

def get_news_zingnews():
    try:
        response = requests.get(URL_ZINGNEWS, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select(".article-item")[:5]:
            title_element = item.select_one("p.article-title a")
            desc_element = item.select_one("p.article-summary")
            thumb_element = item.select_one("p.article-thumbnail img")
            link = title_element["href"].strip() if title_element else "#"
            if not link.startswith("https"):
                link = "https://zingnews.vn" + link
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": link,
                "description": desc_element.text.strip() if desc_element else "Không có mô tả.",
                "thumbnail": thumb_element["src"] if thumb_element and "src" in thumb_element.attrs else None
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ Zing News: {e}")
        return []

def get_news_dantri():
    try:
        response = requests.get(URL_DANTRI, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select("article.article-item")[:5]:
            title_element = item.select_one("h3.article-title a")
            desc_element = item.select_one(".article-excerpt")
            thumb_element = item.select_one(".article-thumb img")
            link = title_element["href"].strip() if title_element else "#"
            if not link.startswith("https"):
                link = "https://dantri.com.vn" + link
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": link,
                "description": desc_element.text.strip() if desc_element else "Không có mô tả.",
                "thumbnail": thumb_element["src"] if thumb_element and "src" in thumb_element.attrs else None
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ Dân Trí: {e}")
        return []

def get_news_vov():
    try:
        response = requests.get(URL_VOV, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select(".carousel .item .article-card")[:5]:
            title_element = item.select_one(".vovvn-title h3")
            link_element = item.select_one(".vovvn-title")
            desc_element = item.select_one(".sapo")
            thumb_element = item.select_one("img")
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": URL_VOV.rstrip('/') + link_element["href"].strip() if link_element else "#",
                "description": desc_element.text.strip() if desc_element else "Không có mô tả.",
                "thumbnail": thumb_element["src"] if thumb_element and "src" in thumb_element.attrs else None
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ VOV: {e}")
        return []

def get_news_thethao247():
    try:
        response = requests.get(URL_THETHAO247, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select(".bot-pick ul li")[:5]:
            title_element = item.select_one("h2 a")
            link_element = item.select_one("a")
            desc_element = item.select_one(".sapo")
            thumb_element = item.select_one("img")
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": link_element["href"].strip() if link_element else "#",
                "description": desc_element.text.strip() if desc_element else "Không có mô tả.",
                "thumbnail": thumb_element["src"] if thumb_element and "src" in thumb_element.attrs else None
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ Thể Thao 247: {e}")
        return []

def get_news_cafef():
    try:
        response = requests.get(URL_CAFEF, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select(".tlitem")[:5]:
            title_element = item.select_one("h3 a")
            desc_element = item.select_one(".sapo")
            thumb_element = item.select_one("img")
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": "https://cafef.vn" + title_element["href"].strip() if title_element else "#",
                "description": desc_element.text.strip() if desc_element else "Không có mô tả.",
                "thumbnail": thumb_element["src"] if thumb_element and "src" in thumb_element.attrs else None
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ CafeF: {e}")
        return []

def create_voice_clip(text):
    try:
        tts = gTTS(text, lang='vi', slow=False)
        mp3_file_path = "news_summary.mp3"
        tts.save(mp3_file_path)
        return mp3_file_path
    except Exception as e:
        print(f"Lỗi khi tạo voice clip: {e}")
        return None

def upload_to_uguu(file_path):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    }
    try:
        with open(file_path, 'rb') as file:
            files = {'files[]': file}
            print(f"➜ Uploading file to Uguu: {file_path}")
            response = requests.post("https://uguu.se/upload", files=files, headers=headers)
            response.raise_for_status()
        result = response.json()
        if result.get("success"):
            print(f"➜ Upload thành công: {result['files'][0]['url']}")
            return result["files"][0]["url"]
        else:
            print(f"Upload thất bại: {result}")
            return None
    except Exception as e:
        print(f"➜ Lỗi khi upload file lên Uguu: {e}")
        return None

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
            "🌤️": (200, 150, 50, 255)
        }

        text_lines = [
            f"Hi, {greeting_name}",
            f"💞 Chào Bạn, tôi có thể giúp gì cho bạn ạ?",
            f"{bot.prefix}news on/off: 🚀 Bật/Tắt tính năng",
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

        right_icons = ["🔔"]
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

txa = {
    "name": "pro_news",
    "desc": "Đọc tin tức mới nhất từ các nguồn uy tín. Hỗ trợ xem tin theo danh mục và gửi vào nhóm. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['news']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'news': news
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
