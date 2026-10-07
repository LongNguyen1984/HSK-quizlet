@echo off
rem Tu chay che do theo doi inbox moi khi bat may
set "S=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\hsk-quizlet-watch.bat"
> "%S%" echo @echo off
>> "%S%" echo start "HSK Quizlet" /min cmd /c "%~dp0start_watch.bat"
echo Da cai tu khoi dong: %S%
echo Go bo: xoa file tren.
pause
