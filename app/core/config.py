import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
FACES_DIR = DATA_DIR / "faces"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
MODELS_DIR = BASE_DIR / "models_weights"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Tạo sẵn các thư mục cần thiết
DATA_DIR.mkdir(parents=True, exist_ok=True)
FACES_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    PROJECT_NAME: str = "Hệ thống Điểm danh Face ID"
    VERSION: str = "1.0.0"
    
    # Database
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'attendance.db'}"
    
    # AI Models Paths
    YUNET_MODEL_PATH: str = str(MODELS_DIR / "face_detection_yunet_2023mar.onnx")
    SFACE_MODEL_PATH: str = str(MODELS_DIR / "face_recognition_sface_2021dec.onnx")
    
    # Face recognition parameters
    # Ngưỡng cosine similarity của SFace: >= 0.363 theo chuẩn OpenCV, đặt 0.40 để cân bằng giữa bảo mật và độ nhạy
    SIMILARITY_THRESHOLD: float = 0.40
    COOLDOWN_SECONDS: int = 45          # Không quét lại cùng 1 người trong vòng 45s để tránh spam
    DETECTION_CONFIDENCE: float = 0.55   # Ngưỡng tin cậy phát hiện khuôn mặt
    
    # Cấu hình ca làm việc mặc định
    DEFAULT_SHIFT_START: str = "08:30"
    DEFAULT_SHIFT_END: str = "17:30"
    GRACE_PERIOD_MINUTES: int = 15      # Cho phép đi muộn tối đa 15 phút không bị tính phạt
    MIN_WORK_HOURS_FOR_CHECKOUT: float = 0.1 # Thời gian tối thiểu giữa in và out (giờ)

settings = Settings()
