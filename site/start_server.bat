@echo off
echo ====================================
echo   File Manager Server - Windows
echo ====================================
echo.

REM Проверяем наличие Python
py --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден в системе!
    echo Установите Python с python.org
    pause
    exit /b 1
)

echo [INFO] Python найден, версия:
py --version

echo.
echo [INFO] Установка зависимостей...
py -m pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] Ошибка установки зависимостей!
    pause
    exit /b 1
)

echo.
echo [INFO] Создание папки uploads...
if not exist "uploads" mkdir uploads

echo.
echo [SUCCESS] Запуск сервера...
echo.
echo Сервер будет доступен по адресу:
echo   http://localhost:5000
echo.
echo Для остановки нажмите Ctrl+C
echo.

py app.py

pause 