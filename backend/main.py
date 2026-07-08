import argparse
import re
import shutil
import sqlite3
from contextlib import asynccontextmanager, closing
from urllib.parse import urlparse

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import (
    ALLOWED_ORIGINS,
    DATABASE_PATH,
    DISCLAIMER,
    FRONTEND_DIR,
    INITIAL_DATABASE_PATH,
    SOURCE_URL,
    USER_DATABASE_PATH,
)
from database import create_database
from user_database import (
    add_favorite,
    create_user_database,
    is_favorite,
    record_product_view,
    remove_favorite,
)


@asynccontextmanager
async def lifespan(_app):
    if not DATABASE_PATH.exists() and INITIAL_DATABASE_PATH.exists():
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(INITIAL_DATABASE_PATH, DATABASE_PATH)
    create_database(DATABASE_PATH)
    create_user_database(USER_DATABASE_PATH)
    yield


app = FastAPI(
    title="溯食光 API",
    description="提供食品產品、公司、分類與營養標示資料。",
    version="1.0.0",
    lifespan=lifespan,
)

# 允許不同網址或連接埠的前端呼叫 API。
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


PRODUCT_FIELDS = (
    "product_id",
    "brand_id",
    "company_id",
    "category_id",
    "trace_code",
    "product_name",
    "brand_name",
    "brand_source",
    "brand_confidence",
    "brand_matched_text",
    "brand_reason",
    "brand_is_fallback",
    "company_name",
    "category",
    "package",
    "front_image",
    "image_available",
    "image_fallback_url",
    "warning",
)

