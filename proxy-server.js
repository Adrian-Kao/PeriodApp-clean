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

// 健康需求對應的餐點分類
const keywordMap = {
  "經痛": ["優質蛋白質", "低GI碳水", "蔬菜類", "健康脂肪", "鐵質補給類", "抗發炎食物"],
  "想吃甜點": ["功能性甜點", "飲品"],
  "容易疲勞": ["健康主食", "優質蛋白質", "高纖類"],
  "控糖": ["低GI碳水", "健康主食", "高纖類"],
  "需要補鐵": ["鐵質補給類", "優質蛋白質"],
  "清爽一點": ["蔬菜類", "湯品", "飲品"],
  "放鬆心情": ["功能性甜點", "飲品", "健康脂肪"]
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

    // 根據輸入篩選分類
    const matchedKeywords = Object.keys(keywordMap).find(key => userMessage.includes(key));
    const tagsToFilter = matchedKeywords ? keywordMap[matchedKeywords] : [];

    const filteredDishes = tagsToFilter.length === 0
      ? allDishes.slice(0, 50)
      : allDishes.filter(dish => tagsToFilter.includes(dish.category)).slice(0, 50);

    // 自動分類函式：主餐 / 配菜 / 飲品
    const getDishType = (dish) => {
      const name = dish.name || '';
      const category = dish.category || '';
      if (
        name.includes("飯") || name.includes("麵") ||
        category.includes("主食") || category.includes("蛋白質")
      ) return "主餐";
      if (
        name.includes("湯") || name.includes("青菜") || name.includes("菜") ||
        category.includes("蔬菜") || category.includes("湯品")
      ) return "配菜";
      if (
        name.includes("茶") || name.includes("豆漿") || name.includes("飲") || name.includes("甜") ||
        category.includes("飲品") || category.includes("甜點")
      ) return "飲品";
      return "其他";
    };

    // 分類各自挑出 10 道以內
    const mains = filteredDishes.filter(d => getDishType(d) === "主餐").slice(0, 10);
    const sides = filteredDishes.filter(d => getDishType(d) === "配菜").slice(0, 10);
    const drinks = filteredDishes.filter(d => getDishType(d) === "飲品").slice(0, 10);

    // 組 Gemini prompt（清楚分類）
    const prompt = `
使用者輸入的健康需求是：「${userMessage}」

請根據下列選項，搭配出一份完整套餐，包含：
- 一份【主餐】
- 一道【配菜】
- 一杯【飲品或甜點】

每道請列出菜名（含店名）與一句推薦理由，語氣簡短明確，避免多餘說明。
格式如下：

【主餐】
雞腿飯（左撇子便當）：富含蛋白質，補充經期體力

【配菜】
燙青菜（給力盒子）：高纖維，幫助消化

【飲品或甜點】
紅豆湯（清心福全）：甜度適中，有助舒緩情緒

【主餐選項】
${JSON.stringify(mains, null, 2)}

【配菜選項】
${JSON.stringify(sides, null, 2)}

【飲品或甜點選項】
${JSON.stringify(drinks, null, 2)}
`;

    const response = await axios.post(
      `https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.7,
          maxOutputTokens: 400
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
