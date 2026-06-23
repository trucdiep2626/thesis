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

# # ---- Repo root & settings loader ----
# REPO_ROOT = Path(__file__).resolve().parents[1]


# def load_settings(cfg_path=None):
#     # allow env override; default to artifact_settings.json if not provided
#     cfg_path = cfg_path or os.getenv("CONFIG", "configs/settings.json")
#     cfg = (REPO_ROOT / cfg_path).resolve()
#     with cfg.open("r", encoding="utf-8") as f:
#         s = json.load(f)
#     # normalize relative paths to absolute
#     for k in ("APK_FOLDER", "OUTPUT_FOLDER", "SENSITIVE_API"):
#         if k in s and not Path(s[k]).is_absolute():
#             s[k] = str((REPO_ROOT / s[k]).resolve())
#     return s


# SETTINGS = load_settings()
# # GLOBAL_MODEL = SETTINGS.get("model_name", "gemma3:latest")
# GLOBAL_MODEL = (
#     os.getenv("OB_MODEL")
#     or os.getenv("MODEL")
#     or SETTINGS.get("model_name")
#     or "gemma3:latest"
# )
# print(f"[INFO] Using model: {GLOBAL_MODEL}")


# # GLOBAL_MODEL ="gemma3:latest"
# # GLOBAL_MODEL = "llama3.1:latest"
# # GLOBAL_MODEL ="qwen3:latest"
# # GLOBAL_MODEL = "deepseek-coder-v2:16b"

# MAX_TOKENS = 40000


# def call_llm(prompt: str) -> str:
#     """Gửi yêu cầu tới LLM để sinh mã Frida."""
#     payload = {
#         "model": SETTINGS.get("model_name"),
#         "prompt": prompt,
#         "stream": False,
#         "options": {"temperature": 0.2},
#     }
#     response = requests.post(SETTINGS.get("ollama_url"), json=payload, timeout=120)
#     if response.status_code == 200:
#         return response.json().get("response", "")
#     return ""


# def generate_frida_script(app_name: str, memory_data: list = None):
#     """
#     Hàm xử lý Giai đoạn 2: Sinh script Frida.
#     - memory_data: Dữ liệu truyền trực tiếp từ Giai đoạn 1 (RAM).
#     - Nếu memory_data là None: Tự động đọc từ file sensitive_only.json (Disk).
#     """

#     # 1. Xác định nguồn dữ liệu
#     leaks_data = None
#     if memory_data is not None:
#         print(
#             f"[INFO] Sử dụng dữ liệu luồng rò rỉ trực tiếp từ bộ nhớ (RAM) cho {app_name}."
#         )
#         leaks_data = memory_data
#     else:
#         # Tự tìm đọc file nếu không có dữ liệu RAM
#         json_path = Path("outputs") / app_name / "sensitive_only.json"
#         if not json_path.exists():
#             print(f"[ERROR] Không tìm thấy tệp dữ liệu tại {json_path}")
#             return
#         with open(json_path, "r", encoding="utf-8") as f:
#             leaks_data = json.load(f)
#             print(f"[INFO] Đã đọc dữ liệu từ tệp: {json_path}")

#     if not leaks_data:
#         print("[INFO] Không có dữ liệu rò rỉ để sinh kịch bản.")
#         return

#     # 2. Xây dựng Prompt
#     prompt = f"""
#     Viết script Frida (JavaScript) để hook các điểm sau: {json.dumps(leaks_data)}.
#     Yêu cầu:
#     - Bọc trong Java.perform().
#     - Hook vào Source (để log) và Sink (để kiểm chứng).
#     - Sử dụng định dạng log: [FRIDA_VERIFIED_LEAK] Data found at Sink: <dữ_liệu>.
#     - Trả về mã JavaScript thuần, không kèm markdown.
#     """

#     # 3. Kích hoạt LLM
#     print("[INFO] Đang gọi LLM sinh script...")
#     raw_code = call_llm(prompt)

#     # Làm sạch mã (loại bỏ markdown nếu có)
#     clean_code = re.sub(r"```javascript|```", "", raw_code).strip()

#     # 4. Lưu script
#     output_dir = Path("outputs") / app_name
#     output_dir.mkdir(parents=True, exist_ok=True)
#     with open(output_dir / "script.js", "w", encoding="utf-8") as f:
#         f.write(clean_code)

