"""Các widget giao diện tự vẽ: thẻ, nhãn trạng thái, khung camera, thanh thời gian, timeline."""
import math
import time

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath,
                           QPen, QRadialGradient)
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QHBoxLayout,
                               QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from core.config import minutes_to_hhmm
from ui import icons
from ui.theme import FAINT, MUTED, TEXT, TONES, font


def label(text="", px=13, weight=QFont.Normal, color=TEXT, spacing=0.0, wrap=False, mono=False):
    lbl = QLabel(text)
    lbl.setFont(font(px, weight, spacing, mono))
    lbl.setStyleSheet(f"color: {color};")
    lbl.setWordWrap(wrap)
    return lbl


def set_color(lbl, color):
    lbl.setStyleSheet(f"color: {color};")


class Card(QFrame):
    def __init__(self, parent=None, shadow=True, name="card"):
        super().__init__(parent)
        self.setObjectName(name)
        if shadow:
            eff = QGraphicsDropShadowEffect(self)
            eff.setBlurRadius(30)
            eff.setOffset(0, 6)
            eff.setColor(QColor(15, 23, 42, 16))
            self.setGraphicsEffect(eff)


class IconBadge(QLabel):
    def __init__(self, name="check", tone="class", size=40, icon_size=20, radius=12):
        super().__init__()
        self._size, self._icon_size, self._radius = size, icon_size, radius
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.set(name, tone)

    def set(self, name, tone):
        fg, bg, border = TONES.get(tone, TONES["neutral"])
        self.setStyleSheet(f"background: {bg}; border: 1px solid {border}; border-radius: {self._radius}px;")
        self.setPixmap(icons.pixmap(name, fg, self._icon_size))


class Pill(QLabel):
    """Nhãn trạng thái nhỏ có chấm màu, ví dụ: ● Đang hoạt động."""

    def __init__(self, text="", tone="success"):
        super().__init__()
        self.setFont(font(11, QFont.DemiBold))
        self.set(text, tone)

    def set(self, text, tone):
        fg, bg, border = TONES.get(tone, TONES["neutral"])
        self.setText(f'<span style="color:{fg}; font-size:13px;">●</span>&nbsp;{text}')
        self.setStyleSheet(f"color: {fg}; background: {bg}; border: 1px solid {border};"
                           f"border-radius: 11px; padding: 3px 10px;")


class StatCard(Card):
    def __init__(self, icon_name, title, value, tone="class"):
        super().__init__(shadow=False)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)
        self.badge = IconBadge(icon_name, tone, 38, 18, 10)
        lay.addWidget(self.badge)
        col = QVBoxLayout()
        col.setSpacing(2)
        self.title = label(title.upper(), 10, QFont.Bold, FAINT, 0.6)
        self.value = label(value, 14, QFont.DemiBold, TEXT)
        col.addWidget(self.title)
        col.addWidget(self.value)
        lay.addLayout(col, 1)
        self.icon_name = icon_name

    def set(self, value, tone=None, icon_name=None):
        self.value.setText(value)
        if tone or icon_name:
            self.icon_name = icon_name or self.icon_name
            self.badge.set(self.icon_name, tone or "class")


class ModeSwitch(QFrame):
    requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("segment")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        self.buttons = {}
        for mode, text, ic in (("CLASS", "Trong giờ học", "presentation"), ("AFTER", "Ngoài giờ", "shield-check")):
            b = QPushButton(text)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setIconSize(QSize(18, 18))
            b.setProperty("ic", ic)
            b.clicked.connect(lambda _=False, m=mode: self.requested.emit(m))
            lay.addWidget(b)
            self.buttons[mode] = b
        self.set_mode("CLASS")

    def set_mode(self, mode):
        accent = TONES["class" if mode == "CLASS" else "after"][0]
        for m, b in self.buttons.items():
            b.setChecked(m == mode)
            b.setIcon(icons.icon(b.property("ic"), accent if m == mode else MUTED, 18))


