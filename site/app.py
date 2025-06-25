#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import socket
import subprocess
import shutil
import requests
import platform
import zipfile
import tarfile
import tempfile
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Импорты для работы с архивами (опциональные)
try:
    import rarfile  # type: ignore
    rarfile_available = True
except ImportError:
    rarfile_available = False

try:
    import py7zr
    py7zr_available = True
except ImportError:
    py7zr_available = False

app = Flask(__name__)
_ = CORS(app)  # Инициализируем CORS

# Конфигурация
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'py', 'js', 'html', 'css', 'zip', 'tar', 'gz'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB макс размер файла

# Создаем папку для загрузок если её нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_all_ips():
    """Получает все IP адреса системы"""
    ips = []
    
    # Локальный IP
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
        if local_ip not in ['127.0.0.1', '0.0.0.0']:
            ips.append({'type': 'local', 'ip': local_ip, 'hostname': hostname})
    except:
        pass
    
    # Попытка получить IP через подключение к внешнему серверу
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            if local_ip not in [ip['ip'] for ip in ips]:
                ips.append({'type': 'network', 'ip': local_ip})
    except:
        pass
    
    # Внешний IP
    try:
        external_ip = requests.get('https://api.ipify.org', timeout=5).text
        ips.append({'type': 'external', 'ip': external_ip})
    except:
        pass
    
    # Добавляем localhost если нет других IP
    if not ips:
        ips.append({'type': 'localhost', 'ip': '127.0.0.1'})
    
    return ips

def get_system_info():
    """Получает упрощенную информацию о системе"""
    try:
        # Получаем количество CPU ядер
        cpu_count = os.cpu_count() or 1
    except:
        cpu_count = 1
    
    # Инициализируем значения по умолчанию
    disk_total = 0
    disk_used = 0
    disk_free = 0
    disk_percent = 0
    
    try:
        # Информация о диске (для текущей директории)
        disk_usage = shutil.disk_usage('.')
        disk_total = disk_usage.total
        disk_used = disk_usage.used
        disk_free = disk_usage.free
        disk_percent = round((disk_usage.used / disk_usage.total) * 100, 1) if disk_usage.total > 0 else 0
    except:
        pass  # Используем значения по умолчанию
    
    # Базовая информация о памяти (упрощенная)
    try:
        # Попробуем получить информацию о памяти через /proc/meminfo (Linux)
        if os.path.exists('/proc/meminfo'):
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(':')
                        value = int(parts[1]) * 1024  # Конвертируем из kB в байты
                        meminfo[key] = value
                
                mem_total = meminfo.get('MemTotal', 0)
                mem_free = meminfo.get('MemFree', 0) + meminfo.get('Buffers', 0) + meminfo.get('Cached', 0)
                mem_used = mem_total - mem_free
                mem_percent = round((mem_used / mem_total) * 100, 1) if mem_total > 0 else 0
        else:
            # Для Windows или других систем используем заглушки
            mem_total = 8 * 1024 * 1024 * 1024  # 8GB заглушка
            mem_used = mem_total // 2  # 50% использования
            mem_free = mem_total - mem_used
            mem_percent = 50.0
    except:
        # Заглушки при ошибке
        mem_total = 8 * 1024 * 1024 * 1024
        mem_used = mem_total // 2
        mem_free = mem_total - mem_used
        mem_percent = 50.0
    
    return {
        'cpu': {
            'percent': 0,  # Упрощенная версия без мониторинга CPU
            'count': cpu_count,
            'frequency': {
                'current': 0,
                'min': 0,
                'max': 0
            }
        },
        'memory': {
            'total': mem_total,
            'available': mem_free,
            'percent': mem_percent,
            'used': mem_used
        },
        'disk': {
            'total': disk_total,
            'used': disk_used,
            'free': disk_free,
            'percent': disk_percent
        },
        'network': {
            'bytes_sent': 0,  # Упрощенная версия без сетевой статистики
            'bytes_recv': 0,
            'packets_sent': 0,
            'packets_recv': 0
        },
        'processes': [],  # Упрощенная версия без мониторинга процессов
        'platform': {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor()
        }
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/system-info')
def system_info():
    """API endpoint для получения информации о системе"""
    return jsonify(get_system_info())

@app.route('/api/network-info')
def network_info():
    """API endpoint для получения сетевой информации"""
    return jsonify({'ips': get_all_ips()})

@app.route('/api/files', methods=['GET'])
def list_files():
    """Список файлов в директории"""
    path = request.args.get('path', '.')
    try:
        # Нормализуем путь
        path = os.path.normpath(path)
        
        # Проверяем существование и безопасность пути
        if not os.path.exists(path):
            path = '.'
        
        # Проверяем, что это директория
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        
        items = []
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                try:
                    stat = os.stat(item_path)
                    items.append({
                        'name': item,
                        'path': os.path.normpath(item_path),
                        'is_dir': os.path.isdir(item_path),
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'permissions': oct(stat.st_mode)[-3:]
                    })
                except (OSError, IOError) as e:
                    # Пропускаем файлы с проблемами доступа
                    print(f"Не удалось прочитать файл {item_path}: {e}")
                    continue
        except PermissionError:
            return jsonify({'error': 'Нет доступа к этой папке'}), 403
        
        current_abs_path = os.path.abspath(path)
        parent_abs_path = os.path.dirname(current_abs_path)
        
        return jsonify({
            'current_path': current_abs_path,
            'parent_path': parent_abs_path,
            'items': sorted(items, key=lambda x: (not x['is_dir'], x['name'].lower()))
        })
    except Exception as e:
        return jsonify({'error': f'Ошибка чтения директории: {str(e)}'}), 400

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Загрузка файла"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    path = request.form.get('path', UPLOAD_FOLDER)
    
    if file and file.filename:
        filename = secure_filename(file.filename)
        filepath = os.path.join(path, filename)
        file.save(filepath)
        
        # Устанавливаем полные права для Python файлов
        if filename.endswith('.py'):
            os.chmod(filepath, 0o777)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'path': filepath
        })

