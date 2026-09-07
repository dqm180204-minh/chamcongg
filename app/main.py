import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, DATA_DIR, FACES_DIR, SNAPSHOTS_DIR, STATIC_DIR, TEMPLATES_DIR
from app.core.database import engine, Base, SessionLocal
from app.models.shift import Shift
from app.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo bảng CSDL
    Base.metadata.create_all(bind=engine)
    
    # Khởi tạo dữ liệu mẫu nếu bảng ca làm việc trống
    db = SessionLocal()
    try:
        shift_count = db.query(Shift).count()
        if shift_count == 0:
            default_shift = Shift(
                name="Ca Hành Chính Chuẩn",
                start_time=settings.DEFAULT_SHIFT_START,
                end_time=settings.DEFAULT_SHIFT_END,
                grace_period_minutes=settings.GRACE_PERIOD_MINUTES,
                work_hours=8.0
            )
            db.add(default_shift)
            db.commit()
    finally:
        db.close()

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount các thư mục phục vụ Static và Uploads
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/faces", StaticFiles(directory=str(FACES_DIR)), name="faces")
app.mount("/snapshots", StaticFiles(directory=str(SNAPSHOTS_DIR)), name="snapshots")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API Router
app.include_router(api_router)

# Web Views
@app.get("/", response_class=HTMLResponse)
async def kiosk_view(request: Request):
    """Màn hình Kiosk Check-in/Check-out toàn màn hình"""
    return templates.TemplateResponse(request=request, name="kiosk.html", context={"title": "Kiosk Điểm Danh Face ID"})

@app.get("/admin", response_class=HTMLResponse)
async def admin_view(request: Request):
    """Bảng điều khiển Quản trị viên"""
    return templates.TemplateResponse(request=request, name="admin.html", context={"title": "Bảng Quản Trị Chấm Công"})
