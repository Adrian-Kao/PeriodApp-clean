require('dotenv').config();
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const admin = require('firebase-admin');

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

// 關鍵字對應分類
const keywordMap = {
  "經痛": ["優質蛋白質", "低GI碳水", "蔬菜類", "健康脂肪", "鐵質補給類", "抗發炎食物"],
  "想吃甜點": ["甜點類", "飲品"],
  "容易疲勞": ["健康主食", "優質蛋白質", "高纖類"],
  "控糖": ["低GI碳水", "健康主食", "高纖類"],
  "需要補鐵": ["鐵質補給類", "優質蛋白質"],
  "清爽一點": ["蔬菜類", "湯品", "飲品"],
  "放鬆心情": ["甜點類", "飲品", "健康脂肪"]
};

// ✅ 最終版分類函式（支援甜點類）
const getDishType = (dish) => {
  const name = (dish.name || '').toLowerCase();
  const category = (dish.category || '').toLowerCase();

  if (
    name.includes("飯") || name.includes("麵") ||
    category.includes("主食") || category.includes("蛋白質")
  ) return "主餐";

  if (
    name.includes("湯") || name.includes("青菜") || name.includes("菜") ||
    category.includes("蔬菜") || category.includes("湯品")
  ) return "配菜";

  if (
    name.match(/茶|豆漿|飲|湯|果汁|奶|紅豆|甜|咖啡|可可|糖/) ||
    category.match(/飲品|甜點|甜點類|功能性甜點/)
  ) return "飲品";

  return "其他";
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

    // 使用者是否只問飲品類
    const lowerMessage = userMessage.toLowerCase();
    const onlyWantsDrink = /飲料|喝的|飲品|茶|湯|甜點|紅豆|豆漿|手搖|咖啡/.test(lowerMessage);

    const matchedKeywords = Object.keys(keywordMap).find(key => userMessage.includes(key));
    const tagsToFilter = matchedKeywords ? keywordMap[matchedKeywords] : [];

    const filteredDishes = tagsToFilter.length === 0
      ? allDishes.slice(0, 50)
      : allDishes.filter(dish => tagsToFilter.includes(dish.category)).slice(0, 50);

    const mains = filteredDishes.filter(d => getDishType(d) === "主餐").slice(0, 10);
    const sides = filteredDishes.filter(d => getDishType(d) === "配菜").slice(0, 10);
    const drinks = filteredDishes.filter(d => getDishType(d) === "飲品").slice(0, 10);

    // 👇 prompt 依使用情境切換
    let prompt = "";

    if (onlyWantsDrink) {
      prompt = `
使用者輸入：「${userMessage}」

請只從下列飲品或甜點中推薦 1～2 項，幫助使用者舒緩經期不適、放鬆身心或補充能量。

請用以下格式輸出，每項之間請保留一行空白：

名稱（店名）：一句推薦理由。

【飲品或甜點選項】  
${JSON.stringify(drinks, null, 2)}
`;
    } else {
      prompt = `
使用者輸入的健康需求是：「${userMessage}」

請你將這視為一位女性在「生理週期」期間的飲食需求。根據她的身體狀態（經前、經期、經後），從以下三組餐點中各挑選一道組成完整套餐。

推薦標準：
- 舒緩經痛／溫熱補養／促進消化／補鐵抗發炎
- 語氣溫和簡潔，不需寒暄
- 每道餐點請用「菜名（店名）：一句推薦理由」表示

📌 請用以下格式輸出，每段之間請保留一行空白！

【主餐】  
菜名（店名）：推薦理由。

【配菜】  
菜名（店名）：推薦理由。

【飲品或甜點】  
菜名（店名）：推薦理由。

小提醒：多補水，也記得讓身體好好休息。

【主餐選項】  
${JSON.stringify(mains, null, 2)}

【配菜選項】  
${JSON.stringify(sides, null, 2)}

【飲品或甜點選項】  
${JSON.stringify(drinks, null, 2)}
`;
    }

    const response = await axios.post(
      `https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.7, maxOutputTokens: 500 },
        safetySettings: [
          { category: "HARM_CATEGORY_HATE_SPEECH", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
          { category: "HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
          { category: "HARM_CATEGORY_DANGEROUS_CONTENT", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
          { category: "HARM_CATEGORY_HARASSMENT", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
          { category: "HARM_CATEGORY_CIVIC_INTEGRITY", threshold: "BLOCK_MEDIUM_AND_ABOVE" }
        ]
      },
      { headers: { 'Content-Type': 'application/json' } }
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
