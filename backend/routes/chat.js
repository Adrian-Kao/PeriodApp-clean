// 📁 routes/chat.js
const express = require('express');
const axios = require('axios');
const router = express.Router();
const admin = require('firebase-admin');

if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert(require('../serviceAccountKey.json'))
  });
}
const db = admin.firestore();
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const { keywordMap, getDishType } = require('../utils/dishHelper');

router.post('/', async (req, res) => {
  const userMessage = req.body.message;
  if (!userMessage) return res.status(400).json({ error: "請提供 message 欄位。" });

  try {
    const snapshot = await db.collection('dishes').get();
    const allDishes = snapshot.docs.map(doc => doc.data());

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

    let prompt = onlyWantsDrink ? `
使用者輸入：「${userMessage}」
請只從下列飲品或甜點中推薦 1～2 項：
${JSON.stringify(drinks, null, 2)}
` : `
使用者輸入：「${userMessage}」
請根據下列選項推薦完整套餐。
【主餐】${JSON.stringify(mains, null, 2)}
【配菜】${JSON.stringify(sides, null, 2)}
【飲品】${JSON.stringify(drinks, null, 2)}
`;

    const response = await axios.post(
      `https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.7, maxOutputTokens: 500 },
      },
      { headers: { 'Content-Type': 'application/json' } }
    );

    const reply = response.data.candidates?.[0]?.content?.parts?.[0]?.text || '無法取得 Gemini 回覆';
    res.json({ reply });
  } catch (error) {
    console.error('Gemini 錯誤：', error.response?.data || error.message);
    res.status(500).json({ error: '伺服器錯誤', detail: error.response?.data || error.message });
  }
});

module.exports = router;
