# 文件服务器

一个简单而美观的文件服务器，支持文件上传、下载和删除功能。

## 功能特点

- 文件上传：支持拖拽上传和点击上传
- 文件下载：一键下载已上传的文件
- 文件删除：安全删除不需要的文件
- 美观的界面：使用 Bootstrap 5 构建的现代化界面
- 响应式设计：适配各种设备尺寸

## 安装说明

1. 克隆项目到本地
2. 创建虚拟环境（推荐）：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

## 运行说明

1. 激活虚拟环境（如果使用）
2. 运行应用：
   ```bash
   python files_server/app.py
   ```
3. 在浏览器中访问：`http://localhost:5000`

## 项目结构

```
files_server/
├── __init__.py
├── app.py
├── templates/
│   └── index.html
├── uploads/          # 上传文件存储目录
└── requirements.txt
```

## 技术栈

- Python 3.x
- Flask
- Bootstrap 5
- Bootstrap Icons 