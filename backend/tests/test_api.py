import sqlite3
import unittest
import uuid

from fastapi.testclient import TestClient

from config import DATABASE_PATH, SOURCE_URL, USER_DATABASE_PATH
from main import app


class FoodApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()
        response = cls.client.get(
            "/api/products",
            params={"page": 1, "page_size": 1},
        )
        cls.base_product = response.json()["items"][0]
        cls.client_id = f"test-{uuid.uuid4().hex}"
        cls.client_headers = {"X-Client-ID": cls.client_id}

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)
        with sqlite3.connect(USER_DATABASE_PATH) as conn:
            conn.execute(
                "DELETE FROM favorites WHERE client_id = ?",
                (cls.client_id,),
            )
            conn.execute(
                "DELETE FROM recent_views WHERE client_id = ?",
                (cls.client_id,),
            )

    def test_lookup_tables_are_stored_in_database(self):
        with sqlite3.connect(DATABASE_PATH) as conn:
            brand_count = conn.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
            category_count = conn.execute(
                "SELECT COUNT(*) FROM categories"
            ).fetchone()[0]
            duplicate_brands = conn.execute("""
                SELECT COUNT(*) FROM (
                    SELECT name FROM brands GROUP BY name HAVING COUNT(*) > 1
                )
            """).fetchone()[0]
        self.assertGreater(brand_count, 0)
        self.assertGreater(category_count, 0)
        self.assertEqual(duplicate_brands, 0)

    def test_database_uses_ids_and_has_search_indexes(self):
        with sqlite3.connect(DATABASE_PATH) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            indexes = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index'"
                )
            }
        self.assertIn("brands", tables)
        self.assertIn("categories", tables)
        self.assertIn("product_search", tables)
        self.assertIn("idx_products_brand_id", indexes)
        self.assertIn("idx_products_brand_category", indexes)
        self.assertIn("idx_products_company_category", indexes)

    def test_product_detail_contains_product_and_nutrition(self):
        product_id = self.base_product["product_id"]
        response = self.client.get(f"/api/products/{product_id}")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("product", body)
        self.assertIn("nutrition", body)
        self.assertEqual(body["product"]["product_id"], product_id)
        self.assertTrue(body["product"]["category"])
        self.assertIn("brand_source", body["product"])
        self.assertIn("brand_confidence", body["product"])
        self.assertIn("brand_is_fallback", body["product"])

    def test_full_text_brand_search(self):
        response = self.client.get(
            "/api/products",
            params={"q": "杜老爺", "page_size": 5},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreater(body["pagination"]["total"], 0)
        self.assertTrue(
            all(item["brand_name"] == "杜老爺" for item in body["items"])
        )

    def test_short_fuzzy_search_remains_available(self):
        response = self.client.get(
            "/api/products",
            params={"q": "七七", "page_size": 5},
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.json()["pagination"]["total"], 0)

    def test_search_can_return_complete_nutrition(self):
        response = self.client.get(
            "/api/products",
            params={
                "q": "杜老爺",
                "include_nutrition": True,
                "page_size": 1,
            },
        )
        self.assertEqual(response.status_code, 200)
        item = response.json()["items"][0]
        self.assertEqual(set(item), {"product", "nutrition"})
        self.assertIn("kcal_100g", item["nutrition"])

    def test_brand_and_category_filter(self):
        brand_id = self.base_product["brand_id"]
        category_id = self.base_product["category_id"]
        response = self.client.get(
            "/api/products",
            params={
                "brand_id": brand_id,
                "category_id": category_id,
                "page_size": 10,
            },
        )
        self.assertEqual(response.status_code, 200)
        for item in response.json()["items"]:
            self.assertEqual(item["brand_id"], brand_id)
            self.assertEqual(item["category_id"], category_id)

    def test_company_brand_and_category_workflow(self):
        company_id = self.base_product["company_id"]
        category_id = self.base_product["category_id"]
        brands_response = self.client.get(
            f"/api/companies/{company_id}/brands",
            params={"category_id": category_id},
        )
        self.assertEqual(brands_response.status_code, 200)
        products_response = self.client.get(
            "/api/products",
            params={
                "company_id": company_id,
                "category_id": category_id,
                "page_size": 10,
            },
        )
        self.assertEqual(products_response.status_code, 200)
        for item in products_response.json()["items"]:
            self.assertEqual(item["company_id"], company_id)
            self.assertEqual(item["category_id"], category_id)

    def test_company_and_category_drill_down_workflow(self):
        company_id = self.base_product["company_id"]
        category_id = self.base_product["category_id"]

        company_categories = self.client.get(
            f"/api/companies/{company_id}/categories"
        )
        self.assertEqual(company_categories.status_code, 200)
        self.assertTrue(any(
            item["category_id"] == category_id
            for item in company_categories.json()["items"]
        ))

        category_companies = self.client.get(
            f"/api/categories/{category_id}/companies"
        )
        self.assertEqual(category_companies.status_code, 200)
        self.assertTrue(any(
            item["company_id"] == company_id
            for item in category_companies.json()["items"]
        ))

        filtered_products = self.client.get(
            "/api/products",
            params={
                "company_id": company_id,
                "category_id": category_id,
                "page_size": 10,
            },
        )
        self.assertEqual(filtered_products.status_code, 200)
        for item in filtered_products.json()["items"]:
            self.assertEqual(item["company_id"], company_id)
            self.assertEqual(item["category_id"], category_id)

    def test_all_brand_list_supports_search_and_pagination(self):
        response = self.client.get(
            "/api/brands",
            params={"page": 1, "page_size": 2, "q": "杜老爺"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["pagination"]["total"], 1)
        self.assertEqual(body["items"][0]["name"], "杜老爺")

    def test_source_and_last_updated_api(self):
        response = self.client.get("/api/meta/source")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["source_url"], SOURCE_URL)
        self.assertTrue(body["source_file_modified_at"])
        self.assertTrue(body["database_last_imported_at"])
        self.assertTrue(body["disclaimer"])

    def test_favorite_and_recent_view_lifecycle(self):
        product_id = self.base_product["product_id"]
        create_response = self.client.post(
            f"/api/favorites/{product_id}",
            headers=self.client_headers,
        )
        self.assertEqual(create_response.status_code, 201)

        detail_response = self.client.get(
            f"/api/products/{product_id}",
            headers=self.client_headers,
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertTrue(detail_response.json()["is_favorite"])

        favorites = self.client.get(
            "/api/favorites",
            headers=self.client_headers,
        )
        recent = self.client.get(
            "/api/recently-viewed",
            headers=self.client_headers,
        )
        self.assertEqual(favorites.status_code, 200)
        self.assertEqual(recent.status_code, 200)
        self.assertTrue(any(
            item["product_id"] == product_id
            for item in favorites.json()["items"]
        ))
        self.assertTrue(any(
            item["product_id"] == product_id
            for item in recent.json()["items"]
        ))

        delete_response = self.client.delete(
            f"/api/favorites/{product_id}",
            headers=self.client_headers,
        )
        self.assertEqual(delete_response.status_code, 204)

    def test_popular_brands_api(self):
        response = self.client.get("/api/brands/popular", params={"limit": 5})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        items = data["items"]
        self.assertEqual(len(items), 5)
        self.assertTrue(all("view_count" in item for item in items))
        self.assertTrue(all("category_count" in item for item in items))
        with sqlite3.connect(DATABASE_PATH) as conn:
            expected_total = conn.execute(
                "SELECT COUNT(*) FROM brands"
            ).fetchone()[0]
        self.assertEqual(data["pagination"]["total"], expected_total)

    def test_popular_companies_api(self):
        response = self.client.get("/api/companies/popular", params={"limit": 5})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        items = data["items"]
        self.assertEqual(len(items), 5)
        self.assertTrue(all("view_count" in item for item in items))
        self.assertTrue(all("brand_count" in item for item in items))
        with sqlite3.connect(DATABASE_PATH) as conn:
            expected_total = conn.execute(
                "SELECT COUNT(*) FROM companies"
            ).fetchone()[0]
        self.assertEqual(data["pagination"]["total"], expected_total)

    def test_company_fallback_does_not_pollute_brand_table(self):
        with sqlite3.connect(DATABASE_PATH) as conn:
            row = conn.execute("""
                SELECT id, brand_fallback_name
                FROM products
                WHERE brand_source = 'company_fallback'
                  AND COALESCE(brand_fallback_name, '') <> ''
                  AND NOT EXISTS (
                    SELECT 1 FROM brands AS b
                    WHERE b.name = products.brand_fallback_name
                  )
                LIMIT 1
            """).fetchone()
            self.assertIsNotNone(row)
            product_id, fallback_name = row
            formal_match = conn.execute(
                "SELECT COUNT(*) FROM brands WHERE name = ?",
                (fallback_name,),
            ).fetchone()[0]
        detail = self.client.get(f"/api/products/{product_id}").json()["product"]
        self.assertIsNone(detail["brand_id"])
        self.assertEqual(detail["brand_name"], fallback_name)
        self.assertTrue(detail["brand_is_fallback"])
        self.assertEqual(formal_match, 0)

    def test_brand_categories_with_company_filter(self):
        brand_id = self.base_product["brand_id"]
        company_id = self.base_product["company_id"]
        response = self.client.get(f"/api/brands/{brand_id}/categories")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.json()["items"]), 0)

        response_filtered = self.client.get(
            f"/api/brands/{brand_id}/categories",
            params={"company_id": company_id},
        )
        self.assertEqual(response_filtered.status_code, 200)
        self.assertGreater(len(response_filtered.json()["items"]), 0)

    def test_error_empty_and_pagination_responses(self):
        self.assertEqual(
            self.client.get("/api/products/999999999").status_code,
            404,
        )
        self.assertEqual(
            self.client.get("/api/favorites").status_code,
            422,
        )
        self.assertEqual(
            self.client.get("/api/products", params={"page": 0}).status_code,
            422,
        )
        empty = self.client.get(
            "/api/products",
            params={"q": "絕對不存在食品甲乙丙"},
        )
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json()["items"], [])
        self.assertEqual(empty.json()["pagination"]["total"], 0)

        far_page = self.client.get(
            "/api/products",
            params={"page": 999999, "page_size": 2},
        )
        self.assertEqual(far_page.status_code, 200)
        self.assertEqual(far_page.json()["items"], [])

    def test_missing_image_has_backend_fallback(self):
        with sqlite3.connect(DATABASE_PATH) as conn:
            product_id = conn.execute(
                """
                SELECT id FROM products
                WHERE COALESCE(front_image, '') = ''
                LIMIT 1
                """
            ).fetchone()[0]
        detail = self.client.get(f"/api/products/{product_id}").json()
        self.assertFalse(detail["product"]["image_available"])
        fallback_url = detail["product"]["image_fallback_url"]
        fallback = self.client.get(fallback_url)
        self.assertEqual(fallback.status_code, 200)
        self.assertIn("image/svg+xml", fallback.headers["content-type"])


if __name__ == "__main__":
    unittest.main()
