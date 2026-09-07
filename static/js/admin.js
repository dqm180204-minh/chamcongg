// Admin Portal Controller
let currentEmpForFace = null;
let regVideoStream = null;
let allEmployees = [];
let allShifts = [];

// Tab switching
function switchTab(tab) {
    const tabs = ['dashboard', 'employees', 'today', 'reports', 'shifts'];
    tabs.forEach(t => {
        const el = document.getElementById(`tab-${t}`);
        const btn = document.getElementById(`tab-btn-${t}`);
        if (t === tab) {
            el.classList.remove('hidden');
            btn.className = "px-3.5 py-2 rounded-lg flex items-center gap-2 transition-all bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold";
        } else {
            el.classList.add('hidden');
            btn.className = "px-3.5 py-2 rounded-lg flex items-center gap-2 transition-all text-slate-400 hover:text-white";
        }
    });

    if (tab === 'dashboard') loadDashboardStats();
    if (tab === 'employees') loadEmployees();
    if (tab === 'today') loadTodayTable();
    if (tab === 'reports') initReportsTab();
    if (tab === 'shifts') loadShifts();
}

// -------------------------------------------------------------
// TAB 1: DASHBOARD STATS
// -------------------------------------------------------------
async function loadDashboardStats() {
    try {
        const res = await fetch("/api/attendance/stats");
        if (!res.ok) return;
        const data = await res.json();
        document.getElementById("db-total-emp").textContent = data.total_employees;
        document.getElementById("db-checked-in").textContent = data.checked_in;
        document.getElementById("db-late").textContent = data.late;
        document.getElementById("db-absent").textContent = data.absent;
    } catch (e) {
        console.error("Lỗi tải dashboard stats", e);
    }
}

// -------------------------------------------------------------
// TAB 2: QUẢN LÝ NHÂN SỰ
// -------------------------------------------------------------
async function loadEmployees() {
    try {
        const res = await fetch("/api/employees");
        if (!res.ok) return;
        allEmployees = await res.json();
        renderEmployeesTable(allEmployees);
        updateDeptSelect();
    } catch (e) {
        console.error("Lỗi tải danh sách nhân viên", e);
    }
}

