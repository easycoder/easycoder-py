"""WatchListWidget for managing the variable watch list in the EasyCoder debugger"""

from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QScrollArea,
    QScrollBar,
    QSizePolicy,
    QPushButton,
)
from PySide6.QtCore import Qt
from .ec_dbg_value_display import ValueDisplay


class WatchListWidget(QWidget):
    """Encapsulates the variable watch list: grid layout, rows, shared horizontal scrollbar, refresh logic."""
    
    class ContentWidget(QWidget):
        """Custom widget that expands horizontally but sizes to content vertically"""
        def sizeHint(self):
            # Use the layout's size hint for natural sizing
            hint = super().sizeHint()
            # For height, use the minimum size (natural content height)
            hint.setHeight(self.minimumSizeHint().height())
            return hint
    
    def __init__(self, debugger):
        super().__init__(debugger)
        self.debugger = debugger
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Content widget holding the grid - use custom widget for hybrid sizing
        self._content_widget = self.ContentWidget()
        self._content_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.grid = QGridLayout(self._content_widget)
        self.grid.setContentsMargins(6, 2, 6, 2)
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(2)
        self.grid.setColumnStretch(0, 1)   # main content stretches
        self.grid.setColumnStretch(1, 0)   # buttons stay compact

        # Tracking structures
        self._row_count = 0              # number of variable rows (excludes placeholder)
        self._row_scrollers = []         # scrollers for shared horizontal scrolling
        self._variable_set = set()       # names of currently watched variables
        self._placeholder = None         # QLabel shown when no variables watched

        # Scroll area wrapping the grid (vertical only)
        self.scrollArea = QScrollArea()
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setWidgetResizable(True)  # Allow horizontal resize to fill width
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scrollArea.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.scrollArea.setWidget(self._content_widget)
        outer.addWidget(self.scrollArea, 1)

        # Horizontal scrollbar row (outside the vertical scroll area)
        hscroll_row = QWidget()
        hscroll_layout = QHBoxLayout(hscroll_row)
        hscroll_layout.setContentsMargins(6, 0, 6, 2)
        hscroll_layout.setSpacing(8)
        
        # Shared horizontal scrollbar
        self.hscroll = QScrollBar(Qt.Orientation.Horizontal)
        self.hscroll.setRange(0, 0)
        self.hscroll.valueChanged.connect(self._on_hscroll_value_changed)
        hscroll_layout.addWidget(self.hscroll, 1)  # stretch to match left column
        
        # Spacer to match button column width
        spacer = QWidget()
        spacer.setFixedWidth(22 + 6 + 22 + 8)  # match buttons width + spacing
        hscroll_layout.addWidget(spacer, 0)
        
        outer.addWidget(hscroll_row, 0)

        # Show placeholder initially
        self._show_placeholder()

    # ------------------------------------------------------------------
    def addVariable(self, name: str):
        try:
            if name in self._variable_set:
                return
            if not hasattr(self.debugger, 'watched'):
                self.debugger.watched = []  # type: ignore[attr-defined]
            if name not in self.debugger.watched:  # type: ignore[attr-defined]
                self.debugger.watched.append(name)  # type: ignore[attr-defined]
            self._add_variable_row(name)
            self._variable_set.add(name)
            self.refreshVariables(self.debugger.program)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _on_hscroll_value_changed(self, value: int):
        try:
            for sc in self._row_scrollers:
                try:
                    sc.horizontalScrollBar().setValue(value)
                except Exception:
                    pass
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _show_placeholder(self):
        try:
            if self._placeholder is not None:
                return
            ph = QLabel("No variables watched. Click + to add.")
            ph.setStyleSheet("color: #666; font-style: italic; padding: 6px 4px;")
            ph.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.grid.addWidget(ph, 0, 0, 1, 2)
            self._placeholder = ph
        except Exception:
            pass

    def _hide_placeholder(self):
        try:
            if self._placeholder is None:
                return
            w = self._placeholder
            self._placeholder = None
            self.grid.removeWidget(w)
            w.deleteLater()
        except Exception:
            pass

    # ------------------------------------------------------------------
    def recalc_width_range(self):
        try:
            max_content_w = 0
            view_w = 0
            for sc in self._row_scrollers:
                widget = sc.widget() if sc else None
                if widget:
                    max_content_w = max(max_content_w, widget.sizeHint().width())
                if view_w == 0 and sc:
                    view_w = sc.viewport().width()
            if view_w <= 0:
                view_w = max(0, self.scrollArea.viewport().width() - 70)
            rng = max(0, max_content_w - view_w)
            self.hscroll.setRange(0, rng)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _add_variable_row(self, name: str):
        # Hide placeholder if present
        self._hide_placeholder()

        content_widget = QWidget()
        cv = QVBoxLayout(content_widget)
        cv.setContentsMargins(0, 2, 0, 2)
        cv.setSpacing(2)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-family: mono; padding: 2px 4px; font-weight: bold;")
        name_lbl.setWordWrap(False)
        cv.addWidget(name_lbl)

        value_display = ValueDisplay()
        value_display.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        cv.addWidget(value_display, 0)

        row_scroller = QScrollArea()
        row_scroller.setFrameShape(QFrame.Shape.NoFrame)
        row_scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        row_scroller.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        row_scroller.setWidgetResizable(True)
        row_scroller.setWidget(content_widget)
        row_scroller.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        buttons_widget = QWidget()
        bh = QHBoxLayout(buttons_widget)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.setSpacing(6)

        expand_btn = QPushButton("⋮")
        expand_btn.setToolTip(f"Expand/collapse '{name}'")
        expand_btn.setFixedSize(22, 22)
        def on_expand():
            try:
                value_display.toggleExpand()
                self.refreshVariables(self.debugger.program)
            except Exception:
                pass
        expand_btn.clicked.connect(on_expand)
        bh.addWidget(expand_btn)

        remove_btn = QPushButton("–")
        remove_btn.setToolTip(f"Remove '{name}' from watch")
        remove_btn.setFixedSize(22, 22)
        def on_remove():
            try:
                if hasattr(self.debugger, 'watched') and name in self.debugger.watched:  # type: ignore[attr-defined]
                    self.debugger.watched.remove(name)  # type: ignore[attr-defined]
                if name in self._variable_set:
                    self._variable_set.remove(name)
                row_scroller.setParent(None)
                buttons_widget.setParent(None)
                if row_scroller in self._row_scrollers:
                    self._row_scrollers.remove(row_scroller)
                self._row_count = max(0, self._row_count - 1)
                # Update content widget size after removal
                self._content_widget.adjustSize()
                self.recalc_width_range()
                # Show placeholder if no rows left
                if self._row_count == 0:
                    self._show_placeholder()
            except Exception:
                pass
        remove_btn.clicked.connect(on_remove)
        bh.addWidget(remove_btn)

        buttons_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        buttons_widget.setFixedWidth(22 + 6 + 22)

        # Attach attributes for refresh
        row_scroller.name = name  # type: ignore[attr-defined]
        row_scroller.value_display = value_display  # type: ignore[attr-defined]

        # Place row
        self.grid.addWidget(row_scroller, self._row_count, 0)
        self.grid.addWidget(buttons_widget, self._row_count, 1)
        self._row_scrollers.append(row_scroller)
        self._row_count += 1
        
        # Update content widget size to fit new rows
        self._content_widget.adjustSize()
        self.recalc_width_range()

    # ------------------------------------------------------------------
    def refreshVariables(self, program):
        try:
            for sc in self._row_scrollers:
                if hasattr(sc, 'name') and hasattr(sc, 'value_display'):
                    var_name = sc.name  # type: ignore[attr-defined]
                    value_display = sc.value_display  # type: ignore[attr-defined]
                    try:
                        symbol_record = program.getVariable(var_name)
                        value_display.setValue(symbol_record, program)
                    except Exception as e:
                        value_display.value_label.setText(f"<error: {e}>")
            # Update size in case values expanded/collapsed
            self._content_widget.adjustSize()
            self.recalc_width_range()
            # If nothing to show, ensure placeholder is visible and scrollbar range reset
            if self._row_count == 0:
                self._show_placeholder()
                self.hscroll.setRange(0, 0)
        except Exception:
            pass
