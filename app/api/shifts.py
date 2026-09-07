from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.shift import Shift

router = APIRouter(prefix="/shifts", tags=["Shifts"])

class ShiftCreate(BaseModel):
    name: str
    start_time: str = "08:30"
    end_time: str = "17:30"
    grace_period_minutes: int = 15
    work_hours: float = 8.0

class ShiftUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    grace_period_minutes: Optional[int] = None
    work_hours: Optional[float] = None

class ShiftOut(BaseModel):
    id: int
    name: str
    start_time: str
    end_time: str
    grace_period_minutes: int
    work_hours: float

    class Config:
        from_attributes = True

@router.get("", response_model=List[ShiftOut])
def get_shifts(db: Session = Depends(get_db)):
    shifts = db.query(Shift).all()
    # Nếu chưa có ca làm việc nào, tạo sẵn ca mặc định
    if not shifts:
        default_shift = Shift(
            name="Ca Hành Chính Chuẩn",
            start_time="08:30",
            end_time="17:30",
            grace_period_minutes=15,
            work_hours=8.0
        )
        db.add(default_shift)
        db.commit()
        db.refresh(default_shift)
        return [default_shift]
    return shifts

@router.post("", response_model=ShiftOut)
def create_shift(data: ShiftCreate, db: Session = Depends(get_db)):
    shift = Shift(
        name=data.name.strip(),
        start_time=data.start_time.strip(),
        end_time=data.end_time.strip(),
        grace_period_minutes=data.grace_period_minutes,
        work_hours=data.work_hours
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift

@router.put("/{shift_id}", response_model=ShiftOut)
def update_shift(shift_id: int, data: ShiftUpdate, db: Session = Depends(get_db)):
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Không tìm thấy ca làm việc")

    if data.name is not None:
        shift.name = data.name.strip()
    if data.start_time is not None:
        shift.start_time = data.start_time.strip()
    if data.end_time is not None:
        shift.end_time = data.end_time.strip()
    if data.grace_period_minutes is not None:
        shift.grace_period_minutes = data.grace_period_minutes
    if data.work_hours is not None:
        shift.work_hours = data.work_hours

    db.commit()
    db.refresh(shift)
    return shift

@router.delete("/{shift_id}")
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Không tìm thấy ca làm việc")
    
    if shift.employees:
        raise HTTPException(status_code=400, detail="Không thể xóa ca làm việc đang có nhân viên gắn kết!")

    db.delete(shift)
    db.commit()
    return {"success": True, "message": "Đã xóa ca làm việc"}
