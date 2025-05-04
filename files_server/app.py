import os
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import mimetypes
import urllib.parse
import time
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

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
        """显示主页和文件列表"""
        try:
            files = [get_file_info(filename, app.config['UPLOAD_FOLDER']) 
                    for filename in os.listdir(app.config['UPLOAD_FOLDER'])]
            return render_template('index.html', files=files)
        except Exception as e:
            return render_template('index.html', files=[])

    @app.route('/upload', methods=['POST'])
    def upload_file():
        """处理文件上传"""
        if 'file' not in request.files:
            FILE_OPERATIONS.labels(operation='upload', status='error').inc()
            flash('没有选择文件')
            return redirect(url_for('index'))
        
        file = request.files['file']
        if file.filename == '':
            FILE_OPERATIONS.labels(operation='upload', status='error').inc()
            flash('没有选择文件')
            return redirect(url_for('index'))
        
        try:
            filename = safe_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            if os.path.exists(file_path):
                FILE_OPERATIONS.labels(operation='upload', status='error').inc()
                flash(f'文件 "{filename}" 已存在，请重命名后上传')
                return redirect(url_for('index'))
            
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            FILE_SIZE.labels(operation='upload').observe(file_size)
            FILE_OPERATIONS.labels(operation='upload', status='success').inc()
            flash('文件上传成功！')
        except Exception as e:
            FILE_OPERATIONS.labels(operation='upload', status='error').inc()
            flash('文件上传失败，请重试')
        
        return redirect(url_for('index'))

    @app.route('/download/<filename>')
    def download_file(filename):
        """处理文件下载"""
        try:
            decoded_filename = urllib.parse.unquote(filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], decoded_filename)
            file_size = os.path.getsize(file_path)
            FILE_SIZE.labels(operation='download').observe(file_size)
            FILE_OPERATIONS.labels(operation='download', status='success').inc()
            return send_file(
                file_path,
                as_attachment=True,
                download_name=decoded_filename
            )
        except Exception as e:
            FILE_OPERATIONS.labels(operation='download', status='error').inc()
            flash('文件下载失败')
            return redirect(url_for('index'))

    @app.route('/delete/<filename>')
    def delete_file(filename):
        """处理单个文件删除"""
        try:
            decoded_filename = urllib.parse.unquote(filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], decoded_filename)
            file_size = os.path.getsize(file_path)
            FILE_SIZE.labels(operation='delete').observe(file_size)
            os.remove(file_path)
            FILE_OPERATIONS.labels(operation='delete', status='success').inc()
            flash('文件删除成功！')
        except Exception as e:
            FILE_OPERATIONS.labels(operation='delete', status='error').inc()
            flash('文件删除失败')
        return redirect(url_for('index'))

    @app.route('/delete-multiple', methods=['POST'])
    def delete_multiple():
        """处理多个文件删除"""
        try:
            filenames = request.json.get('filenames', [])
            success_count = 0
            
            for filename in filenames:
                try:
                    decoded_filename = urllib.parse.unquote(filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], decoded_filename)
                    file_size = os.path.getsize(file_path)
                    FILE_SIZE.labels(operation='delete_multiple').observe(file_size)
                    os.remove(file_path)
                    success_count += 1
                except Exception:
                    continue
            
            if success_count == len(filenames):
                FILE_OPERATIONS.labels(operation='delete_multiple', status='success').inc()
                return jsonify({'status': 'success', 'message': f'成功删除 {success_count} 个文件'})
            elif success_count > 0:
                FILE_OPERATIONS.labels(operation='delete_multiple', status='partial').inc()
                return jsonify({'status': 'partial', 'message': f'成功删除 {success_count} 个文件，部分文件删除失败'})
            else:
                FILE_OPERATIONS.labels(operation='delete_multiple', status='error').inc()
                return jsonify({'status': 'error', 'message': '文件删除失败'})
        except Exception:
            FILE_OPERATIONS.labels(operation='delete_multiple', status='error').inc()
            return jsonify({'status': 'error', 'message': '删除操作失败'})

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