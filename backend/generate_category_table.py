"""從食品 JSON 重新產生 category.py 分類主檔。"""

from pathlib import Path

from transform import extract_products, load_json

try:
    from category import CATEGORY_NAMES as EXISTING_CATEGORY_NAMES
except ImportError:
    EXISTING_CATEGORY_NAMES = ()


OUTPUT_PATH = Path(__file__).resolve().parent / "category.py"


def main():
    products = extract_products(load_json())
    discovered_names = list(dict.fromkeys(
        product["category"]
        for product in products
        if product.get("category")
    ))
    # 已存在的名稱與位置永遠保留，新分類只追加到尾端。
    category_names = list(EXISTING_CATEGORY_NAMES)
    known_names = set(category_names)
    category_names.extend(
        name for name in discovered_names if name not in known_names
    )

    lines = [
        '"""由 generate_category_table.py 自動產生的產品分類主檔。"""',
        "",
        "# 清單位置即固定分類順序；category_id 從 1 開始。",
        "CATEGORY_NAMES = (",
    ]
    lines.extend(f"    {ascii(name)}," for name in category_names)
    lines.extend([
        ")",
        "",
        "CATEGORY_NAME_TO_ID = {",
        "    name: index",
        "    for index, name in enumerate(CATEGORY_NAMES, start=1)",
        "}",
        "",
        "CATEGORY_ID_TO_NAME = {",
        "    index: name",
        "    for index, name in enumerate(CATEGORY_NAMES, start=1)",
        "}",
        "",
    ])
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"分類主檔已產生：{len(category_names)} 個分類")


if __name__ == "__main__":
    main()
