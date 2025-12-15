"""ValueDisplay widget for displaying variable values in the EasyCoder debugger"""

from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QLabel,
    QScrollArea,
)
from PySide6.QtCore import Qt


class ValueDisplay(QLabel):
    """Widget to display a variable value with type-appropriate formatting"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def setValue(self, program, symbol_name):
        record = program.getVariable(symbol_name)
        value = program.textify(record)
        self.setText(str(value))