# ---------------------------------------------------------------------------
class TimelineSlider(QWidget):
    """Thanh thời gian 07:00 → 20:00, có mốc kết thúc giờ học, kéo được để tua."""

    seek = Signal(float)

    def __init__(self):
        super().__init__()
        self.start, self.end, self.split = 7 * 60, 20 * 60, 17 * 60
        self.value = 16 * 60
        self.mode = "CLASS"
        self.setMinimumHeight(54)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_range(self, start, end, split):
        self.start, self.end, self.split = start, max(end, start + 60), split
        self.update()

    def set_value(self, minute, mode):
        self.value, self.mode = minute, mode
        self.update()

    def _x(self, minute, rect):
        t = (min(max(minute, self.start), self.end) - self.start) / (self.end - self.start)
        return rect.left() + t * rect.width()

    def _track(self):
        return QRectF(12, 34, self.width() - 24, 6)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self._track()
        sx = self._x(self.split, r)
        mid_text = f"{minutes_to_hhmm(self.split)} · KẾT THÚC GIỜ HỌC"
        p.setFont(font(10, QFont.Bold, 0.4))
        mid_w = QFontMetrics(p.font()).horizontalAdvance(mid_text) + 4
        mid_x = min(max(sx - mid_w / 2, r.left()), r.right() - mid_w)
        p.setPen(QColor(TONES["after"][0]))
        p.drawText(QRectF(mid_x, 4, mid_w, 16), Qt.AlignCenter, mid_text)
        p.setFont(font(10, QFont.DemiBold))
        p.setPen(QColor(FAINT))
        if mid_x > r.left() + 44:
            p.drawText(QRectF(r.left(), 4, 80, 16), Qt.AlignLeft, minutes_to_hhmm(self.start))
        if mid_x + mid_w < r.right() - 44:
            p.drawText(QRectF(r.right() - 80, 4, 80, 16), Qt.AlignRight, minutes_to_hhmm(self.end))

        # nền: vùng trong giờ (xanh nhạt) và ngoài giờ (cam nhạt)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#DCE3FB"))
        p.drawRoundedRect(QRectF(r.left(), r.top(), sx - r.left(), r.height()), 3, 3)
        p.setBrush(QColor("#FBE2C8"))
        p.drawRoundedRect(QRectF(sx, r.top(), r.right() - sx, r.height()), 3, 3)

        vx = self._x(self.value, r)
        p.setBrush(QColor("#5B78E3"))
        p.drawRoundedRect(QRectF(r.left(), r.top(), min(vx, sx) - r.left(), r.height()), 3, 3)
        if vx > sx:
            p.setBrush(QColor("#E8964A"))
            p.drawRoundedRect(QRectF(sx, r.top(), vx - sx, r.height()), 3, 3)

        # vạch mốc tan học
        p.setBrush(QColor(TONES["after"][0]))
        p.drawRoundedRect(QRectF(sx - 1.5, r.top() - 5, 3, r.height() + 10), 1.5, 1.5)

        # tay nắm
        accent = QColor(TONES["class" if self.mode == "CLASS" else "after"][0])
        c = QPointF(vx, r.center().y())
        p.setBrush(QColor(0, 0, 0, 30))
        p.drawEllipse(c + QPointF(0, 1.5), 10, 10)
        p.setBrush(QColor("white"))
        p.drawEllipse(c, 10, 10)
        p.setBrush(accent)
        p.drawEllipse(c, 6.5, 6.5)
        p.end()

    def _seek(self, x):
        r = self._track()
        t = min(max((x - r.left()) / r.width(), 0), 1)
        self.seek.emit(self.start + t * (self.end - self.start))

    def mousePressEvent(self, e):
        self._seek(e.position().x())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self._seek(e.position().x())


