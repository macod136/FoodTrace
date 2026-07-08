"""從原始食品 JSON 建立可發布的 food.db。"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from brand import BRAND_NAMES
from brand_rules import assign_brands
from category import CATEGORY_NAMES
from company import COMPANY_NAMES
from config import JSON_PATH
from database import rebuild_database, save_products
from transform import extract_products, load_json


def build(output_path: Path) -> dict:
    products = assign_brands(extract_products(load_json()))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rebuild_database(output_path)
    result = save_products(
        output_path,
        products,
        COMPANY_NAMES,
        CATEGORY_NAMES,
        BRAND_NAMES,
    )
    source_modified_at = datetime.fromtimestamp(
        JSON_PATH.stat().st_mtime, timezone.utc
    ).isoformat()
    with sqlite3.connect(output_path) as conn:
        conn.execute("""
            INSERT INTO app_metadata(key, value)
            VALUES ('source_file_modified_at', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (source_modified_at,))
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"資料庫完整性檢查失敗：{integrity}")
        conn.commit()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="建立溯食光食品資料庫")
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_DIR / "output" / "food.db",
    )
    args = parser.parse_args()
    result = build(args.output.resolve())
    print(f"產品匯入完成：{result['products']} 筆")
    print(f"營養資料匯入完成：{result['nutrition']} 筆")
    print(f"資料庫位置：{args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

