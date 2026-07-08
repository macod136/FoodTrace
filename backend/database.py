import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def rebuild_database(db_path):
    """刪除可再生的舊資料庫，依目前結構重新建立。"""
    Path(db_path).unlink(missing_ok=True)
    create_database(db_path)


def create_database(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # =========================
    # groups
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    """)

    # =========================
    # companies
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER,
        name TEXT NOT NULL UNIQUE,
        FOREIGN KEY (group_id) REFERENCES groups(id)
    )
    """)

    # =========================
    # products
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        brand_id INTEGER,
        company_id INTEGER,
        category_id INTEGER,

        brand_fallback_name TEXT,
        brand_source TEXT NOT NULL DEFAULT 'unknown',
        brand_confidence TEXT NOT NULL DEFAULT 'unknown',
        brand_matched_text TEXT,
        brand_reason TEXT,

        trace_code TEXT UNIQUE,

        product_name TEXT NOT NULL,
        package TEXT,

        front_image TEXT,
        back_image TEXT,
        side_image TEXT,

        warning TEXT,
        feature TEXT,

        start_date TEXT,

        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS brands (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE
    )
    """)

    # 讓舊版已建立的資料庫也能加入公司關聯欄位。
    product_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(products)")
    }
    if "company_id" not in product_columns:
        cursor.execute(
            "ALTER TABLE products ADD COLUMN company_id INTEGER "
            "REFERENCES companies(id)"
        )
    brand_audit_columns = {
        "brand_fallback_name": "TEXT",
        "brand_source": "TEXT NOT NULL DEFAULT 'unknown'",
        "brand_confidence": "TEXT NOT NULL DEFAULT 'unknown'",
        "brand_matched_text": "TEXT",
        "brand_reason": "TEXT",
    }
    for column, definition in brand_audit_columns.items():
        if column not in product_columns:
            cursor.execute(
                f"ALTER TABLE products ADD COLUMN {column} {definition}"
            )

    # =========================
    # nutrition
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nutrition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        product_id INTEGER UNIQUE,

        serving_size TEXT,
        servings_per_package TEXT,

        kcal_100g TEXT,
        protein_100g TEXT,
        fat_100g TEXT,
        saturated_fat_100g TEXT,
        trans_fat_100g TEXT,
        carbs_100g TEXT,
        sugar_100g TEXT,
        sodium_100g TEXT,

        kcal_100ml TEXT,
        protein_100ml TEXT,
        fat_100ml TEXT,
        saturated_fat_100ml TEXT,
        trans_fat_100ml TEXT,
        carbs_100ml TEXT,
        sugar_100ml TEXT,
        sodium_100ml TEXT,

        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)

    # =========================
    # aliases
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        type TEXT NOT NULL,
        alias TEXT NOT NULL,
        target_id INTEGER NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    cursor.execute("""
    INSERT INTO app_metadata(key, value) VALUES ('database_schema', '2')
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """)

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_products_company_id "
        "ON products(company_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_products_category_id "
        "ON products(category_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_products_brand_id "
        "ON products(brand_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_products_brand_category "
        "ON products(brand_id, category_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_products_company_category "
        "ON products(company_id, category_id)"
    )

    # contentless trigram FTS：保留搜尋索引，不另外提供重複文字欄位。
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS product_search USING fts5(
        product_name,
        brand_name,
        company_name,
        category_name,
        package,
        content='',
        tokenize='trigram'
    )
    """)

    # 前端可直接查詢這個 View，取得產品頁需要的所有欄位。
    cursor.execute("DROP VIEW IF EXISTS product_details")
    cursor.execute("""
    CREATE VIEW product_details AS
    SELECT
        p.id AS product_id,
        p.brand_id,
        p.company_id,
        p.category_id,
        p.trace_code,
        p.product_name,
        COALESCE(b.name, p.brand_fallback_name) AS brand_name,
        p.brand_source,
        p.brand_confidence,
        p.brand_matched_text,
        p.brand_reason,
        CASE WHEN p.brand_source = 'company_fallback' THEN 1 ELSE 0 END
            AS brand_is_fallback,
        c.name AS company_name,
        cat.name AS category,
        p.package,
        p.front_image,
        p.warning,
        n.serving_size,
        n.servings_per_package,
        n.kcal_100g,
        n.protein_100g,
        n.fat_100g,
        n.saturated_fat_100g,
        n.trans_fat_100g,
        n.carbs_100g,
        n.sugar_100g,
        n.sodium_100g,
        n.kcal_100ml,
        n.protein_100ml,
        n.fat_100ml,
        n.saturated_fat_100ml,
        n.trans_fat_100ml,
        n.carbs_100ml,
        n.sugar_100ml,
        n.sodium_100ml
    FROM products AS p
    LEFT JOIN brands AS b ON b.id = p.brand_id
    LEFT JOIN companies AS c ON c.id = p.company_id
    LEFT JOIN categories AS cat ON cat.id = p.category_id
    LEFT JOIN nutrition AS n ON n.product_id = p.id
    """)

    conn.commit()
    conn.close()
