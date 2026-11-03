"""Điều khiển PowerPoint.

Thứ tự thử:
1. COM (pywin32): điều khiển trực tiếp PowerPoint, không cần focus cửa sổ,
   chạy được cả khi đang trình chiếu lẫn khi đang ở chế độ soạn thảo.
2. Gửi phím: tìm cửa sổ trình chiếu/PowerPoint (hoặc WPS), đưa lên trước rồi mới
   gửi phím, để phím không rơi vào chính cửa sổ Smart Classroom.
"""
import sys
import time

IS_WINDOWS = sys.platform.startswith("win")

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.02
except Exception:  # thiếu thư viện hoặc không có màn hình
    pyautogui = None

try:
    import pythoncom
    import win32com.client
    import win32com.client.dynamic
except Exception:
    win32com = None
    pythoncom = None

try:
    import win32con
    import win32gui
except Exception:
    win32gui = None
    win32con = None

# Lớp cửa sổ: trình chiếu PowerPoint, cửa sổ soạn PowerPoint, WPS Presentation
SHOW_CLASSES = ("screenClass",)
EDIT_CLASSES = ("PPTFrameClass", "PP12FrameClass")
KEY_VK = {"right": 0x27, "left": 0x25, "f5": 0x74, "esc": 0x1B}


class PPTController:
    def __init__(self, backend="auto"):
        self.backend = backend
        self._app = None
        self.last_error = ""
        if pythoncom is not None:
            try:
                pythoncom.CoInitialize()
            except Exception:
                pass

    # ---------------- COM ----------------
    def _get_app(self):
        if win32com is None or self.backend == "keys":
            return None
        try:
            if self._app is not None:
                _ = self._app.Presentations.Count   # kiểm tra còn sống
                return self._app
        except Exception:
            self._app = None
        # Chỉ gắn vào PowerPoint đang mở, không tự mở PowerPoint mới
        if win32gui is not None and not self._find_windows(SHOW_CLASSES + EDIT_CLASSES):
            return None
        for getter in (lambda: win32com.client.GetActiveObject("PowerPoint.Application"),
                       lambda: win32com.client.dynamic.Dispatch("PowerPoint.Application")):
            try:
                self._app = getter()
                _ = self._app.Presentations.Count
                self.last_error = ""
                return self._app
            except Exception as exc:
                self._app = None
                self.last_error = str(exc)
        return None

    def status(self):
        """dict: connected, running, slide, total, title, backend."""
        info = {"connected": False, "running": False, "slide": 0, "total": 0,
                "title": "", "backend": self.describe_backend()}
        app = self._get_app()
        if app is None:
            return info
        try:
            info["connected"] = True
            info["backend"] = "PowerPoint COM"
            if app.Presentations.Count == 0:
                return info
            if app.SlideShowWindows.Count > 0:
                win = app.SlideShowWindows(1)
                pres = win.Presentation
                info["running"] = True
                try:
                    info["slide"] = int(win.View.Slide.SlideIndex)
                except Exception:   # đang ở màn hình đen cuối bài
                    info["slide"] = int(pres.Slides.Count)
            else:
                pres = app.ActivePresentation
            info["total"] = int(pres.Slides.Count)
            info["title"] = str(pres.Name).rsplit(".", 1)[0]
            if not info["running"]:
                info["slide"] = self._edit_slide_index(app) or (1 if info["total"] else 0)
        except Exception:
            self._app = None
        return info

    @staticmethod
    def _edit_slide_index(app):
        try:
            return int(app.ActiveWindow.Selection.SlideRange.SlideIndex)
        except Exception:
            try:
                return int(app.ActiveWindow.View.Slide.SlideIndex)
            except Exception:
                return 0

    def describe_backend(self):
        if self.backend != "keys" and win32com is not None:
            return "PowerPoint COM" if self._app is not None else "Chờ mở PowerPoint (COM)"
        if pyautogui is not None:
            return "Gửi phím tới cửa sổ trình chiếu"
        return "Không khả dụng – cài pywin32 hoặc pyautogui"

    def _execute_com(self, app, command):
        if command == "TOGGLE_SHOW":
            if app.SlideShowWindows.Count > 0:
                app.SlideShowWindows(1).View.Exit()
                return True, "Đã dừng trình chiếu"
            if app.Presentations.Count == 0:
                return False, "Chưa mở file PowerPoint nào"
            app.ActivePresentation.SlideShowSettings.Run()
            return True, "Đã bắt đầu trình chiếu"

        if app.Presentations.Count == 0:
            return False, "Chưa mở file PowerPoint nào"
        if app.SlideShowWindows.Count > 0:
            view = app.SlideShowWindows(1).View
            if command == "NEXT":
                view.Next()
                return True, "Đã chuyển slide tiếp"
            view.Previous()
            return True, "Đã lùi về slide trước"

        # Chưa trình chiếu: chuyển slide ngay trong cửa sổ soạn thảo
        total = int(app.ActivePresentation.Slides.Count)
        cur = self._edit_slide_index(app) or 1
        target = min(total, cur + 1) if command == "NEXT" else max(1, cur - 1)
        app.ActiveWindow.View.GotoSlide(target)
        return True, f"Đã chuyển tới slide {target}/{total} (chế độ soạn thảo)"

    # ---------------- lệnh ----------------
    def execute(self, command):
        """Trả về (ok, message)."""
        if command not in ("NEXT", "PREVIOUS", "TOGGLE_SHOW"):
            return False, "Lệnh không hợp lệ"
        app = self._get_app()
        if app is not None:
            try:
                return self._execute_com(app, command)
            except Exception as exc:
                self._app = None
                self.last_error = str(exc)
                if self.backend == "com":
                    return False, f"Lỗi COM: {exc}"
        elif self.backend == "com":
            return False, "Không kết nối được PowerPoint qua COM (đã mở PowerPoint chưa?)"
        return self._send_key(command)

    # ---------------- gửi phím (dự phòng) ----------------
    @staticmethod
    def _find_windows(classes):
        if win32gui is None:
            return []
        found = []

        def cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetClassName(hwnd) in classes:
                found.append(hwnd)
            return True

        try:
            win32gui.EnumWindows(cb, None)
        except Exception:
            pass
        return found

    @staticmethod
    def _find_wps_window():
        if win32gui is None:
            return None
        found = []

        def cb(hwnd, _):
            title = win32gui.GetWindowText(hwnd)
            if win32gui.IsWindowVisible(hwnd) and ("WPS" in title or title.endswith(".pptx")
                                                   or title.endswith(".ppt")):
                found.append(hwnd)
            return True

        try:
            win32gui.EnumWindows(cb, None)
        except Exception:
            pass
        return found[0] if found else None

    @staticmethod
    def _focus(hwnd):
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            # Windows chỉ cho đổi cửa sổ trước khi vừa có phím được nhấn -> nhấn ALT ảo
            if pyautogui is not None:
                pyautogui.press("alt")
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.08)
            return win32gui.GetForegroundWindow() == hwnd
        except Exception:
            return False

    def _send_key(self, command):
        key = {"NEXT": "right", "PREVIOUS": "left", "TOGGLE_SHOW": "f5"}[command]
        if not IS_WINDOWS:
            return False, "Điều khiển PowerPoint chỉ hỗ trợ trên Windows"
        if win32gui is None:
            return False, "Thiếu pywin32: chạy  pip install pywin32  rồi mở lại ứng dụng"

        target = None
        shows = self._find_windows(SHOW_CLASSES)
        if shows:
            target = shows[0]
            if command == "TOGGLE_SHOW":
                key = "esc"
        else:
            edits = self._find_windows(EDIT_CLASSES)
            target = edits[0] if edits else self._find_wps_window()
        if target is None:
            return False, "Không tìm thấy cửa sổ PowerPoint – hãy mở bài trình chiếu trước"

        if self._focus(target) and pyautogui is not None:
            pyautogui.press(key)
            return True, f"Đã gửi phím {key.upper()} tới cửa sổ trình chiếu"
        # Không đưa được cửa sổ lên trước: gửi thẳng thông điệp phím vào cửa sổ
        try:
            vk = KEY_VK[key]
            win32gui.PostMessage(target, win32con.WM_KEYDOWN, vk, 0)
            win32gui.PostMessage(target, win32con.WM_KEYUP, vk, 0xC0000001)
            return True, f"Đã gửi phím {key.upper()} (PostMessage)"
        except Exception as exc:
            return False, f"Không gửi được phím: {exc}"
