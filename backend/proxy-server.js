require('dotenv').config();
const express = require('express');
const cors = require('cors');
const admin = require('firebase-admin');
const path = require('path');

const chatRoute = require('./routes/chat');
const mapkeyRoute = require('./routes/mapkey');

// ✅ 加入防止重複初始化 Firebase App
const serviceAccount = require('./serviceAccountKey.json');
if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount),
  });
}

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// 🚀 掛載功能模組路由
app.use('/chat', chatRoute); // POST /chat
app.use('/mapkey', mapkeyRoute); // GET /mapkey

// ✅ 提供靜態前端頁面（可選）
app.use(express.static(path.join(__dirname, '../frontend')));

app.listen(PORT, () => {
  console.log(`✅ Server running at http://localhost:${PORT}`);
});
