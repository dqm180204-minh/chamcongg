import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import relationship
import numpy as np
from app.core.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    emp_code = Column(String(50), unique=True, index=True, nullable=False) # e.g. NV001
    full_name = Column(String(150), nullable=False)
    department = Column(String(100), default="Văn Phòng")
    position = Column(String(100), default="Nhân viên")
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    avatar_path = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)
    shift = relationship("Shift", back_populates="employees")

    face_encodings = relationship("FaceEncoding", back_populates="employee", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="employee", cascade="all, delete-orphan")
    attendance_logs = relationship("AttendanceLog", back_populates="employee", cascade="all, delete-orphan")

class FaceEncoding(Base):
    __tablename__ = "face_encodings"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    # Lưu trữ vector nhúng nhị phân (float32 numpy array)
    embedding_blob = Column(LargeBinary, nullable=False)
    image_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="face_encodings")

    def get_embedding(self) -> np.ndarray:
        return np.frombuffer(self.embedding_blob, dtype=np.float32)

    def set_embedding(self, vector: np.ndarray):
        self.embedding_blob = vector.astype(np.float32).tobytes()
