const admin = require("firebase-admin");
const serviceAccount = require("./serviceAccountKey.json");
const dishes = require("./dishes-mos.json");

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

const db = admin.firestore();

async function importDishes() {
  const batch = db.batch();
  const dishesCollection = db.collection("dishes");

  dishes.forEach((dish) => {
    const docRef = dishesCollection.doc(); // 自動產生 ID
    batch.set(docRef, dish);
  });

  await batch.commit();
  console.log("✅ 完整菜單已成功匯入！");
}

importDishes().catch(console.error);
