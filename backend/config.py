import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
JSON_PATH = BASE_DIR / "data" / "188_5.json"


def bundled_path(name):
    bundle_root = Path(getattr(sys, "_MEIPASS", BASE_DIR.parent))
    return bundle_root / name


def default_data_dir():
    configured = os.environ.get("FOODTRACE_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA", Path.home())
        return Path(local_app_data) / "FoodTrace"
    return BASE_DIR / "output"


DATA_DIR = default_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATA_DIR / "food.db"
USER_DATABASE_PATH = DATA_DIR / "user_data.db"
FRONTEND_DIR = Path(
    os.environ.get("FOODTRACE_FRONTEND_DIR", bundled_path("frontend"))
).resolve()
INITIAL_DATABASE_PATH = Path(
    os.environ.get(
        "FOODTRACE_INITIAL_DATABASE",
        bundled_path("initial-data/food.db"),
    )
).resolve()
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "FOODTRACE_ALLOWED_ORIGINS",
        "http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:5501,http://localhost:5501,http://127.0.0.1:5502,http://localhost:5502",
    ).split(",")
    if origin.strip()
]

SOURCE_URL = "https://data.gov.tw/en/datasets/33575?utm_source=chatgpt.com"
DISCLAIMER = (
    "本平台僅將公開資料進行整理、分類與展示，不保證資料的完整性、"
    "即時性及正確性；實際資訊請以產品包裝、製造商及主管機關公告為準。"
)
