@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
call .venv\Scripts\activate.bat
rem Keo tha 1 hoac nhieu file .docx vao file nay
python run.py upload %* --assist
pause