function renderEmployeesTable(employees) {
    const tbody = document.getElementById("employees-tbody");
    if (!employees || employees.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-10 text-slate-500">Chưa có nhân viên nào trong danh sách. Bấm "Thêm Nhân Viên Mới" để bắt đầu.</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = employees.map(emp => {
        const avatarHtml = emp.avatar_path
            ? `<img src="${emp.avatar_path}" class="w-8 h-8 rounded-full object-cover border border-slate-700">`
            : `<div class="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-slate-300">${emp.full_name.charAt(0)}</div>`;

        const shiftName = emp.shift ? `${emp.shift.name} (${emp.shift.start_time}-${emp.shift.end_time})` : "Mặc định";
        const faceBadge = emp.face_count > 0
            ? `<span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold border border-emerald-500/30 text-[11px]">${emp.face_count} mẫu</span>`
            : `<span class="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 font-semibold border border-rose-500/30 text-[11px]">Chưa có</span>`;

        return `
            <tr class="hover:bg-slate-900/40 transition-all">
                <td class="p-4 flex items-center gap-3">
                    ${avatarHtml}
                    <div>
                        <div class="font-bold text-white">${emp.full_name}</div>
                        <div class="text-[11px] text-slate-400">${emp.email || emp.phone || 'Chưa có liên hệ'}</div>
                    </div>
                </td>
                <td class="p-4 font-mono font-bold text-slate-200">${emp.emp_code}</td>
                <td class="p-4 text-slate-300">${emp.department}</td>
                <td class="p-4 text-slate-400">${emp.position}</td>
                <td class="p-4 text-center">${faceBadge}</td>
                <td class="p-4 text-slate-400">${shiftName}</td>
                <td class="p-4 text-center">
                    <span class="px-2 py-0.5 rounded-full ${emp.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-700 text-slate-400'} text-[11px] font-medium">
                        ${emp.is_active ? 'Hoạt động' : 'Tạm dừng'}
                    </span>
                </td>
                <td class="p-4 text-right space-x-2">
                    <button onclick="openFaceModal(${emp.id}, '${emp.full_name}', '${emp.emp_code}')" class="px-2.5 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-semibold inline-flex items-center gap-1">
                        <i data-lucide="scan-face" class="w-3.5 h-3.5"></i> Face ID
                    </button>
                    <button onclick="editEmployee(${emp.id})" class="px-2 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs">
                        <i data-lucide="pencil" class="w-3.5 h-3.5"></i>
                    </button>
                    <button onclick="deleteEmployee(${emp.id}, '${emp.full_name}')" class="px-2 py-1.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 rounded-lg text-xs">
                        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join("");

    lucide.createIcons();
}

function filterEmployees() {
    const q = document.getElementById("search-emp").value.toLowerCase().trim();
    if (!q) {
        renderEmployeesTable(allEmployees);
        return;
    }
    const filtered = allEmployees.filter(e => 
        e.full_name.toLowerCase().includes(q) ||
        e.emp_code.toLowerCase().includes(q) ||
        e.department.toLowerCase().includes(q)
    );
    renderEmployeesTable(filtered);
}

// Biến lưu trữ mẫu khuôn mặt khi tạo mới / sửa nhân viên
let formCapturedFaces = [];
let formCameraStream = null;

// Khởi tạo camera trong form đăng ký nhân viên
async function initFormCamera() {
    stopFormCamera();
    const video = document.getElementById("form-camera-video");
    const statusEl = document.getElementById("form-cam-status");
    if (!video) return;

    try {
        statusEl.textContent = "Đang kết nối camera...";
        formCameraStream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 } }
        });
        video.srcObject = formCameraStream;
        statusEl.textContent = "Camera sẵn sàng";
    } catch (err) {
        console.warn("Không mở được camera trong form:", err);
        statusEl.textContent = "Không mở được camera (kiểm tra quyền)";
    }
}

function stopFormCamera() {
    if (formCameraStream) {
        formCameraStream.getTracks().forEach(t => t.stop());
        formCameraStream = null;
    }
}

// Chụp mẫu khuôn mặt từ video trong form
function captureFaceInForm() {
    const video = document.getElementById("form-camera-video");
    if (!video || !video.videoWidth) {
        alert("Camera chưa sẵn sàng, vui lòng đợi giây lát hoặc bật lại camera!");
        return;
    }

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const base64 = canvas.toDataURL("image/jpeg", 0.9);

    formCapturedFaces.push(base64);
    renderFormCapturedThumbnails();
}

// Tải ảnh khuôn mặt từ file trong form
function uploadFaceInForm(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        formCapturedFaces.push(e.target.result);
        renderFormCapturedThumbnails();
    };
    reader.readAsDataURL(file);
    event.target.value = ""; // Reset
}

function removeCapturedFace(idx) {
    formCapturedFaces.splice(idx, 1);
    renderFormCapturedThumbnails();
}

function renderFormCapturedThumbnails() {
    const container = document.getElementById("form-captured-thumbnails");
    const badge = document.getElementById("captured-faces-count");
    badge.textContent = `${formCapturedFaces.length} mẫu mặt`;

    if (formCapturedFaces.length === 0) {
        container.innerHTML = `<span class="text-[11px] text-slate-500 italic px-2">Chưa chụp ảnh nào. Bấm nút "Chụp Mẫu Khuôn Mặt" ở trên.</span>`;
        return;
    }

    container.innerHTML = formCapturedFaces.map((imgSrc, idx) => `
        <div class="relative flex-shrink-0 w-12 h-12 rounded-xl overflow-hidden border-2 border-emerald-500 group">
            <img src="${imgSrc}" class="w-full h-full object-cover">
            <button type="button" onclick="removeCapturedFace(${idx})" class="absolute inset-0 bg-rose-600/80 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <i data-lucide="trash" class="w-3.5 h-3.5"></i>
            </button>
        </div>
    `).join("");

    lucide.createIcons();
}

// Open/Close Modal
function openAddEmployeeModal() {
    document.getElementById("modal-emp-title").textContent = "Đăng Ký Nhân Viên & Quét Mặt Face ID";
    document.getElementById("emp-edit-id").value = "";
    
    // Tự sinh mã NV kế tiếp (vd NV001, NV002, ...)
    const nextNum = allEmployees.length + 1;
    const defaultCode = "NV" + String(nextNum).padStart(3, "0");
    document.getElementById("emp-code").value = defaultCode;
    document.getElementById("emp-code").disabled = false;
    document.getElementById("emp-name").value = "";
    document.getElementById("emp-dept").value = "";
    document.getElementById("emp-position").value = "";
    document.getElementById("emp-phone").value = "";
    document.getElementById("emp-email").value = "";
    
    // Reset danh sách mẫu mặt đã chụp
    formCapturedFaces = [];
    renderFormCapturedThumbnails();

    populateShiftSelect();
    document.getElementById("modal-employee").classList.remove("hidden");
    initFormCamera();
    lucide.createIcons();
}

function editEmployee(empId) {
    const emp = allEmployees.find(e => e.id === empId);
    if (!emp) return;

    document.getElementById("modal-emp-title").textContent = "Chỉnh Sửa Nhân Viên & Cập Nhật Face ID";
    document.getElementById("emp-edit-id").value = emp.id;
    document.getElementById("emp-code").value = emp.emp_code;
    document.getElementById("emp-code").disabled = true;
    document.getElementById("emp-name").value = emp.full_name;
    document.getElementById("emp-dept").value = emp.department;
    document.getElementById("emp-position").value = emp.position;
    document.getElementById("emp-phone").value = emp.phone || "";
    document.getElementById("emp-email").value = emp.email || "";

    formCapturedFaces = [];
    renderFormCapturedThumbnails();

    populateShiftSelect(emp.shift ? emp.shift.id : null);
    document.getElementById("modal-employee").classList.remove("hidden");
    initFormCamera();
    lucide.createIcons();
}

function closeModal(id) {
    if (id === "modal-employee") {
        stopFormCamera();
    }
    document.getElementById(id).classList.add("hidden");
}

async function populateShiftSelect(selectedId = null) {
    const select = document.getElementById("emp-shift-select");
    if (allShifts.length === 0) {
        const res = await fetch("/api/shifts");
        if (res.ok) allShifts = await res.json();
    }
    select.innerHTML = allShifts.map(s => `
        <option value="${s.id}" ${selectedId === s.id ? 'selected' : ''}>${s.name} (${s.start_time} - ${s.end_time})</option>
    `).join("");
}

// Lưu nhân viên và đồng thời nạp các mẫu Face ID đã chụp
async function saveEmployeeWithFace(e) {
    e.preventDefault();
    const editId = document.getElementById("emp-edit-id").value;
    const empName = document.getElementById("emp-name").value.trim();

    // Cảnh báo nếu chưa chụp ảnh mặt cho nhân viên mới
    if (!editId && formCapturedFaces.length === 0) {
        const confirmNoFace = confirm(`Chú ý: Bạn chưa chụp mẫu khuôn mặt Face ID cho "${empName}". Nhân viên sẽ chưa thể điểm danh tại Kiosk.\n\nBạn có muốn bấm Hủy để quay lại chụp mặt không? Bấm OK nếu muốn tiếp tục lưu không kèm Face ID.`);
        if (!confirmNoFace) return;
    }

    const payload = {
        emp_code: document.getElementById("emp-code").value.trim(),
        full_name: empName,
        department: document.getElementById("emp-dept").value.trim() || "Văn Phòng",
        position: document.getElementById("emp-position").value.trim() || "Nhân viên",
        phone: document.getElementById("emp-phone").value.trim() || null,
        email: document.getElementById("emp-email").value.trim() || null,
        shift_id: parseInt(document.getElementById("emp-shift-select").value) || null
    };

    const saveBtn = document.getElementById("btn-save-emp-main");
    saveBtn.disabled = true;
    saveBtn.innerHTML = `<span>Đang lưu thông tin & Face ID...</span>`;

    try {
        let empRes;
        if (editId) {
            empRes = await fetch(`/api/employees/${editId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
        } else {
            empRes = await fetch("/api/employees", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
        }

        if (!empRes.ok) {
            const err = await empRes.json();
            alert("Lỗi: " + (err.detail || "Không thể lưu nhân viên"));
            return;
        }

        const savedEmp = await empRes.json();
        const targetId = savedEmp.id;

        // Nếu có các mẫu mặt vừa chụp, nạp lần lượt vào Face Engine
        let successFaces = 0;
        let failFaces = 0;

        for (const faceBase64 of formCapturedFaces) {
            try {
                const faceRes = await fetch(`/api/employees/${targetId}/faces/capture`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ image_base64: faceBase64 })
                });
                if (faceRes.ok) {
                    successFaces++;
                } else {
                    failFaces++;
                }
            } catch (err) {
                failFaces++;
            }
        }

        let msg = `Đã lưu thành công nhân viên: ${savedEmp.full_name} (${savedEmp.emp_code})!`;
        if (successFaces > 0) {
            msg += `\nĐã nạp thành công ${successFaces} mẫu khuôn mặt vào hệ thống Face ID. Nhân viên có thể chấm công ngay tại Kiosk!`;
        }
        if (failFaces > 0) {
            msg += `\n(Có ${failFaces} ảnh không nhận diện rõ khuôn mặt)`;
        }

        alert(msg);
        closeModal("modal-employee");
        loadEmployees();
        loadDashboardStats();

    } catch (err) {
        console.error(err);
        alert("Lỗi kết nối máy chủ");
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = `<i data-lucide="check-circle" class="w-4 h-4"></i><span>Lưu & Hoàn Tất Đăng Ký</span>`;
        lucide.createIcons();
    }
}

