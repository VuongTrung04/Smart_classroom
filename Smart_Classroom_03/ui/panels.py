"""Hai panel bên phải: điều khiển trình chiếu (trong giờ) và giám sát ngoài giờ."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from ui import icons
from ui.theme import FAINT, MUTED, TEXT, TEXT_2, TONES
from ui.widgets import Card, EventTimeline, HandIndicator, IconBadge, Pill, SlidePreview, label, set_color


def _header(eyebrow, title, eyebrow_color):
    box = QVBoxLayout()
    box.setSpacing(4)
    e = label(eyebrow, 10, QFont.Bold, eyebrow_color, 0.8)
    t = label(title, 19, QFont.Normal, TEXT)
    box.addWidget(e)
    box.addWidget(t)
    return box, e, t


class GesturePanel(Card):
    prev_clicked = Signal()
    next_clicked = Signal()

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 14)
        lay.setSpacing(12)

        top = QHBoxLayout()
        head, _, _ = _header("ĐIỀU KHIỂN TRÌNH CHIẾU", "Cử chỉ thông minh", TONES["class"][0])
        top.addLayout(head, 1)
        self.pill = Pill("Đang hoạt động", "success")
        top.addWidget(self.pill, 0, Qt.AlignTop)
        lay.addLayout(top)

        # khung nhận diện tay
        detect = QFrame()
        detect.setObjectName("soft")
        dl = QVBoxLayout(detect)
        dl.setContentsMargins(12, 8, 12, 12)
        dl.setSpacing(4)
        self.hand = HandIndicator()
        dl.addWidget(self.hand)
        self.hand_title = label("Sẵn sàng nhận diện", 13, QFont.DemiBold, TEXT)
        self.hand_title.setAlignment(Qt.AlignCenter)
        self.hand_sub = label("Đưa tay vào vùng nhận diện trước camera", 11, QFont.Normal, MUTED)
        self.hand_sub.setAlignment(Qt.AlignCenter)
        self.hand_sub.setWordWrap(True)
        dl.addWidget(self.hand_title)
        dl.addWidget(self.hand_sub)
        lay.addWidget(detect)

        # slide hiện tại
        row = QHBoxLayout()
        row.setSpacing(10)
        self.preview = SlidePreview()
        row.addWidget(self.preview, 3)
        counter = QFrame()
        counter.setObjectName("soft")
        cl = QVBoxLayout(counter)
        cl.setContentsMargins(8, 10, 8, 10)
        cl.addStretch()
        c1 = label("Slide hiện tại", 11, QFont.Normal, FAINT)
        c1.setAlignment(Qt.AlignCenter)
        self.counter = label("— / —", 18, QFont.Bold, TEXT, 1.0, mono=True)
        self.counter.setAlignment(Qt.AlignCenter)
        cl.addWidget(c1)
        cl.addWidget(self.counter)
        cl.addStretch()
        row.addWidget(counter, 2)
        lay.addLayout(row)

        # nút điều khiển tay
        btns = QHBoxLayout()
        btns.setSpacing(10)
        self.btn_prev = QPushButton("  Slide trước")
        self.btn_prev.setIcon(icons.icon("chevron-left", TEXT_2, 16))
        self.btn_next = QPushButton("Slide tiếp  ")
        self.btn_next.setObjectName("primary")
        self.btn_next.setLayoutDirection(Qt.RightToLeft)
        self.btn_next.setIcon(icons.icon("chevron-right", "white", 16))
        for b in (self.btn_prev, self.btn_next):
            b.setMinimumHeight(42)
            b.setCursor(Qt.PointingHandCursor)
        self.btn_prev.clicked.connect(self.prev_clicked)
        self.btn_next.clicked.connect(self.next_clicked)
        btns.addWidget(self.btn_prev)
        btns.addWidget(self.btn_next)
        lay.addLayout(btns)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #E9EDF3;")
        lay.addWidget(line)

        # chú thích cử chỉ
        self.legend = QGridLayout()
        self.legend.setHorizontalSpacing(0)
        self._legend_labels = []
        lay.addLayout(self.legend)
        self.set_legend(True)

        self.backend_label = label("", 10, QFont.Normal, FAINT, wrap=True)
        self.backend_label.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.backend_label)
        lay.addStretch()

    def set_legend(self, swipe_left_is_next):
        while self.legend.count():
            w = self.legend.takeAt(0).widget()
            if w:
                w.deleteLater()
        items = [
            ("chevron-left", "Vuốt trái", "Slide tiếp" if swipe_left_is_next else "Slide trước"),
            ("chevron-right", "Vuốt phải", "Slide trước" if swipe_left_is_next else "Slide tiếp"),
            ("grab", "Nắm tay 1s", "Bắt đầu / dừng"),
        ]
        for i, (ic, t, s) in enumerate(items):
            cell = QWidget()
            if i:
                cell.setStyleSheet("border-left: 1px solid #E9EDF3;")
            cl = QVBoxLayout(cell)
            cl.setContentsMargins(4, 2, 4, 2)
            cl.setSpacing(2)
            icl = label("")
            icl.setPixmap(icons.pixmap(ic, TEXT_2, 16))
            icl.setAlignment(Qt.AlignCenter)
            icl.setStyleSheet("border: none;")
            a = label(t, 11, QFont.DemiBold, TEXT)
            a.setAlignment(Qt.AlignCenter)
            a.setStyleSheet(f"color:{TEXT}; border: none;")
            b = label(s, 10, QFont.Normal, FAINT)
            b.setAlignment(Qt.AlignCenter)
            b.setStyleSheet(f"color:{FAINT}; border: none;")
            for w in (icl, a, b):
                cl.addWidget(w)
            self.legend.addWidget(cell, 0, i)
        hint = label("Dự phòng: giơ 1 ngón = tiếp · giơ 2 ngón = trước", 10, QFont.Normal, FAINT)
        hint.setAlignment(Qt.AlignCenter)
        self.legend.addWidget(hint, 1, 0, 1, 3)

    def set_slide(self, info):
        if info.get("total"):
            self.counter.setText(f"{info['slide']:02d} / {info['total']:02d}")
            sub = "ĐANG TRÌNH CHIẾU" if info.get("running") else "CHƯA TRÌNH CHIẾU · NẮM TAY ĐỂ BẮT ĐẦU"
            self.preview.set_info(info.get("title") or "Bài trình chiếu", sub,
                                  info["slide"] / max(1, info["total"]))
        else:
            self.counter.setText("— / —")
            msg = "Chưa mở PowerPoint" if info.get("backend", "") != "Phím tắt (pyautogui)" \
                else "Gửi phím ← → tới slide"
            self.preview.set_info(msg, "POWERPOINT", 0.15)
        self.backend_label.setText(f"Kết nối slide: {info.get('backend', '')}")


class MonitorPanel(Card):
    send_clicked = Signal()
    ack_clicked = Signal()
    sim_people_changed = Signal(int)

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 16)
        lay.setSpacing(14)

        top = QHBoxLayout()
        head, _, _ = _header("GIÁM SÁT NGOÀI GIỜ", "Phát hiện hiện diện", TONES["after"][0])
        top.addLayout(head, 1)
        self.pill = Pill("Đang quét", "after")
        top.addWidget(self.pill, 0, Qt.AlignTop)
        lay.addLayout(top)

        # ô số người
        self.count_box = QFrame()
        cb = QHBoxLayout(self.count_box)
        cb.setContentsMargins(16, 14, 16, 14)
        cb.setSpacing(14)
        self.count_badge = IconBadge("users", "after", 52, 26, 14)
        cb.addWidget(self.count_badge)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.count_eyebrow = label("ĐÃ PHÁT HIỆN", 10, QFont.Bold, TONES["after"][0], 0.6)
        r = QHBoxLayout()
        r.setSpacing(8)
        self.count_value = label("0", 32, QFont.Bold, "#C2410C")
        self.count_text = label("người còn trong lớp", 12, QFont.Normal, TEXT_2)
        r.addWidget(self.count_value)
        r.addWidget(self.count_text, 1, Qt.AlignVCenter)
        col.addWidget(self.count_eyebrow)
        col.addLayout(r)
        cb.addLayout(col, 1)
        self.conf_label = label("", 10, QFont.Normal, FAINT)
        cb.addWidget(self.conf_label, 0, Qt.AlignTop)
        lay.addWidget(self.count_box)

        # ô trạng thái cảnh báo
        self.alert_box = QFrame()
        ab = QHBoxLayout(self.alert_box)
        ab.setContentsMargins(14, 12, 14, 12)
        ab.setSpacing(12)
        self.alert_badge = IconBadge("check-circle", "success", 38, 20, 10)
        ab.addWidget(self.alert_badge, 0, Qt.AlignTop)
        acol = QVBoxLayout()
        acol.setSpacing(2)
        self.alert_title = label("", 13, QFont.Bold, TEXT)
        self.alert_text = label("", 11, QFont.Normal, MUTED, wrap=True)
        acol.addWidget(self.alert_title)
        acol.addWidget(self.alert_text)
        ab.addLayout(acol, 1)
        self.ack_btn = QPushButton("Đã xử lý")
        self.ack_btn.setCursor(Qt.PointingHandCursor)
        self.ack_btn.clicked.connect(self.ack_clicked)
        ab.addWidget(self.ack_btn, 0, Qt.AlignVCenter)
        lay.addWidget(self.alert_box)

        # điều khiển số người khi dùng camera mô phỏng
        self.sim_row = QFrame()
        sr = QHBoxLayout(self.sim_row)
        sr.setContentsMargins(0, 0, 0, 0)
        sr.addWidget(label("Camera mô phỏng – số học sinh còn lại:", 11, QFont.Normal, MUTED))
        sr.addStretch()
        self.sim_people = 2
        self.btn_minus = QPushButton()
        self.btn_minus.setIcon(icons.icon("minus", TEXT_2, 14))
        self.btn_plus = QPushButton()
        self.btn_plus.setIcon(icons.icon("plus", TEXT_2, 14))
        self.sim_value = label("2", 14, QFont.Bold, TEXT)
        self.sim_value.setAlignment(Qt.AlignCenter)
        self.sim_value.setFixedWidth(28)
        for b, d in ((self.btn_minus, -1), (self.btn_plus, 1)):
            b.setFixedSize(32, 30)
            b.setStyleSheet("padding: 0;")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, d=d: self.set_sim_people(self.sim_people + d))
        sr.addWidget(self.btn_minus)
        sr.addWidget(self.sim_value)
        sr.addWidget(self.btn_plus)
        lay.addWidget(self.sim_row)

        # timeline sự kiện
        lay.addWidget(label("NHẬT KÝ SỰ KIỆN", 10, QFont.Bold, FAINT, 0.6))
        self.timeline = EventTimeline()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self.timeline)
        scroll.setMinimumHeight(120)
        lay.addWidget(scroll, 1)

        self.send_btn = QPushButton("  Gửi cảnh báo ngay")
        self.send_btn.setObjectName("primary")
        self.send_btn.setIcon(icons.icon("bell", "white", 18))
        self.send_btn.setMinimumHeight(46)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self.send_clicked)
        lay.addWidget(self.send_btn)
        self.footer = label("", 10, QFont.Normal, FAINT)
        self.footer.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.footer)

        self.set_count(0, None)
        self.set_state("EMPTY")

    def set_sim_people(self, n):
        self.sim_people = max(0, min(6, int(n)))
        self.sim_value.setText(str(self.sim_people))
        self.sim_people_changed.emit(self.sim_people)

    def set_count(self, count, conf):
        self.count_value.setText(str(count))
        tone = "after" if count else "success"
        fg, bg, border = TONES[tone]
        self.count_box.setStyleSheet(f"QFrame {{ background: {bg}; border: 1px solid {border}; border-radius: 14px; }}"
                                     "QLabel { border: none; }")
        self.count_badge.set("users", tone)
        set_color(self.count_eyebrow, fg)
        set_color(self.count_value, "#C2410C" if count else "#15803D")
        self.count_eyebrow.setText("ĐÃ PHÁT HIỆN" if count else "KHÔNG PHÁT HIỆN")
        self.count_text.setText("người còn trong lớp" if count else "lớp học đang trống")
        self.conf_label.setText(f"Độ tin cậy {conf * 100:.0f}%" if conf else "")

    def set_state(self, state, detail=""):
        cfg = {
            "EMPTY": ("success", "check-circle", "Lớp học an toàn", detail or "Không phát hiện người trong lớp."),
            "CONFIRMING": ("warning", "clock", "Đang xác nhận hiện diện", detail),
            "ALERT": ("danger", "alert", "Cần kiểm tra lớp học", detail or
                      "Phát hiện học sinh còn ở lại sau thời gian học quy định."),
            "ACKED": ("neutral", "check", "Giáo viên đã xác nhận", detail or "Đang chờ lớp học trống."),
            "IDLE": ("neutral", "shield", "Chưa giám sát", "Hệ thống tự kích hoạt khi hết giờ học."),
        }[state]
        tone, ic, title, text = cfg
        fg, bg, border = TONES[tone]
        self.alert_box.setStyleSheet(f"QFrame {{ background: {bg}; border: 1px solid {border}; border-radius: 14px; }}"
                                     "QLabel { border: none; }")
        self.alert_badge.set(ic, tone)
        self.alert_title.setText(title)
        set_color(self.alert_title, "#991B1B" if tone == "danger" else TEXT)
        self.alert_text.setText(text)
        self.ack_btn.setVisible(state == "ALERT")
