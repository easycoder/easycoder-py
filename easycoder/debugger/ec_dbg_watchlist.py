"""WatchListWidget showing variables on a single line with scrollable values."""

import bisect

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QScrollArea,
)
from PySide6.QtCore import Qt
from .ec_dbg_value_display import ValueDisplay


class WatchListWidget(QWidget):
    def __init__(self, debugger):
        super().__init__(debugger)
        self.debugger = debugger
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._rows: dict[str, dict] = {}
        self._variable_set: set[str] = set()
        self._order: list[str] = []
        self._placeholder: QLabel | None = None

        # Outer layout: scrollable labels (left) and fixed button column (right)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)

        # Left: scroll area for labels
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(4, 2, 4, 2)
        self.content_layout.setSpacing(4)
        self.content_layout.addStretch(1)  # keep items grouped at the top

        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll, 1)

        # Right: button column, top-aligned
        self.buttons_column = QVBoxLayout()
        self.buttons_column.setContentsMargins(0, 2, 4, 2)
        self.buttons_column.setSpacing(4)
        self.buttons_column.addStretch(1)
        outer.addLayout(self.buttons_column)

        self._show_placeholder()

    def _show_placeholder(self):
        if self._placeholder is not None:
            return
        self._placeholder = QLabel("No variables watched. Click + to add.")
        self._placeholder.setStyleSheet("color: #666; font-style: italic; padding: 4px 2px;")
        self.content_layout.insertWidget(self.content_layout.count() - 1, self._placeholder)

    def _hide_placeholder(self):
        if self._placeholder is None:
            return
        self.content_layout.removeWidget(self._placeholder)
        self._placeholder.deleteLater()
        self._placeholder = None

    def addVariable(self, name: str):
        if not name or name in self._variable_set:
            return
        if not hasattr(self.debugger, 'watched'):
            self.debugger.watched = []  # type: ignore[attr-defined]
        if name not in self.debugger.watched:  # type: ignore[attr-defined]
            bisect.insort(self.debugger.watched, name)  # type: ignore[attr-defined]

        self._hide_placeholder()

        # Row with label
        row_widget = QWidget(self)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(4, 0, 4, 0)
        row_layout.setSpacing(6)

        label = QLabel("")
        label.setWordWrap(False)
        row_layout.addWidget(label, 1)

        # Remove button in separate column
        remove_btn = QPushButton("-")
        remove_btn.setFixedWidth(22)

        def on_remove():
            try:
                if hasattr(self.debugger, 'watched') and name in self.debugger.watched:  # type: ignore[attr-defined]
                    self.debugger.watched.remove(name)  # type: ignore[attr-defined]
                if name in self._variable_set:
                    self._variable_set.remove(name)
                if name in self._order:
                    self._order.remove(name)
                self.content_layout.removeWidget(row_widget)
                row_widget.deleteLater()
                self.buttons_column.removeWidget(remove_btn)
                remove_btn.deleteLater()
                self._rows.pop(name, None)
                if not self._rows:
                    self._show_placeholder()
            except Exception:
                pass

        remove_btn.clicked.connect(on_remove)

        insert_pos = bisect.bisect_left(self._order, name)
        self._order.insert(insert_pos, name)
        # Insert label row above stretch, keeping alphabetical order
        self.content_layout.insertWidget(insert_pos, row_widget)
        # Insert button above stretch on the right, same position
        self.buttons_column.insertWidget(insert_pos, remove_btn)

        # Align button height to row height
        row_widget.adjustSize()
        btn_h = row_widget.sizeHint().height()
        if btn_h > 0:
            remove_btn.setFixedHeight(btn_h)

        self._rows[name] = {
            'widget': row_widget,
            'label': label,
            'button': remove_btn,
        }
        self._variable_set.add(name)

        try:
            self._refresh_one(name, self.debugger.program)
        except Exception:
            pass

    def _refresh_one(self, name: str, program):
        row = self._rows.get(name)
        if not row:
            return
        try:
            val_display = ValueDisplay()
            val_display.setValue(program, name)
            value_text = val_display.text()
        except Exception as e:
            value_text = f"<error: {e}>"
        row['label'].setText(f"{name} = {value_text}")

    def refreshVariables(self, program):
        if not self._rows:
            self._show_placeholder()
            return
        for name in list(self._rows.keys()):
            self._refresh_one(name, program)
