"""Nhận diện cử chỉ tay bằng MediaPipe Hands.

Cử chỉ hỗ trợ (ảnh đã lật gương nên trái/phải đúng theo người đứng trước camera):
  - Vuốt bàn tay mở sang trái / sang phải  -> slide tiếp / slide trước (đổi được trong Cài đặt)
  - Giơ 1 ngón trỏ (giữ ~0.3 s)            -> slide tiếp
  - Giơ 2 ngón (chữ V)                     -> slide trước
  - Nắm tay giữ 1 giây                     -> bắt đầu / dừng trình chiếu
"""
import math
import time
from collections import deque

try:
    import mediapipe as mp
except ImportError:  # chưa cài
    mp = None

NEXT, PREV, TOGGLE = "NEXT", "PREVIOUS", "TOGGLE_SHOW"

POSE_TEXT = {
    "NONE": "Chưa thấy tay",
    "OPEN": "Bàn tay mở",
    "FIST": "Nắm tay",
    "POINT": "Giơ ngón trỏ",
    "VICTORY": "Giơ 2 ngón",
    "OTHER": "Đang nhận diện",
}


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class GestureModule:
    def __init__(self, swipe_left_is_next=True, cooldown=0.9):
        if mp is None:
            raise RuntimeError("Chưa cài MediaPipe. Chạy: pip install mediapipe==0.10.21")
        if not hasattr(mp, "solutions"):
            raise RuntimeError(
                "Bản MediaPipe này không còn API mp.solutions. Hãy cài mediapipe==0.10.21 "
                "(Python 3.9–3.12) và đảm bảo project không có file tên mediapipe.py."
            )
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        )
        self.swipe_left_is_next = swipe_left_is_next
        self.cooldown = cooldown
        self.track = deque(maxlen=20)      # (t, cx, cy)
        self.poses = deque(maxlen=8)
        self.last_command_at = 0.0
        self.fist_since = None
        self.static_armed = True

    # ------------------------------------------------------------------
    def process(self, frame_rgb):
        """Trả về dict: landmarks (list[(x,y)] chuẩn hoá) | None, pose, command, score."""
        result = self.hands.process(frame_rgb)
        now = time.monotonic()
        if not result.multi_hand_landmarks:
            self.track.clear()
            self.poses.append("NONE")
            self.fist_since = None
            self._maybe_rearm()
            return {"landmarks": None, "pose": "NONE", "command": None, "score": 0.0}

        lm = [(p.x, p.y) for p in result.multi_hand_landmarks[0].landmark]
        score = 0.0
        if result.multi_handedness:
            score = float(result.multi_handedness[0].classification[0].score)
        pose = self.classify(lm)
        self.poses.append(pose)
        cx = sum(lm[i][0] for i in (0, 5, 9, 13, 17)) / 5
        cy = sum(lm[i][1] for i in (0, 5, 9, 13, 17)) / 5
        self.track.append((now, cx, cy))

        command = None
        if now - self.last_command_at >= self.cooldown:
            command = self._detect_swipe(now, pose) or self._detect_static(now, pose)
            if command:
                self.last_command_at = now
                self.track.clear()
        self._maybe_rearm()
        return {"landmarks": lm, "pose": pose, "command": command, "score": score}

    # ------------------------------------------------------------------
    @staticmethod
    def classify(lm):
        wrist = lm[0]
        extended = [
            _dist(lm[tip], wrist) > _dist(lm[pip], wrist) * 1.12
            for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18))
        ]
        n = sum(extended)
        if n >= 4:
            return "OPEN"
        if n == 0:
            return "FIST"
        if extended == [True, False, False, False]:
            return "POINT"
        if extended == [True, True, False, False]:
            return "VICTORY"
        return "OTHER"

    def _detect_swipe(self, now, pose):
        if pose not in ("OPEN", "OTHER") or len(self.track) < 4:
            return None
        window = [p for p in self.track if now - p[0] <= 0.5]
        if len(window) < 4:
            return None
        dx = window[-1][1] - window[0][1]
        dy = window[-1][2] - window[0][2]
        if abs(dx) < 0.20 or abs(dx) < 2 * abs(dy):
            return None
        swipe_left = dx < 0
        if swipe_left == self.swipe_left_is_next:
            return NEXT
        return PREV

    def _detect_static(self, now, pose):
        if pose == "FIST":
            if self.fist_since is None:
                self.fist_since = now
            elif now - self.fist_since >= 1.0 and self.static_armed:
                self.static_armed = False
                self.fist_since = None
                return TOGGLE
            return None
        self.fist_since = None
        recent = list(self.poses)[-6:]
        if not self.static_armed or len(recent) < 6 or any(p != pose for p in recent):
            return None
        if pose == "POINT":
            self.static_armed = False
            return NEXT
        if pose == "VICTORY":
            self.static_armed = False
            return PREV
        return None

    def _maybe_rearm(self):
        recent = list(self.poses)[-3:]
        if len(recent) == 3 and all(p in ("OPEN", "NONE") for p in recent):
            self.static_armed = True

    def close(self):
        if self.hands:
            self.hands.close()
            self.hands = None
