import os
import subprocess
import time

import re

from modules.common.utils import get_apk_path_by_name


def get_android_sdk_path():
    """Get Android SDK path from environment variables or default directories."""
    sdk_path = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")

    if not sdk_path:
        home = os.path.expanduser("~")
        windows_path = os.path.join(home, "AppData", "Local", "Android", "Sdk")
        mac_path = os.path.join(home, "Library", "Android", "sdk")

        if os.path.exists(windows_path):
            sdk_path = windows_path
        elif os.path.exists(mac_path):
            sdk_path = mac_path

    return sdk_path


def start_emulator(emulator_path, avd_name):
    """Start the specified Android Virtual Device (AVD)."""
    print(f"\n[INFO] Starting emulator: {avd_name}...")

    # Run in background using Popen to prevent freezing the Python script
    subprocess.Popen(
        [emulator_path, "-avd", avd_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print("[INFO] Waiting for emulator response...")
    time.sleep(3)
    print("[SUCCESS] Emulator boot command sent successfully!")


def get_adb_path(sdk_path):
    """Get the correct path to the adb tool."""
    adb_path = os.path.join(sdk_path, "platform-tools", "adb")
    if os.name == "nt":
        adb_path += ".exe"
    return adb_path


def wait_for_boot(adb_path):
    """Continuously check if the emulator OS has fully booted."""
    print("[INFO] Waiting for Android OS to nạp (Booting)...")

    # Wait for ADB server to recognize the device in basic state first
    subprocess.run([adb_path, "wait-for-device"], check=True)

    start_time = time.time()
    timeout = 180  # Max 3 minutes timeout

    while True:
        try:
            # Query system property for boot completion status
            result = subprocess.run(
                [adb_path, "shell", "getprop", "sys.boot_completed"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout.strip() == "1":
                print(
                    f"[SUCCESS] Emulator is ready after {int(time.time() - start_time)} seconds!"
                )
                return True
        except subprocess.TimeoutExpired:
            pass

        if time.time() - start_time > timeout:
            print("[ERROR] Timeout waiting for emulator to boot.")
            return False

        time.sleep(3)

    # def install_apk(adb_path, apk_path):
    """Install APK file into the emulator and automatically grant runtime permissions."""
    if not os.path.exists(apk_path):
        print(f"[ERROR] APK file not found at path: {apk_path}")
        return False

    print(f"[INFO] Installing APK: {os.path.basename(apk_path)}...")
    try:
        # -r: Replace existing application if present
        # -g: Grant all runtime permissions listed in Manifest automatically
        result = subprocess.run(
            [adb_path, "install", "-r", "-g", apk_path],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)
        print("[SUCCESS] Application installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install APK: {e.stderr}")
        return False


def install_apk(adb_path, apk_path):
    """
    Check if the application package already exists on the device.
    If detected, uninstall the old version before performing a clean installation.
    """
    if not os.path.exists(apk_path):
        print(f"[ERROR] APK file not found at path: {apk_path}")
        return False

    print(f"[INFO] Extracting package name from APK: {os.path.basename(apk_path)}...")
    package_name = None
    try:
        # Use aapt tool (bundled within Android SDK build-tools) to find the package name
        # If aapt is not directly accessible, fallback to a strict reinstall process
        sdk_path = get_android_sdk_path()
        build_tools_dir = os.path.join(sdk_path, "build-tools")

        # Find the first available build-tools version subfolder
        if os.path.exists(build_tools_dir):
            versions = sorted(os.listdir(build_tools_dir))
            if versions:
                aapt_binary = os.path.join(build_tools_dir, versions[-1], "aapt")
                if os.name == "nt":
                    aapt_binary += ".exe"

                if os.path.exists(aapt_binary):
                    aapt_result = subprocess.run(
                        [aapt_binary, "dump", "badging", apk_path],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    # Extract the package name using regex matching
                    match = re.search(r"package:\s+name='([^']+)'", aapt_result.stdout)
                    if match:
                        package_name = match.group(1)
                        print(f"[INFO] Target package identifier found: {package_name}")
    except Exception as e:
        print(f"[WARNING] Failed to parse package name via aapt: {e}")

    # If package name was resolved, verify existence and uninstall if necessary
    if package_name:
        try:
            print(
                f"[INFO] Checking if package '{package_name}' is already installed..."
            )
            pkg_check = subprocess.run(
                [adb_path, "shell", "pm", "list", "packages", package_name],
                capture_output=True,
                text=True,
                check=True,
            )

            # Check if the specific package exists in the adb shell output
            if f"package:{package_name}" in pkg_check.stdout.strip():
                print(
                    f"[WARNING] Application '{package_name}' already exists. Performing uninstallation..."
                )
                subprocess.run(
                    [adb_path, "uninstall", package_name],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                print(
                    f"[SUCCESS] Successfully uninstalled the previous version of '{package_name}'."
                )
            else:
                print(
                    f"[INFO] No existing deployment found for '{package_name}'. Proceeding with clean install."
                )
        except subprocess.CalledProcessError as e:
            print(f"[WARNING] Error checking/uninstalling existing version: {e.stderr}")

    # Execute the fresh package installation
    print(f"[INFO] Deploying fresh installation for: {os.path.basename(apk_path)}...")
    try:
        # -r: Replace existing application if package verification failed above
        # -g: Grant all runtime permissions listed in Manifest automatically
        result = subprocess.run(
            [adb_path, "install", "-r", "-g", apk_path],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)
        print("[SUCCESS] Application installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install APK: {e.stderr}")
        return False


def check_and_start_avd(apk_path):
    """Check available AVDs, launch emulator, and install the target APK."""
    sdk_path = get_android_sdk_path()
    if not sdk_path:
        print(
            "[ERROR] Android SDK path not found. Please configure ANDROID_HOME environment variable."
        )
        return

    # Path to emulator binary (cross-platform)
    emulator_path = os.path.join(sdk_path, "emulator", "emulator")
    if os.name == "nt":
        emulator_path += ".exe"

    if not os.path.exists(emulator_path):
        print(f"[ERROR] Emulator tool not found at: {emulator_path}")
        return

    # Get ADB path
    adb_path = get_adb_path(sdk_path)

    try:
        # 1. Scan available virtual devices
        print("[INFO] Scanning available virtual devices (AVD)...")
        result = subprocess.run(
            [emulator_path, "-list-avds"],
            capture_output=True,
            text=True,
            check=True,
        )

        avd_list = [line.strip() for line in result.stdout.splitlines() if line.strip()]

        if len(avd_list) == 0:
            print("[ERROR] No Android Virtual Devices (AVD) found in the system.")
            return

        selected_avd = None
        if len(avd_list) == 1:
            print(f"[INFO] Only 1 virtual device found: {avd_list[0]}")
            selected_avd = avd_list[0]
        else:
            print(f"\n[INFO] Found {len(avd_list)} available virtual devices:")
            for index, avd_name in enumerate(avd_list, start=1):
                print(f"  [{index}] - {avd_name}")

            while True:
                try:
                    choice = input(
                        f"\nEnter index number (1-{len(avd_list)}) to launch emulator: "
                    ).strip()
                    choice_idx = int(choice) - 1

                    if 0 <= choice_idx < len(avd_list):
                        selected_avd = avd_list[choice_idx]
                        break
                    else:
                        print(
                            f"[WARNING] Invalid index. Please select between 1 and {len(avd_list)}."
                        )
                except ValueError:
                    print("[WARNING] Please enter a valid number (e.g., 1, 2, 3...).")

        # 2. Orchestrate emulator startup and automatic APK installation
        if selected_avd:
            start_emulator(emulator_path, selected_avd)

            # Wait for OS boot and then proceed to install the APK
            if wait_for_boot(adb_path):
                install_apk(adb_path, apk_path)

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to fetch emulator list: {e.stderr}")
    except Exception as e:
        print(f"[ERROR] System error occurred: {e}")


if __name__ == "__main__":
    target_apk_path = get_apk_path_by_name("ap-news")

    # Proceed to start AVD and install if target path is valid
    if target_apk_path:
        check_and_start_avd(apk_path=target_apk_path)
    else:
        print("[INFO] Execution aborted because the specified file was not found.")
