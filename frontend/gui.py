import sys
from PyQt6.QtWidgets import QApplication
from frontend.widgets import MainWindow


def launch_gui():
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec())
