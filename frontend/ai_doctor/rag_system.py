import os
import json
import tempfile
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()


# RAG 必要的依賴庫
import google.generativeai as genai
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_community.vectorstores import Chroma
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb


genai.configure()
# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MenstrualHealthRAG:
    """女性月經健康RAG系統類"""
    
    def __init__(self, 
                 google_api_key: str,
                 pdf_directory: str = "./pdf_data", 
                 db_directory: str = "./chroma_db",
                 model_name: str = "gemini-2.0-flash",
                 embedding_model: str = "models/embedding-001",
                 language: str = "zh-TW"):
        """
        初始化RAG系統
        
        Args:
            google_api_key: Google API金鑰
            pdf_directory: PDF檔案目錄
            db_directory: 向量資料庫存儲目錄
            model_name: Gemini模型名稱
            embedding_model: 嵌入模型名稱
            language: 系統使用語言
        """
        self.pdf_directory = Path(pdf_directory)
        self.db_directory = Path(db_directory)
        self.model_name = model_name
        self.embedding_model = embedding_model
        self.language = language
        
        # 設置Google API
        genai.configure(api_key=google_api_key)
        # self.embeddings = GoogleGenerativeAIEmbeddings(model=embedding_model)
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=embedding_model,
            google_api_key=google_api_key
        )

        # 初始化向量存儲
        self.vector_store = None
        self.retriever = None
        self.chain = None
        
    def load_and_process_documents(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        """
        加載並處理PDF文檔
        
        Args:
            chunk_size: 文本分塊大小
            chunk_overlap: 文本分塊重疊大小
        """
        logger.info(f"開始載入PDF文件從 {self.pdf_directory}")
        
        if not self.pdf_directory.exists():
            raise FileNotFoundError(f"找不到PDF目錄: {self.pdf_directory}")
        
        # 使用DirectoryLoader加載所有PDF文件
        loader = DirectoryLoader(
            self.pdf_directory.as_posix(),
            glob="**/*.pdf",
            loader_cls=PyPDFLoader
        )
        
        documents = loader.load()
        logger.info(f"成功加載 {len(documents)} 個文檔")
        
        # 分割文檔
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        splits = text_splitter.split_documents(documents)
        logger.info(f"文檔已分割為 {len(splits)} 個片段")
        
        # 創建向量存儲
        self.vector_store = Chroma.from_documents(
            documents=splits,
            embedding=self.embeddings,
            persist_directory=self.db_directory.as_posix()
        )
        
        # 持久化向量存儲
        self.vector_store.persist()
        logger.info(f"向量存儲已創建並保存到 {self.db_directory}")
        
        # 創建檢索器
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        
    def load_existing_vector_store(self) -> bool:
        """
        加載已有的向量存儲
        
        Returns:
            bool: 是否成功加載
        """
        if not self.db_directory.exists():
            logger.warning(f"向量數據庫目錄不存在: {self.db_directory}")
            return False
        
        try:
            self.vector_store = Chroma(
                persist_directory=self.db_directory.as_posix(),
                embedding_function=self.embeddings
            )
            
            self.retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            
            logger.info(f"成功加載已有的向量存儲: {self.db_directory}")
            return True
        except Exception as e:
            logger.error(f"加載向量存儲時出錯: {e}")
            return False
            
    def setup_rag_chain(self) -> None:
        """設置RAG鏈"""
        # 創建Gemini LLM
        llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=0.3,
            convert_system_message_to_human=True,
        )
        
        # 定義系統提示模板
        template = """
        你是一位專業的女性健康顧問，擁有婦科醫學知識，擅長針對青少女提供月經相關健康建議。

        任務：根據提供的知識內容（context）與使用者問題，給出準確、同理且具體的建議。

        請依以下格式回答：

        1. 專業建議回答內容：
        - 回答時請直接融入 context 中的資訊與觀點，不需明確說明資料來源（例如「研究指出」或「根據⋯⋯」等字眼請省略）。
        - 若 context 中未提供明確資訊，可根據你具備的醫學知識給出推論建議，但請標示這是專業推論，並簡潔客觀，不可杜撰。
        - 使用條列式、段落式混合編排，使閱讀更清楚。
        2. 注意事項
        3. 是否需要就醫/尋求進一步協助的建議
        4. 資料來源註記（請放在最後一段，格式如下）：
        - 本回覆部分內容參考自：本回覆部分內容參考自：...-
⋯⋯


        回答規則：
        1. 回答必須以繁體中文呈現，使用清楚、專業且友善的語氣，不要過於冷漠。
        2. 請以條列式或段落說明方式回答。
        3. 若資訊無法確定，請清楚告知並建議尋求專業醫師協助。
        4. 請盡量使用context裡的文內容進行回答，並告知是出自哪裡。
        5. 不可杜撰內容，也不可提供與月經或女性身體無關的知識。
        6. 若能提供附近診所資訊，請提供有關女性健康和月經問題的適當診所建議。
        7. 以溫和、尊重的方式討論敏感話題，提供準確、基於證據的醫療建議。
   

        以下是知識內容：
        {context}

        使用者問題：
        {question}

        請依上述規則提供回答。

        """
        
        # 創建提示模板
        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
        
        # 設置RAG鏈
        self.chain = (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        logger.info("RAG鏈設置完成")
        
    def query(self, question: str) -> str:
        """
        查詢RAG系統
        
        Args:
            question: 用戶問題
            
        Returns:
            str: 系統回答
        """
        if not self.chain:
            raise ValueError("RAG鏈尚未設置，請先調用setup_rag_chain()")
            
        try:
            logger.info(f"接收到查詢: {question}")
            response = self.chain.invoke(question)
            return response
        except Exception as e:
            logger.error(f"查詢處理時出錯: {e}")
            return f"抱歉，處理您的問題時發生錯誤: {str(e)}"
            
    # def add_location_data(self, location_data: List[Dict[str, Any]]) -> None:
    #     """
    #     添加診所位置數據
        
    #     Args:
    #         location_data: 診所位置數據列表
    #     """
    #     # 將位置數據保存到JSON文件中
    #     location_file = Path("./clinic_locations.json")
        
    #     with open(location_file, "w", encoding="utf-8") as f:
    #         json.dump(location_data, f, ensure_ascii=False, indent=4)
            
    #     logger.info(f"診所位置數據已保存到 {location_file}")
        
#     def recommend_nearby_clinics(self, user_location: Dict[str, float], limit: int = 3) -> List[Dict[str, Any]]:
#         """
#         根據用戶位置推薦附近診所
        
#         Args:
#             user_location: 用戶位置 {"latitude": 緯度, "longitude": 經度}
#             limit: 推薦診所數量限制
            
#         Returns:
#             List[Dict[str, Any]]: 推薦診所列表
#         """
#         try:
#             location_file = Path("./clinic_locations.json")
            
#             if not location_file.exists():
#                 return []
                
#             with open(location_file, "r", encoding="utf-8") as f:
#                 clinics = json.load(f)
                
#             # TODO: 實現距離計算和排序
#             # 這裡是一個簡單示例，實際應用中需要計算地理距離
#             # 並根據距離排序診所
                
#             return clinics[:limit]
#         except Exception as e:
#             logger.error(f"推薦附近診所時出錯: {e}")
#             return []

# # 示例診所數據
# sample_clinics = [
#     {
#         "name": "女性健康中心",
#         "address": "台北市信義區忠孝東路五段55號",
#         "phone": "02-12345678",
#         "specialties": ["婦科", "月經問題", "內分泌"],
#         "coordinates": {"latitude": 25.041171, "longitude": 121.565227}
#     },
#     {
#         "name": "月亮診所",
#         "address": "台北市大安區敦化南路一段233號",
#         "phone": "02-87654321",
#         "specialties": ["婦科", "青春期諮詢", "經痛治療"],
#         "coordinates": {"latitude": 25.036398, "longitude": 121.551830}
#     },
#     {
#         "name": "健康女性醫療中心",
#         "address": "新北市板橋區民權路66號",
#         "phone": "02-29876543",
#         "specialties": ["婦科", "不孕症", "經前症候群"],
#         "coordinates": {"latitude": 25.013473, "longitude": 121.465102}
#     }
# ]

def main():
    """主函數"""
    # 請替換為您的API金鑰
    # GOOGLE_API_KEY = "AIzaSyDp6wUDTwfcRV5s6vj1gFERNJ5A88ydTF4"  # 請替換為實際的API金鑰
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("請設定環境變數 GOOGLE_API_KEY，並重新執行程式。")
    
    # 初始化RAG系統
    rag = MenstrualHealthRAG(
        google_api_key=GOOGLE_API_KEY,
        pdf_directory="/Users/ylin/Documents/AI_project/Chinese_paper",  # 使用您提供的PDF目錄
        db_directory="./chroma_db"
    )
    
    # 嘗試加載現有的向量存儲，如果不存在則重新創建
    if not rag.load_existing_vector_store():
        rag.load_and_process_documents()
    
    # 設置RAG鏈
    rag.setup_rag_chain()
    
    # # 添加診所數據
    # rag.add_location_data(sample_clinics)
    
    # 示例查詢
    question = "我的經期不規律，應該怎麼辦？"
    answer = rag.query(question)
    print(f"問題: {question}")
    print(f"回答: {answer}")
    
    # # 示例位置查詢
    # user_location = {"latitude": 25.033671, "longitude": 121.564427}
    # nearby_clinics = rag.recommend_nearby_clinics(user_location)
    # print("\n推薦附近診所:")
    # for clinic in nearby_clinics:
    #     print(f"- {clinic['name']}: {clinic['address']}, 電話: {clinic['phone']}")

if __name__ == "__main__":
    main()