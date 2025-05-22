const keywordMap = {
  "經痛": ["優質蛋白質", "低GI碳水", "蔬菜類", "健康脂肪", "鐵質補給類", "抗發炎食物"],
  "想吃甜點": ["甜點類", "飲品"],
  "容易疲勞": ["健康主食", "優質蛋白質", "高纖類"],
  "控糖": ["低GI碳水", "健康主食", "高纖類"],
  "需要補鐵": ["鐵質補給類", "優質蛋白質"],
  "清爽一點": ["蔬菜類", "湯品", "飲品"],
  "放鬆心情": ["甜點類", "飲品", "健康脂肪"]
};

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

module.exports = { keywordMap, getDishType };