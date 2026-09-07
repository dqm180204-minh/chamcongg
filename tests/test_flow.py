import sys
import os
import io
from datetime import datetime, date
import numpy as np
import cv2

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Thêm thư mục gốc vào sys.path
sys.path.insert(0, os.path.abspath("."))

from app.core.database import SessionLocal, Base, engine
from app.models.shift import Shift
from app.models.employee import Employee, FaceEncoding
from app.models.attendance import AttendanceRecord, AttendanceLog
from app.services.face_engine import face_engine
from app.services.attendance_service import attendance_service
from app.services.report_service import report_service

def test_full_flow():
    print("=== BẮT ĐẦU KIỂM THỬ HỆ THỐNG ===")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 1. Tạo Ca làm việc
    shift = db.query(Shift).filter(Shift.name == "Ca Thử Nghiệm").first()
    if not shift:
        shift = Shift(name="Ca Thử Nghiệm", start_time="08:30", end_time="17:30", grace_period_minutes=15, work_hours=8.0)
        db.add(shift)
        db.commit()
        db.refresh(shift)
    print(f"1. Ca làm việc: {shift.name} ({shift.start_time} - {shift.end_time}) [OK]")

    # 2. Tạo Nhân viên mẫu
    emp = db.query(Employee).filter(Employee.emp_code == "NV999").first()
    if not emp:
        emp = Employee(
            emp_code="NV999",
            full_name="Nguyễn Văn Test",
            department="Phòng Kỹ Thuật",
            position="Kỹ sư AI",
            shift_id=shift.id
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
    print(f"2. Nhân viên: {emp.full_name} ({emp.emp_code}) [OK]")

    # 3. Giả lập một vector nhúng Face ID (128 chiều)
    synthetic_vector = np.random.randn(128).astype(np.float32)
    # Chuẩn hóa L2 norm
    synthetic_vector /= np.linalg.norm(synthetic_vector)

    # Đăng ký Face Encoding
    existing_enc = db.query(FaceEncoding).filter(FaceEncoding.employee_id == emp.id).first()
    if not existing_enc:
        encoding = FaceEncoding(employee_id=emp.id)
        encoding.set_embedding(synthetic_vector)
        db.add(encoding)
        db.commit()
    else:
        existing_enc.set_embedding(synthetic_vector)
        db.commit()
    print("3. Đăng ký mẫu Face ID 128 chiều [OK]")

    # 4. Kiểm tra so khớp Cosine Similarity
    stored_enc = db.query(FaceEncoding).filter(FaceEncoding.employee_id == emp.id).first()
    retrieved_vec = stored_enc.get_embedding()
    sim = face_engine.cosine_similarity(synthetic_vector, retrieved_vec)
    assert sim > 0.999, f"Vector similarity mismatch: {sim}"
    print(f"4. So khớp Cosine Similarity cùng mẫu: {sim:.4f} [OK]")

    # 5. Xóa log cũ của ngày hôm nay để test fresh check-in
    db.query(AttendanceRecord).filter(AttendanceRecord.employee_id == emp.id, AttendanceRecord.record_date == date.today()).delete()
    db.query(AttendanceLog).filter(AttendanceLog.employee_id == emp.id).delete()
    db.commit()

    # 6. Thực hiện Check-in
    dummy_snapshot = np.zeros((100, 100, 3), dtype=np.uint8)
    res_in = attendance_service.record_attendance(db, emp, mode="AUTO", confidence=sim, snapshot_img=dummy_snapshot)
    print(f"6. Kết quả Check-in: Action={res_in['action']}, Status={res_in.get('status')}, Msg={res_in['message']} [OK]")
    assert res_in["action"] == "CHECK_IN"

    # 7. Quét lại ngay lập tức -> Phải kích hoạt Cooldown
    res_cooldown = attendance_service.record_attendance(db, emp, mode="AUTO", confidence=sim)
    print(f"7. Quét lại liên tục: Cooldown={res_cooldown['is_cooldown']}, Action={res_cooldown['action']} [OK]")
    assert res_cooldown["is_cooldown"] == True

    # 8. Test xuất báo cáo Excel
    excel_io = report_service.generate_excel_report(db, from_date=date.today(), to_date=date.today())
    assert excel_io.getbuffer().nbytes > 1000
    print(f"8. Xuất file Excel chấm công: Kích thước {excel_io.getbuffer().nbytes} bytes [OK]")

    # Dọn dẹp bản ghi test
    db.query(AttendanceRecord).filter(AttendanceRecord.employee_id == emp.id).delete()
    db.query(AttendanceLog).filter(AttendanceLog.employee_id == emp.id).delete()
    db.query(FaceEncoding).filter(FaceEncoding.employee_id == emp.id).delete()
    db.query(Employee).filter(Employee.id == emp.id).delete()
    db.commit()
    db.close()
    print("=== TOÀN BỘ BÀI TEST CHẠY THÀNH CÔNG 100%! ===")

if __name__ == "__main__":
    test_full_flow()
