#!/usr/bin/env bash
# Tạo lối tắt trong thư mục Startup của Windows: mỗi lần đăng nhập Windows sẽ mở WSL và chạy ./start_watch.sh
#   ./install_autostart_wsl.sh            cài
#   ./install_autostart_wsl.sh --remove   gỡ
set -e
DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
grep -qi microsoft /proc/version 2>/dev/null || { echo "Script này chỉ dùng trong WSL."; exit 1; }

APPDATA_WIN="$(cd /mnt/c && cmd.exe /c "echo %APPDATA%" 2>/dev/null | tr -d '\r')"
[ -n "$APPDATA_WIN" ] || { echo "Không đọc được %APPDATA% của Windows."; exit 1; }
STARTUP="$(wslpath "$APPDATA_WIN")/Microsoft/Windows/Start Menu/Programs/Startup"
BAT="$STARTUP/hsk-quizlet-watch.bat"

if [ "$1" = "--remove" ]; then
  rm -f "$BAT" && echo "Đã gỡ: $BAT"; exit 0
fi

DISTRO="${WSL_DISTRO_NAME:-Ubuntu}"
printf '@echo off\r\nrem Tu dong chay HSK -> Quizlet (WSL: %s)\r\nstart "HSK Quizlet" /min wsl.exe -d %s --cd "%s" -- ./start_watch.sh\r\n' \
  "$DISTRO" "$DISTRO" "$DIR" > "$BAT"
echo "Đã cài tự khởi động: $BAT"
echo "Lần đăng nhập Windows tới, một cửa sổ thu nhỏ 'HSK Quizlet' sẽ theo dõi thư mục inbox."
