#  Hệ Thống Điểm Danh & Chấm Công Bằng Khuôn Mặt (Face ID)

Dự án Hệ thống Điểm danh & Chấm công tự động qua nhận diện khuôn mặt (Face ID) chạy trên nền tảng Web-based, kết nối trực tiếp Webcam máy tính, tối ưu cho quy mô doanh nghiệp vừa và nhỏ (< 50 nhân sự).

---

##  Các Tính Năng Nổi Bật

1. **Màn hình Kiosk Điểm Danh Tự Động (Check-in / Check-out)**:
   - Nhận diện khuôn mặt thời gian thực qua webcam máy tính.
   - Vẽ khung nhận diện viền xanh/vàng thông minh.
   - Chế độ chấm công:
     - **Tự động (Auto)**: Lần đầu quét trong ngày $\rightarrow$ Check-in; lần quét sau $\rightarrow$ Check-out.
     - **Chỉ Check-in**: Ép chế độ vào ca.
     - **Chỉ Check-out**: Ép chế độ tan ca.
   - Hiệu ứng âm thanh Chime khi nhận diện thành công.
   - Cơ chế Cooldown 45s chống quét trùng lặp liên tục khi đứng trước camera.

2. **Quản trị Nhân sự & Đăng ký Khuôn Mặt**:
   - Thêm/Sửa/Xóa thông tin nhân viên (Mã NV, Họ tên, Phòng ban, Ca làm việc).
   - **Đăng ký Face ID trực tiếp qua Webcam**: Bật camera lên và chụp mẫu mặt ngay trên trình duyệt!
   - **Tải ảnh chân dung lên từ máy tính**.
   - Hỗ trợ lưu nhiều mẫu khuôn mặt cho một nhân viên để tăng tối đa độ chính xác.

3. **Cấu hình Ca làm việc & Quy tắc Tính công**:
   - Tùy chỉnh giờ bắt đầu, giờ kết thúc (mặc định 08:30 - 17:30).
   - Cho phép ân hạn đi muộn (Grace period: ví dụ 15 phút).
   - Tự động phân loại: Đúng giờ (On-time), Đi muộn (Late), Về sớm (Early leave).

4. **Báo cáo & Xuất Bảng Chấm Công Excel**:
   - Lọc dữ liệu theo khoảng ngày (Từ ngày - Đến ngày) và phòng ban.
   - Xuất file báo cáo Excel (`.xlsx`) định dạng chuẩn đẹp mắt, có tổng số giờ công, phút đi muộn, về sớm.

---

##  Cấu Trúc Dự Án (Ổ D:)

```
D:\face_attendance/
├── app/
│   ├── api/                  # Các endpoint API (employees, attendance, face, shifts)
│   ├── core/                 # Cấu hình config.py & kết nối database.py
│   ├── models/               # ORM Models (Employee, FaceEncoding, Shift, Attendance)
│   ├── services/             # FaceEngine (AI YuNet + SFace), AttendanceService, ReportService
│   └── main.py               # FastAPI App entrypoint
├── models_weights/           # Trọng số mô hình AI Face Detection & Recognition
│   ├── face_detection_yunet_2023mar.onnx
│   └── face_recognition_sface_2021dec.onnx
├── static/                   # Static CSS / JS (kiosk.js, admin.js)
├── templates/                # Giao diện HTML (kiosk.html, admin.html)
├── tests/                    # Bài test tự động (test_flow.py)
├── data/                     # Database SQLite và ảnh khuôn mặt
│   ├── attendance.db
│   ├── faces/
│   └── snapshots/
├── .venv/                    # Môi trường ảo Python 3.12
├── requirements.txt          # Danh sách thư viện
├── start.bat                 # File click đúp để chạy ngay trên Windows
└── run.py                    # Khởi chạy server FastAPI
```

---

##  Hướng Dẫn Khởi Chạy

### Cách 1: Click đúp (Khuyên dùng)
- Mở thư mục `D:\face_attendance`
- Click đúp vào file `start.bat`. Hệ thống sẽ tự động khởi động và mở trình duyệt web.

### Cách 2: Chạy bằng Terminal
```powershell
cd D:\face_attendance
.\.venv\Scripts\python.exe run.py
```

---

##  Các Địa Chỉ Truy Cập

- **Màn hình Kiosk Điểm Danh**: [http://localhost:8000/](http://localhost:8000/)
- **Trang Quản Trị (Admin)**: [http://localhost:8000/admin](http://localhost:8000/admin)
- **Tài liệu API (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
