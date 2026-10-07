#!/usr/bin/env bash
# Cài đặt cho macOS / Linux
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
[ -f config.json ] || cp config.example.json config.json
python run.py login
echo "Xong! Chạy: source .venv/bin/activate && python run.py watch"
