# config.py
import os
import json
from pathlib import Path

# Xác định thư mục gốc của dự án
REPO_ROOT = Path(__file__).resolve().parents[0]


def load_settings(config_file=None):
    """Load settings.json từ đường dẫn mặc định hoặc biến môi trường."""
    config_file = config_file or os.getenv("CONFIG", "configs/settings.json")
    settings_path = (REPO_ROOT / config_file).resolve()

    if not settings_path.exists():
        # Trả về mặc định nếu chưa có file JSON
        return {"apk_folder": "APKs", "output_base": "outputs"}

    with settings_path.open("r", encoding="utf-8") as f:
        return json.load(f)


SETTINGS = load_settings()

# Chỉ cần quản lý đường dẫn THƯ MỤC chứa các APK
APK_FOLDER = SETTINGS.get("apk_folder", "APKs")
OUTPUT_FOLDER = SETTINGS.get("output_base", "outputs")
