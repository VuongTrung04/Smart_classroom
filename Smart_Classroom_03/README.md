# Smart Classroom – Lớp học thông minh

Hệ thống giám sát lớp học bằng AI và điều khiển bài giảng bằng cử chỉ tay.
Ứng dụng có **hai giao diện, tự chuyển theo đồng hồ mô phỏng**:

| Thời gian | Giao diện | Camera dùng để |
|---|---|---|
| Trong giờ học (mặc định 07:00 – 17:00) | **Điều khiển bài giảng bằng cử chỉ** (màu xanh) | MediaPipe nhận diện bàn tay → chuyển slide PowerPoint |
| Ngoài giờ học | **Giám sát lớp học ngoài giờ** (màu cam) | YOLO đếm người → còn người quá thời gian cho phép thì cảnh báo giáo viên chủ nhiệm |

Không có webcam vẫn trình diễn được: ứng dụng tự chuyển sang **camera mô phỏng** (vẽ lớp học, chỉnh được số học sinh còn lại).

---

## 1. Cài đặt (PyCharm, Windows)

1. Cài **Python 3.11** (khuyến nghị; 3.10 và 3.12 cũng chạy được). *Không dùng Python 3.13* vì MediaPipe chưa hỗ trợ.
2. Mở PyCharm → **File ▸ Open** → chọn thư mục `Smart_Classroom`.
3. **Settings ▸ Project ▸ Python Interpreter ▸ Add Interpreter ▸ Virtualenv**, chọn Base interpreter là Python 3.11, vị trí `.venv`.
4. Mở **Terminal** trong PyCharm (đã tự kích hoạt `.venv`) và chạy:
   ```bat
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Mở `main.py` → bấm **Run** (▶). Hoặc nhấp đúp `run.bat`.

Lần đầu bước sang chế độ ngoài giờ, YOLO sẽ tự tải `yolov8n.pt` (cần Internet). Có thể đặt sẵn file vào thư mục `models/`.

## 2. Kịch bản trình diễn (khoảng 2 phút)

1. Mở ứng dụng: đồng hồ bắt đầu ở **16:55**, tốc độ **10×**, giao diện **Trong giờ học**.
2. Mở PowerPoint, mở bài thuyết trình. **Nắm tay 1 giây** để bắt đầu trình chiếu, **vuốt tay sang trái** để sang slide tiếp, **vuốt sang phải** để lùi lại. Ô “Slide hiện tại” hiện số slide thật.
3. Bấm **Sắp kết thúc** (đặt 16:59). Khoảng 6 giây sau đồng hồ qua 17:00, giao diện **tự chuyển sang Giám sát ngoài giờ**.
4. Camera phát hiện người còn trong lớp → trạng thái **Đang xác nhận** (đếm ngược). Hết thời gian chờ (mặc định 3 phút mô phỏng) → **Cần kiểm tra lớp học**: viền camera nháy đỏ, chuông kêu, gửi thông báo tới GVCN, ghi nhật ký.
5. Bấm **Đã xử lý** để tắt chuông. Khi mọi người rời khỏi lớp (hoặc giảm số người về 0 ở camera mô phỏng) → **Lớp học an toàn**.

Muốn nhanh hơn thì chọn tốc độ 60× hoặc 300× ở thanh dưới, hoặc kéo trực tiếp thanh thời gian.

### Phím tắt
| Phím | Chức năng |
|---|---|
| `Space` | Chạy / tạm dừng đồng hồ mô phỏng |
| `1` `2` `3` | Mốc Trong tiết / Sắp kết thúc / Ngoài giờ |
| `←` `→` | Slide trước / tiếp (khi đang trong giờ) |
| `F11` | Toàn màn hình |
| `Ctrl + ,` | Cài đặt |

### Cử chỉ tay (trong giờ học)
| Cử chỉ | Lệnh |
|---|---|
| Vuốt bàn tay mở sang **trái** | Slide tiếp (đổi chiều được trong Cài đặt) |
| Vuốt bàn tay mở sang **phải** | Slide trước |
| **Nắm tay** giữ 1 giây | Bắt đầu / dừng trình chiếu |
| Giơ **1 ngón trỏ** | Slide tiếp (dự phòng) |
| Giơ **2 ngón** (chữ V) | Slide trước (dự phòng) |

## 3. Cài đặt trong ứng dụng (biểu tượng ⚙)
- **Lớp học**: tên lớp, tên GVCN, giờ vào học, giờ tan học.
- **Camera & AI**: nguồn camera (Tự động / Webcam / Mô phỏng), số camera, thời gian chờ trước khi cảnh báo, chu kỳ quét YOLO, ngưỡng tin cậy.
- **Trình chiếu & thông báo**: cách điều khiển PowerPoint (COM hoặc gửi phím), chiều vuốt, Telegram bot (không bắt buộc).

Cài đặt lưu ở `config.json`. Nhật ký sự kiện ở `logs/events_YYYYMMDD.log`, cảnh báo ở `logs/alerts.log`.

**Gửi cảnh báo thật qua Telegram (tuỳ chọn):** tạo bot bằng @BotFather để lấy *token*, nhắn cho bot một tin, lấy *chat id* (ví dụ qua @userinfobot), rồi điền vào Cài đặt. Để trống thì cảnh báo chỉ hiển thị và ghi log (mô phỏng).

## 4. Cấu trúc thư mục
```
Smart_Classroom/
├── main.py                         # chạy ứng dụng
├── run.bat                         # chạy nhanh trên Windows
├── requirements.txt
├── config.json                     # tự tạo khi lưu cài đặt
├── core/
│   ├── config.py                   # cấu hình, đọc/ghi config.json
│   ├── time_controller.py          # đồng hồ mô phỏng + xác định chế độ
│   └── event_log.py                # ghi nhật ký
├── modules/
│   ├── camera/
│   │   ├── camera_worker.py        # luồng camera chạy nền (QThread)
│   │   └── sim_scene.py            # camera mô phỏng
│   ├── classroom_monitor/
│   │   ├── person_detector.py      # YOLO (dự phòng HOG của OpenCV)
│   │   └── after_school_monitor.py # máy trạng thái cảnh báo
│   ├── gesture_control/
│   │   ├── gesture_module.py       # MediaPipe: vuốt, nắm tay, 1 ngón, 2 ngón
│   │   └── ppt_controller.py       # điều khiển PowerPoint (COM / phím)
│   └── notify/
│       └── notifier.py             # báo GVCN (log, âm thanh, Telegram)
├── ui/
│   ├── dashboard.py                # cửa sổ chính, logic chuyển chế độ
│   ├── panels.py                   # panel Trình chiếu / Giám sát
│   ├── widgets.py                  # khung camera, thanh thời gian, timeline…
│   ├── dialogs.py                  # Cài đặt, Nhật ký
│   ├── theme.py                    # màu sắc, font, stylesheet
│   └── icons.py                    # icon vector
├── models/                         # đặt yolov8n.pt (tuỳ chọn)
└── logs/
```

## 5. Các lỗi đã sửa so với bản cũ
- Camera mặc định **index 1** (theo yêu cầu), đổi được trong Cài đặt; nếu không mở được thì tự dò 0–3 (DirectShow, rồi Media Foundation). Không có camera thì dùng camera mô phỏng.
- YOLO và MediaPipe chạy trên **luồng giao diện** làm app giật/đứng → chuyển sang `QThread`. Chế độ nào chỉ chạy mô hình của chế độ đó.
- Đồng hồ **nhảy 60 phút mỗi lần**, qua 0h bị tính là “trong giờ”, trước 7h không được coi là ngoài giờ → đồng hồ chạy mượt (cập nhật 10 lần/giây). Ngoài giờ = trước giờ vào học hoặc từ giờ tan học.
- Cử chỉ “ngón cái” dễ nhầm khi nắm tay → slide tự lùi. Giờ nhận diện theo khoảng cách tới cổ tay (không phụ thuộc góc tay), có chống lặp lệnh và thời gian chờ giữa hai lệnh.
- Gửi phím bằng pyautogui chỉ chạy khi PowerPoint đang được focus → ưu tiên **PowerPoint COM** (pywin32), đọc được số slide.
- `opencv-python` cài chung với `mediapipe` (kéo theo `opencv-contrib-python`) gây xung đột → chỉ dùng `opencv-contrib-python`.
- Chữ tiếng Việt trên khung camera bị lỗi khi vẽ bằng `cv2.putText` → toàn bộ lớp phủ (khung người, bàn tay, nhãn) vẽ bằng Qt.
- Cảnh báo dựa vào một khung hình dễ báo nhầm → lấy trung vị 5 lần quét, có thời gian xác nhận và thời gian coi là lớp trống.

## 6. Xử lý sự cố
| Hiện tượng | Cách khắc phục |
|---|---|
| `ImportError` / `DLL load failed` khi `import cv2` | `pip uninstall -y opencv-python opencv-contrib-python` rồi `pip install opencv-contrib-python==4.10.0.84` |
| “MediaPipe không có API mp.solutions” | Cài đúng `mediapipe==0.10.21` với Python 3.10–3.12; trong project không được có file tên `mediapipe.py` |
| Không mở được webcam | Đóng Zoom/Teams/Camera app; đổi “Số camera” trong Cài đặt (0, 1, 2…) |
| Bấm nút / cử chỉ nhưng slide không chuyển | Kiểm tra dòng “Kết nối slide” cuối panel: phải là **PowerPoint COM**. Nếu không, chạy `pip install pywin32` rồi mở lại app. Mở file PowerPoint **trước**, rồi bấm nút trong app (chạy được cả khi chưa trình chiếu). Dùng WPS thì chọn “Chỉ gửi phím” trong Cài đặt |
| Lỗi COM kiểu `CLSIDToClassMap` | Xoá thư mục `%LOCALAPPDATA%\Temp\gen_py` rồi mở lại app |
| Muốn đổi webcam | Mặc định dùng webcam **index 1**. Đổi trong ⚙ Cài đặt ▸ Camera & AI ▸ Số camera (nếu đã có `config.json` cũ thì sửa `camera_index` trong đó) |
| YOLO tải chậm / không có mạng | Chép `yolov8n.pt` vào thư mục `models/` |
| Máy yếu, giật | Tăng “Chu kỳ quét YOLO” lên 1–2 giây |

## 7. Lưu ý
- Hệ thống chỉ phát hiện **có người** (lớp `person`), không nhận dạng danh tính học sinh.
- Một camera dùng chung cho cả hai chế độ. Khi triển khai thật, nên đặt camera thấy được cả bục giảng và toàn bộ lớp.
- Cần thử với ánh sáng và vị trí lắp đặt thực tế trước khi sử dụng.
