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

// 使用者需求 → 對應的餐點分類
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

    // 判斷關鍵字對應分類
    const matchedKeywords = Object.keys(keywordMap).find(key => userMessage.includes(key));
    const tagsToFilter = matchedKeywords ? keywordMap[matchedKeywords] : [];

    // 根據分類篩選餐點
    const filteredDishes = tagsToFilter.length === 0
      ? allDishes.slice(0, 30)
      : allDishes.filter(dish => tagsToFilter.includes(dish.category)).slice(0, 30);

    // 精簡版 Gemini prompt
    const prompt = `
使用者輸入的健康需求是：「${userMessage}」。

以下是餐點選項（最多 30 筆）：
${JSON.stringify(filteredDishes, null, 2)}

請從中推薦最適合的 3 道餐點。每道列出：
- 菜名（店名）
- 一句推薦理由（說明其營養或口味優勢）

請直接列出推薦，勿加入寒暄或多餘文字。格式如下：

1. 菜名（店名）：推薦理由。
2. ...
3. ...
`;

    const response = await axios.post(
      `https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.7,
          maxOutputTokens: 300 // 限制回應長度
        },
        safetySettings: [
          { category: "HARM_CATEGORY_HATE_SPEECH", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
          { category: "HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
          { category: "HARM_CATEGORY_DANGEROUS_CONTENT", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
          { category: "HARM_CATEGORY_HARASSMENT", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
          { category: "HARM_CATEGORY_CIVIC_INTEGRITY", threshold: "BLOCK_MEDIUM_AND_ABOVE" }
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
