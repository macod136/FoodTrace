import json

from config import JSON_PATH


def load_json():
    with open(JSON_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data


def extract_products(data):
    products = []

    for item in data:
        product = {
            "trace_code": item.get("產品追溯系統串接碼", ""),
            "product_name": item.get("產品名稱", ""),
            "company_name": item.get("公司名稱", ""),
            "category": item.get("產品分類", ""),
            "package": item.get("包裝規格", ""),
            "front_image": item.get("正面外包裝照片", ""),
            "warning": item.get("警語", ""),

            "serving_size": item.get("每一份量", ""),
            "servings_per_package": item.get("本包裝含", ""),

            "kcal_100g": item.get("每100公克熱量", ""),
            "protein_100g": item.get("每100公克蛋白質", ""),
            "fat_100g": item.get("每100公克脂肪", ""),
            "saturated_fat_100g": item.get("每100公克飽和脂肪", ""),
            "trans_fat_100g": item.get("每100公克反式脂肪", ""),
            "carbs_100g": item.get("每100公克碳水化合物", ""),
            "sugar_100g": item.get("每100公克糖", ""),
            "sodium_100g": item.get("每100公克鈉", ""),

            "kcal_100ml": item.get("每100毫升熱量", ""),
            "protein_100ml": item.get("每100毫升蛋白質", ""),
            "fat_100ml": item.get("每100毫升脂肪", ""),
            "saturated_fat_100ml": item.get("每100毫升飽和脂肪", ""),
            "trans_fat_100ml": item.get("每100毫升反式脂肪", ""),
            "carbs_100ml": item.get("每100毫升碳水化合物", ""),
            "sugar_100ml": item.get("每100毫升糖", ""),
            "sodium_100ml": item.get("每100毫升鈉", ""),
        }

        products.append(product)

    return products