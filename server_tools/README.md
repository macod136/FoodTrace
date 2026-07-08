# 伺服器資料工具

這個資料夾只供資料維護與發布使用，不會打包給一般使用者。

## 更新主檔

當原始政府食品 JSON 中出現新公司、分類或品牌時，開發者需要手動更新對照表。
請在專案根目錄下執行：

```powershell
cd develop/backend
..\.venv\Scripts\python.exe generate_company_table.py
..\.venv\Scripts\python.exe generate_category_table.py
..\.venv\Scripts\python.exe generate_brand_table.py
cd ../..
```

## 建立資料庫

建議先輸出到新檔案，不要直接覆蓋正式資料庫。
請在專案根目錄下執行：

```powershell
.\develop\.venv\Scripts\python.exe .\develop\server_tools\build_database.py --output .\develop\server_tools\release-data\food-new.db
```

## 發布

請在專案根目錄下執行：

```powershell
.\develop\.venv\Scripts\python.exe .\develop\server_tools\publish_database.py `
  --database .\develop\server_tools\release-data\food-new.db `
  --output-dir .\develop\server_tools\release-data\public `
  --version 2026.07.07 `
  --base-url https://example.com/foodtrace
```

最後將 `release-data/public/` 下生成的 `manifest.json` 與 `food.db.zip` 上傳至雲端更新伺服器。發布時應先上傳壓縮檔 `food.db.zip`，最後才替換 `manifest.json`。
