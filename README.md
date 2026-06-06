# 🌟 TXA Zalo Bot 🌟

Chào mừng bạn đến với **TXA Zalo Bot** — hệ thống Zalo Bot thông minh, mượt mà và hỗ trợ hoạt động 24/7 trên môi trường Termux (Android) lẫn Linux/VPS.

---

## 📋 Mục lục
1. [Giới thiệu](#-giới thiệu)
2. [Cấu trúc thư mục bị ẩn (.gitignore)](#-cấu-trúc-thư-mục-bị-ẩn-gitignore)
3. [Hướng dẫn cài đặt trên Termux (Android)](#-hướng-dẫn-cài-đặt-trên-termux-android)
4. [Hướng dẫn chạy Bot 24/7 không bị tắt](#-hướng-dẫn-chạy-bot-247-không-bị-tắt)
5. [Lưu ý quan trọng](#⚠️-lưu-ý-quan-trọng)

---

## 🚀 Giới thiệu
Dự án được tối ưu hóa để chạy nhẹ nhàng, tự động cài đặt các thư viện cần thiết, sửa lỗi font/emoji và đi kèm script giám sát tự động khởi động lại khi gặp lỗi (crash).

* **Tác giả:** TXA
* **Môi trường khuyến nghị:** Termux (Android 10+) hoặc VPS Linux (Ubuntu/Debian)

---

## 📁 Cấu trúc thư mục bị ẩn (.gitignore)
Để bảo mật tài khoản Zalo của bạn, các tệp tin chứa thông tin nhạy cảm dưới đây **không** được đẩy lên GitHub. Bạn cần sao chép thủ công các tệp này từ máy tính sang điện thoại sau khi clone repo:
* `txa.json` (Chứa cookie, imei đăng nhập Zalo)
* `config.json` (Cấu hình bot)
* `*_setting.json` (Các cài đặt nhóm/người dùng)

---

## 📱 Hướng dẫn cài đặt trên Termux (Android)

Thực hiện lần lượt các bước sau trong ứng dụng Termux của bạn:

### Bước 1: Cập nhật Termux và cài đặt Git / GitHub CLI
```bash
pkg update -y && pkg upgrade -y
pkg install -y git gh
```

### Bước 2: Đăng nhập GitHub trên Termux (Vì đây là Repo Riêng Tư)
```bash
gh auth login
```
*Chọn `GitHub.com` -> `HTTPS` -> Chọn đăng nhập qua trình duyệt (Web) hoặc dán Token của bạn.*

### Bước 3: Clone Repository về Termux
```bash
gh repo clone TXAVLOG/txabot
# Hoặc sử dụng git: git clone https://github.com/TXAVLOG/txabot.git
```

### Bước 4: Di chuyển vào thư mục bot
```bash
cd txabot
```

### Bước 5: Chép các tệp cấu hình bảo mật vào thư mục bot
Bạn cần tạo hoặc chuyển các tệp `txa.json`, `config.json`, và bất kỳ tệp cấu hình nhóm nào (ví dụ: `706121047546334382_setting.json`) vào thư mục `txabot` trên điện thoại.
*Mẹo:* Bạn có thể sử dụng các ứng dụng quản lý tệp tin trên Android hỗ trợ truy cập thư mục Termux (như ZArchiver, MT Manager) hoặc chuyển qua mạng bằng lệnh `scp` / các công cụ chia sẻ tệp tin.

Nếu muốn tự viết lại nhanh cấu hình từ Termux, bạn có thể tạo nhanh bằng trình soạn thảo `nano`:
```bash
nano txa.json
# Dán nội dung txa.json của bạn vào, sau đó nhấn Ctrl+O (Enter) rồi Ctrl+X để thoát.
```

### Bước 6: Cấp quyền và chạy Script Auto Setup / Run
```bash
chmod +x ins.sh
./ins.sh
```
*Script sẽ tự động kiểm tra hệ điều hành, cài đặt các package C/C++ (clang, make, jpeg-turbo) cần thiết cho Python, tạo môi trường ảo `.venv`, cài đặt thư viện từ `requirements.txt` và bắt đầu chạy giám sát 24/7.*

---

## 🔋 Hướng dẫn chạy Bot 24/7 không bị tắt

Hệ điều hành Android rất nghiêm ngặt trong việc tiết kiệm pin và sẽ tắt Termux khi bạn khóa màn hình hoặc ứng dụng chạy ngầm quá lâu. Làm theo các bước sau để đảm bảo bot chạy vĩnh viễn:

### 1. Kích hoạt Termux Wake Lock (Giữ thiết bị luôn hoạt động ngầm)
Vuốt thanh thông báo từ trên xuống, nhấn vào nút **"Acquire Wake Lock"** trên thông báo của Termux.
Hoặc bạn có thể chạy lệnh này trong Termux:
```bash
termux-wake-lock
```

### 2. Tắt Tối ưu hóa Pin cho Termux (Battery Optimization)
* Vào **Cài đặt điện thoại** -> **Ứng dụng** -> **Quản lý ứng dụng** -> Tìm **Termux**.
* Chọn mục **Pin** hoặc **Tiết kiệm pin**.
* Chọn **Không giới hạn (No restrictions)** hoặc **Tắt tối ưu hóa pin**.

### 3. Sử dụng `tmux` để tắt ứng dụng mà bot vẫn chạy
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

---

## ⚠️ Lưu ý quan trọng
* Không chia sẻ thư mục chứa `txa.json` và `config.json` cho bất cứ ai.
* Nếu bot Zalo bị mất kết nối, hãy kiểm tra lại Cookie/IMEI trong `txa.json`.
* Nguồn ảnh font lỗi emoji đã được cập nhật thành `font/NotoEmoji-Bold.ttf` giúp hiển thị emoji hoàn hảo.

---
*Chúc bạn chạy Bot thành công! Bản quyền thuộc về **TXA**.*
