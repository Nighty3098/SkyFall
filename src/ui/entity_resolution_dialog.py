"""Review dialog for entity-resolution candidates.

The automatic pass only merges high-confidence duplicates.  Medium-confidence
pairs are surfaced here with their score and the reasons behind it, so an
analyst can confirm a merge without reading the underlying graph JSON.
"""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from src.modules.entity_resolution import DuplicateGroup, EntityRecord
from src.ui.theme import dialog_palette


class EntityResolutionDialog(QDialog):
    def __init__(
        self,
        groups: Iterable[DuplicateGroup],
        parent=None,
        records: dict[str, EntityRecord] | None = None,
    ):
        super().__init__(parent)
        self._groups = list(groups)
        self._records = records or {}
        self.setWindowTitle("Entity Resolution \u2014 Duplicate Entities")
        self.resize(900, 560)
        self.setModal(True)
        self._build_ui()
        self._populate()
        self._apply_theme()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Group / entity", "Entity id", "Score", "Reasons"])
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.header().setStretchLastSection(True)
        self.tree.setColumnWidth(0, 280)
        self.tree.setColumnWidth(1, 210)
        self.tree.setColumnWidth(2, 90)
        layout.addWidget(self.tree, 1)

        buttons = QHBoxLayout()
        auto_button = QPushButton("Select auto only")
        auto_button.clicked.connect(self._select_auto)
        all_button = QPushButton("Select all")
        all_button.clicked.connect(self._select_all)
        none_button = QPushButton("Clear")
        none_button.clicked.connect(self._select_none)
        buttons.addWidget(auto_button)
        buttons.addWidget(all_button)
        buttons.addWidget(none_button)
        buttons.addStretch(1)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        merge_button = QPushButton("Merge selected")
        merge_button.setDefault(True)
        merge_button.clicked.connect(self._accept)
        buttons.addWidget(cancel_button)
        buttons.addWidget(merge_button)
        layout.addLayout(buttons)

    def _populate(self):
        auto_count = sum(1 for group in self._groups if group.auto)
        review_count = len(self._groups) - auto_count
        self.summary.setText(
            f"{len(self._groups)} duplicate group(s) found \u2014 "
            f"{auto_count} high-confidence (checked) and {review_count} "
            "needing review. Merging keeps all aliases, content lines, "
            "evidence and edges."
        )
        for index, group in enumerate(self._groups):
            primary = self._records.get(group.primary_id)
            primary_title = primary.title if primary else group.primary_id
            header = QTreeWidgetItem(
                [
                    f"Group {index + 1}: {len(group.node_ids)} records",
                    f"primary: {primary_title}",
                    f"{group.score:.0%}",
                    "; ".join(group.reasons),
                ]
            )
            header.setData(0, Qt.ItemDataRole.UserRole, index)
            header.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            header.setCheckState(
                0,
                Qt.CheckState.Checked if group.auto else Qt.CheckState.Unchecked,
            )
            header.setToolTip(3, "\n".join(group.reasons))
            self.tree.addTopLevelItem(header)

            for node_id in group.node_ids:
                record = self._records.get(node_id)
                title = record.title if record else node_id
                entity_type = record.entity_type if record else ""
                alias = ""
                if record:
                    aliases = record.metadata.get("aliases") or []
                    if aliases:
                        alias = ", ".join(str(item) for item in aliases[:4])
                child = QTreeWidgetItem(
                    [
                        f"  {title}",
                        f"{entity_type} \u00b7 {node_id[:12]}",
                        "primary" if node_id == group.primary_id else "merge",
                        alias,
                    ]
                )
                child.setFlags(Qt.ItemFlag.ItemIsEnabled)
                header.addChild(child)
            header.setExpanded(len(self._groups) <= 12)

    def _set_checks(self, predicate) -> None:
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            group_index = item.data(0, Qt.ItemDataRole.UserRole)
            if group_index is None:
                continue
            item.setCheckState(
                0,
                Qt.CheckState.Checked
                if predicate(self._groups[group_index])
                else Qt.CheckState.Unchecked,
            )

    def _select_auto(self):
        self._set_checks(lambda group: group.auto)

    def _select_all(self):
        self._set_checks(lambda group: True)

    def _select_none(self):
        self._set_checks(lambda group: False)

    def selected_groups(self) -> list[DuplicateGroup]:
        selected = []
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            group_index = item.data(0, Qt.ItemDataRole.UserRole)
            if group_index is None:
                continue
            if item.checkState(0) == Qt.CheckState.Checked:
                selected.append(self._groups[group_index])
        return selected

    def _accept(self):
        if not self.selected_groups():
            self.summary.setText(
                "Select at least one group to merge, or use Cancel to close."
            )
            return
        self.accept()

    def _apply_theme(self):
        pal = dialog_palette()
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {pal["bg"]};
                color: {pal["text"]};
            }}
            QLabel {{
                color: {pal["text"]};
            }}
            QTreeWidget {{
                background-color: {pal["surface"]};
                alternate-background-color: {pal["bg"]};
                color: {pal["text"]};
                border: 1px solid {pal["border"]};
                border-radius: {pal["radius"]};
                padding: 4px;
            }}
            QTreeWidget::item:selected {{
                background-color: {pal["surface_hover"]};
                color: {pal["text"]};
            }}
            QHeaderView::section {{
                background-color: {pal["surface"]};
                color: {pal["text"]};
                border: none;
                border-bottom: 1px solid {pal["border"]};
                padding: 5px;
            }}
            QPushButton {{
                background-color: {pal["surface"]};
                color: {pal["text"]};
                border: 1px solid {pal["border"]};
                border-radius: {pal["radius"]};
                padding: 6px 14px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                border-color: {pal["border_hover"]};
                background-color: {pal["surface_hover"]};
            }}
            QPushButton:default {{
                border-color: {pal["border_focus"]};
            }}
            """
        )


__all__ = ["EntityResolutionDialog"]
