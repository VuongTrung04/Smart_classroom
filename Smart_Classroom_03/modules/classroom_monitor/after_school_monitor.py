"""Máy trạng thái giám sát ngoài giờ.

IDLE       : đang trong giờ học, không giám sát
EMPTY      : ngoài giờ, lớp trống
CONFIRMING : phát hiện người, đang chờ đủ thời gian xác nhận (tránh báo nhầm)
ALERT      : còn người quá thời gian cho phép -> báo giáo viên chủ nhiệm
ACKED      : giáo viên đã xác nhận xử lý, chờ lớp trống để quay về EMPTY
"""
from collections import deque
from statistics import median

IDLE, EMPTY, CONFIRMING, ALERT, ACKED = "IDLE", "EMPTY", "CONFIRMING", "ALERT", "ACKED"


class AfterSchoolMonitor:
    def __init__(self, alert_delay_minutes=3.0, clear_delay_minutes=1.0):
        self.alert_delay = float(alert_delay_minutes)
        self.clear_delay = float(clear_delay_minutes)
        self.state = IDLE
        self.present_minutes = 0.0
        self.absent_minutes = 0.0
        self.count = 0
        self._samples = deque(maxlen=5)

    def push_count(self, raw_count: int):
        """Nhận số người từ mỗi lần quét; lấy trung vị để lọc nhiễu của YOLO."""
        self._samples.append(max(0, int(raw_count)))
        self.count = int(round(median(self._samples)))

    def reset(self):
        self.state = IDLE
        self.present_minutes = self.absent_minutes = 0.0
        self._samples.clear()
        self.count = 0

    def acknowledge(self) -> bool:
        if self.state == ALERT:
            self.state = ACKED
            return True
        return False

    def remaining_minutes(self) -> float:
        return max(0.0, self.alert_delay - self.present_minutes)

    def update(self, after_hours: bool, delta_minutes: float):
        """Trả về (state, event) với event thuộc None/'DETECTED'/'ALERT'/'CLEARED'/'STARTED'."""
        if not after_hours:
            was_idle = self.state == IDLE
            self.reset()
            return self.state, (None if was_idle else "STOPPED")

        event = None
        if self.state == IDLE:
            self.state = EMPTY
            event = "STARTED"

        if self.count > 0:
            self.absent_minutes = 0.0
            self.present_minutes += delta_minutes
            if self.state == EMPTY:
                self.state = CONFIRMING
                event = "DETECTED"
            if self.state == CONFIRMING and self.present_minutes >= self.alert_delay:
                self.state = ALERT
                event = "ALERT"
        else:
            self.absent_minutes += delta_minutes
            if self.state != EMPTY and self.absent_minutes >= self.clear_delay:
                self.state = EMPTY
                self.present_minutes = 0.0
                event = "CLEARED"
        return self.state, event
