"""產生品牌判定品質報告，不修改資料庫。"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from brand_rules import GENERIC_BRAND_WORDS, assign_brands
from transform import extract_products, load_json


def audit_products(products: list[dict]) -> tuple[dict, list[dict]]:
    source_counts = Counter(product["brand_source"] for product in products)
    confidence_counts = Counter(
        product["brand_confidence"] for product in products
    )
    candidates: dict[str, dict] = defaultdict(lambda: {
        "product_count": 0,
        "companies": set(),
        "sources": Counter(),
        "confidence": Counter(),
        "examples": [],
    })
    for product in products:
        name = product.get("brand_name") or product.get("brand_fallback_name")
        if not name:
            continue
        item = candidates[name]
        item["product_count"] += 1
        item["companies"].add(product.get("company_name", ""))
        item["sources"][product["brand_source"]] += 1
        item["confidence"][product["brand_confidence"]] += 1
        if len(item["examples"]) < 3:
            item["examples"].append(product.get("product_name", ""))

    rows = []
    for name, item in candidates.items():
        rows.append({
            "candidate": name,
            "product_count": item["product_count"],
            "company_count": len(item["companies"]),
            "sources": ",".join(item["sources"]),
            "confidence": ",".join(item["confidence"]),
            "examples": " | ".join(item["examples"]),
        })
    rows.sort(key=lambda row: (-row["product_count"], row["candidate"].casefold()))

    formal_names = {
        product["brand_name"] for product in products if product.get("brand_name")
    }
    generic_formal_names = sorted(formal_names & GENERIC_BRAND_WORDS)
    summary = {
        "total_products": len(products),
        "formal_brand_products": sum(
            1 for product in products if product.get("brand_name")
        ),
        "company_fallback_products": source_counts["company_fallback"],
        "unknown_products": source_counts["unknown"],
        "formal_brand_count": len(formal_names),
        "all_candidate_count": len(candidates),
        "source_counts": dict(sorted(source_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "generic_formal_names": generic_formal_names,
    }
    return summary, rows


def write_report(output_dir: Path) -> dict:
    products = assign_brands(extract_products(load_json()))
    summary, rows = audit_products(products)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "brand_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "brand_candidates.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=(
            "candidate", "product_count", "company_count", "sources",
            "confidence", "examples",
        ))
        writer.writeheader()
        writer.writerows(rows)
    if summary["generic_formal_names"]:
        raise RuntimeError(
            "通用食品詞被列為正式品牌："
            + ", ".join(summary["generic_formal_names"])
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="產生品牌品質稽核報告")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "reports",
    )
    args = parser.parse_args()
    summary = write_report(args.output_dir.resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

