# Food Traceability API

食品溯源 APP 的 FastAPI 後端，提供產品、營養標示、品牌、公司與產品分類查詢。

## 功能

- 產品關鍵字與中文全文搜尋
- 品牌、公司、分類交叉篩選
- 完整產品與營養資料
- 固定品牌 ID 與分類 ID
- SQLite FTS5 trigram 搜尋索引
- Swagger API 文件
- 自動化 API 測試
- 收藏、最近查看與熱門品牌
- 資料來源、更新時間與免責聲明 API

## 安裝

```powershell
python -m pip install -r requirements.txt
```

## 產生資料庫

```powershell
python generate_company_table.py
python generate_category_table.py
python generate_brand_table.py
python ..\server_tools\build_database.py --output output\food.db
```

## 啟動 API

```powershell
python main.py
```

啟動後開啟：

- 網站：http://127.0.0.1:8000/
- API：http://127.0.0.1:8000/api
- Swagger：http://127.0.0.1:8000/docs

## 使用者功能

收藏與最近查看使用匿名裝置識別碼。前端請產生 UUID，並在請求加入：

```text
X-Client-ID: your-device-uuid
```

主要端點：

```text
GET    /api/brands
GET    /api/brands/popular
GET    /api/meta/source
GET    /api/recently-viewed
GET    /api/favorites
POST   /api/favorites/{product_id}
DELETE /api/favorites/{product_id}
```

使用者資料獨立儲存在 `output/user_data.db`，不會因重建食品資料庫而消失。

## 測試

```powershell
python -m unittest discover -s tests -v
```
