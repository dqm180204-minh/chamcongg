import base64
import os
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
from pathlib import Path

from app.core.config import settings

class FaceEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FaceEngine, cls).__new__(cls)
            cls._instance._init_models()
        return cls._instance

    def _init_models(self):
        yunet_path = settings.YUNET_MODEL_PATH
        sface_path = settings.SFACE_MODEL_PATH

        if not os.path.exists(yunet_path) or not os.path.exists(sface_path):
            raise FileNotFoundError("Mô hình AI chưa được tải đầy đủ trong models_weights/")

        # Khởi tạo bộ phát hiện khuôn mặt YuNet
        self.detector = cv2.FaceDetectorYN.create(
            model=yunet_path,
            config="",
            input_size=(320, 320),
            score_threshold=settings.DETECTION_CONFIDENCE,
            nms_threshold=0.3,
            top_k=5000
        )

        # Khởi tạo bộ trích xuất đặc trưng SFace
        self.recognizer = cv2.FaceRecognizerSF.create(
            model=sface_path,
            config=""
        )

    def decode_image(self, image_data: bytes) -> Optional[np.ndarray]:
        """Giải mã bytes hình ảnh thành mảng numpy BGR"""
        try:
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"Lỗi giải mã ảnh: {e}")
            return None

    def decode_base64(self, base64_str: str) -> Optional[np.ndarray]:
        """Giải mã chuỗi Base64 (có thể kèm data:image/...;base64,)"""
        try:
            if "," in base64_str:
                base64_str = base64_str.split(",", 1)[1]
            image_bytes = base64.b64decode(base64_str)
            return self.decode_image(image_bytes)
        except Exception as e:
            print(f"Lỗi giải mã base64: {e}")
            return None

    def detect_and_extract_all(self, image: np.ndarray) -> List[Dict]:
        """
        Phát hiện toàn bộ khuôn mặt trong ảnh và trích xuất vector đặc trưng 128 chiều.
        Trả về danh sách các dict chứa bbox, score, landmarks, embedding.
        """
        h, w, _ = image.shape
        self.detector.setInputSize((w, h))
        
        status, faces = self.detector.detect(image)
        if faces is None or len(faces) == 0:
            return []

        results = []
        for face in faces:
            score = float(face[14])
            if score < settings.DETECTION_CONFIDENCE:
                continue

            # Bounding box [x, y, w, h]
            x, y, box_w, box_h = map(int, face[0:4])
            # Đảm bảo box nằm trong ảnh
            x = max(0, x)
            y = max(0, y)
            box_w = min(w - x, box_w)
            box_h = min(h - y, box_h)

            # Cắt và căn chỉnh khuôn mặt theo các điểm mốc (landmarks)
            aligned_face = self.recognizer.alignCrop(image, face)
            
            # Trích xuất vector đặc trưng (128-d float32)
            feat = self.recognizer.feature(aligned_face)
            feat_flat = feat.flatten().astype(np.float32)

            results.append({
                "bbox": [x, y, box_w, box_h],
                "score": score,
                "landmarks": face[4:14].reshape(5, 2).tolist(),
                "embedding": feat_flat,
                "aligned_face": aligned_face
            })

        return results

    def extract_single_embedding(self, image: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Trích xuất embedding cho trường hợp đăng ký khuôn mặt (yêu cầu đúng 1 khuôn mặt rõ nét nhất).
        Trả về (embedding, aligned_face) hoặc None.
        """
        detected = self.detect_and_extract_all(image)
        if not detected:
            return None
        # Lấy khuôn mặt có score cao nhất
        best_face = max(detected, key=lambda f: f["score"])
        return best_face["embedding"], best_face["aligned_face"]

    @staticmethod
    def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
        """Tính độ tương đồng Cosine giữa 2 vector"""
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot / (norm1 * norm2))

    def find_best_match(
        self,
        query_embedding: np.ndarray,
        known_encodings: List[Tuple[int, np.ndarray]], # [(emp_id, embedding_vector), ...]
        threshold: Optional[float] = None
    ) -> Tuple[Optional[int], float]:
        """
        So khớp query_embedding với danh sách known_encodings.
        Trả về (employee_id, max_similarity). Nếu không vượt qua threshold, trả về (None, max_similarity).
        """
        if threshold is None:
            threshold = settings.SIMILARITY_THRESHOLD

        if not known_encodings:
            return None, 0.0

        best_emp_id = None
        max_similarity = -1.0

        for emp_id, emb in known_encodings:
            sim = self.cosine_similarity(query_embedding, emb)
            if sim > max_similarity:
                max_similarity = sim
                if sim >= threshold:
                    best_emp_id = emp_id

        if max_similarity < threshold:
            return None, max_similarity

        return best_emp_id, max_similarity

face_engine = FaceEngine()
