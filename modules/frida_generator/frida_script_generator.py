import os
import json
import requests
import re
from pathlib import Path


import logging
import sys
import json_repair
import io
from collections import deque

# ---- Repo root & settings loader ----
REPO_ROOT = Path(__file__).resolve().parents[1]


def load_settings(cfg_path=None):
    # allow env override; default to artifact_settings.json if not provided
    cfg_path = cfg_path or os.getenv("CONFIG", "configs/settings.json")
    cfg = (REPO_ROOT / cfg_path).resolve()
    with cfg.open("r", encoding="utf-8") as f:
        s = json.load(f)
    # normalize relative paths to absolute
    for k in ("APK_FOLDER", "OUTPUT_FOLDER", "SENSITIVE_API"):
        if k in s and not Path(s[k]).is_absolute():
            s[k] = str((REPO_ROOT / s[k]).resolve())
    return s


SETTINGS = load_settings()
# GLOBAL_MODEL = SETTINGS.get("model_name", "gemma3:latest")
GLOBAL_MODEL = (
    os.getenv("OB_MODEL")
    or os.getenv("MODEL")
    or SETTINGS.get("model_name")
    or "gemma3:latest"
)
print(f"[INFO] Using model: {GLOBAL_MODEL}")


# GLOBAL_MODEL ="gemma3:latest"
# GLOBAL_MODEL = "llama3.1:latest"
# GLOBAL_MODEL ="qwen3:latest"
# GLOBAL_MODEL = "deepseek-coder-v2:16b"

MAX_TOKENS = 40000


def call_llm(prompt: str) -> str:
    """Gửi yêu cầu tới LLM để sinh mã Frida."""
    payload = {
        "model": SETTINGS.get("model_name"),
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    response = requests.post(SETTINGS.get("ollama_url"), json=payload, timeout=120)
    if response.status_code == 200:
        return response.json().get("response", "")
    return ""


def generate_frida_script(app_name: str, memory_data: list = None):
    """
    Hàm xử lý Giai đoạn 2: Sinh script Frida.
    - memory_data: Dữ liệu truyền trực tiếp từ Giai đoạn 1 (RAM).
    - Nếu memory_data là None: Tự động đọc từ file sensitive_only.json (Disk).
    """

    # 1. Xác định nguồn dữ liệu
    leaks_data = None
    if memory_data is not None:
        print(
            f"[INFO] Sử dụng dữ liệu luồng rò rỉ trực tiếp từ bộ nhớ (RAM) cho {app_name}."
        )
        leaks_data = memory_data
    else:
        # Tự tìm đọc file nếu không có dữ liệu RAM
        json_path = Path("outputs") / app_name / "sensitive_only.json"
        if not json_path.exists():
            print(f"[ERROR] Không tìm thấy tệp dữ liệu tại {json_path}")
            return
        with open(json_path, "r", encoding="utf-8") as f:
            leaks_data = json.load(f)
            print(f"[INFO] Đã đọc dữ liệu từ tệp: {json_path}")

    if not leaks_data:
        print("[INFO] Không có dữ liệu rò rỉ để sinh kịch bản.")
        return

    # 2. Xây dựng Prompt
    prompt = f"""
    Viết script Frida (JavaScript) để hook các điểm sau: {json.dumps(leaks_data)}.
    Yêu cầu:
    - Bọc trong Java.perform().
    - Hook vào Source (để log) và Sink (để kiểm chứng).
    - Sử dụng định dạng log: [FRIDA_VERIFIED_LEAK] Data found at Sink: <dữ_liệu>.
    - Trả về mã JavaScript thuần, không kèm markdown.
    """

    # 3. Kích hoạt LLM
    print("[INFO] Đang gọi LLM sinh script...")
    raw_code = call_llm(prompt)

    # Làm sạch mã (loại bỏ markdown nếu có)
    clean_code = re.sub(r"```javascript|```", "", raw_code).strip()

    # 4. Lưu script
    output_dir = Path("outputs") / app_name
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "script.js", "w", encoding="utf-8") as f:
        f.write(clean_code)

    print(f"[SUCCESS] Script Frida đã được tạo tại: {output_dir / 'script.js'}")


# --- Ví dụ sử dụng ---
# Cách 1: Chạy ngay sau Giai đoạn 1 (Truyền trực tiếp mảng dữ liệu)
# leaked_data = get_leaks_from_pipeline()
# generate_frida_script("MyTargetApp", memory_data=leaked_data)

# Cách 2: Chạy độc lập từ file (Không truyền memory_data)
# generate_frida_script("MyTargetApp")
