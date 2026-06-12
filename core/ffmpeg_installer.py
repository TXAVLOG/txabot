import os
import shutil
import platform
import subprocess
import time

def is_ffmpeg_installed():
    return shutil.which('ffmpeg') is not None

def install_ffmpeg():
    os_name = platform.system()
    print("\n========================================================")
    print("⚠️  [FFMPEG CHECK] Thiếu thư viện FFmpeg trong hệ thống!")
    print(f"➜ Nền tảng phát hiện: {os_name}")
    print("➜ Đang bắt đầu tự động cài đặt FFmpeg cho bạn...")
    print("========================================================\n")
    
    success = False
    
    if os_name == "Windows":
        # Thử cài bằng winget
        if shutil.which("winget"):
            print("[FFMPEG INSTALL] Phát hiện winget. Đang chạy: winget install Gyan.FFmpeg ...")
            try:
                subprocess.run([
                    "winget", "install", "--no-upgrade", "-e", "--id", "Gyan.FFmpeg", 
                    "--accept-source-agreements", "--accept-package-agreements"
                ], check=True)
                success = True
            except Exception as e:
                print(f"[FFMPEG INSTALL] Cài đặt qua winget thất bại: {e}")
        
        # Thử cài bằng choco nếu winget không thành công
        if not success and shutil.which("choco"):
            print("[FFMPEG INSTALL] Phát hiện choco. Đang chạy: choco install ffmpeg -y ...")
            try:
                subprocess.run(["choco", "install", "ffmpeg", "-y"], check=True)
                success = True
            except Exception as e:
                print(f"[FFMPEG INSTALL] Cài đặt qua choco thất bại: {e}")
                
        if not success:
            print("[FFMPEG INSTALL] Không thể cài đặt tự động trên Windows do thiếu winget/choco hoặc lệnh cài thất bại.")
            print("[FFMPEG INSTALL] Hãy xem hướng dẫn cài đặt thủ công trong file README.md.")

    elif os_name == "Linux":
        # Nhận diện package manager
        if shutil.which("apt-get"):
            print("[FFMPEG INSTALL] Đang dùng apt-get để cài ffmpeg...")
            try:
                subprocess.run(["sudo", "apt-get", "update"], check=True)
                subprocess.run(["sudo", "apt-get", "install", "-y", "ffmpeg"], check=True)
                success = True
            except Exception as e:
                print(f"[FFMPEG INSTALL] Cài đặt qua apt-get thất bại: {e}")
        elif shutil.which("dnf"):
            print("[FFMPEG INSTALL] Đang dùng dnf để cài ffmpeg...")
            try:
                subprocess.run(["sudo", "dnf", "install", "-y", "ffmpeg"], check=True)
                success = True
            except Exception as e:
                print(f"[FFMPEG INSTALL] Cài đặt qua dnf thất bại: {e}")
        elif shutil.which("yum"):
            print("[FFMPEG INSTALL] Đang dùng yum để cài ffmpeg...")
            try:
                subprocess.run(["sudo", "yum", "install", "-y", "ffmpeg"], check=True)
                success = True
            except Exception as e:
                print(f"[FFMPEG INSTALL] Cài đặt qua yum thất bại: {e}")
        elif shutil.which("pacman"):
            print("[FFMPEG INSTALL] Đang dùng pacman để cài ffmpeg...")
            try:
                subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"], check=True)
                success = True
            except Exception as e:
                print(f"[FFMPEG INSTALL] Cài đặt qua pacman thất bại: {e}")
        else:
            print("[FFMPEG INSTALL] Không phát hiện trình quản lý gói (apt-get/dnf/yum/pacman).")
            print("[FFMPEG INSTALL] Hãy cài đặt FFmpeg thủ công theo hướng dẫn trong README.md.")
            
    elif os_name == "Darwin":  # macOS
        if shutil.which("brew"):
            print("[FFMPEG INSTALL] Phát hiện Homebrew. Đang chạy: brew install ffmpeg ...")
            try:
                subprocess.run(["brew", "install", "ffmpeg"], check=True)
                success = True
            except Exception as e:
                print(f"[FFMPEG INSTALL] Cài đặt qua Homebrew thất bại: {e}")
        else:
            print("[FFMPEG INSTALL] Không phát hiện Homebrew (brew). Vui lòng cài đặt Homebrew hoặc tải FFmpeg thủ công.")
            
    else:
        print(f"[FFMPEG CHECK] Hệ điều hành '{os_name}' không được hỗ trợ cài đặt tự động.")
        print("[FFMPEG CHECK] Hãy cấu hình FFmpeg thủ công.")

    # Kiểm tra lại
    if is_ffmpeg_installed():
        print("\n🎉 [FFMPEG CHECK] Chúc mừng! FFmpeg đã được cài đặt thành công và sẵn sàng hoạt động!")
        return True
    else:
        print("\n❌ [FFMPEG CHECK] Cài đặt tự động thất bại hoặc FFmpeg chưa được thêm vào PATH.")
        print("[FFMPEG CHECK] Chức năng phát nhạc sang voice tin nhắn có thể bị lỗi.")
        print("[FFMPEG CHECK] Bot sẽ tiếp tục khởi động sau 5 giây. Vui lòng kiểm tra lại cấu hình sau...")
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            pass
        return False

def check_and_install_ffmpeg():
    if not is_ffmpeg_installed():
        return install_ffmpeg()
    else:
        print("[FFMPEG CHECK] ✅ FFmpeg đã được cài đặt và sẵn sàng hoạt động.")
        return True