# ---------------------------------------------------------------------------
class EventTimeline(QWidget):
    """Dòng sự kiện dạng timeline dọc (mới nhất ở trên)."""

    ROW = 50

    def __init__(self, max_items=60):
        super().__init__()
        self.items = []   # (time, title, detail, tone)
        self.max_items = max_items
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    def add(self, time_text, title, detail="", tone="neutral"):
        self.items.insert(0, (time_text, title, detail, tone))
        del self.items[self.max_items:]
        self.setMinimumHeight(max(1, len(self.items)) * self.ROW)
        self.updateGeometry()
        self.update()

    def clear(self):
        self.items.clear()
        self.update()

    def sizeHint(self):
        return QSize(300, max(1, len(self.items)) * self.ROW)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.items:
            p.setPen(QColor(FAINT))
            p.setFont(font(12))
            p.drawText(self.rect(), Qt.AlignCenter, "Chưa có sự kiện")
            return
        dot_x = 66
        fm_detail = QFontMetrics(font(11))
        for i, (t, title, detail, tone) in enumerate(self.items):
            y = i * self.ROW
            fg, bg, border = TONES.get(tone, TONES["neutral"])
            if i < len(self.items) - 1:
                p.setPen(QPen(QColor("#E5E9F0"), 1.5))
                p.drawLine(QPointF(dot_x, y + 16), QPointF(dot_x, y + self.ROW + 6))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(bg))
            p.setPen(QPen(QColor(border), 1))
            p.drawEllipse(QPointF(dot_x, y + 9), 7, 7)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(fg))
            p.drawEllipse(QPointF(dot_x, y + 9), 3.2, 3.2)
            p.setPen(QColor(FAINT))
            p.setFont(font(10, QFont.Medium, mono=True))
            p.drawText(QRectF(0, y + 1, 52, 16), Qt.AlignLeft | Qt.AlignVCenter, t)
            p.setPen(QColor(TEXT))
            p.setFont(font(12, QFont.DemiBold))
            p.drawText(QRectF(dot_x + 16, y, self.width() - dot_x - 16, 18), Qt.AlignLeft | Qt.AlignVCenter, title)
            p.setPen(QColor(MUTED))
            p.setFont(font(11))
            text = fm_detail.elidedText(detail, Qt.ElideRight, int(self.width() - dot_x - 18))
            p.drawText(QRectF(dot_x + 16, y + 19, self.width() - dot_x - 16, 16), Qt.AlignLeft | Qt.AlignVCenter, text)
        p.end()


