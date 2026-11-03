"""Cửa sổ chính Smart Classroom.

Trong giờ học  -> giao diện "Điều khiển bài giảng bằng cử chỉ" (MediaPipe + PowerPoint)
Ngoài giờ học  -> giao diện "Giám sát lớp học ngoài giờ" (YOLO + cảnh báo GVCN)
Chế độ tự chuyển theo đồng hồ mô phỏng.
"""
import time

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QImage, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                               QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget, QAbstractSpinBox)

from core.config import AppConfig, hhmm_to_minutes, minutes_to_hhmm
from core.event_log import EventLog
from core.time_controller import AFTER, CLASS, SPEEDS, SimClock
from modules.camera.camera_worker import CameraWorker
from modules.classroom_monitor.after_school_monitor import ACKED, ALERT, CONFIRMING, EMPTY, AfterSchoolMonitor
from modules.gesture_control.gesture_module import NEXT, POSE_TEXT, PREV, TOGGLE
from modules.gesture_control.ppt_controller import PPTController
from modules.notify.notifier import TeacherNotifier, beep
from ui import icons
from ui.dialogs import LogDialog, SettingsDialog
from ui.panels import GesturePanel, MonitorPanel
from ui.theme import FAINT, MODES, MUTED, TEXT, TEXT_2, TONES, stylesheet
from ui.widgets import Card, IconBadge, ModeSwitch, StatCard, TimelineSlider, Toast, VideoView, label, set_color

COMMAND_TEXT = {NEXT: "Slide tiếp  ›", PREV: "‹  Slide trước", TOGGLE: "▶  Bắt đầu / dừng trình chiếu"}
COMMAND_NAME = {NEXT: "Slide tiếp", PREV: "Slide trước", TOGGLE: "Bắt đầu/dừng trình chiếu"}


