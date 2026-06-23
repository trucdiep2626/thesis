import os
import subprocess
import time

def execute_dynamic_verification(apk_path, package_name, js_script_path, execution_timeout=30):
    """
    Tự động hóa toàn trình quy trình nạp kịch bản Frida và thu thập log kiểm chứng thực tế
    """
    print("[+] Initializing Sandbox & Dynamic Verification Sandbox...")
    
    # 1. Cài đặt tệp tin APK vào thiết bị giả lập/máy thật qua ADB
    print(f"[+] Installing APK: {apk_path}")
    subprocess.run(["adb", "install", "-r", apk_path], stdout=subprocess.DEVNULL)
    
    # 2. Khởi chạy Frida Server trên thiết bị di động (đã được cấu hình quyền root ngầm)
    print("[+] Starting frida-server on device...")
    subprocess.Popen(["adb", "shell", "su", "-c", "/data/local/tmp/frida-server &"], 
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2) # Chờ tiến trình Frida khởi động ổn định

    # 3. Sử dụng Frida CLI để đính kèm (spawn) kịch bản script.js vào tiến trình ứng dụng
    print(f"[+] Injecting {js_script_path} into application: {package_name}")
    frida_cmd = ["frida", "-U", "-f", package_name, "-l", js_script_path, "--no-pause"]
    
    # Mở một tiến trình chạy Frida và bắt luồng xuất (stdout) của nó
    frida_process = subprocess.Popen(frida_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 4. UI Automation: Sử dụng Android Monkey giả lập 500 hành vi người dùng để ép ứng dụng chạy vào logic lỗi
    print("[+] Launching UI Automation Trigger (Android Monkey)...")
    subprocess.run(["adb", "shell", "monkey", "-p", package_name, "--throttle", "100", "500"], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 5. Đánh chặn thời gian thực: Giám sát log đầu ra từ Frida để tìm kiếm chuỗi định danh chứng cứ
    verified = False
    evidence_log = ""
    start_time = time.time()

    print("[+] Monitoring runtime log stream for verification signatures...")
    while time.time() - start_time < execution_timeout:
        line = frida_process.stdout.readline()
        if not line:
            break
        if "[FRIDA_VERIFIED_LEAK]" in line:
            verified = True
            evidence_log = line.strip()
            print(f"[!] DYNAMIC EVIDENCE FOUND: {evidence_log}")
            break

    # Dọn dẹp: Tắt tiến trình ứng dụng và gỡ cài đặt để giải phóng Sandbox
    frida_process.terminate()
    subprocess.run(["adb", "shell", "am", "force-stop", package_name], stdout=subprocess.DEVNULL)
    
    return verified, evidence_log