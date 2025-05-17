from easycoder import Handler, FatalError, RuntimeError
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QWidget, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtGui import QPixmap, QFont, QPalette, QBrush
from PySide6.QtCore import Qt

# This is the package that handles the RBR user interface.

class RBR_UI(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'points'

    #############################################################################
    # Keyword handlers

    def k_rbr_ui(self, command):
        return self.compileVariable(command, False)

    def r_rbr_ui(self, command):
        return self.nextPC()

    # create the main UI
    def k_create(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['keyword'] == 'rbr_ui':
                command['name'] = record['name']
                self.skip('in')
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    if record['keyword'] == 'window':
                        command['window'] = record['name']
                        self.addCommand(command)
                        return True
        return False

    def r_create(self, command):
        record = self.getVariable(command['name'])
        window = self.getVariable(command['window'])['window']
        # Set the background image
        palette = QPalette()
        background_pixmap = QPixmap("/home/graham/dev/rbr/ui/main/backdrop.jpg")
        palette.setBrush(QPalette.Window, QBrush(background_pixmap))
        window.setPalette(palette)

        # Main layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(10)  # Set spacing between rows to 10

        record['layout'] = main_widget
        return self.nextPC()

    #############################################################################
    # Compile a value in this domain
    def compileValue(self):
        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        return value

    #############################################################################
    # Value handlers

    def v_none(self, v):
        return None

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers
