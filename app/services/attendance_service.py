from datetime import datetime, date, time
from typing import Dict, Any, Optional
import os
import cv2
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings, SNAPSHOTS_DIR
from app.models.employee import Employee
from app.models.attendance import AttendanceRecord, AttendanceLog
from app.models.shift import Shift

class AttendanceService:
    @staticmethod
    def _save_snapshot(image: np.ndarray, prefix: str, emp_code: str) -> Optional[str]:
        """Lưu ảnh chụp lúc điểm danh để làm bằng chứng xác thực"""
        try:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{emp_code}_{timestamp_str}.jpg"
            save_path = SNAPSHOTS_DIR / filename
            cv2.imwrite(str(save_path), image)
            return f"/snapshots/{filename}"
        except Exception as e:
            print(f"Lỗi lưu snapshot: {e}")
            return None

    @staticmethod
    def record_attendance(
        db: Session,
        employee: Employee,
        mode: str = "AUTO",
        confidence: float = 0.0,
        snapshot_img: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Xử lý điểm danh (Check-in / Check-out) cho nhân viên
        """
        now = datetime.now()
        today = date.today()

        # 1. Kiểm tra Cooldown: Tránh điểm danh trùng lặp trong thời gian ngắn
        recent_log = db.query(AttendanceLog).filter(
            AttendanceLog.employee_id == employee.id
        ).order_by(desc(AttendanceLog.timestamp)).first()

        if recent_log:
            delta_sec = (now - recent_log.timestamp).total_seconds()
            if delta_sec < settings.COOLDOWN_SECONDS:
                return {
                    "success": True,
                    "is_cooldown": True,
                    "action": "COOLDOWN",
                    "employee_id": employee.id,
                    "emp_code": employee.emp_code,
                    "full_name": employee.full_name,
                    "department": employee.department,
                    "timestamp": now.strftime("%H:%M:%S"),
                    "message": f"Bạn vừa quét cách đây {int(delta_sec)}s. Vui lòng không quét liên tục!",
                    "avatar_path": employee.avatar_path or ""
                }

        # Lấy ca làm việc của nhân viên
        shift = employee.shift
        shift_start_str = shift.start_time if shift else settings.DEFAULT_SHIFT_START
        shift_end_str = shift.end_time if shift else settings.DEFAULT_SHIFT_END
        grace_mins = shift.grace_period_minutes if shift else settings.GRACE_PERIOD_MINUTES

        try:
            s_hour, s_min = map(int, shift_start_str.split(":"))
            shift_start_time = time(s_hour, s_min)
        except Exception:
            shift_start_time = time(8, 30)

        try:
            e_hour, e_min = map(int, shift_end_str.split(":"))
            shift_end_time = time(e_hour, e_min)
        except Exception:
            shift_end_time = time(17, 30)

        # 2. Tìm bản ghi chấm công ngày hôm nay
        record = db.query(AttendanceRecord).filter(
            AttendanceRecord.employee_id == employee.id,
            AttendanceRecord.record_date == today
        ).first()

        snapshot_url = None
        if snapshot_img is not None:
            snapshot_url = AttendanceService._save_snapshot(snapshot_img, "scan", employee.emp_code)

        # 3. Phân nhánh xử lý Check-in / Check-out
        if record is None:
            # Chưa có bản ghi hôm nay => CHECK-IN
            # Tính toán đi muộn
            current_time = now.time()
            shift_start_dt = datetime.combine(today, shift_start_time)
            actual_dt = datetime.combine(today, current_time)

            late_minutes = 0
            if actual_dt > shift_start_dt:
                diff_minutes = int((actual_dt - shift_start_dt).total_seconds() / 60)
                if diff_minutes > grace_mins:
                    late_minutes = diff_minutes

            status = "LATE" if late_minutes > 0 else "ON_TIME"
            
            new_record = AttendanceRecord(
                employee_id=employee.id,
                record_date=today,
                check_in_time=now,
                status=status,
                late_minutes=late_minutes,
                check_in_image=snapshot_url
            )
            db.add(new_record)
            
            # Ghi nhật ký
            log = AttendanceLog(
                employee_id=employee.id,
                timestamp=now,
                action_type="CHECK_IN",
                confidence=confidence,
                snapshot_path=snapshot_url
            )
            db.add(log)
            db.commit()

            if late_minutes > 0:
                msg = f"Xin chào {employee.full_name}! Check-in thành công ({now.strftime('%H:%M:%S')}) - Đi muộn {late_minutes} phút."
            else:
                msg = f"Xin chào {employee.full_name}! Check-in đúng giờ ({now.strftime('%H:%M:%S')}). Chúc bạn ngày làm việc vui vẻ!"

            return {
                "success": True,
                "is_cooldown": False,
                "action": "CHECK_IN",
                "employee_id": employee.id,
                "emp_code": employee.emp_code,
                "full_name": employee.full_name,
                "department": employee.department,
                "status": status,
                "late_minutes": late_minutes,
                "timestamp": now.strftime("%H:%M:%S"),
                "message": msg,
                "avatar_path": employee.avatar_path or ""
            }

        else:
            # Đã có Check-in trước đó
            if mode == "CHECK_IN":
                # Người dùng chọn cứng nút Check-in nhưng đã check-in rồi
                return {
                    "success": True,
                    "is_cooldown": True,
                    "action": "ALREADY_CHECKED_IN",
                    "employee_id": employee.id,
                    "emp_code": employee.emp_code,
                    "full_name": employee.full_name,
                    "department": employee.department,
                    "timestamp": now.strftime("%H:%M:%S"),
                    "message": f"Bạn đã Check-in hôm nay lúc {record.check_in_time.strftime('%H:%M:%S')}.",
                    "avatar_path": employee.avatar_path or ""
                }

            # Chế độ AUTO hoặc CHECK_OUT:
            # Nếu vừa mới check-in dưới 3 phút mà ở chế độ AUTO thì nhắc nhở
            if mode == "AUTO" and record.check_in_time:
                mins_from_in = (now - record.check_in_time).total_seconds() / 60
                if mins_from_in < 3:
                    return {
                        "success": True,
                        "is_cooldown": True,
                        "action": "COOLDOWN",
                        "employee_id": employee.id,
                        "emp_code": employee.emp_code,
                        "full_name": employee.full_name,
                        "department": employee.department,
                        "timestamp": now.strftime("%H:%M:%S"),
                        "message": f"Bạn vừa Check-in lúc {record.check_in_time.strftime('%H:%M:%S')}. Chưa đến giờ Check-out!",
                        "avatar_path": employee.avatar_path or ""
                    }

            # Cập nhật CHECK-OUT
            record.check_out_time = now
            record.check_out_image = snapshot_url or record.check_out_image

            # Tính tổng giờ làm
            total_hours = (now - record.check_in_time).total_seconds() / 3600.0
            record.work_hours = round(max(0.0, total_hours), 2)

            # Tính về sớm
            shift_end_dt = datetime.combine(today, shift_end_time)
            early_minutes = 0
            if now < shift_end_dt:
                early_minutes = int((shift_end_dt - now).total_seconds() / 60)
            record.early_minutes = early_minutes

            # Cập nhật trạng thái tổng thể
            if record.late_minutes > 0 and early_minutes > 0:
                record.status = "LATE_AND_EARLY"
            elif record.late_minutes > 0:
                record.status = "LATE"
            elif early_minutes > 0:
                record.status = "EARLY_LEAVE"
            else:
                record.status = "COMPLETED"

            # Ghi log
            log = AttendanceLog(
                employee_id=employee.id,
                timestamp=now,
                action_type="CHECK_OUT",
                confidence=confidence,
                snapshot_path=snapshot_url
            )
            db.add(log)
            db.commit()

            if early_minutes > 0:
                msg = f"Tạm biệt {employee.full_name}! Check-out lúc {now.strftime('%H:%M:%S')} (Về sớm {early_minutes}p, công: {record.work_hours}h)."
            else:
                msg = f"Tạm biệt {employee.full_name}! Check-out thành công ({now.strftime('%H:%M:%S')}, công: {record.work_hours}h). Hẹn gặp lại!"

            return {
                "success": True,
                "is_cooldown": False,
                "action": "CHECK_OUT",
                "employee_id": employee.id,
                "emp_code": employee.emp_code,
                "full_name": employee.full_name,
                "department": employee.department,
                "status": record.status,
                "work_hours": record.work_hours,
                "early_minutes": early_minutes,
                "timestamp": now.strftime("%H:%M:%S"),
                "message": msg,
                "avatar_path": employee.avatar_path or ""
            }

attendance_service = AttendanceService()
