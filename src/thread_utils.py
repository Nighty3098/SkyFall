from traceback import print_exc

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt, QThread, Signal


class _Worker(QObject):
    finished = Signal()

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.fn(*self.args, **self.kwargs)
        except Exception:
            print_exc()
        finally:
            self.finished.emit()


def run_in_thread(fn, *args, **kwargs):
    """Run a function in a QThread. 1 line to use."""
    thread = QThread()
    worker = _Worker(fn, *args, **kwargs)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread


def invoke(widget, method_name, *args):
    """Thread-safe Qt slot invocation via QueuedConnection."""
    type_map = {str: str, int: int, float: float, bool: bool}
    qt_args = [Q_ARG(type_map.get(type(a), object), a) for a in args]
    QMetaObject.invokeMethod(
        widget,
        method_name,
        Qt.ConnectionType.QueuedConnection,
        *qt_args,
    )
