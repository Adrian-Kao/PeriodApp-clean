// proxy-server.js（使用 .env 儲存 Gemini 金鑰 + Firebase 初始化）
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const admin = require('firebase-admin');
const fs = require('fs');

// 初始化 Firebase Admin
const serviceAccount = require('./serviceAccountKey.json');
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
});
const db = admin.firestore();

const app = express();
const PORT = process.env.PORT || 3000;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

app.use(cors());
app.use(express.json());

// 對應使用者需求 → 對應分類關鍵字（可擴充）
const keywordMap = {
  "經痛": ["優質蛋白質", "低GI", "蔬菜"],
  "想吃甜點": ["功能性甜點"],
  "容易疲勞": ["健康主食", "優質蛋白質"]
};

app.post('/chat', async (req, res) => {
  const userMessage = req.body.message;
  if (!userMessage) {
    return res.status(400).json({ error: "請提供 message 欄位。" });
  }

  try {
    const snapshot = await db.collection('dishes').get();
    const allDishes = [];
    snapshot.forEach(doc => allDishes.push(doc.data()));

    // 自動從輸入中判斷要過濾的分類（簡易比對）
    const matchedKeywords = Object.keys(keywordMap).find(key => userMessage.includes(key));
    const tagsToFilter = matchedKeywords ? keywordMap[matchedKeywords] : [];

    // 根據關鍵分類篩選餐點
    const filteredDishes = tagsToFilter.length === 0
      ? allDishes.slice(0, 30)
      : allDishes.filter(dish => tagsToFilter.includes(dish.category)).slice(0, 30);

    // 組合 prompt
    const prompt = `使用者目前的健康需求是：「${userMessage}」\n\n以下是可選擇的餐點資料，請根據需求從中推薦 3 道菜，並說明推薦理由：\n\n${JSON.stringify(filteredDishes, null, 2)}`;

    const response = await axios.post(
      `https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.7 },
        safetySettings: [
          { category: "HARM_CATEGORY_DEROGATORY", threshold: 3 },
          { category: "HARM_CATEGORY_VIOLENCE", threshold: 3 },
          { category: "HARM_CATEGORY_SEXUAL", threshold: 3 },
          { category: "HARM_CATEGORY_HARASSMENT", threshold: 3 }
        ]
      },
      {
        headers: { 'Content-Type': 'application/json' }
      }
    );

    const reply = response.data.candidates?.[0]?.content?.parts?.[0]?.text || '無法取得 Gemini 回覆';
    res.json({ reply });
  } catch (error) {
    console.error('❌ Gemini API 錯誤：', error.response?.data || error.message);
    res.status(500).json({ error: '伺服器錯誤', detail: error.response?.data || error.message });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Gemini Proxy Server 已啟動在 http://localhost:${PORT}`);
});

