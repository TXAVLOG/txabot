#!/bin/bash

# --- BANNER & COLOR SETTINGS ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Clear screen
clear

echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "${MAGENTA}${BOLD} ███████╗ █████╗ ██╗      ██████╗     ██████╗  ██████╗ ████████╗${NC}"
echo -e "${MAGENTA}${BOLD} ╚══███╔╝██╔══██╗██║     ██╔═══██╗    ██╔══██╗██╔═══██╗╚══██╔══╝${NC}"
echo -e "${MAGENTA}${BOLD}   ███╔╝ ███████║██║     ██║   ██║    ██████╔╝██║   ██║   ██║   ${NC}"
echo -e "${MAGENTA}${BOLD}  ███╔╝  ██╔══██║██║     ██║   ██║    ██╔══██╗██║   ██║   ██║   ${NC}"
echo -e "${MAGENTA}${BOLD} ███████╗██║  ██║███████╗╚██████╔╝    ██████╔╝╚██████╔╝   ██║   ${NC}"
echo -e "${MAGENTA}${BOLD} ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝     ╚═════╝  ╚═════╝    ╚═╝   ${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "${BLUE}${BOLD}   [+] Script Auto Install & 24/7 Run by TXA${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"

# Hien thi thong tin he thong
echo -e "${BOLD}--- THÔNG TIN HỆ THỐNG ---${NC}"
echo -e "${CYAN}[⚙️] Hệ điều hành:${NC} $(uname -o 2>/dev/null || echo "Linux")"
echo -e "${CYAN}[⚙️] Kiến trúc CPU:${NC} $(uname -m)"
echo -e "${CYAN}[⚙️] Phiên bản Python:${NC} $(python3 -V 2>/dev/null || echo "Chưa cài đặt")"
echo -e "${CYAN}[⚙️] Thư mục chạy Bot:${NC} $(pwd)"
if command -v df &>/dev/null; then
    echo -e "${CYAN}[⚙️] Dung lượng bộ nhớ trống:${NC} $(df -h . | awk 'NR==2 {print $4}')"
fi
echo -e "${CYAN}${BOLD}======================================================${NC}\n"

# 1. KIỂM TRA MÔI TRƯỜNG & CÀI ĐẶT
if [ -n "$TERMUX_VERSION" ] || [ -d "/data/data/com.termux" ]; then
    echo -e "${YELLOW}[⏳] Phát hiện môi trường Termux. Đang cập nhật & cài đặt gói hệ thống...${NC}"
    pkg update -y
    pkg install -y python clang make libjpeg-turbo libcrypt libffi python-cryptography
    echo -e "${GREEN}[✓] Cập nhật hệ thống Termux thành công!${NC}"
else
    echo -e "${YELLOW}[⏳] Phát hiện môi trường Linux/VPS. Đang kiểm tra dependencies...${NC}"
    if ! command -v pip &>/dev/null; then
        echo -e "${YELLOW}[⏳] Không tìm thấy pip. Đang tiến hành cài đặt...${NC}"
        sudo apt update && sudo apt install -y python3-pip python3-venv python3-dev build-essential libjpeg-dev zlib1g-dev
    fi
    echo -e "${GREEN}[✓] Môi trường Linux đã sẵn sàng!${NC}"
fi


# 2. KHỞI TẠO VIRTUAL ENV
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}[⏳] Đang khởi tạo môi trường ảo Python (.venv)...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}[✓] Khởi tạo .venv thành công!${NC}"
fi

# Kích hoạt môi trường ảo
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo -e "${GREEN}[✓] Đã kích hoạt môi trường ảo (.venv)${NC}"
fi

# 3. CÀI ĐẶT THƯ VIỆN
echo -e "${BLUE}[⏳] Đang nâng cấp pip & cài đặt các thư viện Python...${NC}"
python3 -m pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}[✓] Đã cài đặt đầy đủ thư viện Python!${NC}"

# 4. VÒNG LẶP CHẠY 24/7 & TỰ ĐỘNG KHỞI CHẠY LẠI KHI CRASH
RESTART_COUNT=0

echo -e "\n${CYAN}${BOLD}======================================================${NC}"
echo -e "${GREEN}${BOLD}     HỆ THỐNG GIÁM SÁT 24/7 ĐÃ ĐƯỢC KÍCH HOẠT${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}\n"

while true; do
    CURRENT_TIME=$(date "+%Y-%m-%d %H:%M:%S")
    echo -e "${GREEN}[${CURRENT_TIME}] [Khởi chạy #${RESTART_COUNT}] Đang tiến hành chạy Bot Zalo...${NC}"
    
    # Chạy bot và xuất log
    python3 txa.py
    
    # Nếu bot bị crash hoặc exit
    EXIT_CODE=$?
    CURRENT_TIME=$(date "+%Y-%m-%d %H:%M:%S")
    RESTART_COUNT=$((RESTART_COUNT + 1))
    
    echo -e "\n${RED}[${CURRENT_TIME}] [CẢNH BÁO] Bot dừng đột ngột với mã lỗi: ${EXIT_CODE}${NC}"
    echo -e "${YELLOW}[⏳] Tiến trình tự động khởi động lại sau 5 giây (Lần restart thứ: ${RESTART_COUNT})...${NC}"
    
    # Countdown
    for i in {5..1}; do
        echo -ne "${YELLOW}$i... ${NC}"
        sleep 1
    done
    echo -e "\n"
done

