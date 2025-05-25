import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import traceback
from flask import render_template  

# 引入核心RAG系統
from rag_system import MenstrualHealthRAG

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RAGFlaskApp:
    """RAG Flask應用封裝類"""
    
    def __init__(self, google_api_key: str):
        """
        初始化Flask應用
        
        Args:
            google_api_key: Google API金鑰
        """
        self.app = Flask(__name__)
        
        # 設置CORS
        CORS(self.app, resources={
            r"/api/*": {
                "origins": "*",
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "allow_headers": ["Content-Type", "Authorization"]
            }
        })
        
        # 初始化RAG系統
        try:
            self.rag = MenstrualHealthRAG(
                google_api_key=google_api_key,
                pdf_directory="/frontend/ai_doctor/Chinese_paper",
                db_directory="./chroma_db"
            )
            
            # 嘗試加載已有向量存儲
            if not self.rag.load_existing_vector_store():
                logger.warning("未找到現有向量存儲，請確保已初始化RAG系統")
            
            # 設置RAG鏈
            self.rag.setup_rag_chain()
            logger.info("RAG系統初始化成功")
            
        except Exception as e:
            logger.error(f"RAG系統初始化失敗: {e}")
            self.rag = None
        
        # 註冊路由
        self.register_routes()
        
    def register_routes(self):
        """註冊API路由"""
        

        @self.app.route("/", methods=["GET"])
        def root():
            """根路由"""
            return render_template("index.html")

        
        @self.app.route("/api/query", methods=["POST"])
        def query():
            """處理用戶問題"""
            try:
                # 檢查RAG系統是否可用
                if self.rag is None:
                    return jsonify({"error": "RAG系統未正確初始化"}), 500
                
                # 獲取請求數據
                data = request.get_json()
                if not data:
                    return jsonify({"error": "請求數據不能為空"}), 400
                
                question = data.get("question", "").strip()
                if not question:
                    return jsonify({"error": "問題不能為空"}), 400
                
                # 處理查詢
                logger.info(f"處理查詢: {question}")
                answer = self.rag.query(question)
                
                return jsonify({
                    "answer": answer,
                    "question": question,
                    "status": "success"
                })
                
            except Exception as e:
                logger.error(f"處理查詢時出錯: {e}")
                logger.error(traceback.format_exc())
                return jsonify({"error": f"處理查詢時出錯: {str(e)}"}), 500
        
        @self.app.route("/api/nearby-clinics", methods=["POST"])
        def nearby_clinics():
            """推薦附近診所"""
            try:
                # 檢查RAG系統是否可用
                if self.rag is None:
                    return jsonify({"error": "RAG系統未正確初始化"}), 500
                
                # 獲取請求數據
                data = request.get_json()
                if not data:
                    return jsonify({"error": "請求數據不能為空"}), 400
                
                latitude = data.get("latitude")
                longitude = data.get("longitude")
                
                if latitude is None or longitude is None:
                    return jsonify({"error": "緯度和經度不能為空"}), 400
                
                try:
                    latitude = float(latitude)
                    longitude = float(longitude)
                except ValueError:
                    return jsonify({"error": "緯度和經度必須為有效數字"}), 400
                
                # 推薦診所
                user_location = {"latitude": latitude, "longitude": longitude}
                logger.info(f"推薦附近診所: {user_location}")
                clinics = self.rag.recommend_nearby_clinics(user_location)
                
                return jsonify({
                    "clinics": clinics,
                    "location": user_location,
                    "status": "success"
                })
                
            except Exception as e:
                logger.error(f"推薦診所時出錯: {e}")
                logger.error(traceback.format_exc())
                return jsonify({"error": f"推薦診所時出錯: {str(e)}"}), 500
        
        @self.app.route("/api/health", methods=["GET"])
        def health():
            """健康檢查端點"""
            rag_status = "healthy" if self.rag is not None else "error"
            return jsonify({
                "status": "healthy",
                "rag_system": rag_status,
                "timestamp": str(pd.Timestamp.now()) if 'pd' in globals() else "N/A"
            })
        
        @self.app.route("/api/test", methods=["GET"])
        def test():
            """測試端點"""
            return jsonify({
                "message": "API測試成功",
                "endpoints": {
                    "query": "/api/query [POST]",
                    "nearby_clinics": "/api/nearby-clinics [POST]",
                    "health": "/api/health [GET]",
                    "test": "/api/test [GET]"
                }
            })
        
        @self.app.errorhandler(404)
        def not_found(error):
            """404錯誤處理"""
            return jsonify({"error": "端點未找到"}), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            """500錯誤處理"""
            logger.error(f"內部服務器錯誤: {error}")
            return jsonify({"error": "內部服務器錯誤"}), 500
        
        @self.app.errorhandler(Exception)
        def handle_exception(e):
            """全局異常處理"""
            logger.error(f"全局異常: {e}")
            logger.error(traceback.format_exc())
            return jsonify({"error": f"發生內部錯誤: {str(e)}"}), 500
    
    def mount_static_files(self, static_dir: str = "./frontend/build"):
        """
        設置靜態文件服務
        
        Args:
            static_dir: 靜態文件目錄
        """
        if Path(static_dir).exists():
            @self.app.route('/<path:path>')
            def serve_static(path):
                return send_from_directory(static_dir, path)
            
            @self.app.route('/static/<path:path>')
            def serve_static_assets(path):
                return send_from_directory(os.path.join(static_dir, 'static'), path)
            
            logger.info(f"靜態文件路由已設置: {static_dir}")
        else:
            logger.warning(f"靜態文件目錄不存在: {static_dir}")
    
    def run(self, host: str = "0.0.0.0", port: int = 5050, debug: bool = False):
        """
        運行Flask應用
        
        Args:
            host: 主機地址
            port: 端口號
            debug: 調試模式
        """
        logger.info(f"啟動Flask應用 - 主機: {host}, 端口: {port}, 調試模式: {debug}")
        self.app.run(host=host, port=port, debug=debug, threaded=True)

def create_app(google_api_key: str = None) -> Flask:
    """
    應用工廠函數
    
    Args:
        google_api_key: Google API金鑰
        
    Returns:
        Flask應用實例
    """
    if google_api_key is None:
        google_api_key = os.environ.get("GOOGLE_API_KEY", "AIzaSyDp6wUDTwfcRV5s6vj1gFERNJ5A88ydTF4")
    
    webapp = RAGFlaskApp(google_api_key=google_api_key)
    return webapp.app

def main():
    """主函數"""
    # 請替換為您的API金鑰
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyDp6wUDTwfcRV5s6vj1gFERNJ5A88ydTF4")
    
    # 初始化Flask應用
    webapp = RAGFlaskApp(google_api_key=GOOGLE_API_KEY)
    
    # 啟動服務
    webapp.run(host="0.0.0.0", port=5050, debug=True)

if __name__ == "__main__":
    main()