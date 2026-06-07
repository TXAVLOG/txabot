import requests
import json
import re
import urllib.parse
import os
import time
import random
import glob
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from io import BytesIO
import emoji
from colorsys import hsv_to_rgb, rgb_to_hsv
from zlapi.models import *

user_states = {}
SEARCH_TIMEOUT = 120

BACKGROUND_PATH = "background/"
CACHE_PATH = "modules/cache/"
os.makedirs(CACHE_PATH, exist_ok=True)

# Helper to clean NCT slug for nice titles
def clean_nct_slug(slug):
    words = slug.split("-")
    cleaned = " ".join(words).title()
    return cleaned

# Search NCT
def search_music_nct(keyword):
    api_url = "https://graph.nhaccuatui.com/api/v1/search/song"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nhaccuatui.com/",
        "Cache-Control": "no-cache"
    }
    songs = []

    try:
        params = {
            "keyword": keyword,
            "pageindex": 1,
            "pagesize": 20,
            "correct": "false"
        }
        r = requests.post(api_url, params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            songs_data = data.get("data", {}).get("songs", [])
            if isinstance(songs_data, list):
                for item in songs_data:
                    song_link = item.get("linkShare") or item.get("url") or ""
                    if song_link and song_link.startswith("/"):
                        song_link = "https://www.nhaccuatui.com" + song_link
                    title = item.get("name") or item.get("title") or clean_nct_slug(song_link.split("/")[-1].replace(".html", ""))
                    songs.append({
                        "id": item.get("key") or item.get("id") or title,
                        "songLink": song_link,
                        "title": title,
                        "artistsNames": item.get("artistName") or "NCT Artist",
                        "thumbnail": item.get("image") or "https://static.nct.vn/nct-web/nct-share.png",
                        "stream_urls": [
                            x.get("download") or x.get("stream")
                            for x in item.get("streamURL", [])
                            if isinstance(x, dict) and (x.get("download") or x.get("stream"))
                        ]
                    })
    except Exception as e:
        print("Search NCT API error:", e)

    # Fallback to HTML parsing if API search did not return anything
    if not songs:
        url = f"https://www.nhaccuatui.com/search?key={urllib.parse.quote(keyword)}"
        headers_html = {
            "User-Agent": headers["User-Agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.nhaccuatui.com/",
            "Cache-Control": "no-cache"
        }
        try:
            r = requests.get(url, headers=headers_html, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                script = soup.find("script", id="__NUXT_DATA__")
                if script:
                    try:
                        data = json.loads(script.string)
                        for item in data:
                            if isinstance(item, str) and "nhaccuatui.com/bai-hat/" in item and item.endswith(".html"):
                                parts = item.split("/")[-1].replace(".html", "").split(".")
                                if len(parts) >= 2:
                                    key = parts[-1]
                                    slug = parts[0]
                                    title = clean_nct_slug(slug)
                                    songs.append({
                                        "id": key,
                                        "songLink": item,
                                        "title": title,
                                        "artistsNames": "NCT Artist",
                                        "thumbnail": "https://static.nct.vn/nct-web/nct-share.png"
                                    })
                    except Exception as ex:
                        print("Error parsing search nuxt JSON:", ex)

                if not songs:
                    urls = re.findall(r'https?://www\.nhaccuatui\.com/bai-hat/[^\s\'"<>]+?\.html', r.text)
                    for item in urls:
                        try:
                            if not item.startswith("http"):
                                continue
                            parts = item.split("/")[-1].replace(".html", "").split(".")
                            if len(parts) >= 2:
                                key = parts[-1]
                                slug = parts[0]
                                title = clean_nct_slug(slug)
                                songs.append({
                                    "id": key,
                                    "songLink": item,
                                    "title": title,
                                    "artistsNames": "NCT Artist",
                                    "thumbnail": "https://static.nct.vn/nct-web/nct-share.png"
                                })
                        except Exception as url_ex:
                            print(f"Error processing URL {item}:", url_ex)
                            continue

                if not songs:
                    try:
                        for link in soup.find_all('a', href=re.compile(r'/bai-hat/')):
                            href = link.get('href')
                            if href and '/bai-hat/' in href:
                                if not href.startswith("http"):
                                    href = "https://www.nhaccuatui.com" + href
                                parts = href.split("/")[-1].replace(".html", "").split(".")
                                if len(parts) >= 2:
                                    key = parts[-1]
                                    slug = parts[0]
                                    title = clean_nct_slug(slug)
                                    songs.append({
                                        "id": key,
                                        "songLink": href,
                                        "title": title,
                                        "artistsNames": "NCT Artist",
                                        "thumbnail": "https://static.nct.vn/nct-web/nct-share.png"
                                    })
                    except Exception as ex:
                        print("Error parsing HTML links:", ex)
        except Exception as e:
            print("Search NCT error:", e)

    seen = set()
    unique_songs = []
    for s in songs:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique_songs.append(s)
    return unique_songs

# Stream URL & Details NCT
def get_nct_song_details(song_link):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.nhaccuatui.com/",
        "Cache-Control": "no-cache"
    }
    details = {
        "stream_url": None,
        "viewed": 0,
        "totalLiked": 0,
        "commentCnt": 0
    }
    try:
        r = requests.get(song_link, headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"Failed to fetch song page: {r.status_code}")
            return details
            
        soup = BeautifulSoup(r.text, 'html.parser')
        script = soup.find("script", id="__NUXT_DATA__")
        
        # Try NUXT data first
        if script:
            try:
                data = json.loads(script.string)
                for item in data:
                    if isinstance(item, dict):
                        if "viewed" in item and "totalLiked" in item:
                            viewed = item["viewed"]
                            if isinstance(viewed, int) and viewed < len(data):
                                viewed = data[viewed]
                            if isinstance(viewed, (int, float)):
                                details["viewed"] = int(viewed)
                                
                            totalLiked = item["totalLiked"]
                            if isinstance(totalLiked, int) and totalLiked < len(data):
                                totalLiked = data[totalLiked]
                            if isinstance(totalLiked, (int, float)):
                                details["totalLiked"] = int(totalLiked)

                            if "commentCnt" in item:
                                commentCnt = item["commentCnt"]
                                if isinstance(commentCnt, int) and commentCnt < len(data):
                                    commentCnt = data[commentCnt]
                                if isinstance(commentCnt, (int, float)):
                                    details["commentCnt"] = int(commentCnt)
                
                streams_128 = []
                streams_320 = []
                for item in data:
                    if isinstance(item, dict) and "stream" in item and "type" in item:
                        stream_val = item["stream"]
                        if isinstance(stream_val, int) and stream_val < len(data):
                            stream_url = data[stream_val]
                        else:
                            stream_url = stream_val
                            
                        if isinstance(stream_url, str) and stream_url.startswith("https://"):
                            type_val = item["type"]
                            if isinstance(type_val, int) and type_val < len(data):
                                stype = data[type_val]
                            else:
                                stype = type_val
                                
                            only_vip = item.get("onlyVIP", False)
                            if isinstance(only_vip, int) and only_vip < len(data):
                                only_vip = data[only_vip]
                                
                            if not only_vip:
                                if stype == "128":
                                    streams_128.append(stream_url)
                                elif stype == "320":
                                    streams_320.append(stream_url)
                if streams_320:
                    details["stream_url"] = streams_320[0]
                elif streams_128:
                    details["stream_url"] = streams_128[0]
                else:
                    for item in data:
                        if isinstance(item, str) and item.startswith("https://") and (".mp3" in item or ".m4a" in item) and ".nct.vn" in item:
                            details["stream_url"] = item
                            break
            except Exception as e:
                print(f"Error parsing NUXT data: {e}")
        
        if not details["stream_url"]:
            stream_urls = re.findall(r'https://[^\s"\'<>]+\.(?:mp3|m4a)(?:\?[^\s"\'<>]*)?', r.text)
            if stream_urls:
                found = False
                for url in stream_urls:
                    if '.nct.vn' in url or 'storage' in url:
                        details["stream_url"] = url
                        found = True
                        break
                if not found:
                    details["stream_url"] = stream_urls[0]
            else:
                mp3_pattern = r'https://[^\s"\'<>]*\.(?:mp3|m4a)(?:\?[^\s"\'<>]*)?'
                matches = re.findall(mp3_pattern, r.text)
                if matches:
                    details["stream_url"] = matches[0]
    except Exception as e:
        print(f"Error getting NCT details: {e}")
    return details


# Drawing utilities
def get_dominant_color(image_path):
    try:
        if not os.path.exists(image_path):
            return (0, 0, 0)
        img = Image.open(image_path).convert("RGB")
        img = img.resize((150, 150), Image.Resampling.LANCZOS)
        pixels = img.getdata()
        if not pixels:
            return (0, 0, 0)
        r, g, b = 0, 0, 0
        for pixel in pixels:
            r += pixel[0]
            g += pixel[1]
            b += pixel[2]
        total = len(pixels)
        if total == 0:
            return (0, 0, 0)
        return (r // total, g // total, b // total)
    except:
        return (0, 0, 0)

def random_contrast_color(base_color):
    r, g, b, _ = base_color
    box_luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    if box_luminance > 0.5:
        r, g, b = random.randint(0, 50), random.randint(0, 50), random.randint(0, 50)
    else:
        r, g, b = random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)
    h, s, v = rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    s = min(1.0, s + 0.9)
    v = min(1.0, v + 0.9)
    r, g, b = hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255), 255)