#     print(f"[SUCCESS] Script Frida đã được tạo tại: {output_dir / 'script.js'}")


# # --- Ví dụ sử dụng ---
# # Cách 1: Chạy ngay sau Giai đoạn 1 (Truyền trực tiếp mảng dữ liệu)
# # leaked_data = get_leaks_from_pipeline()
# # generate_frida_script("MyTargetApp", memory_data=leaked_data)

# # Cách 2: Chạy độc lập từ file (Không truyền memory_data)
# # generate_frida_script("MyTargetApp")



import os
import json
import requests

# 1. Prompt template thiết kế theo định dạng tiếng Anh chuẩn hóa của Repo
FRIDA_PROMPT_TEMPLATE = """
You are an expert in Android Security and Dynamic Instrumentation using Frida.
Your task is to generate a comprehensive Frida JavaScript script to hook and verify a potential data leakage path discovered during static analysis.

[STATIC ANALYSIS CONTEXT - DATA LEAKAGE PATH]
{leakage_path_json}

[REQUIREMENTS]
The generated Frida script MUST accomplish three concurrent hooking tasks at runtime:
1. Hook the SOURCE method to record the exact timestamp when sensitive data is accessed.
2. Hook the PATH (intermediate methods) to track if the data is being transformed, hashed, encrypted, or passed raw.
3. Hook the SINK method to intercept and extract the raw value of the parameter right before it leaves the application boundary.

[OUTPUT FORMAT]
- Return ONLY the executable JavaScript code for Frida.
- Do NOT include any markdown code blocks (like ```javascript) or explanations.
- When the data hit the SINK method, the script MUST output a log exactly matching this format:
  "[FRIDA_VERIFIED_LEAK] Data found at Sink: <extracted_raw_value>"
- Utilize `Java.use()` and safely handle class loading and method overloading (`.overload(...)`).

[FEW-SHOT TEMPLATE EXAMPLE]
Java.perform(function() {{
    var TargetClass = Java.use('com.example.app.MainActivity');
    TargetClass.sensitiveMethod.overload('java.lang.String').implementation = function(data) {{
        console.log("[FRIDA_HOOK] Source hit: sensitiveMethod called with: " + data);
        var result = this.sensitiveMethod(data);
        return result;
    }};
}});
"""

def generate_frida_script(json_input_path, output_js_dir, lllm_api_url="http://localhost:11434/api/generate", model_name="llama3"):
    """
    Đọc luồng rò rỉ từ tệp JSON, gửi Prompt tới LLM để tự động viết file script.js
    """
    if not os.path.exists(json_input_path):
        print(f"[-] Error: Source file {json_input_path} not found.")
        return None

    # Đọc kết quả phân tích tĩnh nghi vấn (ví dụ: từ file sensitive_only.json)
    with open(json_input_path, 'r', encoding='utf-8') as f:
        leakage_data = json.load(f)

    # Chuyển đổi dữ liệu thô sang chuỗi JSON định dạng đẹp làm ngữ cảnh cho LLM
    path_context = json.dumps(leakage_data, indent=2)
    
    # Định hình Prompt hoàn chỉnh bằng tiếng Anh gửi cho LLM
    full_prompt = FRIDA_PROMPT_TEMPLATE.format(leakage_path_json=path_context)

    print("[+] Sending context to LLM for automated Frida script generation...")
    
    # Payload cấu hình gọi Local LLM qua API (ví dụ: Ollama / Local Server)
    payload = {
        "model": model_name,
        "prompt": full_prompt,
        "stream": False
    }

    try:
        response = requests.post(lllm_api_url, json=payload, timeout=60)
        if response.status_code == 200:
            generated_code = response.json().get("response", "").strip()
            
            # Đảm bảo thư mục đầu ra tồn tại
            os.makedirs(output_js_dir, exist_ok=True)
            output_file_path = os.path.join(output_js_dir, "script.js")
            
            # Ghi mã kịch bản JavaScript thu được từ LLM xuống ổ đĩa
            with open(output_file_path, "w", encoding="utf-8") as js_file:
                js_file.write(generated_code)
                
            print(f"[+] Successfully generated Frida script at: {output_file_path}")
            return output_file_path
        else:
            print(f"[-] LLM API Error: Status code {response.status_code}")
            return None
    except Exception as e:
        print(f"[-] Connection to LLM failed: {str(e)}")
        return None