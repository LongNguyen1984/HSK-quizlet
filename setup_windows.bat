@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
echo === Cai dat HSK -^> Quizlet ===
where python >nul 2>nul || (echo Chua co Python. Cai tu https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^) roi chay lai. & pause & exit /b 1)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || (pause & exit /b 1)
python -m playwright install chromium
if not exist config.json copy config.example.json config.json >nul
echo.
echo === Dang nhap Quizlet (chi lam 1 lan) ===
python run.py login
echo.
echo Xong! Chay start_watch.bat, hoac keo file .docx tha vao upload.bat
pause
