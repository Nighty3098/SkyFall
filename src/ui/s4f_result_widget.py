from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)


class S4FResultWidget(QFrame):
    def __init__(self, profile: dict, face_bytes: bytes | None = None, parent=None):
        super().__init__(parent)
        self.profile = profile
        self._setup_ui(face_bytes)

    def _setup_ui(self, face_bytes: bytes | None):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        face_label = QLabel()
        face_label.setFixedSize(80, 80)
        face_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        face_label.setStyleSheet("border: 1px solid #555;")
        if face_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(face_bytes)
            face_label.setPixmap(
                pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio)
            )
        else:
            face_label.setText("N/A")
        layout.addWidget(face_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        first = self.profile.get("first_name", "")
        last = self.profile.get("last_name", "")
        name = f"{first} {last}".strip()
        if not name:
            name = "Unknown"

        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_layout.addWidget(name_label)

        parts = []
        age = self.profile.get("age")
        if age is not None:
            parts.append(f"Age: {age}")
        city = self.profile.get("city", "")
        country = self.profile.get("country", "")
        if city or country:
            parts.append(f"{city}, {country}".strip(", "))
        similarity = self.profile.get("similarity", 0)
        parts.append(f"Similarity: {similarity:.1f}%")
        details_label = QLabel(" | ".join(parts))
        details_label.setStyleSheet("color: #999;")
        details_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        info_layout.addWidget(details_label)

        vk_url = self.profile.get("vk_url", "")
        if vk_url:
            link_label = QLabel(f'<a href="{vk_url}">{vk_url}</a>')
            link_label.setOpenExternalLinks(True)
            link_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.LinksAccessibleByMouse
            )
            link_label.setStyleSheet("color: #5B9BD5;")
            info_layout.addWidget(link_label)

        info_layout.addStretch()
        layout.addLayout(info_layout, 1)