class Dashboard(QMainWindow):
    notify_result = Signal(bool, str)

    def __init__(self):
        super().__init__()
        self.cfg = AppConfig.load()
        self.events = EventLog()
        self.ppt = PPTController(self.cfg.ppt_backend)
        self.notifier = TeacherNotifier(self.cfg)
        self.monitor = AfterSchoolMonitor(self.cfg.alert_delay_minutes, self.cfg.clear_delay_minutes)
        self.clock = SimClock(hhmm_to_minutes(self.cfg.demo_start, 16 * 60 + 55),
                              hhmm_to_minutes(self.cfg.school_start, 420),
                              hhmm_to_minutes(self.cfg.dismissal, 1020),
                              self.cfg.demo_speed)
        self.mode = self.clock.mode
        self.worker = None
        self.source = {"kind": "sim", "text": "", "size": ""}
        self.engines = {"gesture": "", "person": ""}
        self.last_overlay = {}
        self.last_command = None      # (text, until)
        self.alert_sent_at = None
        self._last_stats = 0.0

        self.setWindowTitle("Smart Classroom – Lớp học thông minh")
        self.resize(1440, 900)
        self.setMinimumSize(1180, 700)
        self._build_ui()
        self._connect()
        self._apply_schedule()
        self.apply_mode(self.mode, initial=True)
        self._start_worker()
        self._log("neutral", "Khởi động hệ thống",
                  f"{self.cfg.class_name} · tan học {self.cfg.dismissal} · tốc độ {self.clock.speed}×")
        self.clock.start()
        self.on_tick(self.clock.minute, 0.0)

    # ======================================================================
    # Giao diện
    # ======================================================================
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(28, 22, 28, 22)
        outer.setSpacing(18)

        # ---------- header ----------
        header = QHBoxLayout()
        header.setSpacing(16)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        eyebrow_row = QHBoxLayout()
        eyebrow_row.setSpacing(6)
        self.eyebrow_icon = QLabel()
        self.eyebrow = label("", 11, QFont.Bold, TONES["class"][0], 1.0)
        eyebrow_row.addWidget(self.eyebrow_icon)
        eyebrow_row.addWidget(self.eyebrow)
        eyebrow_row.addStretch()
        titles.addLayout(eyebrow_row)
        self.title = label("", 32, QFont.Normal, TEXT)
        self.subtitle = label("", 13, QFont.Normal, MUTED)
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        header.addLayout(titles, 1)

        clock_box = QVBoxLayout()
        clock_box.setSpacing(0)
        self.clock_caption = label("GIỜ MÔ PHỎNG", 10, QFont.Bold, FAINT, 0.8)
        self.clock_caption.setAlignment(Qt.AlignRight)
        self.clock_label = label("00:00:00", 26, QFont.DemiBold, TEXT, 0.5, mono=True)
        self.clock_label.setAlignment(Qt.AlignRight)
        self.clock_sub = label("", 11, QFont.Normal, MUTED)
        self.clock_sub.setAlignment(Qt.AlignRight)
        clock_box.addWidget(self.clock_caption)
        clock_box.addWidget(self.clock_label)
        clock_box.addWidget(self.clock_sub)
        header.addLayout(clock_box)

        self.mode_switch = ModeSwitch()
        header.addWidget(self.mode_switch, 0, Qt.AlignVCenter)
        self.btn_log = QPushButton()
        self.btn_log.setObjectName("ghost")
        self.btn_log.setIcon(icons.icon("list", TEXT_2, 20))
        self.btn_log.setIconSize(QSize(20, 20))
        self.btn_log.setToolTip("Nhật ký sự kiện")
        self.btn_settings = QPushButton()
        self.btn_settings.setObjectName("ghost")
        self.btn_settings.setIcon(icons.icon("settings", TEXT_2, 20))
        self.btn_settings.setIconSize(QSize(20, 20))
        self.btn_settings.setToolTip("Cài đặt (Ctrl+,)")
        for b in (self.btn_log, self.btn_settings):
            b.setCursor(Qt.PointingHandCursor)
            header.addWidget(b, 0, Qt.AlignVCenter)
        outer.addLayout(header)

        # ---------- thân ----------
        body = QHBoxLayout()
        body.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(14)
        self.video = VideoView()
        self.video.room_code = self.cfg.room_code
        left.addWidget(self.video, 1)
        stats = QHBoxLayout()
        stats.setSpacing(14)
        self.stat_camera = StatCard("camera", "Camera", "Đang kết nối…", "class")
        self.stat_ai = StatCard("activity", "AI Vision", "Đang khởi động…", "violet")
        self.stat_state = StatCard("check", "Trạng thái", "Sẵn sàng", "success")
        for s in (self.stat_camera, self.stat_ai, self.stat_state):
            stats.addWidget(s, 1)
        left.addLayout(stats)
        body.addLayout(left, 7)

        self.stack = QStackedWidget()
        self.gesture_panel = GesturePanel()
        self.monitor_panel = MonitorPanel()
        for panel in (self.gesture_panel, self.monitor_panel):
            # bọc trong vùng cuộn để màn hình thấp (laptop 768px) không bị chồng chữ
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setWidget(panel)
            self.stack.addWidget(scroll)
        self.stack.setMinimumWidth(380)
        self.stack.setMaximumWidth(460)
        body.addWidget(self.stack, 3)
        outer.addLayout(body, 1)

        # ---------- thanh thời gian ----------
        bar = Card()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(16, 12, 16, 12)
        bl.setSpacing(14)
        self.bar_badge = IconBadge("sparkles", "class", 42, 20, 12)
        bl.addWidget(self.bar_badge)
        tcol = QVBoxLayout()
        tcol.setSpacing(2)
        tcol.addWidget(label("Điều khiển thời gian giả lập", 13, QFont.DemiBold, TEXT))
        tcol.addWidget(label("Chọn mốc để trình diễn chuyển chế độ tự động", 11, QFont.Normal, MUTED))
        bl.addLayout(tcol)
        self.btn_play = QPushButton()
        self.btn_play.setFixedSize(40, 38)
        self.btn_play.setIconSize(QSize(16, 16))
        self.btn_play.setCursor(Qt.PointingHandCursor)
        self.btn_play.setToolTip("Chạy / tạm dừng đồng hồ (Space)")
        bl.addWidget(self.btn_play)
        self.speed_combo = QComboBox()
        for s in SPEEDS:
            self.speed_combo.addItem(f"{s}×", s)
        idx = self.speed_combo.findData(self.clock.speed)
        self.speed_combo.setCurrentIndex(idx if idx >= 0 else 1)
        self.speed_combo.setToolTip("Tốc độ: 60× nghĩa là 1 giây thực = 1 phút mô phỏng")
        self.speed_combo.setFixedWidth(84)
        bl.addWidget(self.speed_combo)
        self.slider = TimelineSlider()
        bl.addWidget(self.slider, 1)
        self.presets = {}
        for key, text in (("class", "Trong tiết"), ("ending", "Sắp kết thúc"), ("after", "Ngoài giờ")):
            b = QPushButton(text)
            b.setObjectName("preset")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.jump_preset(k))
            bl.addWidget(b)
            self.presets[key] = b
        outer.addWidget(bar)

        self.toast = Toast(root)
        self.toast.anchor = self.video

    def _connect(self):
        self.clock.ticked.connect(self.on_tick)
        self.clock.mode_changed.connect(self.on_mode_changed)
        self.clock.running_changed.connect(self._update_play_button)
        self.mode_switch.requested.connect(lambda m: self.jump_preset("class" if m == CLASS else "after"))
        self.btn_play.clicked.connect(self.clock.toggle)
        self.speed_combo.currentIndexChanged.connect(
            lambda _: (self.clock.set_speed(self.speed_combo.currentData()), self._update_clock_sub()))
        self.slider.seek.connect(self.clock.set_time)
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_log.clicked.connect(lambda: LogDialog(self.events.entries, self.events.path, self).exec())
        self.gesture_panel.prev_clicked.connect(lambda: self.on_gesture_command(PREV, manual=True))
        self.gesture_panel.next_clicked.connect(lambda: self.on_gesture_command(NEXT, manual=True))
        self.monitor_panel.send_clicked.connect(lambda: self.trigger_alert(auto=False))
        self.monitor_panel.ack_clicked.connect(self.acknowledge_alert)
        self.monitor_panel.sim_people_changed.connect(self._set_sim_people)
        self.notify_result.connect(self._on_notify_result)

        self.ppt_timer = QTimer(self)
        self.ppt_timer.timeout.connect(self.refresh_ppt)
        self.ppt_timer.start(1500)
        self.alarm_timer = QTimer(self)
        self.alarm_timer.timeout.connect(lambda: self.cfg.sound and beep("alert"))

        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self._space)
        QShortcut(QKeySequence("F11"), self, activated=self._toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self.open_settings)
        QShortcut(QKeySequence("1"), self, activated=lambda: self.jump_preset("class"))
        QShortcut(QKeySequence("2"), self, activated=lambda: self.jump_preset("ending"))
        QShortcut(QKeySequence("3"), self, activated=lambda: self.jump_preset("after"))

    # ======================================================================
    # Camera
    # ======================================================================
    def _start_worker(self):
        if self.worker is not None:
            self.worker.stop()
        self.worker = CameraWorker(self.cfg, self.mode)
        self.worker.sim_people = self.monitor_panel.sim_people
        self.worker.frame_ready.connect(self.on_frame)
        self.worker.source_changed.connect(self.on_source_changed)
        self.worker.log.connect(lambda lvl, t, d: self._log(lvl, t, d))
        self.worker.gesture_command.connect(self.on_gesture_command)
        self.worker.engine_status.connect(self.on_engine_status)
        self.worker.start()

    def _set_sim_people(self, n):
        if self.worker:
            self.worker.sim_people = n

    def on_source_changed(self, info):
        self.source = info
        kind = info["kind"]
        self.video.signal_ok = kind != "none"
        self.video.camera_text = "CAM 01 · TOÀN CẢNH LỚP" if kind == "webcam" else \
            ("CAM MÔ PHỎNG · TOÀN CẢNH LỚP" if kind == "sim" else "CAM 01 · MẤT KẾT NỐI")
        if kind == "webcam":
            self.stat_camera.set("Hoạt động ổn định", "class", "camera")
        elif kind == "sim":
            self.stat_camera.set("Camera mô phỏng", "violet", "camera")
        else:
            self.stat_camera.set("Mất tín hiệu", "danger", "camera")
        self.monitor_panel.sim_row.setVisible(kind == "sim")
        self._update_hand_idle()

    def on_engine_status(self, engine, status):
        self.engines[engine] = status
        if engine == "gesture":
            if status == "error":
                self.gesture_panel.pill.set("Thiếu MediaPipe", "danger")
            self._update_hand_idle()
        if engine == "person" and status == "loading":
            self.stat_ai.set("Đang tải YOLO…", "violet")

    def on_frame(self, image: QImage, overlay: dict):
        self.last_overlay = overlay
        self.video.set_frame(image, overlay)
        if self.mode == AFTER and overlay.get("count") is not None:
            before = self.monitor.count
            self.monitor.push_count(overlay["count"])
            boxes = overlay.get("boxes") or []
            conf = sum(b[4] for b in boxes) / len(boxes) if boxes else None
            self.monitor_panel.set_count(self.monitor.count, conf)
            if before != self.monitor.count and before > 0 and self.monitor.count > 0:
                self._log("warning", "Số người thay đổi", f"{before} → {self.monitor.count} người")
        if self.mode == CLASS:
            hand = overlay.get("hand")
            if hand:
                self.gesture_panel.hand.set_state("tracking") if self.gesture_panel.hand.state != "tracking" else None
                self.gesture_panel.hand_title.setText("Đã nhận diện bàn tay")
                self.gesture_panel.hand_sub.setText(POSE_TEXT.get(overlay.get("pose"), ""))
            elif self.gesture_panel.hand.state == "tracking":
                self._update_hand_idle()
        now = time.monotonic()
        if now - self._last_stats > 0.5:
            self._last_stats = now
            self._update_stats()

    def _update_hand_idle(self):
        gp = self.gesture_panel
        if self.source.get("kind") == "sim":
            gp.hand.set_state("idle")
            gp.hand_title.setText("Camera mô phỏng")
            gp.hand_sub.setText("Không có webcam: dùng nút bên dưới hoặc phím ← → để chuyển slide")
        elif self.engines.get("gesture") == "error":
            gp.hand.set_state("off")
            gp.hand_title.setText("Chưa bật được nhận diện cử chỉ")
            gp.hand_sub.setText("Cài mediapipe==0.10.21 với Python 3.10–3.12 (xem README)")
        else:
            gp.hand.set_state("idle")
            gp.hand_title.setText("Sẵn sàng nhận diện")
            gp.hand_sub.setText("Đưa tay vào vùng nhận diện trước camera")

    def _update_stats(self):
        ov = self.last_overlay
        lat = ov.get("latency", 0) or 0
        if self.mode == CLASS:
            if self.source.get("kind") == "webcam" and self.engines.get("gesture") == "error":
                self.stat_ai.set("MediaPipe chưa sẵn sàng", "danger")
            else:
                self.stat_ai.set(f"Độ trễ {lat:.0f} ms", "violet")
            if self.last_command and time.monotonic() < self.last_command[1]:
                self.stat_state.set(f"Đã nhận: {self.last_command[0]}", "class", "check")
            else:
                self.stat_state.set("Sẵn sàng nhận lệnh", "success", "check")
        else:
            backend = self.engines.get("person") if self.source.get("kind") == "webcam" else "mô phỏng"
            if backend == "loading":
                self.stat_ai.set("Đang tải YOLO…", "violet")
            else:
                self.stat_ai.set(f"Quét mỗi {self.cfg.scan_interval_s:g} giây · {backend or 'YOLO'}", "violet")
            st = self.monitor.state
            text, tone, ic = {
                EMPTY: ("Lớp trống – an toàn", "success", "check"),
                CONFIRMING: ("Đã phát hiện người", "warning", "users"),
                ALERT: ("Đang cảnh báo GVCN", "danger", "alert"),
                ACKED: ("GVCN đã xác nhận", "neutral", "check"),
            }.get(st, ("Đang khởi động giám sát", "neutral", "shield"))
            self.stat_state.set(text, tone, ic)

    # ======================================================================
    # Đồng hồ & chế độ
    # ======================================================================
    def _apply_schedule(self):
        start = hhmm_to_minutes(self.cfg.school_start, 420)
        dismissal = hhmm_to_minutes(self.cfg.dismissal, 1020)
        self.clock.set_schedule(start, dismissal)
        self.slider.set_range(start, hhmm_to_minutes(self.cfg.timeline_end, 1200), dismissal)
        self.monitor.alert_delay = float(self.cfg.alert_delay_minutes)
        self.monitor.clear_delay = float(self.cfg.clear_delay_minutes)
        self.monitor_panel.footer.setText(
            f"Thông báo tới {self.cfg.teacher_name} qua {self.notifier.channel}")
        self.gesture_panel.set_legend(self.cfg.swipe_left_is_next)
        self.video.room_code = self.cfg.room_code

    def jump_preset(self, key):
        d = self.clock.dismissal
        target = {"class": d - 45, "ending": d - 1, "after": d + 3}[key]
        self.clock.set_time(target)
        if key == "ending":
            self.clock.start()
        names = {"class": "Trong tiết", "ending": "Sắp kết thúc", "after": "Ngoài giờ"}
        self._log("neutral", f"Chọn mốc “{names[key]}”", f"Đặt giờ mô phỏng {minutes_to_hhmm(target)}")

    def on_tick(self, minute, delta):
        self.clock_label.setText(self.clock.text())
        self.slider.set_value(minute, self.mode)
        self._update_clock_sub()
        d = self.clock.dismissal
        key = "after" if self.mode == AFTER else ("ending" if (d - minute) % 1440 <= 5 else "class")
        for k, b in self.presets.items():
            b.setChecked(k == key)

        if self.mode == AFTER:
            state, event = self.monitor.update(True, delta)
            self._handle_monitor_event(event)
            if state == CONFIRMING:
                left = self.monitor.remaining_minutes()
                self.monitor_panel.set_state(
                    CONFIRMING,
                    f"Còn {self.monitor.count} người trong lớp. Tự động báo GVCN sau "
                    f"{minutes_to_hhmm(left / 60, True)[3:]} phút mô phỏng nếu vẫn còn người.")
            elif state == ALERT:
                self.monitor_panel.set_state(
                    ALERT, f"Phát hiện {self.monitor.count} học sinh còn ở lại sau giờ học. "
                           f"Đã báo {self.cfg.teacher_name} lúc {self.alert_sent_at or '—'}.")
            elif state == ACKED:
                self.monitor_panel.set_state(ACKED)
            else:
                self.monitor_panel.set_state(EMPTY)

    def _update_clock_sub(self):
        left = self.clock.minutes_until_dismissal()
        speed = f"{self.clock.speed}×" + ("" if self.clock.running else " · tạm dừng")
        if self.mode == CLASS:
            self.clock_sub.setText(f"Tan học sau {minutes_to_hhmm(left, True)} · {speed}")
        else:
            self.clock_sub.setText(f"Ngoài giờ học · {speed}")

    def on_mode_changed(self, new, old):
        self.apply_mode(new)
        if new == AFTER:
            self._log("after", "Tiết học kết thúc", "Dữ liệu trình chiếu đã được lưu")
            self._log("neutral", "Chuyển chế độ tự động", "Giám sát ngoài giờ được kích hoạt")
            self.video.show_banner("Đã chuyển sang giám sát ngoài giờ", "after")
            self.toast.show_message("Chuyển chế độ an ninh", "Hết giờ học – camera chuyển sang phát hiện người.",
                                    "after", "shield", 3.0)
        else:
            self._log("class", "Vào giờ học", "Chuyển sang điều khiển bài giảng bằng cử chỉ")
            self.video.show_banner("Đã chuyển sang chế độ trình chiếu", "class")
            self.toast.show_message("Chế độ trình chiếu", "Trong giờ học – dùng cử chỉ tay để chuyển slide.",
                                    "class", "presentation", 3.0)

    def apply_mode(self, mode, initial=False):
        self.mode = mode
        m = MODES[mode]
        tone = "class" if mode == CLASS else "after"
        QApplication.instance().setStyleSheet(stylesheet(mode))
        self.eyebrow_icon.setPixmap(icons.pixmap(m["icon"], m["accent"], 16))
        self.eyebrow.setText(m["eyebrow"])
        set_color(self.eyebrow, m["accent"])
        self.title.setText(m["title"])
        self.subtitle.setText(m["subtitle"])
        self.mode_switch.set_mode(mode)
        self.stack.setCurrentIndex(0 if mode == CLASS else 1)
        self.bar_badge.set("sparkles", tone)
        self.video.mode = mode
        self.slider.set_value(self.clock.minute, mode)
        self._update_play_button(self.clock.running)
        if self.worker:
            self.worker.set_mode(mode)
        self.monitor.reset()
        self.video.alert = False
        self.alarm_timer.stop() if hasattr(self, "alarm_timer") else None
        self.alert_sent_at = None
        if mode == AFTER:
            self.monitor_panel.set_count(0, None)
            self.monitor_panel.set_state(EMPTY)
        self.monitor_panel.sim_row.setVisible(self.source.get("kind") == "sim")
        self._update_stats()

    def _update_play_button(self, running):
        accent = MODES[self.mode]["accent"]
        self.btn_play.setIcon(icons.icon("pause" if running else "play", accent, 16))
        self._update_clock_sub()

    # ======================================================================
    # Giám sát ngoài giờ
    # ======================================================================
    def _handle_monitor_event(self, event):
        if event == "STARTED":
            self.monitor_panel.pill.set("Đang quét", "after")
        elif event == "DETECTED":
            self._log("warning", "Phát hiện người",
                      f"{self.monitor.count} người trong lớp – chờ xác nhận {self.cfg.alert_delay_minutes:g} phút")
            self.toast.show_message("Phát hiện người trong lớp",
                                    f"{self.monitor.count} người sau giờ tan học. Đang xác nhận…",
                                    "warning", "users", 3.0)
            if self.cfg.sound:
                beep("info")
        elif event == "ALERT":
            self.trigger_alert(auto=True)
        elif event == "CLEARED":
            self._log("success", "Lớp học đã trống", "Không còn phát hiện người")
            self.video.alert = False
            self.alarm_timer.stop()
            self.alert_sent_at = None
            self.monitor_panel.pill.set("Đang quét", "after")
            self.toast.show_message("Lớp học đã trống", "Không còn người trong lớp. Hệ thống an toàn.",
                                    "success", "check-circle", 3.0)

    def trigger_alert(self, auto=True):
        n = self.monitor.count
        now = self.clock.text(False)
        if self.mode != AFTER:
            self.toast.show_message("Đang trong giờ học", "Chức năng cảnh báo chỉ hoạt động ngoài giờ học.",
                                    "neutral", "clock", 2.5)
            return
        if not auto and n == 0:
            msg = f"{self.cfg.class_name}: kiểm tra thủ công lúc {now}, hiện không phát hiện người trong lớp."
        else:
            msg = (f"{self.cfg.class_name}: phát hiện {n} người còn trong lớp lúc {now} "
                   f"(sau giờ tan học {self.cfg.dismissal}). Đề nghị kiểm tra.")
            if self.monitor.state in (CONFIRMING, EMPTY) and n > 0:
                self.monitor.state = ALERT
            self.video.alert = True
            self.monitor_panel.pill.set("Cảnh báo", "danger")
            if self.cfg.sound:
                beep("alert")
                self.alarm_timer.start(4000)
        self.alert_sent_at = now
        self.notifier.send("Cảnh báo Smart Classroom", msg,
                           on_result=lambda ok, info: self.notify_result.emit(ok, info))
        self._log("danger", "Đã gửi cảnh báo tới GVCN" if auto else "Gửi cảnh báo thủ công",
                  f"{self.cfg.teacher_name} · {msg}")
        self.toast.show_message(f"Đã báo {self.cfg.teacher_name}", msg, "danger", "bell", 5.0)

    def _on_notify_result(self, ok, info):
        if not ok:
            self._log("danger", "Gửi thông báo thất bại", info)
            self.toast.show_message("Gửi thông báo thất bại", info, "danger", "alert", 5.0)

    def acknowledge_alert(self):
        if self.monitor.acknowledge():
            self.video.alert = False
            self.alarm_timer.stop()
            self.monitor_panel.pill.set("Đang quét", "after")
            self._log("success", "GVCN xác nhận đã xử lý", "Tắt chuông cảnh báo, tiếp tục giám sát")

    # ======================================================================
    # Điều khiển trình chiếu
    # ======================================================================
    def on_gesture_command(self, command, manual=False):
        if self.mode != CLASS:
            return
        ok, msg = self.ppt.execute(command)
        name = COMMAND_NAME.get(command, command)
        self.video.flash_gesture(COMMAND_TEXT.get(command, command))
        self.gesture_panel.hand.set_state("fired")
        self.last_command = (name, time.monotonic() + 2.0)
        source = "Nút bấm" if manual else "Cử chỉ"
        self._log("class" if ok else "warning", f"{source}: {name}", msg, timeline=False)
        self.gesture_panel.hand_title.setText(f"{source}: {name}")
        self.gesture_panel.hand_sub.setText(msg)
        if not ok:
            self.toast.show_message("Chưa điều khiển được slide", msg, "warning", "presentation", 4.5)
        QTimer.singleShot(300, self.refresh_ppt)
        self._update_stats()

    def refresh_ppt(self):
        if self.mode == CLASS:
            self.gesture_panel.set_slide(self.ppt.status())

    # ======================================================================
    # Tiện ích
    # ======================================================================
    def _log(self, level, title, detail="", timeline=True):
        t = self.clock.text(False)
        self.events.add(t, level, title, detail)
        if timeline:
            self.monitor_panel.timeline.add(self.clock.text(), title, detail, level if level in TONES else "neutral")

    def _space(self):
        if isinstance(QApplication.focusWidget(), (QLineEdit, QAbstractSpinBox)):
            return
        self.clock.toggle()

    def keyPressEvent(self, e):
        if self.mode == CLASS and e.key() in (Qt.Key_Right, Qt.Key_PageDown):
            self.on_gesture_command(NEXT, manual=True)
        elif self.mode == CLASS and e.key() in (Qt.Key_Left, Qt.Key_PageUp):
            self.on_gesture_command(PREV, manual=True)
        else:
            super().keyPressEvent(e)

    def _toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def open_settings(self):
        old_cam = (self.cfg.camera_source, self.cfg.camera_index, self.cfg.yolo_confidence,
                   self.cfg.swipe_left_is_next)
        dlg = SettingsDialog(self.cfg, self)
        if dlg.exec():
            dlg.apply()
            self.ppt.backend = self.cfg.ppt_backend
            self._apply_schedule()
            self._log("neutral", "Đã lưu cài đặt", f"Tan học {self.cfg.dismissal}, chờ cảnh báo "
                                                   f"{self.cfg.alert_delay_minutes:g} phút")
            if old_cam != (self.cfg.camera_source, self.cfg.camera_index, self.cfg.yolo_confidence,
                           self.cfg.swipe_left_is_next):
                self._start_worker()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.toast.isVisible():
            self.toast.reposition()

    def closeEvent(self, event):
        self.clock.pause()
        if self.worker:
            self.worker.stop()
        event.accept()
