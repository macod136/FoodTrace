# 溯食光前端

本前端保留 Stitch 產生的主要視覺頁面，並透過根目錄下的 `shared.js` 串接 FastAPI 後端。

## 啟動

先在「後端」資料夾啟動 API：

```powershell
python main.py
```

再開另一個終端機，在「前端」資料夾啟動靜態網站：

```powershell
python -m http.server 5500 --bind 127.0.0.1
```

瀏覽器開啟：

```text
http://127.0.0.1:5500/
```

## 已串接功能

- 首頁食品大類、熱門品牌與最近查看
- 產品、品牌與公司搜尋
- 食品大類列表與分類產品
- 產品詳細資料及營養標示
- 收藏新增、移除與收藏列表
- 資料來源、免責聲明與最後更新時間
- 圖片載入失敗備援
- 載入、空資料、錯誤與重試狀態

匿名收藏及最近查看使用瀏覽器 `localStorage` 保存裝置識別碼。

## API 位址

預設為 `http://127.0.0.1:8000`。需要改用其他後端時，可在瀏覽器主控台設定：

```javascript
localStorage.setItem("foodTraceApiBase", "https://your-api.example.com")
```
