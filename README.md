# 🌟 TXA Zalo Bot 🌟

Chào mừng bạn đến với **TXA Zalo Bot** — hệ thống Zalo Bot thông minh, mượt mà và hỗ trợ hoạt động 24/7 trên môi trường Termux (Android) lẫn Linux/VPS. **Dùng file `ins.sh` để auto setup nhanh chóng cho mọi hệ điều hành!**

---

## 📋 Mục lục
1. [Giới thiệu](#-giới-thiệu)
2. [Cấu trúc thư mục cần tạo](#-cấu-trúc-thư-mục-cần-tạo)
3. [Hướng dẫn cài đặt trên Termux (Android)](#-hướng-dẫn-cài-đặt-trên-termux-android)
4. [Hướng dẫn cài đặt trên Linux/VPS](#-hướng-dẫn-cài-đặt-trên-linuxvps)
5. [Hướng dẫn chạy Bot 24/7 không bị tắt](#-hướng-dẫn-chạy-bot-247-không-bị-tắt)
6. [Lưu ý quan trọng](#⚠️-lưu-ý-quan-trọng)

---

## 🚀 Giới thiệu
Dự án được tối ưu hóa để chạy nhẹ nhàng, tự động cài đặt các thư viện cần thiết, sửa lỗi font/emoji và đi kèm script giám sát tự động khởi động lại khi gặp lỗi (crash).

* **Tác giả:** TXA
* **Môi trường khuyến nghị:** Termux (Android 10+) hoặc VPS Linux (Ubuntu/Debian)

---

## 📁 Cấu trúc thư mục cần tạo
Để bảo mật tài khoản Zalo của bạn, bạn cần tự tạo các tệp tin cấu hình sau:
* `txa.json` (Chứa cookie, imei đăng nhập Zalo)
* `config.json` (Cấu hình bot)
* `*_setting.json` (Các cài đặt nhóm/người dùng)

**Ví dụ nội dung `txa.json`:**
```json
{
  "cookie": "zpw_sek=...; other_cookies=...",
  "imei": "your_imei_here",
  "phone": "your_phone_number"
}
```

**Ví dụ nội dung `config.json`:**
```json
{
  "prefix": "!",
  "admin_bot": ["your_admin_id"],
  "high_level_admins": ["your_high_level_admin_id"]
}
```

---

## 📱 Hướng dẫn cài đặt trên Termux (Android)

Thực hiện lần lượt các bước sau trong ứng dụng Termux của bạn:

### Bước 1: Cập nhật Termux và cài đặt Git
```bash
pkg update -y && pkg upgrade -y
pkg install -y git
```

### Bước 2: Clone Repository về Termux
```bash
git clone https://github.com/TXAVLOG/txabot.git
# Hoặc dùng repo của bạn
```

### Bước 3: Di chuyển vào thư mục bot
```bash
cd txabot
```

### Bước 4: Tạo các tệp cấu hình bảo mật
Tạo và chỉnh sửa các tệp `txa.json`, `config.json` bằng trình soạn thảo `nano`:
```bash
nano txa.json
# Dán nội dung txa.json của bạn vào, sau đó nhấn Ctrl+O (Enter) rồi Ctrl+X để thoát.
```

### Bước 5: Cấp quyền và chạy Script Auto Setup / Run
```bash
chmod +x ins.sh
./ins.sh
```
*Script sẽ tự động kiểm tra hệ điều hành, cài đặt các package C/C++ cần thiết cho Python, tạo môi trường ảo `.venv`, cài đặt thư viện từ `requirements.txt` và bắt đầu chạy giám sát 24/7.*

---

## � Hướng dẫn cài đặt trên Linux/VPS

Thực hiện lần lượt các bước sau:

### Bước 1: Cập nhật hệ thống và cài đặt dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-pip python3-venv python3-dev build-essential libjpeg-dev zlib1g-dev
```

### Bước 2: Clone Repository
```bash
git clone https://github.com/TXAVLOG/txabot.git
cd txabot
```

### Bước 3: Tạo các tệp cấu hình bảo mật
Tạo `txa.json` và `config.json` như hướng dẫn ở phần [Cấu trúc thư mục cần tạo](#-cấu-trúc-thư-mục-cần-tạo).

### Bước 4: Chạy Script Auto Setup / Run
```bash
chmod +x ins.sh
./ins.sh
```

---

## �🔋 Hướng dẫn chạy Bot 24/7 không bị tắt

### Trên Termux (Android)
Hệ điều hành Android rất nghiêm ngặt trong việc tiết kiệm pin và sẽ tắt Termux khi bạn khóa màn hình hoặc ứng dụng chạy ngầm quá lâu. Làm theo các bước sau để đảm bảo bot chạy vĩnh viễn:

#### 1. Kích hoạt Termux Wake Lock (Giữ thiết bị luôn hoạt động ngầm)
Vuốt thanh thông báo từ trên xuống, nhấn vào nút **"Acquire Wake Lock"** trên thông báo của Termux.
Hoặc bạn có thể chạy lệnh này trong Termux:
```bash
termux-wake-lock
```

#### 2. Tắt Tối ưu hóa Pin cho Termux (Battery Optimization)
* Vào **Cài đặt điện thoại** -> **Ứng dụng** -> **Quản lý ứng dụng** -> Tìm **Termux**.
* Chọn mục **Pin** hoặc **Tiết kiệm pin**.
* Chọn **Không giới hạn (No restrictions)** hoặc **Tắt tối ưu hóa pin**.

#### 3. Sử dụng `tmux` để tắt ứng dụng mà bot vẫn chạy
Để bạn có thể đóng cửa sổ Termux hoặc vuốt tắt ứng dụng mà tiến trình bot vẫn tiếp tục chạy ngầm:
1. Cài đặt tmux:
   ```bash
   pkg install tmux -y
   ```
2. Khởi tạo một session tmux mới:
   ```bash
   tmux new -s bot
   ```
3. Chạy lệnh start bot trong session này:
   ```bash
   ./ins.sh
   ```
4. Để thoát ra màn hình Termux ngoài mà bot vẫn chạy ngầm (Detach):
   * Nhấn tổ hợp phím: `Ctrl + B` sau đó nhả ra và nhấn phím `D`.
5. Bây giờ bạn có thể đóng Termux thoải mái.
6. Để quay trở lại theo dõi log bot (Attach):
   ```bash
   tmux a -t bot
   ```

### Trên Linux/VPS
Sử dụng `tmux` hoặc `screen` để giữ bot chạy 24/7:

#### Sử dụng `tmux`:
1. Cài đặt tmux:
   ```bash
   sudo apt install tmux -y
   ```
2. Khởi tạo session:
   ```bash
   tmux new -s bot
   ```
3. Chạy bot:
   ```bash
   ./ins.sh
   ```
4. Detach: `Ctrl + B` rồi `D`
5. Attach lại:
   ```bash
   tmux a -t bot
   ```

---

## 🎵 Hướng dẫn cài đặt FFmpeg (Yêu cầu cho tính năng nhạc)

Bot sử dụng FFmpeg để chuyển đổi định dạng nhạc sang m4a giúp thiết bị iOS nghe được voice tin nhắn. Nếu hệ thống tự động cài đặt không thành công, hãy cài đặt thủ công theo hướng dẫn bên dưới:

<details>
<summary><b>💻 Windows</b></summary>

### Cách 1: Sử dụng Winget (Khuyến nghị)
Mở PowerShell (Run as Administrator) và chạy lệnh:
```bash
winget install Gyan.FFmpeg
```
Sau đó khởi động lại Terminal/PowerShell của bạn.

### Cách 2: Tải thủ công
1. Tải bản build của FFmpeg từ trang chủ: [ffmpeg.org](https://ffmpeg.org/download.html) hoặc [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/).
2. Giải nén thư mục và copy thư mục `bin` (chứa `ffmpeg.exe`) vào ổ đĩa mong muốn (ví dụ `C:\ffmpeg\bin`).
3. Thêm đường dẫn `C:\ffmpeg\bin` vào biến môi trường `PATH` của hệ thống.
</details>

<details>
<summary><b>📱 Termux (Android)</b></summary>

Chạy lệnh sau trong ứng dụng Termux:
```bash
pkg update && pkg install -y ffmpeg
```
</details>

<details>
<summary><b>🐧 Linux / VPS (Ubuntu, Debian, CentOS, Arch)</b></summary>

### Trên Ubuntu / Debian:
```bash
sudo apt update && sudo apt install -y ffmpeg
```

### Trên CentOS / RHEL:
```bash
sudo yum install epel-release -y
sudo yum install ffmpeg ffmpeg-devel -y
```

### Trên Arch Linux:
```bash
sudo pacman -S ffmpeg
```
</details>

<details>
<summary><b>🍎 macOS</b></summary>

Yêu cầu đã cài đặt [Homebrew](https://brew.sh/). Mở Terminal và chạy:
```bash
brew install ffmpeg
```
</details>

---

## ⚠️ Lưu ý quan trọng
* Không chia sẻ thư mục chứa `txa.json` và `config.json` cho bất cứ ai.
* Nếu bot Zalo bị mất kết nối, hãy kiểm tra lại Cookie/IMEI trong `txa.json`.
* Nguồn ảnh font lỗi emoji đã được cập nhật thành `font/NotoEmoji-Bold.ttf` giúp hiển thị emoji hoàn hảo.
* **Termux/Android**: Script `ins.sh` sẽ tự động cài đặt gói `python-psutil` từ repo Termux để có thể dùng các lệnh `details` và `uptime` đầy đủ.

---
*Chúc bạn chạy Bot thành công! Bản quyền thuộc về **TXA**.*
