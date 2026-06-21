import os
from .config import APK_FOLDER  # Import thư mục chứa APK từ file cấu hình chung


def get_apk_path_by_name(apk_name):
    """
    Tìm kiếm file APK trong thư mục APK_FOLDER dựa trên tên file cung cấp.

    :param apk_name: str - Tên file APK cần tìm (có hoặc không có đuôi .apk)
    :return: str hoặc None - Đường dẫn tuyệt đối đến file nếu tìm thấy, ngược lại trả về None
    """
    # Đảm bảo tên file luôn có đuôi .apk để so sánh chính xác
    if not apk_name.endswith(".apk"):
        apk_name += ".apk"

    # Tạo đường dẫn dự kiến của file trong thư mục cấu hình
    potential_path = os.path.join(APK_FOLDER, apk_name)

    # Kiểm tra xem file đó có thực sự tồn tại hay không
    if os.path.exists(potential_path) and os.path.isfile(potential_path):
        print(f"Tìm thấy file APK: {apk_name}")
        return os.path.abspath(potential_path)
    else:
        # Nếu không tìm thấy, thông báo lỗi ra console và trả về None
        print(f"Lỗi: Không tìm thấy file '{apk_name}' trong thư mục '{APK_FOLDER}'!")
        return None
