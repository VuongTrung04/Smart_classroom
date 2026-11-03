"""Phát hiện người: ưu tiên YOLO (ultralytics), dự phòng HOG của OpenCV nếu chưa cài."""
import cv2

from core.config import MODEL_DIR


class PersonDetector:
    def __init__(self, model_name="yolov8n.pt", confidence=0.45):
        self.confidence = confidence
        self.backend = None
        self.note = ""
        self.model = None
        self.hog = None
        try:
            from ultralytics import YOLO
            local = MODEL_DIR / model_name
            self.model = YOLO(str(local) if local.exists() else model_name)
            self.backend = "YOLO"
        except Exception as exc:  # thiếu thư viện, không tải được model...
            self.note = f"Không dùng được YOLO ({exc}); chuyển sang HOG của OpenCV."
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            self.backend = "HOG"

    def detect(self, frame_bgr):
        """Trả về list (x1, y1, x2, y2, conf) theo toạ độ chuẩn hoá 0..1."""
        h, w = frame_bgr.shape[:2]
        boxes = []
        if self.model is not None:
            result = self.model.predict(
                source=frame_bgr, classes=[0], conf=self.confidence,
                verbose=False, imgsz=640,
            )[0]
            if result.boxes is not None:
                for xyxy, conf in zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist()):
                    x1, y1, x2, y2 = xyxy
                    boxes.append((x1 / w, y1 / h, x2 / w, y2 / h, float(conf)))
        elif self.hog is not None:
            scale = 640 / max(w, h)
            small = cv2.resize(frame_bgr, (int(w * scale), int(h * scale)))
            rects, weights = self.hog.detectMultiScale(small, winStride=(8, 8), padding=(8, 8), scale=1.05)
            for (x, y, rw, rh), wt in zip(rects, weights):
                conf = float(min(0.99, 0.5 + float(wt) / 4))
                if conf >= self.confidence:
                    boxes.append((x / scale / w, y / scale / h, (x + rw) / scale / w, (y + rh) / scale / h, conf))
        return boxes

    def close(self):
        self.model = None
        self.hog = None
