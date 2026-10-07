@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
call .venv\Scripts\activate.bat
title HSK -^> Quizlet (dang theo doi thu muc inbox)
python run.py watch --assist
