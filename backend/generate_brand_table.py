"""依品牌規則與食品 JSON 重新產生 brand.py 品牌主檔。"""

import argparse
from pathlib import Path

from brand_rules import assign_brands
from transform import extract_products, load_json

try:
    from brand import BRAND_NAMES as EXISTING_BRAND_NAMES
except ImportError:
    EXISTING_BRAND_NAMES = ()


OUTPUT_PATH = Path(__file__).resolve().parent / "brand.py"


def generate(clean=False):
    products = assign_brands(extract_products(load_json()))
    discovered_names = sorted(set(
        product["brand_name"]
        for product in products
        if product.get("brand_name")
    ), key=lambda name: (name.casefold(), name))
    # 首次發布前可乾淨重建；發布後預設保留既有 ID，只追加新品牌。
    brand_names = [] if clean else list(EXISTING_BRAND_NAMES)
    known_names = set(brand_names)
    brand_names.extend(
        name for name in discovered_names if name not in known_names
    )

    lines = [
        '"""由 generate_brand_table.py 自動產生的品牌主檔。"""',
        "",
        "# 清單位置即固定品牌順序；brand_id 從 1 開始。",
        "BRAND_NAMES = (",
    ]
    lines.extend(f"    {ascii(name)}," for name in brand_names)
    lines.extend([
        ")",
        "",
        "BRAND_NAME_TO_ID = {",
        "    name: index",
        "    for index, name in enumerate(BRAND_NAMES, start=1)",
        "}",
        "",
        "BRAND_ID_TO_NAME = {",
        "    index: name",
        "    for index, name in enumerate(BRAND_NAMES, start=1)",
        "}",
        "",
    ])
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"品牌主檔已產生：{len(brand_names)} 個品牌")
    return brand_names


def main():
    parser = argparse.ArgumentParser(description="產生品牌主檔")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="首次發布前乾淨重建，不保留舊品牌與 ID",
    )
    args = parser.parse_args()
    generate(clean=args.clean)


if __name__ == "__main__":
    main()
