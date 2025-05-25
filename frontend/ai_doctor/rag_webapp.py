
import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# 引入核心RAG系統
from rag_system import MenstrualHealthRAG

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定義API模型
class QuestionRequest(BaseModel):
    question: str
    
class LocationRequest(BaseModel):
    latitude: float
    longitude: float

class RAGWebApp:
    """RAG Web應用封裝類"""
    
    def __init__(self, google_api_key: str):
        """
        初始化Web應用
        
        Args:
            google_api_key: Google API金鑰
        """
        self.app = FastAPI(
            title="女性月經健康RAG系統",
            description="提供女性月經健康問答和附近診所推薦的API",
            version="1.0.0"
        )
        
        # 設置CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 正式環境中應限制來源
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 初始化RAG系統
        self.rag = MenstrualHealthRAG(
            google_api_key=google_api_key,
            pdf_directory="/Users/ylin/Documents/AI_project/Chinese_paper",
            db_directory="./chroma_db"
        )
        
        # 嘗試加載已有向量存儲
        if not self.rag.load_existing_vector_store():
            logger.warning("未找到現有向量存儲，請確保已初始化RAG系統")
        
        # 設置RAG鏈
        self.rag.setup_rag_chain()
        
        # 註冊路由
        self.register_routes()
        
    def register_routes(self):
        """註冊API路由"""
        
        @self.app.get("/")
        async def root():
            return {"message": "女性月經健康RAG系統API"}
        
        @self.app.post("/api/query")
        async def query(request: QuestionRequest):
            """處理用戶問題"""
            try:
                question = request.question
                if not question or question.strip() == "":
                    raise HTTPException(status_code=400, detail="問題不能為空")
                
                answer = self.rag.query(question)
                return JSONResponse(content={"answer": answer})
            except Exception as e:
                logger.error(f"處理查詢時出錯: {e}")
                raise HTTPException(status_code=500, detail=f"處理查詢時出錯: {str(e)}")
        
        @self.app.post("/api/nearby-clinics")
        async def nearby_clinics(request: LocationRequest):
            """推薦附近診所"""
            try:
                user_location = {"latitude": request.latitude, "longitude": request.longitude}
                clinics = self.rag.recommend_nearby_clinics(user_location)
                return JSONResponse(content={"clinics": clinics})
            except Exception as e:
                logger.error(f"推薦診所時出錯: {e}")
                raise HTTPException(status_code=500, detail=f"推薦診所時出錯: {str(e)}")
        
        @self.app.get("/api/health")
        async def health():
            """健康檢查端點"""
            return {"status": "healthy"}
        
        @self.app.exception_handler(Exception)
        async def handle_exception(request: Request, exc: Exception):
            """全局異常處理"""
            logger.error(f"全局異常: {exc}")
            return JSONResponse(
                status_code=500,
                content={"message": f"發生內部錯誤: {str(exc)}"}
            )
    
    def mount_static_files(self, static_dir: str = "./frontend/build"):
        """
        掛載靜態文件以提供前端頁面
        
        Args:
            static_dir: 靜態文件目錄
        """
        if Path(static_dir).exists():
            self.app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
            logger.info(f"靜態文件已掛載: {static_dir}")
        else:
            logger.warning(f"靜態文件目錄不存在: {static_dir}")
    
    def start(self, host: str = "0.0.0.0", port: int = 8000):
        """
        啟動Web應用
        
        Args:
            host: 主機地址
            port: 端口號
        """
        uvicorn.run(self.app, host=host, port=port)

def main():
    """主函數"""
    # 請替換為您的API金鑰
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyDp6wUDTwfcRV5s6vj1gFERNJ5A88ydTF4")
    
    # 初始化並啟動Web應用
    webapp = RAGWebApp(google_api_key=GOOGLE_API_KEY)
    
    # 掛載靜態文件
    webapp.mount_static_files()
    
    # 啟動服務
    webapp.start()

if __name__ == "__main__":
    main()