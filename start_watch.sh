#!/usr/bin/env bash
# Theo dõi thư mục inbox: thả .docx vào là tự tạo học phần Quizlet
DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
exec "$DIR/hsk" watch --assist "$@"
