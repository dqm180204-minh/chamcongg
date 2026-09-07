import os
from typing import List, Optional
from datetime import datetime
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import FACES_DIR, settings
from app.models.employee import Employee, FaceEncoding
from app.models.shift import Shift
from app.services.face_engine import face_engine

router = APIRouter(prefix="/employees", tags=["Employees"])

# Pydantic Schemas
class ShiftInfo(BaseModel):
    id: int
    name: str
    start_time: str
    end_time: str
    grace_period_minutes: int

    class Config:
        from_attributes = True

class EmployeeCreate(BaseModel):
    emp_code: str
    full_name: str
    department: Optional[str] = "Văn Phòng"
    position: Optional[str] = "Nhân viên"
    phone: Optional[str] = None
    email: Optional[str] = None
    shift_id: Optional[int] = None

class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    shift_id: Optional[int] = None
    is_active: Optional[bool] = None

class EmployeeOut(BaseModel):
    id: int
    emp_code: str
    full_name: str
    department: str
    position: str
    phone: Optional[str]
    email: Optional[str]
    avatar_path: Optional[str]
    is_active: bool
    face_count: int
    shift: Optional[ShiftInfo]
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("", response_model=List[EmployeeOut])
def get_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).order_by(Employee.id.desc()).all()
    results = []
    for emp in employees:
        emp_dict = {
            "id": emp.id,
            "emp_code": emp.emp_code,
            "full_name": emp.full_name,
            "department": emp.department,
            "position": emp.position,
            "phone": emp.phone,
            "email": emp.email,
            "avatar_path": emp.avatar_path,
            "is_active": emp.is_active,
            "face_count": len(emp.face_encodings),
            "shift": emp.shift,
            "created_at": emp.created_at
        }
        results.append(emp_dict)
    return results

@router.post("", response_model=EmployeeOut)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    existing = db.query(Employee).filter(Employee.emp_code == data.emp_code.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Mã nhân viên '{data.emp_code}' đã tồn tại!")

    emp = Employee(
        emp_code=data.emp_code.strip().upper(),
        full_name=data.full_name.strip(),
        department=data.department.strip() if data.department else "Văn Phòng",
        position=data.position.strip() if data.position else "Nhân viên",
        phone=data.phone,
        email=data.email,
        shift_id=data.shift_id
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)

    return {
        "id": emp.id,
        "emp_code": emp.emp_code,
        "full_name": emp.full_name,
        "department": emp.department,
        "position": emp.position,
        "phone": emp.phone,
        "email": emp.email,
        "avatar_path": emp.avatar_path,
        "is_active": emp.is_active,
        "face_count": 0,
        "shift": emp.shift,
        "created_at": emp.created_at
    }

@router.put("/{emp_id}", response_model=EmployeeOut)
def update_employee(emp_id: int, data: EmployeeUpdate, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên")

    if data.full_name is not None:
        emp.full_name = data.full_name.strip()
    if data.department is not None:
        emp.department = data.department.strip()
    if data.position is not None:
        emp.position = data.position.strip()
    if data.phone is not None:
        emp.phone = data.phone
    if data.email is not None:
        emp.email = data.email
    if data.shift_id is not None:
        emp.shift_id = data.shift_id
    if data.is_active is not None:
        emp.is_active = data.is_active

    db.commit()
    db.refresh(emp)

    return {
        "id": emp.id,
        "emp_code": emp.emp_code,
        "full_name": emp.full_name,
        "department": emp.department,
        "position": emp.position,
        "phone": emp.phone,
        "email": emp.email,
        "avatar_path": emp.avatar_path,
        "is_active": emp.is_active,
        "face_count": len(emp.face_encodings),
        "shift": emp.shift,
        "created_at": emp.created_at
    }

@router.delete("/{emp_id}")
def delete_employee(emp_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên")

    db.delete(emp)
    db.commit()
    return {"success": True, "message": f"Đã xóa nhân viên {emp.full_name}"}

class FaceRegisterBase64(BaseModel):
    image_base64: str

@router.post("/{emp_id}/faces/capture")
def register_face_base64(emp_id: int, payload: FaceRegisterBase64, db: Session = Depends(get_db)):
    """Đăng ký khuôn mặt từ chuỗi Base64 (chụp từ webcam trên web)"""
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên")

    img_bgr = face_engine.decode_base64(payload.image_base64)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Hình ảnh không hợp lệ hoặc bị lỗi")

    extracted = face_engine.extract_single_embedding(img_bgr)
    if not extracted:
        raise HTTPException(status_code=400, detail="Không nhận diện được khuôn mặt rõ ràng trong ảnh. Vui lòng nhìn thẳng và đủ sáng!")

    embedding_vec, aligned_face = extracted

    # Lưu ảnh mẫu khuôn mặt vào thư mục data/faces
    filename = f"{emp.emp_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    img_save_path = FACES_DIR / filename
    cv2.imwrite(str(img_save_path), aligned_face)

    # Nếu nhân viên chưa có avatar, đặt ảnh này làm avatar
    if not emp.avatar_path:
        emp.avatar_path = f"/faces/{filename}"

    # Lưu vector vào DB
    encoding_rec = FaceEncoding(
        employee_id=emp.id,
        image_path=f"/faces/{filename}"
    )
    encoding_rec.set_embedding(embedding_vec)
    db.add(encoding_rec)
    db.commit()

    return {
        "success": True,
        "message": f"Đăng ký mẫu khuôn mặt thành công cho {emp.full_name}",
        "face_id": encoding_rec.id,
        "image_url": f"/faces/{filename}",
        "total_faces": len(emp.face_encodings)
    }

@router.post("/{emp_id}/faces/upload")
async def register_face_upload(emp_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Đăng ký khuôn mặt từ file ảnh tải lên"""
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên")

    contents = await file.read()
    img_bgr = face_engine.decode_image(contents)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="File không phải định dạng ảnh hợp lệ")

    extracted = face_engine.extract_single_embedding(img_bgr)
    if not extracted:
        raise HTTPException(status_code=400, detail="Không nhận diện được khuôn mặt trong ảnh tải lên. Vui lòng chọn ảnh chân dung rõ mặt!")

    embedding_vec, aligned_face = extracted

    filename = f"{emp.emp_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    img_save_path = FACES_DIR / filename
    cv2.imwrite(str(img_save_path), aligned_face)

    if not emp.avatar_path:
        emp.avatar_path = f"/faces/{filename}"

    encoding_rec = FaceEncoding(
        employee_id=emp.id,
        image_path=f"/faces/{filename}"
    )
    encoding_rec.set_embedding(embedding_vec)
    db.add(encoding_rec)
    db.commit()

    return {
        "success": True,
        "message": f"Đã thêm mẫu khuôn mặt cho {emp.full_name}",
        "face_id": encoding_rec.id,
        "image_url": f"/faces/{filename}",
        "total_faces": len(emp.face_encodings)
    }

@router.delete("/{emp_id}/faces/{face_id}")
def delete_face_sample(emp_id: int, face_id: int, db: Session = Depends(get_db)):
    face = db.query(FaceEncoding).filter(FaceEncoding.id == face_id, FaceEncoding.employee_id == emp_id).first()
    if not face:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu khuôn mặt")

    # Xóa file ảnh vật lý nếu có
    if face.image_path:
        real_path = FACES_DIR / os.path.basename(face.image_path)
        if real_path.exists():
            try:
                os.remove(real_path)
            except Exception:
                pass

    db.delete(face)
    db.commit()
    return {"success": True, "message": "Đã xóa mẫu khuôn mặt"}
