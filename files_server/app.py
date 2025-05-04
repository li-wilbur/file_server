import os
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import mimetypes
import urllib.parse
import time
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from datetime import datetime

from .config import config
from .utils import get_file_type, safe_filename, get_file_info
from .metrics import REQUEST_COUNT, REQUEST_LATENCY, FILE_OPERATIONS, FILE_SIZE

def create_app(config_name='default'):
    """创建Flask应用"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # 确保上传目录存在
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # 请求中间件
    @app.before_request
    def before_request():
        request.start_time = time.time()

    @app.after_request
    def after_request(response):
        if hasattr(request, 'start_time'):
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.endpoint
            ).observe(time.time() - request.start_time)
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.endpoint,
            status=response.status_code
        ).inc()
        
        return response

    # 路由定义
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/files')
    def get_files():
        files = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_stat = os.stat(file_path)
                files.append({
                    'name': filename,
                    'size': file_stat.st_size,
                    'uploadTime': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    'type': mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                })
        return jsonify(files)

    @app.route('/upload', methods=['POST'])
    def upload_file():
        if 'file' not in request.files:
            return jsonify({'error': '没有文件被上传'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            return jsonify({'message': '文件上传成功', 'filename': filename})

    @app.route('/download/<filename>')
    def download_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

    @app.route('/delete/<filename>', methods=['DELETE'])
    def delete_file(filename):
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.remove(file_path)
            return jsonify({'message': '文件删除成功'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/delete-multiple', methods=['POST'])
    def delete_multiple_files():
        try:
            filenames = request.json.get('filenames', [])
            for filename in filenames:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            return jsonify({'message': '文件删除成功'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/preview/<filename>')
    def preview_file(filename):
        """处理文件预览"""
        try:
            decoded_filename = urllib.parse.unquote(filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], decoded_filename)
            
            if not os.path.exists(file_path):
                return jsonify({'type': 'error', 'message': '文件不存在'}), 404

            file_size = os.path.getsize(file_path)
            file_type = get_file_type(decoded_filename)

            if file_size == 0:
                return jsonify({
                    'type': 'empty',
                    'message': '这是一个空文件',
                    'size': 0,
                    'name': decoded_filename
                })

            if file_type == 'image':
                mime_type = mimetypes.guess_type(file_path)[0]
                return send_file(file_path, mimetype=mime_type, as_attachment=False)

            if file_type == 'text':
                encodings = ['utf-8', 'gbk']
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        return jsonify({
                            'type': 'text',
                            'content': content,
                            'encoding': encoding,
                            'name': decoded_filename
                        })
                    except UnicodeDecodeError:
                        continue
                return jsonify({
                    'type': 'error',
                    'message': '文件编码不支持',
                    'name': decoded_filename
                }), 500

            return jsonify({
                'type': 'other',
                'message': '该文件类型不支持预览',
                'size': file_size,
                'name': decoded_filename
            })

        except Exception as e:
            return jsonify({
                'type': 'error',
                'message': f'文件预览失败: {str(e)}',
                'name': decoded_filename if 'decoded_filename' in locals() else filename
            }), 500

    @app.route('/metrics')
    def metrics():
        """Prometheus metrics endpoint"""
        return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

    return app 