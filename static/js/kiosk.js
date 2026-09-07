// Kiosk Face ID Attendance Controller
let currentMode = "AUTO"; // AUTO, CHECK_IN, CHECK_OUT
let video = document.getElementById("webcam");
let overlay = document.getElementById("overlay");
let ctx = overlay.getContext("2d");
let cameraSelect = document.getElementById("camera-select");
let isProcessing = false;
let audioCtx = null;
let lastAnnouncedName = "";
let lastAnnounceTime = 0;

// Initialize Web Audio API on first user interaction
function getAudioContext() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    return audioCtx;
}

// Chime sound generator (pleasant success beep)
function playSuccessChime() {
    try {
        const ctx = getAudioContext();
        const now = ctx.currentTime;
        
        // Tone 1
        const osc1 = ctx.createOscillator();
        const gain1 = ctx.createGain();
        osc1.type = "sine";
        osc1.frequency.setValueAtTime(587.33, now); // D5
        gain1.gain.setValueAtTime(0.15, now);
        gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
        osc1.connect(gain1);
        gain1.connect(ctx.destination);
        osc1.start(now);
        osc1.stop(now + 0.3);

        // Tone 2 (Higher)
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.type = "sine";
        osc2.frequency.setValueAtTime(880, now + 0.12); // A5
        gain2.gain.setValueAtTime(0.2, now + 0.12);
        gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        osc2.start(now + 0.12);
        osc2.stop(now + 0.45);
    } catch (e) {
        console.warn("Audio chime error:", e);
    }
}

