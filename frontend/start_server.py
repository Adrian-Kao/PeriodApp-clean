#!/usr/bin/env python3
"""
阿月生理期系統 - 服務器啟動腳本
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_requirements():
    """檢查必要的套件是否已安裝"""
    required_packages = ['flask', 'flask_cors']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"缺少必要套件: {', '.join(missing_packages)}")
        print("正在安裝套件...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements_flask.txt'])
            print("套件安裝完成！")
        except subprocess.CalledProcessError:
            print("套件安裝失敗，請手動安裝:")
            print("pip install flask flask-cors")
            return False
    
    return True

def check_rag_system():
    """檢查 RAG 系統文件是否存在"""
    ai_doctor_path = Path('ai_doctor')
    required_files = ['rag_system.py', 'query_bot.py']
    
    if not ai_doctor_path.exists():
        print("錯誤: 找不到 ai_doctor 目錄")
        return False
    
    missing_files = []
    for file in required_files:
        if not (ai_doctor_path / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"警告: 缺少 RAG 系統文件: {', '.join(missing_files)}")
        print("系統將以基本模式啟動")
        return False
    
    return True

def start_server():
    """啟動 Flask 服務器"""
    print("=== 阿月生理期系統 ===")
    print("正在啟動服務器...")
    
    # 檢查要求
    if not check_requirements():
        return False
    
    rag_available = check_rag_system()
    if rag_available:
        print("✓ RAG 系統檢查通過")
    else:
        print("⚠ RAG 系統檢查未通過，將使用基本回應")
    
    try:
        # 設置環境變數
        os.environ['FLASK_APP'] = 'app.py'
        os.environ['FLASK_ENV'] = 'development'
        
        print("\n服務器啟動中...")
        print("前端地址: http://localhost:5000")
        print("API 地址: http://localhost:5000/api/")
        print("\n按 Ctrl+C 停止服務器")
        print("-" * 40)
        
        # 延遲開啟瀏覽器
        def open_browser():
            time.sleep(2)
            try:
                # 檢查是否有 index.html
                if Path('index.html').exists():
                    # 如果有 HTML 文件，開啟本地文件
                    file_path = Path('index.html').absolute().as_uri()
                    webbrowser.open(file_path)
                else:
                    print("提示: 請將前端 HTML 文件保存為 index.html")
            except Exception as e:
                print(f"無法自動開啟瀏覽器: {e}")
        
        # 在背景開啟瀏覽器
        import threading
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # 啟動 Flask 應用
        from app import app
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\n\n服務器已停止")
    except Exception as e:
        print(f"啟動失敗: {e}")
        return False
    
    return True

if __name__ == '__main__':
    start_server()