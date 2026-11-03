"""Gửi cảnh báo tới giáo viên chủ nhiệm.

Mặc định là mô phỏng: ghi vào logs/alerts.log và phát âm thanh.
Nếu điền telegram_token + telegram_chat_id trong Cài đặt thì gửi tin nhắn Telegram thật.
"""
import json
import sys
import threading
import urllib.parse
import urllib.request
from datetime import datetime

from core.config import LOG_DIR


def beep(kind="alert"):
    try:
        if sys.platform.startswith("win"):
            import winsound
            winsound.MessageBeep(winsound.MB_ICONHAND if kind == "alert" else winsound.MB_ICONASTERISK)
            return
    except Exception:
        pass
    try:
        from PySide6.QtWidgets import QApplication
        QApplication.beep()
    except Exception:
        pass


class TeacherNotifier:
    def __init__(self, config):
        self.config = config

    @property
    def channel(self):
        if self.config.telegram_token and self.config.telegram_chat_id:
            return "Telegram"
        return "ứng dụng (mô phỏng)"

    def send(self, title, message, on_result=None):
        """Gửi không chặn giao diện; on_result(ok, info) được gọi từ luồng phụ."""
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        line = f"{datetime.now():%Y-%m-%d %H:%M:%S} | {title} | {message}\n"
        try:
            with (LOG_DIR / "alerts.log").open("a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass

        if self.channel != "Telegram":
            if on_result:
                on_result(True, "Đã ghi nhận cảnh báo (mô phỏng)")
            return

        def worker():
            try:
                url = f"https://api.telegram.org/bot{self.config.telegram_token}/sendMessage"
                data = urllib.parse.urlencode({
                    "chat_id": self.config.telegram_chat_id,
                    "text": f"🔔 {title}\n{message}",
                }).encode()
                with urllib.request.urlopen(url, data=data, timeout=8) as resp:
                    ok = json.loads(resp.read().decode()).get("ok", False)
                if on_result:
                    on_result(ok, "Đã gửi Telegram" if ok else "Telegram từ chối tin nhắn")
            except Exception as exc:
                if on_result:
                    on_result(False, f"Gửi Telegram lỗi: {exc}")

        threading.Thread(target=worker, daemon=True).start()
