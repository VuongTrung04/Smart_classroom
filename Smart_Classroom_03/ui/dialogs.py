"""Hộp thoại Cài đặt và Nhật ký."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QLineEdit, QPlainTextEdit, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from ui.theme import MUTED
from ui.widgets import label


class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("Cài đặt Smart Classroom")
        self.setMinimumWidth(520)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.addWidget(label("Cài đặt", 20, QFont.DemiBold))
        root.addWidget(label("Thay đổi được lưu vào config.json.", 12, QFont.Normal, MUTED))
        tabs = QTabWidget()
        root.addWidget(tabs, 1)

        def page():
            w = QWidget()
            f = QFormLayout(w)
            f.setLabelAlignment(Qt.AlignRight)
            f.setVerticalSpacing(10)
            f.setContentsMargins(8, 14, 8, 8)
            return w, f

        # --- Lớp học & lịch ---
        w, f = page()
        self.class_name = QLineEdit(cfg.class_name)
        self.teacher = QLineEdit(cfg.teacher_name)
        self.room = QLineEdit(cfg.room_code)
        self.start = QLineEdit(cfg.school_start)
        self.dismissal = QLineEdit(cfg.dismissal)
        self.tl_end = QLineEdit(cfg.timeline_end)
        for e in (self.start, self.dismissal, self.tl_end):
            e.setInputMask("99:99")
        f.addRow("Tên lớp", self.class_name)
        f.addRow("Giáo viên chủ nhiệm", self.teacher)
        f.addRow("Mã camera/phòng", self.room)
        f.addRow("Giờ vào học", self.start)
        f.addRow("Giờ tan học", self.dismissal)
        f.addRow("Cuối thanh thời gian", self.tl_end)
        tabs.addTab(w, "Lớp học")

        # --- Camera & AI ---
        w, f = page()
        self.source = QComboBox()
        for text, val in (("Tự động (webcam, lỗi thì mô phỏng)", "auto"), ("Chỉ webcam", "webcam"),
                          ("Camera mô phỏng", "sim")):
            self.source.addItem(text, val)
        self.source.setCurrentIndex(max(0, self.source.findData(cfg.camera_source)))
        self.cam_index = QSpinBox()
        self.cam_index.setRange(0, 9)
        self.cam_index.setValue(int(cfg.camera_index))
        self.delay = QDoubleSpinBox()
        self.delay.setRange(0, 120)
        self.delay.setSuffix(" phút mô phỏng")
        self.delay.setValue(float(cfg.alert_delay_minutes))
        self.clear = QDoubleSpinBox()
        self.clear.setRange(0, 60)
        self.clear.setSuffix(" phút mô phỏng")
        self.clear.setValue(float(cfg.clear_delay_minutes))
        self.scan = QDoubleSpinBox()
        self.scan.setRange(0.1, 10)
        self.scan.setSingleStep(0.1)
        self.scan.setSuffix(" giây")
        self.scan.setValue(float(cfg.scan_interval_s))
        self.conf = QDoubleSpinBox()
        self.conf.setRange(0.1, 0.95)
        self.conf.setSingleStep(0.05)
        self.conf.setValue(float(cfg.yolo_confidence))
        self.sound = QCheckBox("Phát âm thanh khi cảnh báo")
        self.sound.setChecked(bool(cfg.sound))
        f.addRow("Nguồn camera", self.source)
        f.addRow("Số camera (index)", self.cam_index)
        f.addRow("Chờ trước khi cảnh báo", self.delay)
        f.addRow("Coi là lớp trống sau", self.clear)
        f.addRow("Chu kỳ quét YOLO", self.scan)
        f.addRow("Ngưỡng tin cậy YOLO", self.conf)
        f.addRow("", self.sound)
        tabs.addTab(w, "Camera & AI")

        # --- Trình chiếu & thông báo ---
        w, f = page()
        self.ppt = QComboBox()
        for text, val in (("Tự động (COM, lỗi thì phím)", "auto"), ("Chỉ PowerPoint COM", "com"),
                          ("Chỉ gửi phím (pyautogui)", "keys")):
            self.ppt.addItem(text, val)
        self.ppt.setCurrentIndex(max(0, self.ppt.findData(cfg.ppt_backend)))
        self.swipe = QComboBox()
        self.swipe.addItem("Vuốt trái = slide tiếp", True)
        self.swipe.addItem("Vuốt phải = slide tiếp", False)
        self.swipe.setCurrentIndex(0 if cfg.swipe_left_is_next else 1)
        self.tg_token = QLineEdit(cfg.telegram_token)
        self.tg_token.setEchoMode(QLineEdit.Password)
        self.tg_token.setPlaceholderText("Để trống = chỉ mô phỏng")
        self.tg_chat = QLineEdit(cfg.telegram_chat_id)
        f.addRow("Điều khiển PowerPoint", self.ppt)
        f.addRow("Hướng vuốt", self.swipe)
        f.addRow("Telegram bot token", self.tg_token)
        f.addRow("Telegram chat id", self.tg_chat)
        tabs.addTab(w, "Trình chiếu & thông báo")

        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Save).setText("Lưu")
        bb.button(QDialogButtonBox.Save).setObjectName("primary")
        bb.button(QDialogButtonBox.Cancel).setText("Huỷ")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def apply(self):
        c = self.cfg
        c.class_name = self.class_name.text().strip() or c.class_name
        c.teacher_name = self.teacher.text().strip() or c.teacher_name
        c.room_code = self.room.text().strip()
        c.school_start = self.start.text()
        c.dismissal = self.dismissal.text()
        c.timeline_end = self.tl_end.text()
        c.camera_source = self.source.currentData()
        c.camera_index = self.cam_index.value()
        c.alert_delay_minutes = self.delay.value()
        c.clear_delay_minutes = self.clear.value()
        c.scan_interval_s = self.scan.value()
        c.yolo_confidence = self.conf.value()
        c.sound = self.sound.isChecked()
        c.ppt_backend = self.ppt.currentData()
        c.swipe_left_is_next = bool(self.swipe.currentData())
        c.telegram_token = self.tg_token.text().strip()
        c.telegram_chat_id = self.tg_chat.text().strip()
        c.save()


class LogDialog(QDialog):
    def __init__(self, entries, path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nhật ký sự kiện")
        self.resize(720, 480)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 16)
        lay.addWidget(label("Nhật ký sự kiện", 20, QFont.DemiBold))
        lay.addWidget(label(f"Lưu tại: {path}", 11, QFont.Normal, MUTED))
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setFont(QFont("Consolas", 10))
        text.setPlainText("\n".join(
            f"[{t}] {lvl.upper():8} {title}" + (f" — {d}" if d else "") for t, lvl, title, d in reversed(entries)))
        lay.addWidget(text, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText("Đóng")
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
