# -*- coding: UTF-8 -*-
import os
import re
import json
import time
import threading
import tempfile
import shutil
import subprocess
import yt_dlp
import psutil
from io import BytesIO
from typing import Optional, Tuple, Callable

CACHE_PATH = "modules/cache/"
os.makedirs(CACHE_PATH, exist_ok=True)

PLATFORM_REGEX = {
    'youtube': re.compile(
        r'(?:https?://)?(?:www\.|m\.)?(?:youtube\.com|youtu\.be)'
        r'(?:/watch\?v=|/embed/|/shorts/|/)([a-zA-Z0-9_-]{11,})',
        re.IGNORECASE
    ),
    'douyin': re.compile(
        r'(?:https?://)?(?:www\.)?(?:douyin\.com|iesdouyin\.com)'
        r'(?:/video/|/share/video/|/)(\d+)',
        re.IGNORECASE
    ),
    'facebook': re.compile(
        r'(?:https?://)?(?:www\.|m\.|mbasic\.)?'
        r'(?:facebook\.com|fb\.watch|fb\.com)'
        r'(?:/(?:watch/?\?v=|reel/|video/|share/|plugins/|(?:[^/]+/videos/)))?'
        r'\S*',
        re.IGNORECASE
    ),
    'tiktok': re.compile(
        r'https?://(?:www\.|m\.|vm\.|t\.)?tiktok\.com/\S+'
        r'|https?://vt\.tiktok\.com/\S+',
        re.IGNORECASE
    ),
}

PLATFORM_LABELS = {
    'youtube': 'YouTube',
    'douyin': 'Douyin',
    'facebook': 'Facebook',
    'tiktok': 'TikTok',
}

def detect_platform(url: str) -> Optional[str]:
    for platform, regex in PLATFORM_REGEX.items():
        if regex.search(url):
            return platform
    return None

def get_platform_label(platform: str) -> str:
    return PLATFORM_LABELS.get(platform, platform.capitalize())

def _fmt_size(bytes_val: int) -> str:
    if bytes_val >= 1_000_000_000:
        return f"{bytes_val/1_000_000_000:.2f} GB"
    if bytes_val >= 1_000_000:
        return f"{bytes_val/1_000_000:.2f} MB"
    if bytes_val >= 1_000:
        return f"{bytes_val/1_000:.2f} KB"
    return f"{bytes_val} B"

def check_storage(required_bytes: int) -> Tuple[bool, str]:
    try:
        disk = psutil.disk_usage(os.path.abspath('.'))
        free = disk.free
        if free >= required_bytes:
            return True, _fmt_size(free)
        return False, f"Còn {_fmt_size(free)}, cần {_fmt_size(required_bytes)}"
    except Exception as e:
        print(f"[StorageCheck] Error: {e}")
        return True, "Khong the kiem tra"

def get_video_info(url: str) -> dict:
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

def _progress_hook_factory(prefix: str, total: int) -> Callable:
    def hook(d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
            pct = (downloaded / total_bytes) * 100
            print(f"\r[{prefix}] Tien trinh: {pct:.1f}% ({_fmt_size(downloaded)}/{_fmt_size(total_bytes)})      ", end='', flush=True)
        elif d['status'] == 'finished':
            print(f"\n[{prefix}] Da tai xong file goc.")
    return hook

def download_video(url: str, output_template: str = None) -> Optional[str]:
    if not output_template:
        output_template = os.path.join(CACHE_PATH, f"%(id)s_%(title)s.%(ext)s")
    try:
        opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_template,
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [_progress_hook_factory('DL_VIDEO', 0)],
            'postprocessor_args': ['-threads', '0'],
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                for ext in ['.mp4', '.mkv', '.webm']:
                    p = base + ext
                    if os.path.exists(p):
                        filename = p
                        break
            if os.path.exists(filename):
                return filename
        return None
    except Exception as e:
        print(f"[yt-dlp] download_video error: {e}")
        return None

def download_audio(url: str, output_template: str = None) -> Optional[str]:
    if not output_template:
        output_template = os.path.join(CACHE_PATH, f"%(id)s_%(title)s.%(ext)s")
    try:
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [_progress_hook_factory('DL_AUDIO', 0)],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'postprocessor_args': ['-threads', '0'],
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            filename = os.path.splitext(filename)[0] + '.mp3'
            if os.path.exists(filename):
                return filename
            for f in os.listdir(CACHE_PATH):
                if f.startswith(info.get('id', '')) and f.endswith('.mp3'):
                    return os.path.join(CACHE_PATH, f)
        return None
    except Exception as e:
        print(f"[yt-dlp] download_audio error: {e}")
        return None

def convert_to_m4a(mp3_path: str) -> str:
    m4a_path = mp3_path.rsplit('.', 1)[0] + '.m4a'
    try:
        if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) < 1024:
            return mp3_path
        file_size = os.path.getsize(mp3_path)
        is_long = file_size > 8 * 1024 * 1024
        cmd = ['ffmpeg', '-y', '-threads', '0', '-i', mp3_path,
               '-vn', '-sn', '-dn', '-c:a', 'aac']
        if is_long:
            cmd += ['-ac', '1', '-b:a', '96k']
        else:
            cmd += ['-b:a', '128k']
        cmd += ['-movflags', '+faststart', m4a_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(m4a_path) and os.path.getsize(m4a_path) > 0:
            return m4a_path
    except Exception as e:
        print(f"[Convert] Loi convert m4a: {e}")
    if os.path.exists(m4a_path):
        try:
            os.remove(m4a_path)
        except:
            pass
    return mp3_path

def upload_file(file_path: str, mime_type: str = "video/mp4") -> Optional[str]:
    try:
        import requests
        with open(file_path, "rb") as f:
            files = {'fileToUpload': (os.path.basename(file_path), f, mime_type)}
            resp = requests.post("https://catbox.moe/user/api.php",
                                 files=files, data={"reqtype": "fileupload"}, timeout=300)
        if resp.status_code == 200:
            url = resp.text.strip()
            if url and not url.startswith("http"):
                url = "https://files.catbox.moe/" + url
            return url
    except Exception as e:
        print(f"[Upload] Catbox error: {e}")
    try:
        import requests
        with open(file_path, 'rb') as f:
            resp = requests.post("https://uguu.se/upload", files={'files[]': f}, timeout=300)
        if resp.status_code == 200:
            return resp.json().get('files')[0].get('url')
    except Exception as e:
        print(f"[Upload] Uguu error: {e}")
    return None

def extract_urls_from_message(message_text: str, message_object) -> list:
    urls = set()
    url_pattern = re.compile(
        r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s<>"\'()\[\]{}]*',
        re.IGNORECASE
    )
    if message_text:
        for m in url_pattern.finditer(message_text):
            urls.add(m.group(0).rstrip('.,;:!?)'))
    if message_object:
        obj_dict = None
        if hasattr(message_object, '__dict__'):
            obj_dict = vars(message_object)
        elif isinstance(message_object, dict):
            obj_dict = message_object
        if obj_dict:
            def _walk(val, depth=0):
                if depth > 3:
                    return
                if isinstance(val, str):
                    for m in url_pattern.finditer(val):
                        urls.add(m.group(0).rstrip('.,;:!?)'))
                elif isinstance(val, dict):
                    for v in val.values():
                        _walk(v, depth + 1)
                elif isinstance(val, (list, tuple)):
                    for v in val:
                        _walk(v, depth + 1)
            _walk(obj_dict)
    return list(urls)