async function deleteEmployee(id, name) {
    if (!confirm(`Bạn có chắc chắn muốn xóa nhân viên "${name}" cùng toàn bộ dữ liệu Face ID liên quan?`)) return;
    try {
        const res = await fetch(`/api/employees/${id}`, { method: "DELETE" });
        if (res.ok) {
            loadEmployees();
            loadDashboardStats();
        } else {
            alert("Không thể xóa nhân viên");
        }
    } catch (e) {
        alert("Lỗi kết nối");
    }
}

// -------------------------------------------------------------
// MODAL: ĐĂNG KÝ MẪU KHUÔN MẶT (FACE ID)
// -------------------------------------------------------------
function openFaceModal(empId, empName, empCode) {
    currentEmpForFace = { id: empId, name: empName, code: empCode };
    document.getElementById("face-modal-emp-info").textContent = `Nhân viên: ${empName} (Mã NV: ${empCode})`;
    document.getElementById("modal-face-register").classList.remove("hidden");
    
    switchFaceMode("webcam");
    loadExistingFaceSamples(empId);
    lucide.createIcons();
}

function closeFaceModal() {
    stopRegCamera();
    document.getElementById("modal-face-register").classList.add("hidden");
    loadEmployees(); // Reload list to update sample count
}

function switchFaceMode(mode) {
    const camBtn = document.getElementById("btn-face-tab-cam");
    const uploadBtn = document.getElementById("btn-face-tab-upload");
    const camSection = document.getElementById("face-section-webcam");
    const uploadSection = document.getElementById("face-section-upload");

    if (mode === "webcam") {
        camBtn.className = "flex-1 py-1.5 rounded-lg font-semibold bg-emerald-600 text-white flex items-center justify-center gap-1.5";
        uploadBtn.className = "flex-1 py-1.5 rounded-lg font-semibold text-slate-400 hover:text-white flex items-center justify-center gap-1.5";
        camSection.classList.remove("hidden");
        uploadSection.classList.add("hidden");
        initRegCamera();
    } else {
        uploadBtn.className = "flex-1 py-1.5 rounded-lg font-semibold bg-emerald-600 text-white flex items-center justify-center gap-1.5";
        camBtn.className = "flex-1 py-1.5 rounded-lg font-semibold text-slate-400 hover:text-white flex items-center justify-center gap-1.5";
        uploadSection.classList.remove("hidden");
        camSection.classList.add("hidden");
        stopRegCamera();
    }
}

