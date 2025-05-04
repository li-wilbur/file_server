import os
import urllib.parse
from .config import Config

def get_file_type(filename):
    """获取文件类型"""
    ext = os.path.splitext(filename)[1].lower()
    return next((file_type for file_type, extensions in Config.PREVIEW_EXTENSIONS.items() 
                if ext in extensions), 'other')

def get_file_icon(file_type):
    """获取文件图标"""
    icons = {
        'image': 'bi-file-earmark-image',
        'text': 'bi-file-earmark-text',
        'other': 'bi-file-earmark'
    }
    return icons.get(file_type, 'bi-file-earmark')

def safe_filename(filename):
    """安全处理文件名，保留中文"""
    return filename

def format_file_size(size):
    """格式化文件大小"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"

def get_file_info(filename, upload_folder):
    """获取文件信息"""
    file_path = os.path.join(upload_folder, filename)
    size = os.path.getsize(file_path)
    file_type = get_file_type(filename)
    return {
        'name': filename,
        'encoded_name': urllib.parse.quote(filename),
        'size': format_file_size(size),
        'type': file_type,
        'icon': get_file_icon(file_type)
    } 