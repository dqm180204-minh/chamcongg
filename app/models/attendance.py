from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    record_date = Column(Date, default=date.today, index=True, nullable=False)
    
    check_in_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    
    # Trạng thái: ON_TIME (Đúng giờ), LATE (Đi muộn), EARLY_LEAVE (Về sớm), INCOMPLETE (Chưa check-out)
    status = Column(String(50), default="INCOMPLETE")
    
    late_minutes = Column(Integer, default=0)
    early_minutes = Column(Integer, default=0)
    work_hours = Column(Float, default=0.0)
    
    check_in_image = Column(String(255), nullable=True)
    check_out_image = Column(String(255), nullable=True)
    note = Column(String(255), nullable=True)

    employee = relationship("Employee", back_populates="attendance_records")

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    action_type = Column(String(20), nullable=False) # CHECK_IN, CHECK_OUT
    confidence = Column(Float, default=0.0)
    snapshot_path = Column(String(255), nullable=True)

    employee = relationship("Employee", back_populates="attendance_logs")
