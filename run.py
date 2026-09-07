import sys
import os
import uvicorn

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def check_and_download_models():
    import urllib.request
    models_dir = os.path.join(os.path.dirname(__file__), "models_weights")
    os.makedirs(models_dir, exist_ok=True)

    yunet_path = os.path.join(models_dir, "face_detection_yunet_2023mar.onnx")
    sface_path = os.path.join(models_dir, "face_recognition_sface_2021dec.onnx")

    yunet_url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
    sface_url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

    if not os.path.exists(yunet_path):
        print("Đang tải mô hình nhận diện khuôn mặt YuNet...")
        urllib.request.urlretrieve(yunet_url, yunet_path)
        print("Đã tải xong YuNet!")

    if not os.path.exists(sface_path):
        print("Đang tải mô hình trích xuất đặc trưng SFace...")
        urllib.request.urlretrieve(sface_url, sface_path)
        print("Đã tải xong SFace!")

if __name__ == "__main__":
    check_and_download_models()
    print("==================================================================")
    print("      HỆ THỐNG ĐIỂM DANH & CHẤM CÔNG FACE ID (CHECK-IN / OUT)     ")
    print("==================================================================")
    print(" Đang khởi chạy máy chủ tại: http://localhost:8000")
    print(" - Màn hình Kiosk Điểm Danh : http://localhost:8000/")
    print(" - Trang Quản Trị (Admin)   : http://localhost:8000/admin")
    print(" - Tài liệu API (Swagger UI): http://localhost:8000/docs")
    print("==================================================================")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
