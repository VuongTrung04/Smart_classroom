"""Cấu hình ứng dụng, lưu trong file config.json cạnh main.py."""
import json
from dataclasses import dataclass, asdict, fields
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
LOG_DIR = ROOT / "logs"
MODEL_DIR = ROOT / "models"


@dataclass
class AppConfig:
    # Thông tin lớp học
    class_name: str = "Lớp 9A1"
    room_code: str = "CAM-A2-304-01"
    teacher_name: str = "Cô Nguyễn Thị Lan"

    # Lịch học (HH:MM)
    school_start: str = "07:00"
    dismissal: str = "17:00"
    timeline_end: str = "20:00"
    demo_start: str = "16:55"
    demo_speed: int = 10

    # Camera: "auto" = thử webcam, lỗi thì dùng camera mô phỏng; "webcam"; "sim"
    camera_source: str = "auto"
    camera_index: int = 1

    # Giám sát ngoài giờ
    alert_delay_minutes: float = 3.0      # phút mô phỏng còn người liên tục thì cảnh báo
    clear_delay_minutes: float = 1.0      # phút mô phỏng không còn ai thì coi là lớp trống
    scan_interval_s: float = 0.5          # chu kỳ quét YOLO (giây thực)
    yolo_model: str = "yolov8n.pt"
    yolo_confidence: float = 0.45
    sound: bool = True

    # Điều khiển slide: "auto" (COM rồi phím), "com", "keys"
    ppt_backend: str = "auto"
    swipe_left_is_next: bool = True

    # Gửi cảnh báo thật qua Telegram (để trống = chỉ mô phỏng)
    telegram_token: str = ""
    telegram_chat_id: str = ""

    @classmethod
    def load(cls) -> "AppConfig":
        cfg = cls()
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                names = {f.name for f in fields(cls)}
                for key, value in data.items():
                    if key in names:
                        setattr(cfg, key, value)
            except (OSError, ValueError):
                pass
        return cfg

    def save(self):
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8"
        )


def hhmm_to_minutes(text: str, default: float = 0.0) -> float:
    try:
        h, m = str(text).strip().split(":")[:2]
        return (int(h) % 24) * 60 + int(m) % 60
    except (ValueError, AttributeError):
        return default


def minutes_to_hhmm(minutes: float, seconds: bool = False) -> str:
    total = int(round(minutes * 60)) % (24 * 3600)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if seconds else f"{h:02d}:{m:02d}"
