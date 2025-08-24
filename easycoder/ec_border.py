import os
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt, Signal, QRect

class Border(QWidget):
    tickClicked = Signal()
    closeClicked = Signal()

    def __init__(self):
        super().__init__()
        self.size = 40
        self.setFixedHeight(self.size)
        self._drag_active = False
        self._drag_start_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Draw the tick icon
        self.tick = QPixmap(f'{os.path.dirname(os.path.abspath(__file__))}/tick.png').scaled(self.size, self.size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = 0
        y = 0
        painter.drawPixmap(x, y, self.tick)
        # Draw the close icon
        self.close = QPixmap(f'{os.path.dirname(os.path.abspath(__file__))}/close.png').scaled(self.size, self.size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = self.width() - self.close.width()
        y = 0
        painter.drawPixmap(x, y, self.close)

    def mousePressEvent(self, event):
        # Tick icon
        x = 0
        y = 0
        tickRect = self.tick.rect().translated(x, y)
        # Close icon
        x = self.width() - self.close.width()
        y = 0
        closeRect = self.close.rect().translated(x, y)
        if tickRect.contains(event.pos()):
            self.tickClicked.emit()
        if closeRect.contains(event.pos()):
            self.closeClicked.emit()
        elif QRect(0, 0, self.width(), self.height()).contains(event.pos()):
            if hasattr(self.window().windowHandle(), 'startSystemMove'):
                self.window().windowHandle().startSystemMove()
            else:
                self._drag_active = True
                self._drag_start_pos = event.globalPosition().toPoint()
                self._dialog_start_pos = self.window().pos()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_active:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            self.window().move(self._dialog_start_pos + delta)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_active = False
        super().mouseReleaseEvent(event)
