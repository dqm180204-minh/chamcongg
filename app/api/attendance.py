from datetime import date, datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.models.attendance import AttendanceRecord, AttendanceLog
from app.models.employee import Employee
from app.services.report_service import report_service

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Lấy số liệu thống kê nhanh cho Admin Dashboard"""
    today = date.today()
    total_active_employees = db.query(Employee).filter(Employee.is_active == True).count()
    
    today_records = db.query(AttendanceRecord).filter(AttendanceRecord.record_date == today).all()
    checked_in_count = len(today_records)
    late_count = sum(1 for r in today_records if r.late_minutes > 0)
    checked_out_count = sum(1 for r in today_records if r.check_out_time is not None)
    absent_count = max(0, total_active_employees - checked_in_count)

    return {
        "today": today.strftime("%d/%m/%Y"),
        "total_employees": total_active_employees,
        "checked_in": checked_in_count,
        "checked_out": checked_out_count,
        "late": late_count,
        "absent": absent_count
    }

@router.get("/today")
def get_today_attendance(db: Session = Depends(get_db)):
    """Lấy danh sách điểm danh ngày hôm nay"""
    today = date.today()
    records = db.query(AttendanceRecord).join(Employee).filter(
        AttendanceRecord.record_date == today
    ).order_by(desc(AttendanceRecord.check_in_time)).all()

    results = []
    for r in records:
        emp = r.employee
        results.append({
            "id": r.id,
            "emp_code": emp.emp_code,
            "full_name": emp.full_name,
            "department": emp.department,
            "avatar_path": emp.avatar_path,
            "check_in_time": r.check_in_time.strftime("%H:%M:%S") if r.check_in_time else None,
            "check_out_time": r.check_out_time.strftime("%H:%M:%S") if r.check_out_time else None,
            "status": r.status,
            "late_minutes": r.late_minutes,
            "early_minutes": r.early_minutes,
            "work_hours": r.work_hours,
            "check_in_image": r.check_in_image,
            "check_out_image": r.check_out_image
        })
    return results

@router.get("/logs")
def get_attendance_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Lấy danh sách nhật ký quét thẻ/quét mặt gần nhất"""
    logs = db.query(AttendanceLog).join(Employee).order_by(
        desc(AttendanceLog.timestamp)
    ).limit(limit).all()

    results = []
    for l in logs:
        emp = l.employee
        results.append({
            "id": l.id,
            "emp_code": emp.emp_code,
            "full_name": emp.full_name,
            "department": emp.department,
            "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "action_type": l.action_type,
            "confidence": round(float(l.confidence), 2),
            "snapshot_path": l.snapshot_path
        })
    return results

@router.get("/records")
def get_records_filter(
    from_date: Optional[str] = None, # YYYY-MM-DD
    to_date: Optional[str] = None,   # YYYY-MM-DD
    department: Optional[str] = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Truy vấn bảng chấm công theo khoảng thời gian và phòng ban"""
    query = db.query(AttendanceRecord).join(Employee)

    if from_date:
        try:
            f_d = datetime.strptime(from_date, "%Y-%m-%d").date()
            query = query.filter(AttendanceRecord.record_date >= f_d)
        except ValueError:
            pass

    if to_date:
        try:
            t_d = datetime.strptime(to_date, "%Y-%m-%d").date()
            query = query.filter(AttendanceRecord.record_date <= t_d)
        except ValueError:
            pass

    if department and department != "ALL":
        query = query.filter(Employee.department == department)

    if employee_id:
        query = query.filter(AttendanceRecord.employee_id == employee_id)

    records = query.order_by(desc(AttendanceRecord.record_date), Employee.emp_code).all()

    results = []
    for r in records:
        emp = r.employee
        results.append({
            "id": r.id,
            "record_date": r.record_date.strftime("%d/%m/%Y"),
            "emp_code": emp.emp_code,
            "full_name": emp.full_name,
            "department": emp.department,
            "check_in_time": r.check_in_time.strftime("%H:%M:%S") if r.check_in_time else "--:--",
            "check_out_time": r.check_out_time.strftime("%H:%M:%S") if r.check_out_time else "--:--",
            "status": r.status,
            "late_minutes": r.late_minutes,
            "early_minutes": r.early_minutes,
            "work_hours": r.work_hours
        })
    return results

@router.get("/export")
def export_excel(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    department: Optional[str] = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Xuất file Excel bảng chấm công"""
    f_d = None
    t_d = None
    if from_date:
        try:
            f_d = datetime.strptime(from_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    if to_date:
        try:
            t_d = datetime.strptime(to_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    excel_stream = report_service.generate_excel_report(
        db=db,
        from_date=f_d,
        to_date=t_d,
        department=department,
        employee_id=employee_id
    )

    filename = f"Bang_Cham_Cong_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