async function initRegCamera() {
    try {
        stopRegCamera();
        const video = document.getElementById("reg-video");
        regVideoStream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 } }
        });
        video.srcObject = regVideoStream;
    } catch (e) {
        console.error("Lỗi mở camera đăng ký", e);
        alert("Không thể truy cập camera. Vui lòng kiểm tra quyền trình duyệt!");
    }
}

function stopRegCamera() {
    if (regVideoStream) {
        regVideoStream.getTracks().forEach(track => track.stop());
        regVideoStream = null;
    }
}

async function captureFaceFromWebcam() {
    if (!currentEmpForFace) return;
    const video = document.getElementById("reg-video");
    if (!video.videoWidth) {
        alert("Camera chưa sẵn sàng, vui lòng đợi giây lát!");
        return;
    }

    const btn = document.getElementById("btn-capture-face");
    btn.disabled = true;
    btn.textContent = "Đang trích xuất...";

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const base64 = canvas.toDataURL("image/jpeg", 0.9);

    try {
        const res = await fetch(`/api/employees/${currentEmpForFace.id}/faces/capture`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image_base64: base64 })
        });

        const data = await res.json();
        if (res.ok) {
            alert("Thành công: " + data.message);
            loadExistingFaceSamples(currentEmpForFace.id);
        } else {
            alert("Lỗi: " + (data.detail || "Không thể đăng ký mẫu khuôn mặt"));
        }
    } catch (e) {
        alert("Lỗi gửi dữ liệu lên máy chủ");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="camera" class="w-4 h-4"></i> Chụp Mẫu Khuôn Mặt`;
        lucide.createIcons();
    }
}

async function uploadFaceFile(event) {
    if (!currentEmpForFace) return;
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`/api/employees/${currentEmpForFace.id}/faces/upload`, {
            method: "POST",
            body: formData
        });

        const data = await res.json();
        if (res.ok) {
            alert("Thành công: " + data.message);
            loadExistingFaceSamples(currentEmpForFace.id);
        } else {
            alert("Lỗi: " + (data.detail || "Không thể trích xuất khuôn mặt từ file ảnh"));
        }
    } catch (e) {
        alert("Lỗi tải ảnh lên");
    }
}

async function loadExistingFaceSamples(empId) {
    const grid = document.getElementById("face-samples-grid");
    grid.innerHTML = '<span class="text-xs text-slate-500">Đang tải...</span>';
    
    // Refresh employee data to get face samples
    await loadEmployees();
    const emp = allEmployees.find(e => e.id === empId);
    if (!emp) return;

    if (emp.face_count === 0) {
        grid.innerHTML = '<span class="text-xs text-slate-500">Chưa có mẫu khuôn mặt nào được lưu. Hãy chụp ảnh đầu tiên!</span>';
        return;
    }

    grid.innerHTML = `
        <div class="flex items-center gap-3">
            ${emp.avatar_path ? `<img src="${emp.avatar_path}" class="w-14 h-14 rounded-xl object-cover border border-emerald-500">` : ''}
            <span class="text-xs text-emerald-400 font-semibold">Đã lưu ${emp.face_count} mẫu đặc trưng khuôn mặt</span>
        </div>
    `;
}

// -------------------------------------------------------------
// TAB 3: CHẤM CÔNG HÔM NAY
// -------------------------------------------------------------
async function loadTodayTable() {
    try {
        const res = await fetch("/api/attendance/today");
        if (!res.ok) return;
        const records = await res.json();
        const tbody = document.getElementById("today-tbody");

        if (records.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center py-10 text-slate-500">Hôm nay chưa có lượt điểm danh nào</td></tr>`;
            return;
        }

        tbody.innerHTML = records.map(r => {
            const avatarSrc = r.avatar_path || (r.check_in_image || "");
            const avatarHtml = avatarSrc
                ? `<img src="${avatarSrc}" class="w-8 h-8 rounded-full object-cover border border-slate-700">`
                : `<div class="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-slate-300">${r.full_name.charAt(0)}</div>`;

            let statusBadge = `<span class="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[11px] font-medium">Đúng giờ</span>`;
            if (r.late_minutes > 0) {
                statusBadge = `<span class="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 text-[11px] font-medium">Muộn ${r.late_minutes}p</span>`;
            }

            const snapshotHtml = r.check_in_image
                ? `<a href="${r.check_in_image}" target="_blank"><img src="${r.check_in_image}" class="w-9 h-9 rounded-lg object-cover mx-auto border border-slate-700 hover:border-emerald-500 transition-all"></a>`
                : `<span class="text-slate-600">--</span>`;

            return `
                <tr class="hover:bg-slate-900/40">
                    <td class="p-4 flex items-center gap-3">
                        ${avatarHtml}
                        <span class="font-bold text-white">${r.full_name}</span>
                    </td>
                    <td class="p-4 font-mono text-slate-300 font-bold">${r.emp_code}</td>
                    <td class="p-4 text-slate-300">${r.department}</td>
                    <td class="p-4 text-center font-mono font-bold text-emerald-400">${r.check_in_time || '--:--'}</td>
                    <td class="p-4 text-center font-mono font-bold text-blue-400">${r.check_out_time || '--:--'}</td>
                    <td class="p-4 text-center font-mono text-slate-200">${r.work_hours ? r.work_hours + 'h' : '--'}</td>
                    <td class="p-4 text-center">${statusBadge}</td>
                    <td class="p-4 text-center">${snapshotHtml}</td>
                </tr>
            `;
        }).join("");
    } catch (e) {
        console.error("Lỗi load today table", e);
    }
}