// Update live clock
function updateClock() {
    const now = new Date();
    const days = ["Chủ Nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];
    const dStr = days[now.getDay()];
    const dateStr = `${dStr}, ${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;
    const timeStr = now.toTimeString().split(' ')[0];

    document.getElementById("live-clock").textContent = timeStr;
    document.getElementById("live-date").textContent = dateStr;
}
setInterval(updateClock, 1000);
updateClock();

// Mode Switcher
function setMode(mode) {
    currentMode = mode;
    const btnAuto = document.getElementById("btn-mode-auto");
    const btnIn = document.getElementById("btn-mode-in");
    const btnOut = document.getElementById("btn-mode-out");

    [btnAuto, btnIn, btnOut].forEach(btn => {
        btn.className = "px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all text-slate-400 hover:text-white";
    });

    if (mode === "AUTO") {
        btnAuto.className = "px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all bg-emerald-600 text-white shadow-lg shadow-emerald-600/30";
    } else if (mode === "CHECK_IN") {
        btnIn.className = "px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all bg-blue-600 text-white shadow-lg shadow-blue-600/30";
    } else if (mode === "CHECK_OUT") {
        btnOut.className = "px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all bg-amber-600 text-white shadow-lg shadow-amber-600/30";
    }
}

// Camera initialization
async function initCamera(deviceId = null) {
    try {
        const constraints = {
            video: deviceId ? { deviceId: { exact: deviceId } } : { width: { ideal: 1280 }, height: { ideal: 720 } },
            audio: false
        };

        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = stream;
        
        video.onloadedmetadata = () => {
            overlay.width = video.videoWidth;
            overlay.height = video.videoHeight;
            document.getElementById("cam-status").textContent = "Camera sẵn sàng";
            document.getElementById("cam-dot").className = "w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse";
            startRecognitionLoop();
        };

        populateCameraList();
    } catch (err) {
        console.error("Camera access error:", err);
        document.getElementById("cam-status").textContent = "Không thể mở camera (" + err.name + ")";
        document.getElementById("cam-dot").className = "w-2.5 h-2.5 rounded-full bg-red-500";
    }
}

async function populateCameraList() {
    try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(d => d.kind === 'videoinput');
        
        cameraSelect.innerHTML = '<option value="">Đổi Camera...</option>';
        videoDevices.forEach((dev, idx) => {
            const opt = document.createElement("option");
            opt.value = dev.deviceId;
            opt.textContent = dev.label || `Camera ${idx + 1}`;
            cameraSelect.appendChild(opt);
        });

        cameraSelect.onchange = (e) => {
            if (e.target.value) {
                initCamera(e.target.value);
            }
        };
    } catch (e) {
        console.warn("Could not list video devices", e);
    }
}

// Main Frame Capture & AI Recognition Loop
let offscreenCanvas = document.createElement("canvas");
let offscreenCtx = offscreenCanvas.getContext("2d");

async function captureAndRecognize() {
    if (isProcessing || video.paused || video.ended || !video.videoWidth) {
        return;
    }

    isProcessing = true;

    try {
        // Render frame to offscreen canvas
        // Scale down to 640px width for fast network & processing speed
        const scale = Math.min(1.0, 640 / video.videoWidth);
        const w = Math.round(video.videoWidth * scale);
        const h = Math.round(video.videoHeight * scale);

        offscreenCanvas.width = w;
        offscreenCanvas.height = h;
        offscreenCtx.drawImage(video, 0, 0, w, h);

        const base64Image = offscreenCanvas.toDataURL("image/jpeg", 0.85);

        const response = await fetch("/api/face/recognize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                image: base64Image,
                mode: currentMode
            })
        });

        if (response.ok) {
            const data = await response.json();
            drawOverlays(data.results || [], scale);
            handleAttendanceResults(data.results || []);
        }
    } catch (err) {
        console.warn("Recognition loop error:", err);
    } finally {
        isProcessing = false;
    }
}

// Draw futuristic bounding box on overlay canvas
function drawOverlays(results, scale) {
    ctx.clearRect(0, 0, overlay.width, overlay.height);

    results.forEach(res => {
        // Rescale bbox back to video resolution
        const [x, y, bw, bh] = res.bbox.map(v => v / scale);
        const isMatched = res.matched;
        const color = isMatched ? "#22c55e" : "#eab308";

        // Draw outer corner brackets
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        const cornerLen = Math.min(24, bw * 0.25);

        // Top-Left
        ctx.beginPath();
        ctx.moveTo(x, y + cornerLen);
        ctx.lineTo(x, y);
        ctx.lineTo(x + cornerLen, y);
        ctx.stroke();

        // Top-Right
        ctx.beginPath();
        ctx.moveTo(x + bw - cornerLen, y);
        ctx.lineTo(x + bw, y);
        ctx.lineTo(x + bw, y + cornerLen);
        ctx.stroke();

        // Bottom-Left
        ctx.beginPath();
        ctx.moveTo(x, y + bh - cornerLen);
        ctx.lineTo(x, y + bh);
        ctx.lineTo(x + cornerLen, y + bh);
        ctx.stroke();

        // Bottom-Right
        ctx.beginPath();
        ctx.moveTo(x + bw - cornerLen, y + bh);
        ctx.lineTo(x + bw, y + bh);
        ctx.lineTo(x + bw, y + bh - cornerLen);
        ctx.stroke();

        // Draw soft filled rectangle
        ctx.fillStyle = isMatched ? "rgba(34, 197, 94, 0.12)" : "rgba(234, 179, 8, 0.08)";
        ctx.fillRect(x, y, bw, bh);

        // Label above face
        const label = isMatched ? `${res.full_name} (${res.emp_code})` : "Chưa nhận diện";
        ctx.font = "bold 16px sans-serif";
        const textMetrics = ctx.measureText(label);
        
        ctx.fillStyle = isMatched ? "rgba(22, 101, 52, 0.85)" : "rgba(113, 63, 18, 0.85)";
        ctx.beginPath();
        ctx.roundRect(x, y - 32, textMetrics.width + 16, 26, 6);
        ctx.fill();

        ctx.fillStyle = "#ffffff";
        ctx.fillText(label, x + 8, y - 14);
    });
}

// Handle Attendance Notification & Voice/Chime
let hideResultTimeout = null;

function handleAttendanceResults(results) {
    results.forEach(res => {
        if (res.matched && res.attendance) {
            const att = res.attendance;
            const nowTime = Date.now();

            // Show card if not announced recently
            if (lastAnnouncedName !== att.full_name || (nowTime - lastAnnounceTime > 5000)) {
                lastAnnouncedName = att.full_name;
                lastAnnounceTime = nowTime;

                if (!att.is_cooldown) {
                    playSuccessChime();
                    loadTodayLogs();
                    loadStats();
                }

                showResultCard(att);
            }
        }
    });
}

function showResultCard(att) {
    const card = document.getElementById("result-card");
    const avatar = document.getElementById("result-avatar");
    const avatarIcon = document.getElementById("result-avatar-icon");
    const nameEl = document.getElementById("result-name");
    const badgeEl = document.getElementById("result-badge");
    const metaEl = document.getElementById("result-meta");
    const msgEl = document.getElementById("result-msg");

    nameEl.textContent = att.full_name;
    metaEl.textContent = `Mã NV: ${att.emp_code} • ${att.department} • Lúc ${att.timestamp}`;
    msgEl.textContent = att.message;

    if (att.avatar_path) {
        avatar.src = att.avatar_path;
        avatar.classList.remove("hidden");
        avatarIcon.classList.add("hidden");
    } else {
        avatar.classList.add("hidden");
        avatarIcon.classList.remove("hidden");
    }

    // Badge styling
    if (att.action === "CHECK_IN") {
        if (att.status === "LATE") {
            badgeEl.textContent = `Đi muộn ${att.late_minutes}p`;
            badgeEl.className = "px-2.5 py-0.5 rounded-md text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30";
        } else {
            badgeEl.textContent = "Check-in Đúng Giờ";
            badgeEl.className = "px-2.5 py-0.5 rounded-md text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
        }
    } else if (att.action === "CHECK_OUT") {
        badgeEl.textContent = `Check-out (${att.work_hours || 0}h)`;
        badgeEl.className = "px-2.5 py-0.5 rounded-md text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30";
    } else if (att.is_cooldown) {
        badgeEl.textContent = "Đã ghi nhận";
        badgeEl.className = "px-2.5 py-0.5 rounded-md text-xs font-bold bg-slate-500/20 text-slate-300 border border-slate-500/30";
    }

    card.classList.remove("opacity-0", "translate-y-4", "pointer-events-none");
    card.classList.add("opacity-100", "translate-y-0", "pulse-box");

    clearTimeout(hideResultTimeout);
    hideResultTimeout = setTimeout(() => {
        card.classList.add("opacity-0", "translate-y-4", "pointer-events-none");
        card.classList.remove("opacity-100", "translate-y-0", "pulse-box");
        ctx.clearRect(0, 0, overlay.width, overlay.height);
    }, 4500);
}

// Load today's attendance logs
async function loadTodayLogs() {
    try {
        const res = await fetch("/api/attendance/today");
        if (!res.ok) return;
        const logs = await res.json();
        
        const listEl = document.getElementById("recent-logs-list");
        const badgeEl = document.getElementById("log-count-badge");
        badgeEl.textContent = `${logs.length} lượt`;

        if (logs.length === 0) {
            listEl.innerHTML = `
                <div class="text-center py-10 text-slate-500">
                    <p>Chưa có lượt điểm danh nào hôm nay</p>
                </div>
            `;
            return;
        }

        listEl.innerHTML = logs.map(l => {
            const isLate = l.late_minutes > 0;
            const statusBadge = isLate 
                ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 font-medium">Muộn ${l.late_minutes}p</span>`
                : `<span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-medium">Đúng giờ</span>`;

            const avatarSrc = l.avatar_path || (l.check_in_image || "");
            const avatarHtml = avatarSrc
                ? `<img src="${avatarSrc}" class="w-8 h-8 rounded-full object-cover border border-slate-700">`
                : `<div class="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-slate-300">${l.full_name.charAt(0)}</div>`;

            return `
                <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-800/40 border border-slate-800/60 hover:border-slate-700 transition-all">
                    <div class="flex items-center gap-2.5">
                        ${avatarHtml}
                        <div>
                            <div class="font-semibold text-slate-200 text-xs">${l.full_name}</div>
                            <div class="text-[11px] text-slate-400">${l.emp_code} • ${l.department}</div>
                        </div>
                    </div>
                    <div class="text-right">
                        <div class="font-mono text-emerald-400 font-bold text-xs">Vào: ${l.check_in_time || '--:--'}</div>
                        <div class="text-[11px] text-slate-400">${l.check_out_time ? 'Ra: ' + l.check_out_time : statusBadge}</div>
                    </div>
                </div>
            `;
        }).join("");

    } catch (e) {
        console.warn("Could not load today logs", e);
    }
}

// Load statistics
async function loadStats() {
    try {
        const res = await fetch("/api/attendance/stats");
        if (!res.ok) return;
        const stats = await res.json();
        document.getElementById("stat-checked-in").textContent = stats.checked_in;
        document.getElementById("stat-late").textContent = stats.late;
    } catch (e) {
        console.warn("Could not load stats", e);
    }
}

function startRecognitionLoop() {
    setInterval(captureAndRecognize, 650);
}

// Kick off
window.addEventListener("DOMContentLoaded", () => {
    initCamera();
    loadTodayLogs();
    loadStats();
    setInterval(loadTodayLogs, 15000);
    setInterval(loadStats, 15000);
    lucide.createIcons();
});
