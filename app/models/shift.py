from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False) # e.g., "Ca Hành Chính"
    start_time = Column(String(10), default="08:30") # HH:MM
    end_time = Column(String(10), default="17:30")   # HH:MM
    grace_period_minutes = Column(Integer, default=15) # Phút cho phép đi trễ
    work_hours = Column(Float, default=8.0)            # Tiêu chuẩn số giờ công
    created_at = Column(DateTime, default=datetime.utcnow)

    employees = relationship("Employee", back_populates="shift")
