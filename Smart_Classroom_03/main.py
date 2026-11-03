import os
import sys

# Chạy được cả khi mở bằng PyCharm từ thư mục khác
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from PySide6.QtWidgets import QApplication  # noqa: E402

from ui.dashboard import Dashboard  # noqa: E402
from ui.theme import font  # noqa: E402


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Smart Classroom")
    app.setStyle("Fusion")   # giao diện đồng nhất, không bị ảnh hưởng bởi theme tối của Windows
    app.setFont(font(13))
    window = Dashboard()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
