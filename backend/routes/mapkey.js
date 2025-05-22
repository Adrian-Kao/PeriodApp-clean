// 📁 routes/mapkey.js
const express = require('express');
const router = express.Router();

router.get('/', (req, res) => {
  const key = process.env.GOOGLE_MAPS_API_KEY;
  if (!key) {
    return res.status(500).json({ error: 'GOOGLE_MAPS_API_KEY 未設定' });
  }
  res.json({ key });
});

module.exports = router;
