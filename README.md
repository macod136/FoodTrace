# 溯食光 Food Trace - 開發指南

本專案採用離線優先的桌面架構。使用者安裝後，由程式在本機啟動 FastAPI，食品查詢都從本機 SQLite 執行；只有資料庫有新版時才連線下載一次更新。

---

## 📁 目錄結構

* **`frontend/`**：HTML、JavaScript 與圖片（原「前端」）。
* **`backend/`**：桌面程式執行時使用的 FastAPI、SQLite 結構與使用者資料功能（原「後端」）。
* **`server_tools/`**：只由資料維護者使用的建庫與發布工具。
* **`.venv/`**：本機 Python 虛擬開發環境。

---

## 💻 本地開發模式

### 1. 啟動後端 API 伺服器
請於專案根目錄下執行：
```powershell
.\develop\.venv\Scripts\python.exe .\develop\backend\main.py
```
這會在 `http://127.0.0.1:8000/` 啟動 API 伺服器，同時會將前端資源載入進來。

### 2. 雙服務開發模式（推薦開發網頁時使用）
如果您需要獨立測試前端網頁，可以在 `develop/frontend` 目錄下啟動靜態伺服器：
* **前端網頁**：`http://127.0.0.1:5500` (會自動串接 API `8000` 埠)
* **後端 API**：`http://127.0.0.1:8000`

---

## 📄 相關文件

* **[桌面版打包與執行建置](../../packaging/README.md)** (位於根目錄下的 `packaging/README.md`)
* **[伺服器資料整理與發布](server_tools/README.md)**
