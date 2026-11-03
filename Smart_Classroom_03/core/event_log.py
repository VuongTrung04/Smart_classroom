"""Ghi nhật ký sự kiện ra file logs/events_YYYYMMDD.log."""
from datetime import datetime

from core.config import LOG_DIR


class EventLog:
    def __init__(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.path = LOG_DIR / f"events_{datetime.now():%Y%m%d}.log"
        self.entries = []   # (sim_time, level, title, detail)

    def add(self, sim_time: str, level: str, title: str, detail: str = ""):
        self.entries.append((sim_time, level, title, detail))
        self.entries = self.entries[-500:]
        line = f"{datetime.now():%Y-%m-%d %H:%M:%S} | giờ mô phỏng {sim_time} | {level.upper():7} | {title}"
        if detail:
            line += f" — {detail}"
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass
