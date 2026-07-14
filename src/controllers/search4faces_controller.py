from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy

from src.ui.s4f_result_widget import S4FResultWidget

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.search4faces import Search4Faces


class S4FController:
    def __init__(
        self,
        ui: "QMainWindow",
        search4faces: "Search4Faces",
    ):
        logger.debug("Init: S4FController")
        self.ui = ui
        self.api = search4faces
        self.image_path = ""
        self._search_index = -1

    def on_image_dropped(self, path: str):
        if not path:
            return
        self.image_path = path
        self._clear_results()

        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                300,
                300,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.ui.s4fTargetLabel.setPixmap(scaled)
            self.ui.s4fTargetLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self.ui.s4fTargetLabel.setText(path)

    def _clear_results(self):
        self._search_index = -1
        layout = self.ui.s4fResultsLayout
        while layout.count():
            child = layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.deleteLater()

    def _add_status_label(self, text: str):
        layout = self.ui.s4fResultsLayout
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #999; padding: 20px;")
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(label)

    def _get_result_widgets(self) -> list[S4FResultWidget]:
        widgets = []
        layout = self.ui.s4fResultsLayout
        for i in range(layout.count()):
            child = layout.itemAt(i)
            if child and child.widget() and isinstance(child.widget(), S4FResultWidget):
                widgets.append(child.widget())
        return widgets

    def _match_profile(self, profile: dict, text: str) -> bool:
        text = text.lower()
        fields = [
            profile.get("first_name", ""),
            profile.get("last_name", ""),
            profile.get("city", ""),
            profile.get("country", ""),
        ]
        return any(text in f.lower() for f in fields)

    def search_next(self):
        text = self.ui.s4fSearchEdit.text().strip()
        if not text:
            return

        widgets = self._get_result_widgets()
        if not widgets:
            return

        start = self._search_index + 1
        for i in range(len(widgets)):
            idx = (start + i) % len(widgets)
            if self._match_profile(widgets[idx].profile, text):
                self._search_index = idx
                self.ui.s4fResultsScrollArea.ensureWidgetVisible(widgets[idx])
                self._highlight_widget(widgets[idx], True)
                return

    def _highlight_widget(self, widget: S4FResultWidget, on: bool):
        if on:
            widget.setStyleSheet("S4FResultWidget { border: 2px solid #5B9BD5; }")
        else:
            widget.setStyleSheet("")

    async def run_search(self):
        if not self.image_path:
            self._add_status_label("No image selected")
            return

        self._clear_results()
        self._add_status_label("Searching...")
        self.ui.runS4FButton.setEnabled(False)

        try:
            profiles = await self.api.search_face(self.image_path)
            self._clear_results()

            if not profiles:
                self._add_status_label("No matches found")
                return

            self._add_status_label(f"Found {len(profiles)} matches")

            for profile in profiles:
                face_url = profile.get("face_image_url", "")
                face_bytes = None
                if face_url:
                    face_bytes = await self.api.download_image(face_url)
                widget = S4FResultWidget(profile, face_bytes)
                self.ui.s4fResultsLayout.addWidget(widget)

            self.ui.s4fResultsLayout.addStretch()

        except Exception as e:
            logger.error(f"S4F search error: {e}")
            self._clear_results()
            self._add_status_label(f"Error: {e}")
        finally:
            self.ui.runS4FButton.setEnabled(True)