NUTRITION_FIELDS = (
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

PRODUCT_DATABASE_FIELDS = tuple(
    field
    for field in PRODUCT_FIELDS
    if field not in {
        "image_available",
        "image_fallback_url",
    }
)

CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
PRODUCT_PLACEHOLDER_URL = "/api/assets/product-placeholder.svg"


def validate_client_id(client_id):
    if not client_id or not CLIENT_ID_PATTERN.fullmatch(client_id):
        raise HTTPException(
            status_code=422,
            detail="X-Client-ID 必須是 1 至 128 字元的英數識別碼",
        )
    return client_id


def optional_client_id(
    x_client_id: str | None = Header(None, alias="X-Client-ID"),
):
    return validate_client_id(x_client_id) if x_client_id else None


def required_client_id(
    x_client_id: str = Header(..., alias="X-Client-ID"),
):
    return validate_client_id(x_client_id)


def is_valid_image_url(value):
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def serialize_product(row):
    data = dict(row)
    data["image_available"] = is_valid_image_url(data.get("front_image"))
    data["image_fallback_url"] = PRODUCT_PLACEHOLDER_URL
    return {field: data.get(field) for field in PRODUCT_FIELDS}


def serialize_full_product(row):
    data = dict(row)
    return {
        "product": serialize_product(row),
        "nutrition": {
            field: data.get(field)
            for field in NUTRITION_FIELDS
        },
    }


def build_search_condition(search_text):
    # trigram FTS 可有效處理三字以上的中文／英文片段搜尋。
    if len(search_text) >= 3:
        escaped_text = search_text.replace('"', '""')
        return (
            "product_id IN ("
            "SELECT rowid FROM product_search "
            "WHERE product_search MATCH ?"
            ")",
            [f'"{escaped_text}"'],
        )

    # FTS trigram 無法索引一至二字，短查詢沿用 LIKE 與資料庫主檔。
    keyword = f"%{search_text}%"
    parts = [
        "product_name LIKE ?",
        "company_name LIKE ?",
        "package LIKE ?",
        "category LIKE ?",
        "brand_name LIKE ?",
    ]
    parameters = [keyword] * len(parts)
    return "(" + " OR ".join(parts) + ")", parameters


def get_connection(include_user_data=False):
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    if include_user_data:
        conn.execute(
            "ATTACH DATABASE ? AS user_data",
            (str(USER_DATABASE_PATH),),
        )
    return conn


@app.exception_handler(sqlite3.Error)
async def database_exception_handler(_request: Request, _exc: sqlite3.Error):
    return JSONResponse(
        status_code=503,
        content={"detail": "資料庫暫時無法使用，請稍後再試"},
    )


@app.get("/api/health", tags=["系統"])
def api_info():
    return {
        "name": "溯食光 API",
        "status": "ok",
        "docs": "/docs",
        "products": "/api/products",
    }


@app.get("/api/meta/source", tags=["系統"])
def data_source_info():
    with closing(get_connection()) as conn:
        metadata = dict(conn.execute(
            "SELECT key, value FROM app_metadata"
        ).fetchall())
    return {
        "app_name": "溯食光",
        "source_name": "政府資料開放平臺",
        "source_url": SOURCE_URL,
        "source_file_modified_at": metadata.get("source_file_modified_at"),
        "database_last_imported_at": metadata.get("last_imported_at"),
        "disclaimer": DISCLAIMER,
    }


@app.get("/api/assets/product-placeholder.svg", tags=["系統"])
def product_placeholder():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480"
    viewBox="0 0 640 480"><rect width="640" height="480" fill="#F3F4EF"/>
    <circle cx="320" cy="210" r="90" fill="#DCE8D4"/>
    <path d="M270 225c25-65 75-65 100 0-20 30-80 30-100 0Z" fill="#5F7F55"/>
    <text x="320" y="350" text-anchor="middle" font-family="sans-serif"
    font-size="28" fill="#52604D">暫無產品圖片</text></svg>"""
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/api/products", tags=["產品"])
def list_products(
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(20, ge=1, le=100, description="每頁筆數"),
    q: str | None = Query(None, description="搜尋產品、品牌、公司或分類"),
    category_id: int | None = Query(None, ge=1, description="產品分類 ID"),
    brand_id: int | None = Query(None, ge=1, description="品牌 ID"),
    company_id: int | None = Query(None, ge=1, description="公司 ID"),
    category: str | None = Query(None, description="產品分類"),
    company: str | None = Query(None, description="公司名稱"),
    include_nutrition: bool = Query(
        False,
        description="是否直接回傳完整營養資料",
    ),
):
    base_conditions = []
    base_parameters = []

    if category_id is not None:
        base_conditions.append("category_id = ?")
        base_parameters.append(category_id)
    if brand_id is not None:
        base_conditions.append("brand_id = ?")
        base_parameters.append(brand_id)
    if company_id is not None:
        base_conditions.append("company_id = ?")
        base_parameters.append(company_id)
    if category:
        base_conditions.append(
            "category_id = (SELECT id FROM categories WHERE name = ?)"
        )
        base_parameters.append(category)
    if company:
        base_conditions.append("company_name = ?")
        base_parameters.append(company)

    conditions = list(base_conditions)
    parameters = list(base_parameters)
    search_text = q.strip() if q else ""
    if search_text:
        search_condition, search_parameters = build_search_condition(search_text)
        conditions.append(search_condition)
        parameters.extend(search_parameters)

    where_clause = (
        " WHERE " + " AND ".join(conditions) if conditions else ""
    )
    offset = (page - 1) * page_size

    with closing(get_connection()) as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM product_details" + where_clause,
            parameters,
        ).fetchone()[0]

        # 完整詞找不到時，改用每個不重複字元做寬鬆搜尋。
        # 例如「七七」會退回搜尋「七」，避免因重複輸入而完全無結果。
        if search_text and total == 0:
            fuzzy_characters = list(dict.fromkeys(
                character
                for character in search_text
                if character.isalnum()
            ))[:8]
            if fuzzy_characters:
                conditions = list(base_conditions)
                parameters = list(base_parameters)
                for character in fuzzy_characters:
                    fuzzy_condition, fuzzy_parameters = (
                        build_search_condition(character)
                    )
                    conditions.append(fuzzy_condition)
                    parameters.extend(fuzzy_parameters)
                where_clause = " WHERE " + " AND ".join(conditions)
                total = conn.execute(
                    "SELECT COUNT(*) FROM product_details" + where_clause,
                    parameters,
                ).fetchone()[0]

        select_fields = (
            "*" if include_nutrition
            else ", ".join(PRODUCT_DATABASE_FIELDS)
        )
        rows = conn.execute(
            "SELECT " + select_fields
            + " FROM product_details"
            + where_clause
            + " ORDER BY product_id LIMIT ? OFFSET ?",
            (*parameters, page_size, offset),
        ).fetchall()

    return {
        "items": [
            (
                serialize_full_product(row)
                if include_nutrition
                else serialize_product(row)
            )
            for row in rows
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@app.get("/api/products/{product_id}", tags=["產品"])
def get_product(
    product_id: int,
    client_id: str | None = Depends(optional_client_id),
):
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT * FROM product_details WHERE product_id = ?",
            (product_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="找不到此產品")

    data = dict(row)
    record_product_view(USER_DATABASE_PATH, data["trace_code"], client_id)
    return {
        "product": serialize_product(row),
        "nutrition": {field: data[field] for field in NUTRITION_FIELDS},
        "is_favorite": (
            is_favorite(USER_DATABASE_PATH, client_id, data["trace_code"])
            if client_id
            else False
        ),
    }


@app.get("/api/recently-viewed", tags=["使用者"])
def list_recently_viewed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    client_id: str = Depends(required_client_id),
):
    offset = (page - 1) * page_size
    with closing(get_connection(include_user_data=True)) as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM user_data.recent_views WHERE client_id = ?",
            (client_id,),
        ).fetchone()[0]
        rows = conn.execute("""
            SELECT p.*
            FROM product_details AS p
            JOIN user_data.recent_views AS rv
              ON rv.trace_code = p.trace_code
            WHERE rv.client_id = ?
            ORDER BY rv.viewed_at DESC
            LIMIT ? OFFSET ?
        """, (client_id, page_size, offset)).fetchall()
    return {
        "items": [serialize_product(row) for row in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@app.get("/api/favorites", tags=["使用者"])
def list_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    client_id: str = Depends(required_client_id),
):
    offset = (page - 1) * page_size
    with closing(get_connection(include_user_data=True)) as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM user_data.favorites WHERE client_id = ?",
            (client_id,),
        ).fetchone()[0]
        rows = conn.execute("""
            SELECT p.*
            FROM product_details AS p
            JOIN user_data.favorites AS f ON f.trace_code = p.trace_code
            WHERE f.client_id = ?
            ORDER BY f.created_at DESC
            LIMIT ? OFFSET ?
        """, (client_id, page_size, offset)).fetchall()
    return {
        "items": [serialize_product(row) for row in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@app.post("/api/favorites/{product_id}", status_code=201, tags=["使用者"])
def create_favorite(
    product_id: int,
    client_id: str = Depends(required_client_id),
):
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT trace_code FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="找不到此產品")
    created = add_favorite(
        USER_DATABASE_PATH,
        client_id,
        row["trace_code"],
    )
    return {"product_id": product_id, "is_favorite": True, "created": created}


@app.delete("/api/favorites/{product_id}", status_code=204, tags=["使用者"])
def delete_favorite(
    product_id: int,
    client_id: str = Depends(required_client_id),
):
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT trace_code FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="找不到此產品")
    removed = remove_favorite(
        USER_DATABASE_PATH,
        client_id,
        row["trace_code"],
    )
    if not removed:
        raise HTTPException(status_code=404, detail="此產品尚未收藏")
    return Response(status_code=204)


@app.get("/api/categories", tags=["篩選資料"])
def list_categories():
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT
                c.id AS category_id,
                c.name,
                COUNT(p.id) AS product_count,
                COUNT(DISTINCT p.brand_id) AS brand_count
            FROM categories AS c
            LEFT JOIN products AS p ON p.category_id = c.id
            GROUP BY c.id, c.name
            ORDER BY c.id
            """
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.get("/api/categories/{category_id}/brands", tags=["篩選資料"])
def list_category_brands(category_id: int):
    with closing(get_connection()) as conn:
        category_row = conn.execute(
            "SELECT id, name FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        if category_row is None:
            raise HTTPException(status_code=404, detail="找不到此產品分類")
        rows = conn.execute(
            """
            SELECT
                p.brand_id,
                b.name,
                COUNT(p.id) AS product_count
            FROM products AS p
            JOIN brands AS b ON b.id = p.brand_id
            WHERE p.category_id = ? AND p.brand_id IS NOT NULL
            GROUP BY p.brand_id, b.name
            ORDER BY b.name
            """,
            (category_id,),
        ).fetchall()
        unbranded_count = conn.execute(
            """
            SELECT COUNT(*) FROM products
            WHERE category_id = ? AND brand_id IS NULL
            """,
            (category_id,),
        ).fetchone()[0]

    return {
        "category": {
            "category_id": category_id,
            "name": category_row["name"],
        },
        "items": [dict(row) for row in rows],
        "unbranded_product_count": unbranded_count,
    }


@app.get("/api/categories/{category_id}/companies", tags=["篩選資料"])
def list_category_companies(category_id: int):
    with closing(get_connection()) as conn:
        category_row = conn.execute(
            "SELECT id, name FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        if category_row is None:
            raise HTTPException(status_code=404, detail="找不到此產品分類")
        rows = conn.execute(
            """
            SELECT
                c.id AS company_id,
                c.name,
                COUNT(p.id) AS product_count,
                COUNT(DISTINCT p.brand_id) AS brand_count
            FROM products AS p
            JOIN companies AS c ON c.id = p.company_id
            WHERE p.category_id = ?
            GROUP BY c.id, c.name
            ORDER BY c.name
            """,
            (category_id,),
        ).fetchall()

    return {
        "category": {"category_id": category_id, "name": category_row["name"]},
        "items": [dict(row) for row in rows],
    }


@app.get("/api/brands", tags=["篩選資料"])
def list_brands(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    q: str | None = Query(None, description="搜尋品牌名稱"),
):
    conditions = []
    parameters = []
    if q:
        conditions.append("b.name LIKE ?")
        parameters.append(f"%{q.strip()}%")
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    offset = (page - 1) * page_size
    with closing(get_connection()) as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM brands AS b" + where_clause,
            parameters,
        ).fetchone()[0]
        rows = conn.execute("""
            SELECT
                b.id AS brand_id,
                b.name,
                COUNT(p.id) AS product_count,
                COUNT(DISTINCT p.category_id) AS category_count,
                COUNT(DISTINCT p.company_id) AS company_count
            FROM brands AS b
            LEFT JOIN products AS p ON p.brand_id = b.id
        """ + where_clause + """
            GROUP BY b.id, b.name
            ORDER BY b.name
            LIMIT ? OFFSET ?
        """, (*parameters, page_size, offset)).fetchall()
    return {
        "items": [dict(row) for row in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@app.get("/api/brands/popular", tags=["篩選資料"])
def list_popular_brands(limit: int = Query(10, ge=1, le=100)):
    with closing(get_connection(include_user_data=True)) as conn:
        rows = conn.execute("""
            SELECT
                p.brand_id,
                b.name,
                COUNT(*) AS product_count,
                COUNT(DISTINCT p.category_id) AS category_count,
                COALESCE(SUM(vc.view_count), 0) AS view_count
            FROM products AS p
            JOIN brands AS b ON b.id = p.brand_id
            LEFT JOIN user_data.product_view_counts AS vc
              ON vc.trace_code = p.trace_code
            WHERE p.brand_id IS NOT NULL
            GROUP BY p.brand_id, b.name
            ORDER BY view_count DESC, product_count DESC, p.brand_id
            LIMIT ?
        """, (limit,)).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
    return {
        "items": [
            {
                "brand_id": row["brand_id"],
                "name": row["name"],
                "product_count": row["product_count"],
                "category_count": row["category_count"],
                "view_count": row["view_count"],
            }
            for row in rows
        ],
        "pagination": {
            "total": total
        }
    }


@app.get("/api/companies/popular", tags=["篩選資料"])
def list_popular_companies(limit: int = Query(10, ge=1, le=100)):
    with closing(get_connection(include_user_data=True)) as conn:
        rows = conn.execute("""
            SELECT
                c.id AS company_id,
                c.name,
                COUNT(p.id) AS product_count,
                COUNT(DISTINCT p.brand_id) AS brand_count,
                COALESCE(SUM(vc.view_count), 0) AS view_count
            FROM companies AS c
            LEFT JOIN products AS p ON p.company_id = c.id
            LEFT JOIN user_data.product_view_counts AS vc
              ON vc.trace_code = p.trace_code
            GROUP BY c.id, c.name
            ORDER BY view_count DESC, product_count DESC, c.id
            LIMIT ?
        """, (limit,)).fetchall()
        
        # Calculate total companies count in the system
        total = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        
    return {
        "items": [
            {
                "company_id": row["company_id"],
                "name": row["name"],
                "product_count": row["product_count"],
                "brand_count": row["brand_count"],
                "view_count": row["view_count"],
            }
            for row in rows
        ],
        "pagination": {
            "total": total
        }
    }


@app.get("/api/brands/{brand_id}/categories", tags=["篩選資料"])
def list_brand_categories(
    brand_id: int,
    company_id: int | None = Query(None, description="限定公司 ID"),
):
    conditions = ["brand_id = ?"]
    parameters = [brand_id]
    if company_id is not None:
        conditions.append("company_id = ?")
        parameters.append(company_id)

    with closing(get_connection()) as conn:
        brand_row = conn.execute(
            "SELECT id, name FROM brands WHERE id = ?", (brand_id,)
        ).fetchone()
        if brand_row is None:
            raise HTTPException(status_code=404, detail="找不到此品牌")
        rows = conn.execute(
            """
            SELECT p.category_id, c.name, COUNT(*) AS product_count
            FROM products AS p
            JOIN categories AS c ON c.id = p.category_id
            WHERE """
            + " AND ".join(conditions)
            + """
            GROUP BY p.category_id, c.name
            ORDER BY p.category_id
            """,
            parameters,
        ).fetchall()

    return {
        "brand": {"brand_id": brand_id, "name": brand_row["name"]},
        "items": [
            {
                "category_id": row["category_id"],
                "name": row["name"],
                "product_count": row["product_count"],
            }
            for row in rows
        ],
    }


@app.get("/api/companies", tags=["篩選資料"])
def list_companies(
    q: str | None = Query(None, description="搜尋公司名稱"),
    limit: int = Query(100, ge=1, le=500),
):
    sql = """
    SELECT
        c.id AS company_id,
        c.name,
        COUNT(p.id) AS product_count,
        COUNT(DISTINCT p.brand_id) AS brand_count
    FROM companies AS c
    LEFT JOIN products AS p ON p.company_id = c.id
    """
    parameters = []
    if q:
        sql += " WHERE c.name LIKE ?"
        parameters.append(f"%{q.strip()}%")
    sql += " GROUP BY c.id, c.name ORDER BY c.name LIMIT ?"
    parameters.append(limit)

    with closing(get_connection()) as conn:
        rows = conn.execute(sql, parameters).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.get("/api/companies/{company_id}/brands", tags=["篩選資料"])
def list_company_brands(
    company_id: int,
    category_id: int | None = Query(
        None,
        ge=1,
        description="限定產品分類 ID",
    ),
):
    with closing(get_connection()) as conn:
        company_row = conn.execute(
            "SELECT id, name FROM companies WHERE id = ?",
            (company_id,),
        ).fetchone()
        if company_row is None:
            raise HTTPException(status_code=404, detail="找不到此公司")
        category_row = None
        if category_id is not None:
            category_row = conn.execute(
                "SELECT id, name FROM categories WHERE id = ?", (category_id,)
            ).fetchone()
            if category_row is None:
                raise HTTPException(status_code=404, detail="找不到此產品分類")

        conditions = ["company_id = ?", "brand_id IS NOT NULL"]
        parameters = [company_id]
        if category_id is not None:
            conditions.append("category_id = ?")
            parameters.append(category_id)
        rows = conn.execute(
            """
            SELECT p.brand_id, b.name, COUNT(*) AS product_count
            FROM products AS p
            JOIN brands AS b ON b.id = p.brand_id
            WHERE """
            + " AND ".join(conditions)
            + " GROUP BY p.brand_id, b.name ORDER BY b.name",
            parameters,
        ).fetchall()

    return {
        "company": {
            "company_id": company_row["id"],
            "name": company_row["name"],
        },
        "category": (
            {
                "category_id": category_id,
                "name": category_row["name"],
            }
            if category_id is not None
            else None
        ),
        "items": [dict(row) for row in rows],
    }


@app.get("/api/companies/{company_id}/categories", tags=["篩選資料"])
def list_company_categories(company_id: int):
    with closing(get_connection()) as conn:
        company_row = conn.execute(
            "SELECT id, name FROM companies WHERE id = ?",
            (company_id,),
        ).fetchone()
        if company_row is None:
            raise HTTPException(status_code=404, detail="找不到此公司")

        rows = conn.execute(
            """
            SELECT p.category_id, c.name, COUNT(*) AS product_count
            FROM products AS p
            JOIN categories AS c ON c.id = p.category_id
            WHERE p.company_id = ?
            GROUP BY p.category_id, c.name
            ORDER BY p.category_id
            """,
            (company_id,),
        ).fetchall()

    return {
        "company": {
            "company_id": company_row["id"],
            "name": company_row["name"],
        },
        "items": [
            {
                "category_id": row["category_id"],
                "name": row["name"],
                "product_count": row["product_count"],
            }
            for row in rows
        ],
    }


if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


def main():
    parser = argparse.ArgumentParser(description="食品資料 API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
