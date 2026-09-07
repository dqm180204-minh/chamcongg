@echo off
chcp 65001 > nul
title Hệ Thống Điểm Danh & Chấm Công Face ID

echo ===================================================================
echo     ĐANG KHỞI CHẠY HỆ THỐNG ĐIỂM DANH FACE ID TRÊN Ổ D:
echo ===================================================================
echo.

cd /d "D:\face_attendance"

REM Tự động mở trình duyệt sau 2 giây
start "" http://localhost:8000

REM Chạy máy chủ qua Python Virtual Environment
".venv\Scripts\python.exe" run.py

pause
