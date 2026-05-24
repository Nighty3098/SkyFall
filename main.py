import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.addImportPath(Path(__file__).parent)
    engine.loadFromModule("SkyFall", "Main")
    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())
