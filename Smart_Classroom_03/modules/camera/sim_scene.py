"""Camera mô phỏng: vẽ một lớp học bằng OpenCV để trình diễn khi không có webcam."""
import math

import cv2
import numpy as np

W, H = 1280, 720

# Vị trí chỗ ngồi (tâm x, đáy thân người y, tỉ lệ) - dùng cho chế độ ngoài giờ
DESKS = [(90, 450, 520), (760, 1060, 430), (220, 560, 640), (660, 1010, 650), (520, 760, 540)]
# (tâm x, đáy thân người y, tỉ lệ, chỉ số bàn che phía trước)
SEATS = [
    (300, 560, 0.95, 0),
    (880, 470, 0.85, 1),
    (820, 690, 1.05, 3),
    (640, 580, 0.92, 4),
    (400, 680, 1.05, 2),
    (990, 470, 0.85, 1),
]


def _bgr(hex_color):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return (b, g, r)


def _vgradient(h, w, top, bottom):
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    top = np.array(_bgr(top), np.float32)
    bottom = np.array(_bgr(bottom), np.float32)
    return np.repeat(top * (1 - t) + bottom * t, w, axis=1)


class SimScene:
    def __init__(self):
        self.background = self._build_background()
        rng = np.random.default_rng(7)
        self.noise = [rng.integers(-6, 7, (H, W, 1), dtype=np.int16) for _ in range(4)]
        self.frame_no = 0

    # ------------------------------------------------------------------
    def _build_background(self):
        img = np.zeros((H, W, 3), np.float32)
        img[:430] = _vgradient(430, W, "#5d6577", "#4a5162")
        img[430:] = _vgradient(H - 430, W, "#3a3f4c", "#272b35")
        img = img.astype(np.uint8)

        # Cửa sổ bên trái
        cv2.rectangle(img, (0, 0), (330, 450), _bgr("#9eabbc"), -1)
        glow = _vgradient(450, 330, "#b9c4d2", "#8d9aab").astype(np.uint8)
        img[0:450, 0:330] = glow
        for x in (0, 165, 322):
            cv2.rectangle(img, (x, 0), (x + 10, 450), _bgr("#3d4350"), -1)
        for y in (0, 300):
            cv2.rectangle(img, (0, y), (330, y + 10), _bgr("#3d4350"), -1)
        cv2.rectangle(img, (0, 440), (340, 452), _bgr("#2f343f"), -1)

        # Bảng
        cv2.rectangle(img, (440, 210), (870, 410), _bgr("#3a3e48"), -1)
        cv2.rectangle(img, (452, 222), (858, 398), _bgr("#2c3a34"), -1)
        cv2.putText(img, "SMART CLASSROOM", (480, 268), cv2.FONT_HERSHEY_SIMPLEX, 0.62,
                    _bgr("#d7e0da"), 1, cv2.LINE_AA)
        for i, length in enumerate((230, 230, 160)):
            y = 298 + i * 16
            cv2.line(img, (480, y), (480 + length, y), _bgr("#8fa198"), 2, cv2.LINE_AA)

        # Sàn có vệt sáng
        overlay = img.copy()
        pts = np.array([[330, 452], [520, 452], [380, H], [0, H], [0, 600]], np.int32)
        cv2.fillPoly(overlay, [pts], _bgr("#4a505e"))
        img = cv2.addWeighted(overlay, 0.25, img, 0.75, 0)

        # Bàn học
        for x1, x2, y in DESKS:
            img = self._desk(img, x1, x2, y)

        # Vignette
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W / 1.3)) ** 2 + ((yy - H / 2) / (H / 1.2)) ** 2)
        vign = np.clip(1.05 - d * 0.55, 0.55, 1.0)[..., None]
        return (img.astype(np.float32) * vign).astype(np.uint8)

    @staticmethod
    def _desk(img, x1, x2, y):
        cv2.rectangle(img, (x1, y), (x2, y + 12), _bgr("#6e6a66"), -1)
        cv2.rectangle(img, (x1, y + 12), (x2, y + 16), _bgr("#45423f"), -1)
        for lx in (x1 + 8, x2 - 30):
            cv2.rectangle(img, (lx, y + 16), (lx + 22, y + 75), _bgr("#262930"), -1)
        return img

    @staticmethod
    def _person(img, cx, bottom, scale, sway=0.0, arm=None):
        """Vẽ bóng người; trả về bbox (x1, y1, x2, y2) pixel."""
        cx = int(cx + sway)
        head_r = int(26 * scale)
        body_w = int(70 * scale)
        body_h = int(115 * scale)
        top = bottom - body_h
        body_col = _bgr("#2f3647")
        # thân
        cv2.ellipse(img, (cx, top + int(28 * scale)), (body_w // 2, int(30 * scale)), 0, 180, 360, body_col, -1)
        cv2.rectangle(img, (cx - body_w // 2, top + int(28 * scale)), (cx + body_w // 2, bottom), body_col, -1)
        # vệt sáng trên vai
        cv2.ellipse(img, (cx - int(10 * scale), top + int(30 * scale)), (int(18 * scale), int(10 * scale)),
                    0, 180, 330, _bgr("#465068"), -1)
        # đầu
        hy = top - int(4 * scale)
        cv2.circle(img, (cx, hy), head_r, _bgr("#1d222c"), -1, cv2.LINE_AA)
        x1, y1 = cx - body_w // 2 - 6, hy - head_r - 6
        x2, y2 = cx + body_w // 2 + 6, bottom
        if arm is not None:  # tay chỉ lên bảng
            sx, sy = cx - body_w // 2 + 6, top + int(40 * scale)
            ex = sx - int(60 * scale)
            ey = sy - int(25 * scale) + int(arm * 10)
            cv2.line(img, (sx, sy), (ex, ey), body_col, int(16 * scale), cv2.LINE_AA)
            x1 = min(x1, ex - 10)
        return x1, y1, x2, y2

    # ------------------------------------------------------------------
    def render(self, mode, people=2):
        """Trả về (frame_bgr, boxes chuẩn hoá [(x1,y1,x2,y2,conf,kind)])."""
        self.frame_no += 1
        t = self.frame_no / 30.0
        img = self.background.copy()
        boxes = []
        if mode == "CLASS":
            sway = 25 * math.sin(t * 0.6)
            box = self._person(img, 640, 455, 1.0, sway=sway, arm=math.sin(t * 2.0))
            boxes.append(self._norm(box, 0.95 + 0.03 * math.sin(t), "presenter"))
        else:
            seated = list(enumerate(SEATS[:max(0, min(people, len(SEATS)))]))
            for i, (cx, bottom, sc, desk) in sorted(seated, key=lambda s: s[1][1]):
                sway = 4 * math.sin(t * (0.7 + i * 0.2) + i)
                box = self._person(img, cx, bottom, sc, sway=sway)
                self._desk(img, *DESKS[desk])          # bàn che phần thân dưới
                conf = 0.9 + 0.06 * math.sin(t * 0.8 + i * 1.7)
                boxes.append(self._norm(box, conf, "student"))
        noisy = img.astype(np.int16) + self.noise[self.frame_no % 4]
        return np.clip(noisy, 0, 255).astype(np.uint8), boxes

    @staticmethod
    def _norm(box, conf, kind):
        x1, y1, x2, y2 = box
        return (max(0, x1) / W, max(0, y1) / H, min(W, x2) / W, min(H, y2) / H, float(conf), kind)