# ---------------------------------------------------------------------------
class HandIndicator(QWidget):
    """Vòng tròn có biểu tượng bàn tay, nhấp nháy khi thấy tay, loé xanh khi nhận lệnh."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(100)
        self.state = "idle"       # idle | tracking | fired | off
        self.icon_name = "hand"
        self.flash_until = 0.0
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def set_state(self, state, icon_name="hand"):
        if state == "fired":
            self.flash_until = time.monotonic() + 0.7
        self.state, self.icon_name = state, icon_name
        self.update()

    def _tick(self):
        if self.isVisible():
            self._phase = (self._phase + 0.04) % 1.0
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        flashing = time.monotonic() < self.flash_until
        if flashing:
            fg = QColor(TONES["success"][0])
        elif self.state == "off":
            fg = QColor(FAINT)
        else:
            fg = QColor(TONES["class"][0])
        # vòng nét đứt ngoài
        pen = QPen(QColor(fg.red(), fg.green(), fg.blue(), 70), 1.2, Qt.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, 44, 44)
        # sóng lan toả khi đang theo dõi tay
        if self.state == "tracking" or flashing:
            for k in (0.0, 0.5):
                ph = (self._phase + k) % 1.0
                col = QColor(fg)
                col.setAlpha(int(90 * (1 - ph)))
                p.setPen(QPen(col, 2))
                p.drawEllipse(c, 32 + 16 * ph, 32 + 16 * ph)
        p.setPen(QPen(QColor(fg.red(), fg.green(), fg.blue(), 60), 1))
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(c, 32, 32)
        p.setPen(Qt.NoPen)
        soft = QColor(fg)
        soft.setAlpha(28)
        p.setBrush(soft)
        p.drawEllipse(c, 32, 32)
        icons.paint_icon(p, "check" if flashing else self.icon_name,
                         QRectF(c.x() - 17, c.y() - 17, 34, 34), fg.name(), 2.0)
        p.end()


# ---------------------------------------------------------------------------
class SlidePreview(QWidget):
    """Thẻ xem trước bài trình chiếu (nền xanh đậm như ảnh mẫu)."""

    def __init__(self):
        super().__init__()
        self.title = "Chưa kết nối PowerPoint"
        self.sub = "POWERPOINT"
        self.progress = 0.0
        self.setMinimumSize(200, 104)

    def set_info(self, title, sub, progress):
        self.title, self.sub, self.progress = title, sub, progress
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor("#24315E"))
        g.setColorAt(1, QColor("#141A33"))
        p.fillPath(path, g)
        p.setClipPath(path)
        rg = QRadialGradient(QPointF(r.right() - 50, r.top() + 20), 90)
        rg.setColorAt(0, QColor(110, 140, 255, 110))
        rg.setColorAt(1, QColor(110, 140, 255, 0))
        p.fillRect(r, rg)
        p.setPen(QColor("#9DB0F5"))
        p.setFont(font(9, QFont.Bold, 0.8))
        p.drawText(QRectF(14, 14, r.width() - 28, 14), Qt.AlignLeft, self.sub.upper())
        p.setPen(QColor("white"))
        p.setFont(font(14, QFont.DemiBold))
        fm = QFontMetrics(p.font())
        p.drawText(QRectF(14, 32, r.width() - 28, 22), Qt.AlignLeft,
                   fm.elidedText(self.title, Qt.ElideRight, int(r.width() - 28)))
        # biểu đồ cột trang trí, cột cuối thể hiện tiến độ bài
        base = r.bottom() - 12
        heights = [10, 16, 22, max(8.0, 34 * self.progress)]
        for i, h in enumerate(heights):
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#5BD69A") if i == 3 else QColor("#7C92F0"))
            p.drawRoundedRect(QRectF(14 + i * 13, base - h, 9, h), 2, 2)
        p.end()


# ---------------------------------------------------------------------------
class VideoView(QWidget):
    """Khung camera bo góc với các lớp phủ: nhãn camera, FPS, khung người, bàn tay, cảnh báo."""

    HAND_EDGES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11),
                  (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]

    def __init__(self):
        super().__init__()
        self.image = None
        self.overlay = {}
        self.mode = "CLASS"
        self.camera_text = "CAM 01 · TOÀN CẢNH LỚP"
        self.room_code = ""
        self.signal_ok = True
        self.alert = False
        self.banner = None        # (text, tone, until)
        self.gesture_flash = None  # (text, until)
        self.setMinimumSize(560, 330)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._pulse = QTimer(self)
        self._pulse.timeout.connect(self.update)
        self._pulse.start(50)

    def set_frame(self, image, overlay):
        self.image, self.overlay = image, overlay

    def show_banner(self, text, tone="class", seconds=2.5):
        self.banner = (text, tone, time.monotonic() + seconds)

    def flash_gesture(self, text):
        self.gesture_flash = (text, time.monotonic() + 1.0)

    # -- toạ độ: ảnh được phủ kín khung (cover) --
    def _mapping(self, r):
        if self.image is None:
            return 1.0, 0.0, 0.0, 1, 1
        iw, ih = self.image.width(), self.image.height()
        s = max(r.width() / iw, r.height() / ih)
        ox = r.left() + (r.width() - iw * s) / 2
        oy = r.top() + (r.height() - ih * s) / 2
        return s, ox, oy, iw, ih

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(r, 18, 18)
        p.fillPath(path, QColor("#1B2030"))
        p.save()
        p.setClipPath(path)

        if self.image is not None:
            s, ox, oy, iw, ih = self._mapping(r)
            p.drawImage(QRectF(ox, oy, iw * s, ih * s), self.image)

            def pt(nx, ny):
                return QPointF(ox + nx * iw * s, oy + ny * ih * s)

            self._draw_boxes(p, pt)
            self._draw_hand(p, pt)
        else:
            p.setPen(QColor("#94A3B8"))
            p.setFont(font(15, QFont.DemiBold))
            p.drawText(r, Qt.AlignCenter, "Đang khởi động camera…")

        # lớp tối nhẹ phía trên/dưới để chữ dễ đọc
        for top in (True, False):
            g = QLinearGradient(0, r.top() if top else r.bottom(), 0, r.top() + 70 if top else r.bottom() - 70)
            g.setColorAt(0, QColor(10, 14, 25, 120))
            g.setColorAt(1, QColor(10, 14, 25, 0))
            p.fillRect(QRectF(r.left(), r.top() if top else r.bottom() - 70, r.width(), 70), g)

        self._draw_chrome(p, r)
        self._draw_flash(p, r)
        p.restore()

        if self.alert:   # viền đỏ nhấp nháy
            a = 0.55 + 0.45 * math.sin(time.monotonic() * 6)
            p.setPen(QPen(QColor(239, 68, 68, int(255 * a)), 4))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 17, 17)
        p.end()

    def _draw_boxes(self, p, pt):
        boxes = self.overlay.get("boxes") or []
        students = 0
        for b in boxes:
            x1, y1, x2, y2, conf = b[:5]
            kind = b[5] if len(b) > 5 else "student"
            if kind == "presenter":
                col, text = QColor("#5BD69A"), "NGƯỜI THUYẾT TRÌNH"
            else:
                students += 1
                col, text = QColor("#F59E2B"), f"HỌC SINH {students:02d}"
            a, b2 = pt(x1, y1), pt(x2, y2)
            rect = QRectF(a, b2)
            fill = QColor(col)
            fill.setAlpha(28)
            p.setPen(QPen(col, 2))
            p.setBrush(fill)
            p.drawRect(rect)
            p.setFont(font(9, QFont.Bold, 0.5))
            fm = QFontMetrics(p.font())
            tw = fm.horizontalAdvance(text) + 12
            tag = QRectF(rect.left() - 1, rect.top() - 18, tw, 17)
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawRect(tag)
            p.setPen(QColor("#1A1F2B"))
            p.drawText(tag, Qt.AlignCenter, text)
            p.setPen(col)
            p.setFont(font(10, QFont.Bold))
            p.drawText(QRectF(rect.right() - 44, rect.bottom() - 17, 40, 14), Qt.AlignRight,
                       f"{int(conf * 100)}%")

    def _draw_hand(self, p, pt):
        hand = self.overlay.get("hand")
        if not hand:
            return
        pts = [pt(x, y) for x, y in hand]
        xs = [q.x() for q in pts]
        ys = [q.y() for q in pts]
        box = QRectF(min(xs) - 14, min(ys) - 14, max(xs) - min(xs) + 28, max(ys) - min(ys) + 28)
        col = QColor("#5BD69A")
        p.setPen(QPen(col, 2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(box, 8, 8)
        p.setPen(QPen(QColor(255, 255, 255, 200), 2))
        for a, b in self.HAND_EDGES:
            p.drawLine(pts[a], pts[b])
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        for q in pts:
            p.drawEllipse(q, 3.5, 3.5)
        from modules.gesture_control.gesture_module import POSE_TEXT
        text = POSE_TEXT.get(self.overlay.get("pose"), "")
        if text:
            p.setFont(font(10, QFont.Bold, 0.4))
            fm = QFontMetrics(p.font())
            tag = QRectF(box.left(), box.top() - 20, fm.horizontalAdvance(text.upper()) + 14, 18)
            p.setBrush(col)
            p.drawRoundedRect(tag, 4, 4)
            p.setPen(QColor("#10231A"))
            p.drawText(tag, Qt.AlignCenter, text.upper())

    def _chip(self, p, rect, text, dot=None):
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.setBrush(QColor(15, 20, 32, 165))
        p.drawRoundedRect(rect, 8, 8)
        x = rect.left() + 12
        if dot:
            p.setPen(Qt.NoPen)
            col = QColor(dot)
            col.setAlpha(int(155 + 100 * abs(math.sin(time.monotonic() * 2.5))))
            p.setBrush(col)
            p.drawEllipse(QPointF(x + 3, rect.center().y()), 4, 4)
            x += 14
        p.setPen(QColor("#E8ECF5"))
        p.drawText(QRectF(x, rect.top(), rect.width(), rect.height()), Qt.AlignVCenter | Qt.AlignLeft, text)

    def _draw_chrome(self, p, r):
        p.setFont(font(11, QFont.Bold, 0.4))
        fm = QFontMetrics(p.font())
        cam = self.camera_text.upper()
        self._chip(p, QRectF(r.left() + 16, r.top() + 16, fm.horizontalAdvance(cam) + 40, 30), cam,
                   dot="#EF4444" if self.signal_ok else "#94A3B8")

        w, h = self.overlay.get("size", (0, 0))
        fps = self.overlay.get("fps", 0) or 0
        p.setFont(font(11, QFont.Bold, 1.0, mono=True))
        p.setPen(QColor("#E8ECF5"))
        res = f"{h}P · {fps:.0f} FPS" if h else "— · — FPS"
        p.drawText(QRectF(r.right() - 260, r.top() + 16, 244, 30), Qt.AlignRight | Qt.AlignVCenter, res)

        p.setFont(font(11, QFont.DemiBold))
        ic = "wifi" if self.signal_ok else "wifi-off"
        icons.paint_icon(p, ic, QRectF(r.left() + 18, r.bottom() - 32, 16, 16),
                         "#D6DCE8" if self.signal_ok else "#FCA5A5")
        p.setPen(QColor("#D6DCE8"))
        p.drawText(QRectF(r.left() + 42, r.bottom() - 36, 200, 24), Qt.AlignVCenter,
                   "Tín hiệu tốt" if self.signal_ok else "Mất tín hiệu")
        p.setFont(font(11, QFont.Bold, 1.0, mono=True))
        p.drawText(QRectF(r.right() - 260, r.bottom() - 36, 244, 24), Qt.AlignRight | Qt.AlignVCenter,
                   self.room_code)

    def _draw_flash(self, p, r):
        now = time.monotonic()
        if self.gesture_flash and now < self.gesture_flash[1]:
            text = self.gesture_flash[0]
            alpha = min(1.0, (self.gesture_flash[1] - now) / 0.4)
            p.setFont(font(20, QFont.Bold))
            fm = QFontMetrics(p.font())
            rect = QRectF(0, 0, fm.horizontalAdvance(text) + 48, 54)
            rect.moveCenter(QPointF(r.center().x(), r.top() + 90))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(59, 91, 219, int(225 * alpha)))
            p.drawRoundedRect(rect, 14, 14)
            p.setPen(QColor(255, 255, 255, int(255 * alpha)))
            p.drawText(rect, Qt.AlignCenter, text)
        if self.banner and now < self.banner[2]:
            text, tone, until = self.banner
            alpha = min(1.0, (until - now) / 0.5)
            fg = QColor(TONES.get(tone, TONES["class"])[0])
            p.setFont(font(15, QFont.DemiBold))
            fm = QFontMetrics(p.font())
            rect = QRectF(0, 0, fm.horizontalAdvance(text) + 60, 48)
            rect.moveCenter(QPointF(r.center().x(), r.bottom() - 70))
            p.setPen(Qt.NoPen)
            bg = QColor(255, 255, 255, int(235 * alpha))
            p.setBrush(bg)
            p.drawRoundedRect(rect, 24, 24)
            fg.setAlpha(int(255 * alpha))
            p.setBrush(fg)
            p.drawEllipse(QPointF(rect.left() + 24, rect.center().y()), 5, 5)
            p.setPen(QColor(15, 23, 42, int(255 * alpha)))
            p.drawText(rect.adjusted(36, 0, -12, 0), Qt.AlignVCenter | Qt.AlignLeft, text)


# ---------------------------------------------------------------------------
class Toast(QFrame):
    """Thông báo nổi góc trên phải, tự ẩn."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 18, 12)
        lay.setSpacing(12)
        self.badge = IconBadge("bell", "danger", 36, 18, 10)
        lay.addWidget(self.badge)
        col = QVBoxLayout()
        col.setSpacing(2)
        self.title = label("", 13, QFont.Bold)
        self.text = label("", 12, QFont.Normal, MUTED, wrap=True)
        col.addWidget(self.title)
        col.addWidget(self.text)
        lay.addLayout(col, 1)
        self.setFixedWidth(380)
        eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(eff)
        self._anim = QPropertyAnimation(eff, b"opacity", self)
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)
        self._anim.finished.connect(self._on_anim_done)
        self.anchor = None        # widget để căn vị trí (khung camera)
        self.hide()

    def reposition(self):
        par = self.parentWidget()
        if self.anchor is not None:
            top_left = self.anchor.mapTo(par, self.anchor.rect().topLeft())
            self.move(top_left.x() + (self.anchor.width() - self.width()) // 2, top_left.y() + 58)
        else:
            self.move(par.width() - self.width() - 28, 96)

    def _on_anim_done(self):
        if self._anim.endValue() == 0.0:
            self.hide()

    def show_message(self, title, text, tone="danger", icon_name="bell", seconds=4.0):
        fg, bg, border = TONES.get(tone, TONES["neutral"])
        self.setStyleSheet(f"QFrame#toast {{ background: white; border: 1px solid {border};"
                           f" border-left: 4px solid {fg}; border-radius: 12px; }}")
        self.badge.set(icon_name, tone)
        self.title.setText(title)
        self.text.setText(text)
        self.adjustSize()
        self.reposition()
        self.raise_()
        self.show()
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self._hide_timer.start(int(seconds * 1000))

    def _fade_out(self):
        self._anim.stop()
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()