def format_number(number):
    if number is None:
        return "0"
    try:
        return f"{int(number):,}".replace(",", ".")
    except:
        return str(number)

def get_text_width(draw, text, font_used):
    bbox = draw.textbbox((0, 0), text, font=font_used)
    return bbox[2] - bbox[0]

def truncate_text(draw, text, max_width, font_text, font_emoji):
    result = ''
    total_width = 0
    for char in text:
        font_used = font_emoji if emoji.is_emoji(char) else font_text
        char_width = get_text_width(draw, char, font_used)
        if total_width + char_width > max_width:
            result += '...'
            break
        result += char
        total_width += char_width
    return result

def draw_text_with_shadow(draw, position, text, font, fill, shadow_color=(0, 0, 0, 150), shadow_offset=(2, 2)):
    x, y = position
    draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=fill)

def create_song_list_image(songs):
    try:
        scale = 2
        font_path = "font/arial unicode ms.otf"
        emoji_font_path = "font/NotoEmoji-Bold.ttf"
        font = ImageFont.truetype(font_path, 28 * scale)  
        artist_font = ImageFont.truetype(font_path, 20 * scale) 
        artist_emoji_font = ImageFont.truetype(emoji_font_path, 21 * scale)  
        emoji_font = ImageFont.truetype(emoji_font_path, 28 * scale) 
        number_font = ImageFont.truetype(font_path, 40 * scale)  
        info_font = ImageFont.truetype(font_path, 14 * scale) 
        info_emoji_font = ImageFont.truetype(emoji_font_path, 14 * scale)  

        card_height = 105 * scale  
        card_width = 583 * scale   
        thumb_size = 90 * scale    
        padding = 20 * scale      
        spacing_y = 10 * scale     
        spacing_x = 15 * scale
        card_padding = 8 * scale   

        songs_to_draw = songs[:20]
        N = len(songs_to_draw)
        
        # Dynamic column-splitting to optimize aspect ratio for mobile view (max 3 columns)
        if N <= 5:
            col_count = 1
            songs_per_col = N
        elif N <= 12:
            col_count = 2
            songs_per_col = (N + 1) // 2
        else:
            col_count = 3
            songs_per_col = (N + 2) // 3

        img_width = card_width * col_count + spacing_x * (col_count - 1) + 2 * padding
        img_height = padding * 2 + songs_per_col * card_height + (songs_per_col - 1) * spacing_y

        background_images = glob.glob(BACKGROUND_PATH + "*.jpg") + glob.glob(BACKGROUND_PATH + "*.png") + glob.glob(BACKGROUND_PATH + "*.jpeg")
        if not background_images:
            background = Image.new("RGBA", (img_width, img_height), (20, 20, 20, 255))
        else:
            background_path = random.choice(background_images)
            background = Image.open(background_path).convert("RGBA").resize((img_width, img_height), Image.Resampling.LANCZOS)
            background = background.filter(ImageFilter.GaussianBlur(radius=7)) 

        image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        image.paste(background, (0, 0))
        draw = ImageDraw.Draw(image)

        box_colors = [
            (255, 20, 147, 110),   
            (128, 0, 128, 110),    
            (0, 100, 0, 110),      
            (0, 0, 139, 110),      
            (184, 134, 11, 110),   
            (138, 3, 3, 110),      
            (0, 0, 0, 80)        
        ]
        box_color = random.choice(box_colors) 
        title_color = random_contrast_color(box_color)

        info_color = (255, 255, 255, 255)
        number_color = random_contrast_color(box_color)
        artist_color = (255, 255, 255, 255)  

        for i, song in enumerate(songs_to_draw):
            song_link = song["songLink"]
            title = song["title"]
            cover_url = song["thumbnail"]
            artists = song["artistsNames"]

            col = i // songs_per_col
            row = i % songs_per_col

            left = padding + col * (card_width + spacing_x)
            top = padding + row * (card_height + spacing_y)

            card_img = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
            card_draw = ImageDraw.Draw(card_img)
            radius = 20 * scale
            card_draw.rounded_rectangle([0, 0, card_width, card_height], radius=radius, fill=box_color)
            image.paste(card_img, (left, top), card_img.split()[3])

            if cover_url:
                try:
                    response = requests.get(cover_url, timeout=5)
                    cover = Image.open(BytesIO(response.content)).convert("RGB")
                    cover = ImageOps.fit(cover, (thumb_size, thumb_size), centering=(0.5, 0.5))
                    mask = Image.new("L", (thumb_size, thumb_size), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.ellipse((0, 0, thumb_size, thumb_size), fill=255)
                    cover.putalpha(mask)

                    border_size = thumb_size + 10
                    rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
                    draw_border = ImageDraw.Draw(rainbow_border)
                    steps = 360
                    for j in range(steps):
                        h = j / steps
                        r, g, b = hsv_to_rgb(h, 1.0, 1.0)
                        draw_border.arc([(0, 0), (border_size-1, border_size-1)], j, j + (360 / steps), fill=(int(r * 255), int(g * 255), int(b * 255), 255), width=5)
                    cover_y = top + (card_height - thumb_size) // 2
                    image.paste(rainbow_border, (left + card_padding - 5, cover_y - 5), rainbow_border)
                    image.paste(cover, (left + card_padding, cover_y), cover)
                except:
                    cover = Image.new("RGBA", (thumb_size, thumb_size), (60, 60, 60, 255))
                    image.paste(cover, (left + card_padding, top + card_padding), cover)
            else:
                cover = Image.new("RGBA", (thumb_size, thumb_size), (60, 60, 60, 255))
                image.paste(cover, (left + card_padding, top + card_padding), cover)

            x_text = left + card_padding + thumb_size + 20 * scale
            y_text = top + card_padding
            max_text_width = card_width - thumb_size - 3 * card_padding - 20 * scale
            truncated_title = truncate_text(draw, title, max_text_width, font, emoji_font)

            for char in truncated_title:
                font_used = emoji_font if emoji.is_emoji(char) else font
                draw_text_with_shadow(draw, (x_text, y_text), char, font_used, title_color)
                x_text += get_text_width(draw, char, font_used)

            x_artist = left + card_padding + thumb_size + 20 * scale
            y_artist = y_text + int(35 * scale)
            truncated_artist = truncate_text(draw, artists, max_text_width, artist_font, artist_emoji_font)
            for char in truncated_artist:
                font_used = artist_emoji_font if emoji.is_emoji(char) else artist_font
                draw_text_with_shadow(draw, (x_artist, y_artist), char, font_used, artist_color, shadow_offset=(1, 1))
                x_artist += get_text_width(draw, char, font_used)

            info_text = "Nền tảng: NhacCuaTui"
            x_info = left + card_padding + thumb_size + 20 * scale
            info_height = info_font.size
            y_info = top + card_height - card_padding - info_height
            for char in info_text:
                font_used = info_emoji_font if emoji.is_emoji(char) else info_font
                draw_text_with_shadow(draw, (x_info, y_info), char, font_used, info_color, shadow_offset=(1, 1))
                x_info += get_text_width(draw, char, font_used)

            number_text = str(i + 1)
            number_width = get_text_width(draw, number_text, number_font)
            number_x = left + card_width - number_width - card_padding
            number_y = top + (card_height - number_font.size) // 2
            draw_text_with_shadow(draw, (number_x, number_y), number_text, number_font, number_color)

        file_path = os.path.join(CACHE_PATH, "nct_song_list.png")
        image.convert("RGB").save(file_path, format="JPEG", quality=95, optimize=True)
        return file_path
    except Exception as e:
        print("Error in NCT list image drawing:", e)
        return None

def create_single_song_image(song):
    try:
        scale = 2
        font_path = "font/arial unicode ms.otf"
        emoji_font_path = "font/NotoEmoji-Bold.ttf"
        font = ImageFont.truetype(font_path, 32 * scale)
        emoji_font = ImageFont.truetype(emoji_font_path, 32 * scale)
        title_font = ImageFont.truetype(font_path, 48 * scale)
        emoji_title_font = ImageFont.truetype(emoji_font_path, 48 * scale)

        padding = 80 * scale
        thumb_size = 300 * scale

        img_width = 1200 * scale
        img_height = 420 * scale

        image = Image.new("RGB", (img_width, img_height), (25, 25, 25))
        draw = ImageDraw.Draw(image)

        title = song["title"]
        cover_url = song["thumbnail"]
        artists = song["artistsNames"]

        thumb = Image.new("RGB", (thumb_size, thumb_size), (50, 50, 50))
        if cover_url:
            try:
                response = requests.get(cover_url, timeout=5)
                thumb = Image.open(BytesIO(response.content)).convert("RGB")
                thumb = ImageOps.fit(thumb, (thumb_size, thumb_size), centering=(0.5, 0.5))

                mask = Image.new("L", (thumb_size, thumb_size), 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.ellipse((0, 0, thumb_size, thumb_size), fill=255)
                thumb.putalpha(mask)

                border_size = 8 * scale
                border = Image.new("RGBA", (thumb_size + border_size*2, thumb_size + border_size*2), (0, 0, 0, 0))
                border_draw = ImageDraw.Draw(border)
                border_draw.ellipse((0, 0, border.width, border.height), fill=(0, 255, 180, 255))
                border.paste(thumb, (border_size, border_size), thumb)
                thumb = border
            except:
                pass

        background = Image.new("RGB", (img_width, img_height), (25, 25, 25))
        if cover_url:
            try:
                response = requests.get(cover_url, timeout=5)
                background = Image.open(BytesIO(response.content)).convert("RGB")
                background = ImageOps.fit(background, (img_width, img_height), centering=(0.5, 0.5))
            except:
                pass

        overlay = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 128))
        image.paste(background, (0, 0))
        image.paste(overlay, (0, 0), overlay)
        image.paste(thumb, (padding, (img_height - thumb.height) // 2), thumb)

        base_colors = [(102, 204, 255), (255, 255, 180), (102, 255, 204)]
        colors = random.sample(base_colors, 3)

        def get_gradient_color(x, total_width):
            ratio = x / total_width
            if ratio < 0.5:
                c1, c2 = colors[0], colors[1]
                ratio *= 2
            else:
                c1, c2 = colors[1], colors[2]
                ratio = (ratio - 0.5) * 2
            r = int(c1[0] + (c2[0] - c1[0]) * ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * ratio)
            return (r, g, b)

        text_x = padding + thumb.width + 50 * scale
        max_text_width = img_width - text_x - padding

        def shorten_text(text, font, emoji_font):
            current_width = 0
            result = ""
            for char in text:
                f = emoji_font if emoji.emoji_count(char) else font
                char_width = f.getlength(char)
                if current_width + char_width > max_text_width:
                    result += "..."
                    break
                result += char
                current_width += char_width
            return result

        def draw_gradient_text_line(draw, text, x, y, font, emoji_font):
            shortened = shorten_text(text, font, emoji_font)
            total_width = sum((emoji_font if emoji.emoji_count(c) else font).getlength(c) for c in shortened)

            current_x = x
            for char in shortened:
                f = emoji_font if emoji.emoji_count(char) else font
                char_width = f.getlength(char)
                color = get_gradient_color(current_x - x, total_width)

                shadow_offset = 2
                draw.text((current_x + shadow_offset, y + shadow_offset), char, font=f, fill=(0, 0, 0, 120))
                draw.text((current_x, y), char, font=f, fill=color)
                current_x += char_width

            return y + int(font.size * 1.6)

        text_y = padding
        text_y = draw_gradient_text_line(draw, f"🎵 {title}", text_x, text_y, title_font, emoji_title_font)
        text_y = draw_gradient_text_line(draw, f"👤 Tác giả: {artists}", text_x, text_y, font, emoji_font)
        text_y = draw_gradient_text_line(draw, "🎯 Nền tảng: NhacCuaTui ☁️", text_x, text_y, font, emoji_font)

        viewed = song.get("viewed", 0)
        total_liked = song.get("totalLiked", 0)
        if viewed > 0 or total_liked > 0:
            draw_gradient_text_line(draw, f"👂 {viewed:,}   ❤️ {total_liked:,}".replace(",", "."), text_x, text_y, font, emoji_font)

        file_path = os.path.join(CACHE_PATH, "selected_song.png")
        image.save(file_path, format="JPEG", quality=95)
        return file_path
    except Exception as e:
        print("Error in create_single_song_image:", e)
        return None

def upload_to_uguu(file_path):
    try:
        with open(file_path, 'rb') as file:
            response = requests.post("https://uguu.se/upload", files={'files[]': file})
            return response.json().get('files')[0].get('url')
    except Exception as e:
        print("Upload to uguu error:", e)
        return None

def delete_file(file_path):
    try:
        os.remove(file_path)
    except:
        pass

# Command handler
def handle_nct_command(message, message_object, thread_id, thread_type, author_id, client):
    global user_states
    global SEARCH_TIMEOUT

    reactions = ["😍", "❤️", "/-ok", "👋", "🫠", "/-strong", "😂", "😉", "🥳", "🤩", "Dạ", "Yew", "Yes", "Ok", "Oki", "Uwu", "😃", "🥰"]

    if not message or not isinstance(message, str):
        return

    try:
        user_info = client.fetchUserInfo(author_id)
        if user_info and hasattr(user_info, 'changed_profiles') and author_id in user_info.changed_profiles:
            user = user_info.changed_profiles[author_id]
            username = getattr(user, 'name', None) or getattr(user, 'displayName', None) or f"ID_{author_id}"
        else:
            username = f"ID_{author_id}"
    except Exception as e:
        username = f"ID_{author_id}"

    content = message.strip().split()

    # Selection reply handling
    if len(content) == 2 and content[0].lower() in [f"{client.prefix}nct", f"{client.prefix}nhaccuatui"] and content[1].isdigit():
        if author_id not in user_states:
            return

        state = user_states[author_id]
        if time.time() - state['time_of_search'] > SEARCH_TIMEOUT:
            del user_states[author_id]
            text = f"🚦{username} Thời gian chọn bài hát đã hết hạn! Vui lòng tìm kiếm lại nhé."
            mention = Mention(author_id, offset=2, length=len(username)) if thread_type != ThreadType.USER else None
            msg = Message(text=text, mention=mention)
            client.send(msg, thread_id, thread_type, ttl=60000)
            return

        songs = state['songs']
        selector_index = int(content[1]) - 1 

        if selector_index < 0 or selector_index >= len(songs):
            text = f"🚦{username}, số thứ tự không hợp lệ: {content[1]}"
            mention = Mention(author_id, offset=2, length=len(username)) if thread_type != ThreadType.USER else None
            client.replyMessage(Message(text=text, mention=mention), message_object, thread_id, thread_type, ttl=60000)
            return

        # Recall the search image
        search_msg = state.get('search_msg')
        if search_msg and hasattr(search_msg, 'msgId') and hasattr(search_msg, 'cliMsgId'):
            try:
                client.undoMessage(search_msg.msgId, search_msg.cliMsgId, thread_id, thread_type)
            except Exception as e:
                print(f"[ERROR] Recall search image error: {e}")

        # Delete the user's original search query message
        query_msg_id = state.get('query_msg_id')
        query_cli_msg_id = state.get('query_cli_msg_id')
        if thread_type == ThreadType.GROUP and query_msg_id and query_cli_msg_id:
            try:
                client.deleteGroupMsg(query_msg_id, author_id, query_cli_msg_id, thread_id)
            except Exception as e:
                print(f"[ERROR] Delete search query msg error: {e}")

        # Delete the user's selection message
        if thread_type == ThreadType.GROUP and message_object and hasattr(message_object, 'msgId') and hasattr(message_object, 'cliMsgId'):
            try:
                client.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
            except Exception as e:
                print(f"[ERROR] Delete selection msg error: {e}")

        song = songs[selector_index]
        song_link = song["songLink"]
        title = song["title"]
        artists = song["artistsNames"]
        song_id = song["id"]

        text = f"""🚦{username} chọn: {content[1]}
📩 Tên Bài Hát: {title}
☁️ Nguồn: NhacCuaTui
⏳ Bé đang tải nhạc, đợi tí nha... 🎧"""
        mention = Mention(author_id, offset=2, length=len(username)) if thread_type != ThreadType.USER else None
        client.replyMessage(Message(text=text, mention=mention), message_object, thread_id, thread_type, ttl=60000)

        # Get stream url & stats
        nct_details = get_nct_song_details(song_link)
        stream_url = nct_details["stream_url"]
        song["viewed"] = nct_details["viewed"]
        song["totalLiked"] = nct_details["totalLiked"]
        song["commentCnt"] = nct_details["commentCnt"]

        if not stream_url:
            text = f"🚦{username}, không tìm thấy link stream hoặc bài hát yêu cầu tài khoản VIP 🤧"
            client.replyMessage(Message(text=text, mention=mention), message_object, thread_id, thread_type, ttl=60000)
            return

        # Single image
        song_image_path = create_single_song_image(song)

        # Download and upload
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            r_audio = requests.get(stream_url, headers=headers, timeout=20)
            temp_file = os.path.join(CACHE_PATH, f"nct_{song_id}.mp3")
            with open(temp_file, "wb") as f:
                f.write(r_audio.content)
            
            upload_url = upload_to_uguu(temp_file)
            delete_file(temp_file)

            if not upload_url:
                text = f"🚦{username}, không thể tải nhạc lên server trung gian 🤧"
                client.replyMessage(Message(text=text, mention=mention), message_object, thread_id, thread_type, ttl=60000)
                return

            if song_image_path and os.path.exists(song_image_path):
                with Image.open(song_image_path) as img:
                    w, h = img.size
                client.sendLocalImage(song_image_path, thread_id=thread_id, thread_type=thread_type, width=w, height=h, ttl=600000)
                delete_file(song_image_path)

            client.sendRemoteVoice(voiceUrl=upload_url, thread_id=thread_id, thread_type=thread_type, ttl=600000)

        except Exception as e:
            print("NCT play error:", e)
            client.replyMessage(Message(text=f"🚦{username}, đã xảy ra lỗi khi tải nhạc: {str(e)}"), message_object, thread_id, thread_type, ttl=60000)

        if author_id in user_states:
            del user_states[author_id]
        return

    # Help/No search keyword
    if len(content) < 2:
        action = random.choice(reactions)
        if random.random() > 0.3:
            client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        client.sendReaction(message_object, "TBOT OK ✅", thread_id, thread_type)
        
        caption = f"""🚦{username}
➜ Vui lòng nhập từ khóa tìm kiếm sau lệnh {client.prefix}nct 🎵
➜ Ví dụ: {client.prefix}nct dừng thương"""
        mention = Mention(author_id, offset=2, length=len(username)) if thread_type != ThreadType.USER else None
        client.replyMessage(Message(text=caption, mention=mention), message_object, thread_id, thread_type)
        return

    # Regular search query
    query = ' '.join(content[1:])
    action = random.choice(reactions)
    if random.random() > 0.3:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    client.sendReaction(message_object, "TBOT OK ✅", thread_id, thread_type)

    pending_msg = client.replyMessage(Message(text="⏳ Chờ bé một tí, đang tìm bài hát trên NhacCuaTui..."), message_object, thread_id, thread_type)
    songs = search_music_nct(query)

    if not songs:
        if pending_msg and hasattr(pending_msg, 'msgId') and hasattr(pending_msg, 'cliMsgId'):
            try:
                client.undoMessage(pending_msg.msgId, pending_msg.cliMsgId, thread_id, thread_type)
            except:
                pass
        text = f"🚦{username}, không tìm thấy bài hát nào trên NhacCuaTui."
        client.replyMessage(Message(text=text, mention=Mention(author_id, offset=2, length=len(username)) if thread_type != ThreadType.USER else None), message_object, thread_id, thread_type)
        return

    songs = songs[:20]
    user_states[author_id] = {
        'songs': songs,
        'time_of_search': time.time(),
        'query_msg_id': message_object.msgId if message_object else None,
        'query_cli_msg_id': message_object.cliMsgId if message_object else None
    }

    image_path = create_song_list_image(songs)
    if image_path:
        text = f"🚦{username}, Nhập {client.prefix}nct <số> để chọn nghe bài nhé! 🎧"
        mention = Mention(author_id, offset=2, length=len(username)) if thread_type != ThreadType.USER else None
        with Image.open(image_path) as img:
            w, h = img.size
        sent_msg = client.sendLocalImage(image_path, message=Message(text=text, mention=mention), thread_id=thread_id, thread_type=thread_type, width=w, height=h, ttl=600000)
        if sent_msg:
            user_states[author_id]['search_msg'] = sent_msg
        delete_file(image_path)
    else:
        text = f"🚦{username}, gặp lỗi khi tạo danh sách hình ảnh bài hát."
        client.replyMessage(Message(text=text, mention=Mention(author_id, offset=2, length=len(username)) if thread_type != ThreadType.USER else None), message_object, thread_id, thread_type)

    if pending_msg and hasattr(pending_msg, 'msgId') and hasattr(pending_msg, 'cliMsgId'):
        try:
            client.undoMessage(pending_msg.msgId, pending_msg.cliMsgId, thread_id, thread_type)
        except:
            pass


txa = {
    "name": "pro_ncl",
    "desc": "Nghe nhạc từ NhacCuaTui. Hỗ trợ tìm kiếm bài hát, playlist và gửi audio vào nhóm. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['ncl']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'ncl': handle_nct_command
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