// -------------------------------------------------------------
// TAB 4: BÁO CÁO & XUẤT EXCEL
// -------------------------------------------------------------
function initReportsTab() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById("rep-from-date").value = today;
    document.getElementById("rep-to-date").value = today;
    queryReports();
}

function updateDeptSelect() {
    const deptSelect = document.getElementById("rep-dept");
    const depts = Array.from(new Set(allEmployees.map(e => e.department))).filter(Boolean);
    deptSelect.innerHTML = `<option value="ALL">Tất cả phòng ban</option>` + depts.map(d => `<option value="${d}">${d}</option>`).join("");
}

async function queryReports() {
    const fromDate = document.getElementById("rep-from-date").value;
    const toDate = document.getElementById("rep-to-date").value;
    const dept = document.getElementById("rep-dept").value;

    const params = new URLSearchParams();
    if (fromDate) params.append("from_date", fromDate);
    if (toDate) params.append("to_date", toDate);
    if (dept && dept !== "ALL") params.append("department", dept);

    try {
        const res = await fetch(`/api/attendance/records?${params.toString()}`);
        if (!res.ok) return;
        const records = await res.json();
        const tbody = document.getElementById("report-tbody");

        if (records.length === 0) {
            tbody.innerHTML = `<tr><td colspan="10" class="text-center py-10 text-slate-500">Không có bản ghi nào phù hợp với bộ lọc</td></tr>`;
            return;
        }

        tbody.innerHTML = records.map(r => `
            <tr class="hover:bg-slate-900/40">
                <td class="p-4 font-mono text-slate-300">${r.record_date}</td>
                <td class="p-4 font-mono font-bold text-white">${r.emp_code}</td>
                <td class="p-4 font-semibold text-slate-200">${r.full_name}</td>
                <td class="p-4 text-slate-400">${r.department}</td>
                <td class="p-4 text-center font-mono text-emerald-400 font-bold">${r.check_in_time}</td>
                <td class="p-4 text-center font-mono text-blue-400 font-bold">${r.check_out_time}</td>
                <td class="p-4 text-center font-mono text-slate-200">${r.work_hours}h</td>
                <td class="p-4 text-center ${r.late_minutes > 0 ? 'text-amber-400 font-bold' : 'text-slate-500'}">${r.late_minutes}p</td>
                <td class="p-4 text-center ${r.early_minutes > 0 ? 'text-rose-400 font-bold' : 'text-slate-500'}">${r.early_minutes}p</td>
                <td class="p-4 text-center font-semibold ${r.late_minutes > 0 ? 'text-amber-400' : 'text-emerald-400'}">${r.status}</td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("Lỗi tải báo cáo", e);
    }
}

function exportExcelReport() {
    const fromDate = document.getElementById("rep-from-date").value;
    const toDate = document.getElementById("rep-to-date").value;
    const dept = document.getElementById("rep-dept").value;

    const params = new URLSearchParams();
    if (fromDate) params.append("from_date", fromDate);
    if (toDate) params.append("to_date", toDate);
    if (dept && dept !== "ALL") params.append("department", dept);

    window.location.href = `/api/attendance/export?${params.toString()}`;
}

// -------------------------------------------------------------
// TAB 5: CA LÀM VIỆC
// -------------------------------------------------------------
async function loadShifts() {
    try {
        const res = await fetch("/api/shifts");
        if (!res.ok) return;
        allShifts = await res.json();
        const tbody = document.getElementById("shifts-tbody");

        tbody.innerHTML = allShifts.map(s => `
            <tr class="hover:bg-slate-900/40">
                <td class="p-4 font-bold text-white">${s.name}</td>
                <td class="p-4 text-center font-mono text-emerald-400">${s.start_time}</td>
                <td class="p-4 text-center font-mono text-blue-400">${s.end_time}</td>
                <td class="p-4 text-center text-slate-300">${s.grace_period_minutes} phút</td>
                <td class="p-4 text-center font-bold text-slate-200">${s.work_hours}h</td>
                <td class="p-4 text-right">
                    <span class="text-xs text-slate-500 italic">Mặc định hệ thống</span>
                </td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("Lỗi load shifts", e);
    }
}

function openAddShiftModal() {
    const name = prompt("Nhập tên ca làm việc:", "Ca Sáng");
    if (!name) return;
    const start = prompt("Giờ bắt đầu (HH:MM):", "08:00");
    const end = prompt("Giờ kết thúc (HH:MM):", "17:00");
    const grace = prompt("Số phút cho phép đi trễ:", "15");

    fetch("/api/shifts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: name,
            start_time: start,
            end_time: end,
            grace_period_minutes: parseInt(grace) || 15,
            work_hours: 8.0
        })
    }).then(r => {
        if (r.ok) loadShifts();
    });
}

// Init
window.addEventListener("DOMContentLoaded", () => {
    loadDashboardStats();
    loadEmployees();
    lucide.createIcons();
});