@app.route('/api/upload-folder', methods=['POST'])
def upload_folder():
    """Загрузка файла из папки с сохранением структуры"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    base_path = request.form.get('path', UPLOAD_FOLDER)
    relative_path = request.form.get('relative_path', file.filename)
    
    try:
        if file and file.filename:
            # Разбираем относительный путь для создания структуры папок
            path_parts = relative_path.split('/')
            
            # Создаем структуру папок
            current_path = base_path
            for part in path_parts[:-1]:  # Все кроме имени файла
                if part:  # Пропускаем пустые части
                    part = secure_filename(part)
                    current_path = os.path.join(current_path, part)
                    os.makedirs(current_path, exist_ok=True)
            
            # Сохраняем файл
            filename = secure_filename(path_parts[-1])
            filepath = os.path.join(current_path, filename)
            
            # Проверяем, что файл не существует или перезаписываем
            file.save(filepath)
            
            # Устанавливаем полные права для Python файлов
            if filename.endswith('.py'):
                os.chmod(filepath, 0o777)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'path': filepath,
                'relative_path': relative_path
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'filename': file.filename
        })

def extract_archive(archive_path, extract_to):
    """Извлекает архив в указанную папку"""
    try:
        # Определяем тип архива по расширению
        _, ext = os.path.splitext(archive_path.lower())
        
        if ext in ['.zip']:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
                return True, f"ZIP архив успешно извлечен"
        
        elif ext in ['.tar', '.gz', '.tgz', '.tar.gz', '.tar.bz2', '.tar.xz']:
            # Определяем режим для разных типов tar архивов
            if archive_path.endswith('.tar.gz') or archive_path.endswith('.tgz'):
                mode = 'r:gz'
            elif archive_path.endswith('.tar.bz2'):
                mode = 'r:bz2'
            elif archive_path.endswith('.tar.xz'):
                mode = 'r:xz'
            else:
                mode = 'r'
                
            with tarfile.open(archive_path, mode) as tar_ref:
                tar_ref.extractall(extract_to)
                return True, f"TAR архив успешно извлечен"
        
        elif ext in ['.rar'] and rarfile_available:
            import rarfile  # type: ignore
            with rarfile.RarFile(archive_path) as rar_ref:
                rar_ref.extractall(extract_to)
                return True, f"RAR архив успешно извлечен"
        
        elif ext in ['.7z'] and py7zr_available:
            import py7zr  # Повторный импорт для линтера
            with py7zr.SevenZipFile(archive_path, mode='r') as z7_ref:
                z7_ref.extractall(extract_to)
                return True, f"7Z архив успешно извлечен"
        
        else:
            return False, f"Неподдерживаемый формат архива: {ext}"
            
    except Exception as e:
        return False, f"Ошибка извлечения архива: {str(e)}"

@app.route('/api/install-archive', methods=['POST'])
def install_archive():
    """Загрузка и установка архива"""
    if 'file' not in request.files:
        return jsonify({'error': 'Архив не найден'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Архив не выбран'}), 400
    
    install_path = request.form.get('path', UPLOAD_FOLDER)
    create_folder = request.form.get('create_folder', 'true').lower() == 'true'
    temp_archive_path = None  # Инициализируем переменную
    
    try:
        # Проверяем, что это архив
        filename = secure_filename(file.filename)
        _, ext = os.path.splitext(filename.lower())
        
        supported_formats = ['.zip', '.tar', '.gz', '.tgz', '.tar.gz', '.tar.bz2', '.tar.xz']
        if rarfile_available:
            supported_formats.append('.rar')
        if py7zr_available:
            supported_formats.append('.7z')
        
        if not any(filename.lower().endswith(fmt) for fmt in supported_formats):
            return jsonify({
                'error': f'Неподдерживаемый формат. Поддерживаются: {", ".join(supported_formats)}'
            }), 400
        
        # Создаем временный файл для архива
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            file.save(temp_file.name)
            temp_archive_path = temp_file.name
        
        # Определяем папку назначения
        if create_folder:
            # Создаем папку с именем архива (без расширения)
            archive_name = os.path.splitext(filename)[0]
            final_extract_path = os.path.join(install_path, secure_filename(archive_name))
            os.makedirs(final_extract_path, exist_ok=True)
        else:
            final_extract_path = install_path
        
        # Извлекаем архив
        success, message = extract_archive(temp_archive_path, final_extract_path)
        
        # Удаляем временный файл
        try:
            os.unlink(temp_archive_path)
        except:
            pass
        
        if success:
            # Устанавливаем права для Python файлов
            for root, _, files in os.walk(final_extract_path):
                for file in files:
                    if file.endswith('.py'):
                        filepath = os.path.join(root, file)
                        try:
                            os.chmod(filepath, 0o777)
                        except:
                            pass
            
            return jsonify({
                'success': True,
                'message': message,
                'extracted_to': final_extract_path,
                'archive_name': filename
            })
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        # Удаляем временный файл в случае ошибки
        try:
            if temp_archive_path and os.path.exists(temp_archive_path):
                os.unlink(temp_archive_path)
        except:
            pass
        
        return jsonify({'error': f'Ошибка установки архива: {str(e)}'}), 500

@app.route('/api/download/<path:filepath>')
def download_file(filepath):
    """Скачивание файла"""
    try:
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/delete', methods=['POST'])
def delete_file():
    """Удаление файла или папки"""
    data = request.get_json()
    path = data.get('path')
    
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/execute-python', methods=['POST'])
def execute_python():
    """Выполнение Python скрипта"""
    data = request.get_json()
    script_path = data.get('path')
    args = data.get('args', [])
    
    if not script_path or not script_path.endswith('.py'):
        return jsonify({'error': 'Неверный Python файл'}), 400
    
    process = None  # Инициализируем переменную
    try:
        # Выполняем скрипт с полными правами
        cmd = [sys.executable, script_path] + args
        
        # Для Termux может понадобиться специальная обработка
        if 'termux' in sys.prefix.lower():
            env = os.environ.copy()
            env['PYTHONPATH'] = os.pathsep.join(sys.path)
        else:
            env = None
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        stdout, stderr = process.communicate(timeout=30)
        
        return jsonify({
            'success': True,
            'stdout': stdout,
            'stderr': stderr,
            'returncode': process.returncode
        })
    except subprocess.TimeoutExpired:
        if process:
            process.kill()
        return jsonify({'error': 'Превышено время выполнения (30 сек)'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/proxy', methods=['GET', 'POST'])
def proxy():
    """Прокси для загрузки веб-страниц"""
    url = request.args.get('url')
    
    # Если URL не указан, попробуем определить из Referer или использовать Google
    if not url:
        referer = request.headers.get('Referer', '')
        
        if '/api/proxy?url=' in referer:
            # Извлекаем хост из предыдущего прокси-запроса
            try:
                import urllib.parse
                referer_parts = urllib.parse.parse_qs(urllib.parse.urlparse(referer).query)
                original_url = referer_parts.get('url', ['google.com'])[0]
                if '://' in original_url:
                    host = original_url.split('://')[1].split('/')[0]
                else:
                    host = original_url.split('/')[0]
                
                # Восстанавливаем полный URL с параметрами запроса
                query_string = request.query_string.decode('utf-8')
                if query_string:
                    url = f"https://{host}/search?{query_string}"
                else:
                    url = f"https://{host}"
            except:
                return Response(
                    json.dumps({'error': 'Не удалось определить URL для запроса'}),
                    status=400,
                    headers={'Content-Type': 'application/json'}
                )
        else:
            return Response(
                json.dumps({'error': 'URL не указан'}),
                status=400,
                headers={'Content-Type': 'application/json'}
            )
    
    # Добавляем протокол если его нет
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        # Улучшенные заголовки для лучшей совместимости
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        }
        
        # Делаем запрос (GET или POST в зависимости от метода)
        if request.method == 'POST':
            # Для POST запросов передаем данные формы
            resp = requests.post(url, headers=headers, data=request.form, timeout=15, allow_redirects=True)
        else:
            resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        
        # Определяем тип контента
        content_type = resp.headers.get('content-type', '').lower()
        
        if 'text/html' in content_type:
            # Получаем HTML контент
            content = resp.text
            
            # Простое исправление кодировки и мета-тегов
            if 'charset=' not in content.lower():
                # Добавляем UTF-8 если кодировка не указана
                if '<head>' in content.lower():
                    content = content.replace('<head>', '<head>\n<meta charset="utf-8">', 1)
                elif '<html>' in content.lower():
                    content = content.replace('<html>', '<html>\n<head><meta charset="utf-8"></head>', 1)
            
            # Убираем проблемные мета-теги
            import re
            content = re.sub(r'<meta[^>]*http-equiv[^>]*>', '', content, flags=re.IGNORECASE)
            content = re.sub(r'<meta[^>]*refresh[^>]*>', '', content, flags=re.IGNORECASE)
            
            # Получаем базовый хост
            if '://' in url:
                base_host = url.split('://')[1].split('/')[0]
            else:
                base_host = url.split('/')[0]
            
            # Заменяем формы чтобы они отправлялись через прокси
            content = re.sub(
                r'<form([^>]*?)action=["\']([^"\']*)["\']',
                lambda m: f'<form{m.group(1)}action="/api/proxy?url=https://{base_host}{m.group(2) if m.group(2).startswith("/") else "/" + m.group(2)}"',
                content,
                flags=re.IGNORECASE
            )
            
            # Заменяем относительные ссылки
            content = re.sub(
                r'href=["\']([^"\']*)["\']',
                lambda m: f'href="/api/proxy?url=https://{base_host}{m.group(1) if m.group(1).startswith("/") else "/" + m.group(1)}"' if m.group(1).startswith('/') and not m.group(1).startswith('//') else f'href="{m.group(1)}"',
                content,
                flags=re.IGNORECASE
            )
            
            return Response(
                content,
                status=resp.status_code,
                headers={
                    'Content-Type': 'text/html; charset=utf-8',
                    'X-Frame-Options': 'SAMEORIGIN',
                    'Cache-Control': 'no-cache'
                }
            )
        else:
            # Для других типов файлов 
            return Response(
                resp.content,
                status=resp.status_code,
                headers={'Content-Type': resp.headers.get('content-type', 'application/octet-stream')}
            )
            
    except Exception as e:
        error_msg = str(e)
        error_html = f"""
        <html><head><meta charset="utf-8"></head><body style="background:#1a1a1a;color:#e0e0e0;font-family:sans-serif;padding:20px;">
        <h2 style="color:#ff4444;">Ошибка загрузки страницы</h2>
        <p><strong>URL:</strong> {url}</p>
        <p><strong>Ошибка:</strong> {error_msg}</p>
        <p>Попробуйте:</p>
        <ul>
            <li>Проверить правильность URL</li>
            <li>Использовать другой протокол (http/https)</li>
            <li>Подождать и попробовать снова</li>
        </ul>
        </body></html>
        """
        return Response(error_html, status=200, headers={'Content-Type': 'text/html; charset=utf-8'})

@app.route('/api/create-folder', methods=['POST'])
def create_folder():
    """Создание новой папки"""
    data = request.get_json()
    path = data.get('path')
    name = data.get('name')
    
    if not path or not name:
        return jsonify({'error': 'Путь и имя обязательны'}), 400
    
    try:
        folder_path = os.path.join(path, secure_filename(name))
        os.makedirs(folder_path, exist_ok=True)
        return jsonify({'success': True, 'path': folder_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/file-content/<path:filepath>')
def get_file_content(filepath):
    """Получение содержимого файла для просмотра"""
    try:
        # Определяем тип файла
        _, ext = os.path.splitext(filepath)
        
        # Текстовые файлы
        text_extensions = ['.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', '.yml', '.yaml']
        
        if ext.lower() in text_extensions:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({
                'type': 'text',
                'content': content,
                'extension': ext
            })
        
        # Изображения
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg']
        if ext.lower() in image_extensions:
            return jsonify({
                'type': 'image',
                'url': f'/api/download/{filepath}'
            })
        
        # Остальные файлы
        return jsonify({
            'type': 'binary',
            'size': os.path.getsize(filepath)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Универсальный перехватчик для прокси-запросов
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all_proxy(path):
    """Перехватывает все неизвестные запросы и проксирует их через последний загруженный сайт"""
    
    # Получаем последний использованный хост из cookie или используем google.com по умолчанию
    from flask import request as flask_request
    
    # Попробуем определить хост из Referer
    referer = flask_request.headers.get('Referer', '')
    
    if '/api/proxy?url=' in referer:
        # Извлекаем хост из предыдущего прокси-запроса
        try:
            import urllib.parse
            referer_parts = urllib.parse.parse_qs(urllib.parse.urlparse(referer).query)
            original_url = referer_parts.get('url', ['google.com'])[0]
            if '://' in original_url:
                host = original_url.split('://')[1].split('/')[0]
            else:
                host = original_url.split('/')[0]
        except:
            host = 'google.com'
    else:
        host = 'google.com'  # По умолчанию
    
    # Создаем полный URL для проксирования
    query_string = flask_request.query_string.decode('utf-8')
    if query_string:
        full_url = f"https://{host}/{path}?{query_string}"
    else:
        full_url = f"https://{host}/{path}"
    
    # Перенаправляем через наш прокси
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        }
        
        if flask_request.method == 'POST':
            resp = requests.post(full_url, headers=headers, data=flask_request.form, timeout=15, allow_redirects=True)
        else:
            resp = requests.get(full_url, headers=headers, timeout=15, allow_redirects=True)
        
        content_type = resp.headers.get('content-type', '').lower()
        
        if 'text/html' in content_type:
            content = resp.text
            
            # Исправление кодировки
            if 'charset=' not in content.lower():
                if '<head>' in content.lower():
                    content = content.replace('<head>', '<head>\n<meta charset="utf-8">', 1)
                elif '<html>' in content.lower():
                    content = content.replace('<html>', '<html>\n<head><meta charset="utf-8"></head>', 1)
            
            # Убираем проблемные мета-теги
            import re
            content = re.sub(r'<meta[^>]*http-equiv[^>]*>', '', content, flags=re.IGNORECASE)
            content = re.sub(r'<meta[^>]*refresh[^>]*>', '', content, flags=re.IGNORECASE)
            
            # Заменяем относительные ссылки на абсолютные через прокси
            base_host = host
            
            # Формы должны отправляться через прокси
            content = re.sub(
                r'<form([^>]*?)action=["\']([^"\']*)["\']',
                lambda m: f'<form{m.group(1)}action="/api/proxy?url=https://{base_host}{m.group(2) if m.group(2).startswith("/") else "/" + m.group(2)}"',
                content,
                flags=re.IGNORECASE
            )
            
            # Ссылки должны идти через прокси
            content = re.sub(
                r'href=["\']([^"\']*)["\']',
                lambda m: f'href="/api/proxy?url=https://{base_host}{m.group(1) if m.group(1).startswith("/") else "/" + m.group(1)}"' if m.group(1).startswith('/') else f'href="{m.group(1)}"',
                content,
                flags=re.IGNORECASE
            )
            
            return Response(
                content,
                status=resp.status_code,
                headers={
                    'Content-Type': 'text/html; charset=utf-8',
                    'X-Frame-Options': 'SAMEORIGIN',
                    'Cache-Control': 'no-cache'
                }
            )
        else:
            return Response(
                resp.content,
                status=resp.status_code,
                headers={'Content-Type': resp.headers.get('content-type', 'application/octet-stream')}
            )
            
    except Exception as e:
        error_html = f"""
        <html><head><meta charset="utf-8"></head><body style="background:#1a1a1a;color:#e0e0e0;font-family:sans-serif;padding:20px;">
        <h2 style="color:#ff4444;">Ошибка прокси-запроса</h2>
        <p><strong>Запрошенный путь:</strong> /{path}</p>
        <p><strong>Полный URL:</strong> {full_url}</p>
        <p><strong>Ошибка:</strong> {str(e)}</p>
        <p><a href="/" style="color:#00ffff;">← Вернуться на главную</a></p>
        </body></html>
        """
        return Response(error_html, status=500, headers={'Content-Type': 'text/html; charset=utf-8'})

if __name__ == '__main__':
    print(f"Сервер запущен на http://localhost:5000")
    print(f"IP адреса системы:")
    for ip_info in get_all_ips():
        print(f"  - {ip_info['type']}: {ip_info['ip']}")
    
    # Для Termux используем все интерфейсы
    app.run(host='0.0.0.0', port=5000, debug=True) 