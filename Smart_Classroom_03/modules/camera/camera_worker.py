"""Luồng camera chạy nền (QThread) để giao diện không bị giật.

- Chế độ CLASS: chỉ chạy MediaPipe (nhận diện cử chỉ).
- Chế độ AFTER: chỉ chạy bộ phát hiện người (YOLO) theo chu kỳ quét.
- Không mở được webcam: tự chuyển sang camera mô phỏng (nếu nguồn = auto/sim).
"""
import sys
import time

import cv2
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from modules.camera.sim_scene import SimScene


class CameraWorker(QThread):
    frame_ready = Signal(QImage, dict)
    source_changed = Signal(dict)       # {"kind": "webcam"/"sim"/"none", "text": ...}
    log = Signal(str, str, str)         # level, title, detail
    gesture_command = Signal(str)
    engine_status = Signal(str, str)    # engine ("gesture"/"person"), trạng thái

    def __init__(self, config, mode="CLASS"):
        super().__init__()
        self.cfg = config
        self.mode = mode
        self.sim_people = 2
        self._running = True
        self._gesture = None
        self._gesture_failed = False
        self._detector = None
        self._detector_failed = False

    # gọi từ luồng giao diện (gán thuộc tính đơn giản là an toàn)
    def set_mode(self, mode):
        self.mode = mode

    def stop(self):
        self._running = False
        self.wait(3000)

    # ------------------------------------------------------------------
    def _open_webcam(self):
        if self.cfg.camera_source == "sim":
            return None
        indices = [int(self.cfg.camera_index)] + [i for i in range(4) if i != int(self.cfg.camera_index)]
        if sys.platform.startswith("win"):
            backends = [("DirectShow", cv2.CAP_DSHOW), ("Media Foundation", cv2.CAP_MSMF)]
        else:
            backends = [("mặc định", cv2.CAP_ANY)]
        for idx in indices:
            for name, backend in backends:
                if not self._running:
                    return None
                cap = cv2.VideoCapture(idx, backend)
                if not cap.isOpened():
                    cap.release()
                    continue
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                ok, frame = cap.read()
                if ok and frame is not None and frame.size:
                    self.log.emit("info", "Đã kết nối webcam", f"Camera số {idx} ({name}), {frame.shape[1]}×{frame.shape[0]}")
                    self.source_changed.emit({"kind": "webcam", "text": f"Webcam {idx}",
                                              "size": f"{frame.shape[1]}×{frame.shape[0]}"})
                    return cap
                cap.release()
        return None

    def _ensure_gesture(self):
        if self._gesture is None and not self._gesture_failed:
            try:
                from modules.gesture_control.gesture_module import GestureModule
                self._gesture = GestureModule(swipe_left_is_next=self.cfg.swipe_left_is_next)
                self.engine_status.emit("gesture", "ready")
                self.log.emit("success", "MediaPipe sẵn sàng", "Đưa tay vào khung hình để điều khiển slide")
            except Exception as exc:
                self._gesture_failed = True
                self.engine_status.emit("gesture", "error")
                self.log.emit("danger", "Không khởi động được MediaPipe", str(exc))
        return self._gesture

    def _ensure_detector(self):
        if self._detector is None and not self._detector_failed:
            self.engine_status.emit("person", "loading")
            try:
                from modules.classroom_monitor.person_detector import PersonDetector
                self._detector = PersonDetector(self.cfg.yolo_model, self.cfg.yolo_confidence)
                self.engine_status.emit("person", self._detector.backend)
                if self._detector.note:
                    self.log.emit("warning", "Dùng bộ phát hiện dự phòng", self._detector.note)
                else:
                    self.log.emit("success", "YOLO sẵn sàng", f"Model {self.cfg.yolo_model}")
            except Exception as exc:
                self._detector_failed = True
                self.engine_status.emit("person", "error")
                self.log.emit("danger", "Không khởi động được bộ phát hiện người", str(exc))
        return self._detector

    # ------------------------------------------------------------------
    def run(self):
        cap = self._open_webcam()
        scene = None
        if cap is None:
            if self.cfg.camera_source == "webcam":
                self.log.emit("danger", "Không mở được webcam",
                              "Hãy đóng ứng dụng khác đang dùng camera hoặc đổi số camera trong Cài đặt")
                self.source_changed.emit({"kind": "none", "text": "Mất tín hiệu", "size": "—"})
            else:
                if self.cfg.camera_source == "auto":
                    self.log.emit("warning", "Không tìm thấy webcam", "Đang dùng camera mô phỏng để trình diễn")
                scene = SimScene()
                self.source_changed.emit({"kind": "sim", "text": "Camera mô phỏng", "size": "1280×720"})

        last_boxes = []
        last_scan = 0.0
        fails = 0
        fps = 0.0
        t_prev = time.perf_counter()

        while self._running:
            t0 = time.perf_counter()
            mode = self.mode
            overlay = {"mode": mode, "boxes": [], "hand": None, "pose": None,
                       "latency": 0.0, "count": None, "source": "sim" if scene else "webcam"}

            if cap is not None:
                ok, frame = cap.read()
                if not ok or frame is None:
                    fails += 1
                    if fails > 60:
                        cap.release()
                        cap = None
                        self.log.emit("danger", "Mất tín hiệu camera", "Không đọc được hình ảnh từ webcam")
                        self.source_changed.emit({"kind": "none", "text": "Mất tín hiệu", "size": "—"})
                    self.msleep(30)
                    continue
                fails = 0
                frame = cv2.flip(frame, 1)   # lật gương cho tự nhiên khi điều khiển bằng tay
                if mode == "CLASS":
                    last_boxes = []
                    g = self._ensure_gesture()
                    if g is not None:
                        ta = time.perf_counter()
                        res = g.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        overlay["latency"] = (time.perf_counter() - ta) * 1000
                        overlay["hand"] = res["landmarks"]
                        overlay["pose"] = res["pose"]
                        if res["command"]:
                            self.gesture_command.emit(res["command"])
                else:
                    det = self._ensure_detector()
                    now = time.perf_counter()
                    if det is not None and now - last_scan >= self.cfg.scan_interval_s:
                        last_scan = now
                        try:
                            last_boxes = [b + ("student",) for b in det.detect(frame)]
                            overlay["latency"] = (time.perf_counter() - now) * 1000
                        except Exception as exc:
                            self.log.emit("danger", "Lỗi phát hiện người", str(exc))
                            self._detector, self._detector_failed = None, True
                    overlay["boxes"] = last_boxes
                    overlay["count"] = len(last_boxes) if det is not None else None
            elif scene is not None:
                frame, boxes = scene.render(mode, self.sim_people)
                overlay["boxes"] = boxes
                overlay["latency"] = 18 + 6 * (time.time() % 1)
                if mode == "AFTER":
                    overlay["count"] = len(boxes)
            else:
                self.msleep(200)
                continue

            now = time.perf_counter()
            dt = now - t_prev
            t_prev = now
            if dt > 0:
                fps = fps * 0.9 + (1.0 / dt) * 0.1 if fps else 1.0 / dt
            overlay["fps"] = fps

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            image = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
            overlay["size"] = (w, h)
            self.frame_ready.emit(image, overlay)

            if scene is not None:   # camera mô phỏng: giữ ~30 FPS
                spent = time.perf_counter() - t0
                self.msleep(max(1, int((1 / 30 - spent) * 1000)))

        if cap is not None:
            cap.release()
        if self._gesture is not None:
            self._gesture.close()
        if self._detector is not None:
            self._detector.close()
