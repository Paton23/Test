import os
import zipfile
import shutil
from flask import Flask, request, send_file, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import tempfile
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Измените на свой секретный ключ

# Настройки
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB максимум
ALLOWED_EXTENSIONS = set()  # Разрешаем все типы файлов

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Создаем папку для загрузок если её нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return True  # Разрешаем все файлы

def get_folder_size(folder_path):
    """Получает размер папки в байтах"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size

def format_size(size_bytes):
    """Форматирует размер в удобочитаемый вид"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

@app.route('/')
def index():
    """Главная страница со списком файлов"""
    files = []
    folders = []
    
    if os.path.exists(UPLOAD_FOLDER):
        for item in os.listdir(UPLOAD_FOLDER):
            item_path = os.path.join(UPLOAD_FOLDER, item)
            if os.path.isdir(item_path):
                size = get_folder_size(item_path)
                folders.append({
                    'name': item,
                    'size': format_size(size)
                })
            else:
                size = os.path.getsize(item_path)
                files.append({
                    'name': item,
                    'size': format_size(size)
                })
    
    return render_template('index.html', files=files, folders=folders)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загрузки файлов"""
    if 'files' not in request.files:
        flash('Файлы не выбраны', 'error')
        return redirect(request.url)
    
    files = request.files.getlist('files')
    
    if not files or all(file.filename == '' for file in files):
        flash('Файлы не выбраны', 'error')
        return redirect(url_for('index'))
    
    uploaded_count = 0
    for file in files:
        if file and file.filename and file.filename != '':
            filename = secure_filename(file.filename)
            if filename:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                uploaded_count += 1
    
    if uploaded_count > 0:
        flash(f'Успешно загружено {uploaded_count} файлов', 'success')
    else:
        flash('Не удалось загрузить файлы', 'error')
    
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    """Скачивание файла"""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            flash('Файл не найден', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'Ошибка при скачивании: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/download_folder/<foldername>')
def download_folder(foldername):
    """Скачивание папки как ZIP архива"""
    try:
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], foldername)
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            flash('Папка не найдена', 'error')
            return redirect(url_for('index'))
        
        # Создаем временный ZIP файл
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, f"{foldername}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname)
        
        return send_file(zip_path, as_attachment=True, download_name=f"{foldername}.zip")
        
    except Exception as e:
        flash(f'Ошибка при создании архива: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/delete/<filename>')
def delete_file(filename):
    """Удаление файла"""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            if os.path.isfile(file_path):
                os.remove(file_path)
                flash(f'Файл {filename} удален', 'success')
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                flash(f'Папка {filename} удалена', 'success')
        else:
            flash('Файл не найден', 'error')
    except Exception as e:
        flash(f'Ошибка при удалении: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    flash('Файл слишком большой. Максимальный размер: 500MB', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("Запуск файлового сервера...")
    print(f"Сервер будет доступен на: http://192.168.0.211:8111")
    print(f"Папка для файлов: {os.path.abspath(UPLOAD_FOLDER)}")
    app.run(host='0.0.0.0', port=8111, debug=True) 