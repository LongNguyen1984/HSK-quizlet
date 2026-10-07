#!/usr/bin/env bash
# Cài đặt cho WSL (Ubuntu/Debian), Linux hoặc macOS
set -e
cd "$(dirname "$(readlink -f "$0")")"

IS_WSL=0; grep -qi microsoft /proc/version 2>/dev/null && IS_WSL=1

if command -v apt-get >/dev/null 2>&1; then
  echo "== Cài gói hệ thống: Python venv + font tiếng Trung (cần mật khẩu sudo) =="
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip fonts-noto-cjk fonts-dejavu-core
fi

echo "== Tạo môi trường Python (.venv) =="
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "== Cài trình duyệt Chromium cho Playwright (kèm thư viện hệ thống) =="
python -m playwright install --with-deps chromium

[ -f config.json ] || cp config.example.json config.json
chmod +x hsk start_watch.sh install_autostart_wsl.sh

if [ -z "${DISPLAY}${WAYLAND_DISPLAY}" ]; then
  echo
  echo "[!] Không thấy màn hình đồ họa. Trên WSL cần WSLg (Windows 11, hoặc Windows 10 bản 21H2+):"
  echo "    mở PowerShell chạy:  wsl --update   rồi  wsl --shutdown , mở lại Ubuntu và chạy lại ./setup.sh"
  exit 1
fi

echo
echo "== Đăng nhập Quizlet (chỉ 1 lần) =="
./hsk login

echo
echo "Xong! Thử:  ./hsk upload ~/Bai_27.docx     hoặc chạy nền:  ./start_watch.sh"
[ "$IS_WSL" = 1 ] && echo "Tự chạy khi bật Windows:  ./install_autostart_wsl.sh"
