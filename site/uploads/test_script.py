#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Демонстрационный скрипт для тестирования File Manager
Этот скрипт показывает различные возможности Python выполнения
"""

import os
import sys
import platform
import datetime
import socket

def main():
    print("🚀 Демонстрационный скрипт запущен!")
    print("=" * 50)
    
    # Информация о системе
    print(f"📍 Платформа: {platform.platform()}")
    print(f"🐍 Python версия: {platform.python_version()}")
    print(f"🏠 Домашняя папка: {os.path.expanduser('~')}")
    print(f"📂 Текущая папка: {os.getcwd()}")
    print(f"⏰ Время: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Сетевая информация
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"🌐 Хост: {hostname}")
        print(f"🔗 IP: {local_ip}")
    except:
        print("❌ Не удалось получить сетевую информацию")
    
    # Переменные окружения
    print("\n🔧 Важные переменные окружения:")
    env_vars = ['PATH', 'PYTHONPATH', 'HOME', 'USER', 'LANG']
    for var in env_vars:
        value = os.environ.get(var, 'Не установлено')
        print(f"   {var}: {value[:50]}{'...' if len(value) > 50 else ''}")
    
    # Тест файловых операций
    print("\n📁 Тест файловых операций:")
    test_file = "test_output.txt"
    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(f"Тестовый файл создан в {datetime.datetime.now()}\n")
            f.write("Этот файл создан Python скриптом через веб-интерфейс!\n")
        print(f"✅ Файл {test_file} успешно создан")
        
        # Проверяем размер файла
        size = os.path.getsize(test_file)
        print(f"📏 Размер файла: {size} байт")
        
    except Exception as e:
        print(f"❌ Ошибка создания файла: {e}")
    
    # Математические вычисления
    print("\n🧮 Математические вычисления:")
    numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    print(f"Числа: {numbers}")
    print(f"Сумма: {sum(numbers)}")
    print(f"Среднее: {sum(numbers) / len(numbers):.2f}")
    print(f"Максимум: {max(numbers)}")
    print(f"Минимум: {min(numbers)}")
    
    # Проверка доступности модулей
    print("\n📦 Проверка доступности модулей:")
    modules_to_check = ['json', 'urllib', 'sqlite3', 'hashlib', 'base64']
    for module in modules_to_check:
        try:
            __import__(module)
            print(f"✅ {module} - доступен")
        except ImportError:
            print(f"❌ {module} - недоступен")
    
    # Генерация случайных данных
    print("\n🎲 Случайные данные:")
    import random
    random_numbers = [random.randint(1, 100) for _ in range(5)]
    print(f"Случайные числа: {random_numbers}")
    
    # Список файлов в текущей папке
    print("\n📋 Файлы в текущей папке:")
    try:
        files = os.listdir('.')
        for i, file in enumerate(files[:10], 1):  # Показываем первые 10 файлов
            size = os.path.getsize(file) if os.path.isfile(file) else 0
            file_type = "📁" if os.path.isdir(file) else "📄"
            print(f"   {i}. {file_type} {file} ({size} байт)")
        
        if len(files) > 10:
            print(f"   ... и еще {len(files) - 10} файлов")
            
    except Exception as e:
        print(f"❌ Ошибка чтения папки: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Скрипт выполнен успешно!")
    print("🎉 Все функции работают корректно!")

if __name__ == "__main__":
    main() 