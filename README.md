# Smart Classroom 🎓

Hệ thống giám sát lớp học bằng AI và điều khiển bài giảng bằng cử chỉ tay.

## 📋 Tính năng

| Chế độ | Mô tả | Camera |
|-------|-------|--------|
| **Trong giờ học** (07:00 – 17:00) | Điều khiển slide PowerPoint bằng cử chỉ tay | MediaPipe nhận diện bàn tay |
| **Ngoài giờ học** | Giám sát lớp học, cảnh báo nếu còn người | YOLO đếm người |

- ✅ Tự chuyển chế độ theo đồng hồ mô phỏng (hỗ trợ tốc độ 10x, 60x, 300x)
- ✅ Không cần webcam: camera mô phỏng (vẽ lớp học)
- ✅ Thông báo qua Telegram (tuỳ chọn)
- ✅ Ghi nhật ký sự kiện chi tiết

---

## 🚀 Setup (Windows)

### 1️⃣ Yêu cầu
- **Windows 10/11**
- **Python 3.10, 3.11, hoặc 3.12**
  - ⚠️ **Không dùng Python 3.13** (MediaPipe chưa hỗ trợ)

### 2️⃣ Cài đặt

**Tùy chọn A: Dùng `setup.bat` (tự động)**
```bat
# Chỉ cần double-click file setup.bat
# Hoặc chạy từ terminal:
setup.bat
```

**Tùy chọn B: Cài tay**
```bash
# Tạo virtual environment
python -m venv venv

# Kích hoạt venv
venv\Scripts\activate

# Cài dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3️⃣ Chạy ứng dụng

**Từ PyCharm:**
- Mở `Smart_Classroom_03\main.py` → Click **Run** ▶

**Từ terminal:**
```bash
cd Smart_Classroom_03
python main.py
```

**Windows Explorer:**
- Double-click `Smart_Classroom_03\run.bat`

---

## 🎮 Hướng dẫn sử dụng

### Kịch bản trình diễn (~2 phút)

1. **Mở ứng dụng** (16:55, tốc độ 10×)
   - Giao diện Trong giờ học (màu xanh)

2. **Mở PowerPoint**, mở bài thuyết trình
   - **Nắm tay 1 giây** → bắt đầu trình chiếu
   - **Vuốt tay sang trái** → slide tiếp
   - **Vuốt tay sang phải** → slide trước

3. **Khoảng 6 giây sau 17:00**
   - Giao diện tự chuyển sang **Giám sát ngoài giờ** (màu cam)
   - YOLO phát hiện người → cảnh báo

4. **Khi không còn ai trong lớp**
   - Trạng thái **Lớp học an toàn** ✅

### ⌨️ Phím tắt

| Phím | Chức năng |
|------|----------|
| `Space` | Chạy / tạm dừng |
| `1` / `2` / `3` | Mốc Trong tiết / Sắp kết thúc / Ngoài giờ |
| `←` / `→` | Slide trước / tiếp |
| `F11` | Toàn màn hình |
| `Ctrl+,` | Cài đặt |

### 🖐️ Cử chỉ tay (Trong giờ)

| Cử chỉ | Lệnh |
|-------|------|
| Vuốt mở **sang trái** | Slide tiếp |
| Vuốt mở **sang phải** | Slide trước |
| **Nắm tay** giữ 1s | Bắt đầu / dừng trình chiếu |
| **1 ngón trỏ** | Slide tiếp (dự phòng) |
| **2 ngón** (V) | Slide trước (dự phòng) |

---

## ⚙️ Cài đặt

Nhấp biểu tượng ⚙ trong ứng dụng:

### Lớp học
- Tên lớp, tên GVCN
- Giờ vào học, giờ tan học

### Camera & AI
- **Nguồn camera:** Tự động / Webcam / Mô phỏng
- **Số camera:** 0, 1, 2, ... (nếu có nhiều camera)
- **Thời gian chờ:** Phút mô phỏng trước khi cảnh báo (mặc định 3 phút)
- **Chu kỳ quét YOLO:** Giây thực (mặc định 0.5s)
- **Ngưỡng tin cậy YOLO:** 0–1 (mặc định 0.45)

### Trình chiếu & Thông báo
- **Backend PowerPoint:** COM (khuyến nghị) / Phím
- **Chiều vuốt:** Trái = Next hay Prev
- **Telegram Bot:** Token + Chat ID (tuỳ chọn)

**Cài đặt lưu ở** `Smart_Classroom_03/config.json`

---

## 📁 Cấu trúc

```
Smart_Classroom_03/
├── main.py                    # Chạy ứng dụng
├── run.bat                    # Quick start (Windows)
├── config.json               # Cài đặt (tự tạo)
├── requirements.txt
│
├── core/
│   ├── config.py             # Quản lý cấu hình
│   ├── time_controller.py    # Đồng hồ mô phỏng + chế độ
│   └── event_log.py          # Ghi nhật ký
│
├── modules/
│   ├── camera/
│   │   ├── camera_worker.py  # Thread camera (QThread)
│   │   └── sim_scene.py      # Camera mô phỏng
│   │
│   ├── classroom_monitor/
│   │   ├── person_detector.py    # YOLO
│   │   └── after_school_monitor.py # State machine cảnh báo
│   │
│   ├── gesture_control/
│   │   ├── gesture_module.py  # MediaPipe gesture
│   │   └── ppt_controller.py  # Điều khiển PowerPoint
│   │
│   └── notify/
│       └── notifier.py        # Telegram / Log / Sound
│
├── ui/
│   ├── dashboard.py          # Cửa sổ chính
│   ├── panels.py             # Panel Trình chiếu / Giám sát
│   ├── widgets.py            # Widgets camera, timeline
│   ├── dialogs.py            # Dialog Cài đặt, Logs
│   ├── theme.py              # Màu sắc, font
│   └── icons.py              # Icons vector
│
├── models/
│   └── yolov8n.pt (tuỳ chọn)
│
└── logs/
    ├── events_YYYYMMDD.log
    └── alerts.log
```

---

## 🔧 Khắc phục sự cố

| Lỗi | Giải pháp |
|-----|----------|
| `ImportError: No module named 'cv2'` | `pip install --upgrade opencv-contrib-python==4.10.0.84` |
| MediaPipe API không tìm thấy | Đảm bảo `mediapipe==0.10.21` + Python 3.10–3.12 |
| Webcam không mở | Đóng Zoom/Teams; đổi "Số camera" (0, 1, 2...) |
| Slide không chuyển | Kiểm tra dòng "Kết nối slide" = **PowerPoint COM** |
| YOLO tải chậm | Chép `yolov8n.pt` vào thư mục `models/` |
| Máy giật | Tăng "Chu kỳ quét YOLO" lên 1–2 giây |

---

## 📝 Triển khai Raspberry Pi 4

Xem hướng dẫn riêng: `RASPBERRY_PI.md` (sắp có)

**Cách chung:**
- Sử dụng FastAPI backend (YOLO + MediaPipe)
- Web dashboard (live camera stream)
- Kết nối tới Windows PC để điều khiển PowerPoint

---

## 📞 Liên hệ

- 🐛 Báo lỗi: Tạo issue
- 💡 Gợi ý: Tạo discussion
- 📧 Email: vamoss204@gmail.com

---

**Phiên bản:** 1.0  
**Ngày cập nhật:** 2026-11-03  
**Yêu cầu:** Python 3.10+, Windows 10+
