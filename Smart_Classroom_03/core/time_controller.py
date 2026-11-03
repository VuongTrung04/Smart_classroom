"""Đồng hồ mô phỏng: chạy mượt theo thời gian thực nhân với hệ số tốc độ."""
import time

from PySide6.QtCore import QObject, QTimer, Signal

from core.config import minutes_to_hhmm

CLASS = "CLASS"   # trong giờ học -> điều khiển slide bằng cử chỉ
AFTER = "AFTER"   # ngoài giờ -> giám sát người còn trong lớp

SPEEDS = [1, 10, 30, 60, 120, 300, 600]


def mode_for(minute: float, school_start: float, dismissal: float) -> str:
    """Trong giờ khi school_start <= t < dismissal, còn lại (kể cả sau 0h) là ngoài giờ."""
    m = minute % (24 * 60)
    if school_start <= dismissal:
        return CLASS if school_start <= m < dismissal else AFTER
    # Lịch qua nửa đêm (hiếm gặp, vẫn xử lý đúng)
    return CLASS if (m >= school_start or m < dismissal) else AFTER


class SimClock(QObject):
    """speed = số giây mô phỏng trôi qua trong 1 giây thực (60x: 1 giây = 1 phút)."""

    ticked = Signal(float, float)       # phút trong ngày, số phút mô phỏng vừa trôi
    mode_changed = Signal(str, str)     # mode mới, mode cũ
    running_changed = Signal(bool)

    def __init__(self, minute: float, school_start: float, dismissal: float, speed: int = 10):
        super().__init__()
        self.minute = float(minute) % 1440
        self.school_start = school_start
        self.dismissal = dismissal
        self.speed = speed
        self.running = False
        self.mode = self.current_mode()
        self._last = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._on_timer)

    # ---- điều khiển ----
    def start(self):
        if not self.running:
            self.running = True
            self._last = time.monotonic()
            self._timer.start()
            self.running_changed.emit(True)

    def pause(self):
        if self.running:
            self.running = False
            self._timer.stop()
            self.running_changed.emit(False)

    def toggle(self):
        self.pause() if self.running else self.start()

    def set_speed(self, speed: int):
        self.speed = max(1, int(speed))

    def set_schedule(self, school_start: float, dismissal: float):
        self.school_start, self.dismissal = school_start, dismissal
        self._check_mode()

    def set_time(self, minute: float):
        self.minute = float(minute) % 1440
        self._last = time.monotonic()
        self.ticked.emit(self.minute, 0.0)
        self._check_mode()

    # ---- truy vấn ----
    def current_mode(self) -> str:
        return mode_for(self.minute, self.school_start, self.dismissal)

    def text(self, seconds=True) -> str:
        return minutes_to_hhmm(self.minute, seconds)

    def minutes_until_dismissal(self) -> float:
        return (self.dismissal - self.minute) % 1440

    # ---- nội bộ ----
    def _on_timer(self):
        now = time.monotonic()
        dt = min(now - self._last, 1.0)   # tránh nhảy giờ khi máy bị treo
        self._last = now
        delta = dt * self.speed / 60.0
        self.minute = (self.minute + delta) % 1440
        self.ticked.emit(self.minute, delta)
        self._check_mode()

    def _check_mode(self):
        new = self.current_mode()
        if new != self.mode:
            old, self.mode = self.mode, new
            self.mode_changed.emit(new, old)