def save_products(
    db_path,
    products,
    company_names,
    category_names,
    brand_names,
):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    try:
        json_company_names = {
            product["company_name"]
            for product in products
            if product.get("company_name")
        }
        if len(company_names) != len(set(company_names)):
            raise ValueError("company.py 內含重複的公司名稱")
        missing_companies = json_company_names - set(company_names)
        if missing_companies:
            raise ValueError(
                "company.py 缺少 JSON 中的公司，請先執行 "
                "python generate_company_table.py"
            )

        json_category_names = {
            product["category"]
            for product in products
            if product.get("category")
        }
        if len(category_names) != len(set(category_names)):
            raise ValueError("category.py 內含重複的分類名稱")
        missing_categories = json_category_names - set(category_names)
        if missing_categories:
            raise ValueError(
                "category.py 缺少 JSON 中的分類，請先執行 "
                "python generate_category_table.py"
            )

        json_brand_names = {
            product["brand_name"]
            for product in products
            if product.get("brand_name")
        }
        if len(brand_names) != len(set(brand_names)):
            raise ValueError("brand.py 內含重複的品牌名稱")
        missing_brands = json_brand_names - set(brand_names)
        if missing_brands:
            raise ValueError(
                "brand.py 缺少本次提取出的品牌，請先執行 "
                "python generate_brand_table.py"
            )

        # 公司 ID 完全依 company.py 的清單順序重建。
        cursor.execute("UPDATE products SET company_id = NULL")
        cursor.execute("DELETE FROM companies")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'companies'")
        cursor.executemany(
            "INSERT INTO companies(id, name) VALUES (?, ?)",
            enumerate(company_names, start=1),
        )
        company_ids = {
            name: company_id
            for company_id, name in enumerate(company_names, start=1)
        }
        category_ids = {
            name: category_id
            for category_id, name in enumerate(category_names, start=1)
        }

        brand_ids = {
            name: brand_id
            for brand_id, name in enumerate(brand_names, start=1)
        }

        cursor.execute("DELETE FROM categories")
        cursor.executemany(
            "INSERT INTO categories(id, name) VALUES (?, ?)",
            enumerate(category_names, start=1),
        )
        cursor.execute("DELETE FROM brands")
        cursor.executemany(
            "INSERT INTO brands(id, name) VALUES (?, ?)",
            enumerate(brand_names, start=1),
        )

        product_sql = """
        INSERT INTO products (
            brand_id,
            company_id,
            category_id,
            brand_fallback_name,
            brand_source,
            brand_confidence,
            brand_matched_text,
            brand_reason,
            trace_code,
            product_name,
            package,
            front_image,
            warning
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(trace_code) DO UPDATE SET
            brand_id = excluded.brand_id,
            company_id = excluded.company_id,
            category_id = excluded.category_id,
            brand_fallback_name = excluded.brand_fallback_name,
            brand_source = excluded.brand_source,
            brand_confidence = excluded.brand_confidence,
            brand_matched_text = excluded.brand_matched_text,
            brand_reason = excluded.brand_reason,
            product_name = excluded.product_name,
            package = excluded.package,
            front_image = excluded.front_image,
            warning = excluded.warning
        """
        cursor.executemany(
            product_sql,
            (
                (
                    brand_ids.get(product.get("brand_name")),
                    company_ids.get(product.get("company_name")),
                    category_ids.get(product.get("category")),
                    product.get("brand_fallback_name", ""),
                    product.get("brand_source", "unknown"),
                    product.get("brand_confidence", "unknown"),
                    product.get("brand_matched_text", ""),
                    product.get("brand_reason", ""),
                    product["trace_code"],
                    product["product_name"],
                    product["package"],
                    product["front_image"],
                    product["warning"],
                )
                for product in products
            ),
        )

        product_ids = dict(cursor.execute(
            "SELECT trace_code, id FROM products"
        ))
        cursor.executemany(
            """
            INSERT INTO product_search(
                rowid,
                product_name,
                brand_name,
                company_name,
                category_name,
                package
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    product_ids[product["trace_code"]],
                    product["product_name"],
                    product.get("brand_name")
                    or product.get("brand_fallback_name", ""),
                    product.get("company_name", ""),
                    product.get("category", ""),
                    product.get("package", ""),
                )
                for product in products
            ),
        )
        nutrition_sql = """
        INSERT INTO nutrition (
            product_id,
            serving_size,
            servings_per_package,
            kcal_100g,
            protein_100g,
            fat_100g,
            saturated_fat_100g,
            trans_fat_100g,
            carbs_100g,
            sugar_100g,
            sodium_100g,
            kcal_100ml,
            protein_100ml,
            fat_100ml,
            saturated_fat_100ml,
            trans_fat_100ml,
            carbs_100ml,
            sugar_100ml,
            sodium_100ml
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(product_id) DO UPDATE SET
            serving_size = excluded.serving_size,
            servings_per_package = excluded.servings_per_package,
            kcal_100g = excluded.kcal_100g,
            protein_100g = excluded.protein_100g,
            fat_100g = excluded.fat_100g,
            saturated_fat_100g = excluded.saturated_fat_100g,
            trans_fat_100g = excluded.trans_fat_100g,
            carbs_100g = excluded.carbs_100g,
            sugar_100g = excluded.sugar_100g,
            sodium_100g = excluded.sodium_100g,
            kcal_100ml = excluded.kcal_100ml,
            protein_100ml = excluded.protein_100ml,
            fat_100ml = excluded.fat_100ml,
            saturated_fat_100ml = excluded.saturated_fat_100ml,
            trans_fat_100ml = excluded.trans_fat_100ml,
            carbs_100ml = excluded.carbs_100ml,
            sugar_100ml = excluded.sugar_100ml,
            sodium_100ml = excluded.sodium_100ml
        """
        nutrition_fields = (
            "serving_size",
            "servings_per_package",
            "kcal_100g",
            "protein_100g",
            "fat_100g",
            "saturated_fat_100g",
            "trans_fat_100g",
            "carbs_100g",
            "sugar_100g",
            "sodium_100g",
            "kcal_100ml",
            "protein_100ml",
            "fat_100ml",
            "saturated_fat_100ml",
            "trans_fat_100ml",
            "carbs_100ml",
            "sugar_100ml",
            "sodium_100ml",
        )
        cursor.executemany(
            nutrition_sql,
            (
                (product_ids[product["trace_code"]],)
                + tuple(product[field] for field in nutrition_fields)
                for product in products
            ),
        )

        cursor.execute("""
        INSERT INTO app_metadata(key, value) VALUES ('last_imported_at', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (datetime.now(timezone.utc).isoformat(),))

        conn.commit()
        return {
            "products": cursor.execute(
                "SELECT COUNT(*) FROM products"
            ).fetchone()[0],
            "nutrition": cursor.execute(
                "SELECT COUNT(*) FROM nutrition"
            ).fetchone()[0],
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
