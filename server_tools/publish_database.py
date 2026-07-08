"""壓縮 food.db，計算校驗碼並建立 manifest.json。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_database(path: Path) -> str:
    with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as conn:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("food.db 完整性檢查失敗")
        metadata = dict(conn.execute("SELECT key, value FROM app_metadata"))
        if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] <= 0:
            raise RuntimeError("food.db 沒有產品資料")
    return metadata.get("database_schema", "")


def publish(database: Path, output_dir: Path, version: str, base_url: str) -> dict:
    schema = validate_database(database)
    if not schema:
        raise RuntimeError("food.db 缺少 database_schema")
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / "food.db.zip"
    temporary_archive = output_dir / "food.db.zip.tmp"
    with zipfile.ZipFile(
        temporary_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as package:
        package.write(database, "food.db")
    temporary_archive.replace(archive_path)
    manifest = {
        "version": version,
        "database_schema": schema,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "size": archive_path.stat().st_size,
        "sha256": sha256_file(archive_path),
        "download_url": f"{base_url.rstrip('/')}/food.db.zip",
    }
    temporary_manifest = output_dir / "manifest.json.tmp"
    temporary_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary_manifest.replace(output_dir / "manifest.json")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="發布溯食光食品資料庫")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    manifest = publish(
        args.database.resolve(),
        args.output_dir.resolve(),
        args.version,
        args.base_url,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
