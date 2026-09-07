from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.employee import Employee, FaceEncoding
from app.services.face_engine import face_engine
from app.services.attendance_service import attendance_service

router = APIRouter(prefix="/face", tags=["Face Recognition"])

class RecognizeRequest(BaseModel):
    image: str  # Base64 string from browser webcam
    mode: str = "AUTO"  # AUTO, CHECK_IN, CHECK_OUT

@router.post("/recognize")
def recognize_and_attend(payload: RecognizeRequest, db: Session = Depends(get_db)):
    """
    Nhận diện khuôn mặt từ khung hình webcam và tự động thực hiện điểm danh
    """
    img = face_engine.decode_base64(payload.image)
    if img is None:
        raise HTTPException(status_code=400, detail="Không thể giải mã hình ảnh")

    # 1. Phát hiện tất cả khuôn mặt trong ảnh
    detected_faces = face_engine.detect_and_extract_all(img)
    if not detected_faces:
        return {
            "faces_detected": 0,
            "results": [],
            "message": "Không phát hiện khuôn mặt"
        }

    # 2. Lấy danh sách toàn bộ vector khuôn mặt đã đăng ký từ nhân viên đang hoạt động
    known_records = db.query(FaceEncoding).join(Employee).filter(
        Employee.is_active == True
    ).all()

    known_list = []
    emp_map = {}
    for r in known_records:
        known_list.append((r.employee_id, r.get_embedding()))
        if r.employee_id not in emp_map:
            emp_map[r.employee_id] = r.employee

    results = []
    
    for face in detected_faces:
        query_emb = face["embedding"]
        bbox = face["bbox"]
        det_score = face["score"]

        # So khớp
        matched_emp_id, similarity = face_engine.find_best_match(query_emb, known_list)

        face_res: Dict[str, Any] = {
            "bbox": bbox,
            "detection_score": round(float(det_score), 2),
            "matched": False,
            "similarity": round(float(similarity), 2)
        }

        if matched_emp_id and matched_emp_id in emp_map:
            emp = emp_map[matched_emp_id]
            face_res["matched"] = True
            face_res["employee_id"] = emp.id
            face_res["emp_code"] = emp.emp_code
            face_res["full_name"] = emp.full_name
            face_res["department"] = emp.department

            # Cắt ảnh snapshot khuôn mặt hiện tại để lưu bằng chứng
            x, y, w, h = bbox
            snapshot_crop = img[y:y+h, x:x+w] if (w > 0 and h > 0) else img

            # Xử lý chấm công
            attend_res = attendance_service.record_attendance(
                db=db,
                employee=emp,
                mode=payload.mode,
                confidence=similarity,
                snapshot_img=snapshot_crop
            )
            face_res["attendance"] = attend_res
        else:
            face_res["message"] = "Khuôn mặt chưa được đăng ký"

        results.append(face_res)

    return {
        "faces_detected": len(detected_faces),
        "results": results
    }
