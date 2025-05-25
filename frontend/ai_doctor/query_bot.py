import torch
import chromadb
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer

# 1. 嵌入模型（中文適配）
embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# 2. 本地 LLM 模型（可改為更輕量模型）
model_id = "THUDM/chatglm3-6b"
device = torch.device("cpu")
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True).to(device).eval()

# 3. 向量資料庫連線
client = chromadb.Client()
collection = client.get_or_create_collection("menstruation_knowledge")

# 4. 提問
user_question = input("請輸入你的問題（中文）：\n> ")

# 5. 查詢向量庫
query_vector = embedding_model.encode(user_question).tolist()
results = collection.query(query_embeddings=[query_vector], n_results=3)

docs = results["documents"][0]
metas = results["metadatas"][0]
context = "\n---\n".join(docs)

# 顯示引用資料與來源
print("\n🔍 使用到的段落與來源：\n")
for i, (doc, meta) in enumerate(zip(docs, metas), 1):
    print(f"段落 {i}: {doc[:100]}...")
    source_info = f"{meta.get('source', '未知檔案')}"
    if "page" in meta:
        source_info += f"（第 {meta['page']} 頁）"
    print(f"來源：{source_info}\n")

# 6. 建立 Prompt
prompt = f"""你是一位具有婦產科背景的專業中文醫師，請根據下列段落內容，使用溫柔且具有同理心的語氣，以繁體中文詳細回答使用者的問題。

特別注意事項：
1. 回答內容必須大部分基於提供的段落內容，不得引入額外未提及的知識或主觀推測。
2. 如果段落中沒有明確提供答案，請直接告知「建議諮詢專業醫師」。
3. 語氣要溫柔、清楚且具同理心，適量使用專業術語。
4. 最終回答請簡潔明瞭，適合一般民眾理解或可以讓他們拿著藥方去藥局或求醫。

📚 段落內容：
{context}

🙋 使用者提問：
{user_question}

✍️ 請以繁體中文詳細且溫柔地回答：

"""

# 7. 使用 ChatGLM3 回應
response_text, _ = model.chat(tokenizer, prompt, history=[], temperature=0.7)

# 8. 輸出結果
print("\n✅ 本地模型回應：\n")
print(response_text.strip())
