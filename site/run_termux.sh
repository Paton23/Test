#!/data/data/com.termux/files/usr/bin/bash

# Скрипт для запуска на Termux
echo "=== Запуск File Manager Server на Termux ==="

# Обновляем пакеты
echo "Обновление пакетов..."
pkg update -y

# Устанавливаем необходимые пакеты
echo "Установка зависимостей..."
pkg install -y python python-pip

# Устанавливаем Python пакеты
echo "Установка Python модулей..."
pip install --upgrade pip
pip install -r requirements.txt

# Создаем папку для загрузок
mkdir -p uploads

# Запускаем сервер
echo "Запуск сервера..."
echo "Сервер будет доступен по адресам:"
echo "  - http://localhost:5000"
echo "  - http://$(hostname -I | awk '{print $1}'):5000"

# Запускаем с правами root если есть
if command -v tsu &> /dev/null; then
    echo "Обнаружен tsu, запуск с повышенными правами..."
    tsu -c "python app.py"
else
    python app.py
fi 