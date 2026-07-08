"""從食品 JSON 重新產生 company.py 公司主檔。"""

from pathlib import Path

from transform import extract_products, load_json


OUTPUT_PATH = Path(__file__).resolve().parent / "company.py"


def main():
    products = extract_products(load_json())
    company_names = list(dict.fromkeys(
        product["company_name"]
        for product in products
        if product.get("company_name")
    ))

    lines = [
        '"""由 generate_company_table.py 自動產生的公司主檔。"""',
        "",
        "# 清單位置即公司固定順序；資料庫 company_id 從 1 開始。",
        "COMPANY_NAMES = (",
    ]
    lines.extend(f"    {ascii(name)}," for name in company_names)
    lines.extend([
        ")",
        "",
        "COMPANY_NAME_TO_ID = {",
        "    name: index",
        "    for index, name in enumerate(COMPANY_NAMES, start=1)",
        "}",
        "",
    ])
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"公司主檔已產生：{len(company_names)} 家公司")


if __name__ == "__main__":
    main()
