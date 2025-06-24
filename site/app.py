#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import socket
import subprocess
import shutil
import psutil
import requests
import platform
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

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
    """Получает информацию о системе"""
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()
    
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Информация о процессах
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info
            if pinfo['cpu_percent'] > 0.1:  # Только активные процессы
                processes.append(pinfo)
        except:
            pass
    
    # Сортируем по CPU использованию
    processes = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:10]
    
    # Сетевая статистика
    net_io = psutil.net_io_counters()
    
    return {
        'cpu': {
            'percent': cpu_percent,
            'count': cpu_count,
            'frequency': {
                'current': cpu_freq.current if cpu_freq else 0,
                'min': cpu_freq.min if cpu_freq else 0,
                'max': cpu_freq.max if cpu_freq else 0
            }
        },
        'memory': {
            'total': memory.total,
            'available': memory.available,
            'percent': memory.percent,
            'used': memory.used
        },
        'disk': {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': disk.percent
        },
        'network': {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv
        },
        'processes': processes,
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
        if not os.path.exists(path):
            path = '.'
        
        items = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            stat = os.stat(item_path)
            items.append({
                'name': item,
                'path': item_path,
                'is_dir': os.path.isdir(item_path),
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'permissions': oct(stat.st_mode)[-3:]
            })
        
        return jsonify({
            'current_path': os.path.abspath(path),
            'parent_path': os.path.dirname(os.path.abspath(path)),
            'items': sorted(items, key=lambda x: (not x['is_dir'], x['name']))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

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