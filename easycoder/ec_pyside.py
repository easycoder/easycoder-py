import sys
from functools import partial
from .ec_handler import Handler
from .ec_classes import RuntimeError, Object
from .ec_border import Border
from .ec_debug import Debugger
from PySide6.QtCore import Qt, QTimer, Signal, QRect
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDial,
    QDoubleSpinBox,
    QFontComboBox,
    QLabel,
    QLCDNumber,
    QLineEdit,
    QPlainTextEdit,
    QListWidget,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTimeEdit,
    QLayout,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QStackedLayout,
    QGroupBox,
    QWidget,
    QSpacerItem,
    QSizePolicy,
    QDialog,
    QMessageBox,
    QDialogButtonBox,
    QGraphicsDropShadowEffect
)

class Graphics(Handler):

    def __init__(self, compiler):
        super().__init__(compiler)
        self.blocked = False
        self.runOnTick = 0
        self.vkb = False

    def getName(self):
        return 'graphics'

    def closeEvent(self):
        print('window closed')
    
    def isWidget(self, keyword):
        return keyword in [
            'layout',
            'group',
            'label',
            'pushbutton',
            'checkbox',
            'lineinput',
            'multiline',
            'listbox',
            'combobox',
            'widget'
            ]
    
    def setWidget(self, record, widget):
        if record['index'] >= record['elements']:
            RuntimeError(self.program, f'Index out of range for widget {record["name"]}')
        if not 'widget' in record:
            record['widget'] = [None] * record['elements']
        while len(record['widget']) < record['elements']:
            record['widget'].append(None)
        record['widget'][record['index']] = widget
    
    def getWidget(self, record):
        if 'widget' in record and record['widget'] != None:
            if record['keyword'] in ['layout', 'group']: return record['widget'] 
            return record['widget'][record['index']]
        else:
            return None

    def dialogTypes(self):
        return ['confirm', 'lineedit', 'multiline', 'generic']

    class ClickableLineEdit(QLineEdit):
        clicked = Signal()

        def __init__(self):
            super().__init__()
            self.multiline = False
            self.container = None
        
        def setContainer(self, container):
            self.container = container

        def mousePressEvent(self, event):
            self.clicked.emit()
            super().mousePressEvent(event)
            if self.container != None: self.container.setClickSource(self)

    class ClickablePlainTextEdit(QPlainTextEdit):
        clicked = Signal()

        def __init__(self):
            super().__init__()
            self.multiline = True
            self.container = None
        
        def setContainer(self, container):
            self.container = container

        def mousePressEvent(self, event):
            self.clicked.emit()
            super().mousePressEvent(event)
            if self.container != None: self.container.setClickSource(self)

    #############################################################################
    # Keyword handlers

    # (1) add {value} to {widget}
    # (2) add {widget} to {layout}
    # (3) add stretch {widget} to {layout}
    # (4) add stretch to {layout}
    # (5) add spacer [size] {size} to {layout}
    # (6) add {widget} at {col} {row} in {grid layout}
    def k_add(self, command):
        def addToLayout():
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] in ['layout', 'group', 'element']:
                    command['layout'] = record['name']
                    self.add(command)
                    return True
            return False
        
        token = self.peek()
        if token == 'stretch':
            self.nextToken()
            # It's either (3) or (4)
            if self.nextIs('to'):
                # (4)
                command['stretch'] = False
                command['widget'] = 'stretch'
                return addToLayout()
            if self.isSymbol():
                # (3)
                record = self.getSymbolRecord()
                command['widget'] = record['name']
                command['stretch'] = True
                if self.nextIs('to'):
                    return addToLayout()
            return False
        
        elif token == 'spacer':
            self.nextToken()
            self.skip('size')
            command['widget'] = 'spacer'
            command['size'] = self.nextValue()
            self.skip('to')
            return addToLayout()

        # Here it's either (1) or (2)
        elif self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['extra'] == 'gui':
                if self.isWidget(record['keyword']):
                    command['widget'] = record['name']
                    if self.peek() == 'to':
                        # (2)
                        record = self.getSymbolRecord()
                        self.nextToken()
                        return addToLayout()
                    elif self.peek() == 'at':
                        # (6)
                        self.nextToken()
                        command['row'] = self.nextValue()
                        command['col'] = self.nextValue()
                        self.skip('in')
                        return addToLayout()

                else: return False
        # (1)
        value = self.getValue()
        if value == None: return False
        command['value'] = value
        self.skip('to')
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            command['widget'] = record['name']
            self.add(command)
            return True
        return False
    
    def r_add(self, command):
        if 'value' in command:
            value = self.getRuntimeValue(command['value'])
            record = self.getVariable(command['widget'])
            if record['keyword'] == 'listbox':
                self.getWidget(record).addItem(value)  # type: ignore
            elif record['keyword'] == 'combobox':
                if isinstance(value, list): record['widget'].addItems(value)
                else: self.getWidget(record).addItem(value)  # type: ignore
        elif 'row' in command and 'col' in command:
            layout = self.getVariable(command['layout'])['widget']
            record = self.getVariable(command['widget'])
            widget = self.getWidget(record)
            row = self.getRuntimeValue(command['row'])
            col = self.getRuntimeValue(command['col'])
            if record['keyword'] == 'layout':
                layout.addLayout(widget, row, col)
            else:
                layout.addWidget(widget, row, col)
        else:
            layoutRecord = self.getVariable(command['layout'])
            widget = command['widget']
            if widget == 'stretch':
                self.getWidget(layoutRecord).addStretch()  # type: ignore
            elif widget == 'spacer':
                self.getWidget(layoutRecord).addSpacing(self.getRuntimeValue(command['size']))  # type: ignore
            else:
                widgetRecord = self.getVariable(widget)
                layoutRecord = self.getVariable(command['layout'])
                widget = self.getWidget(widgetRecord)
                layout = layoutRecord['widget']
                stretch = 'stretch' in command
                if widgetRecord['keyword'] == 'layout':
                    if layoutRecord['keyword'] == 'group':
                        if widgetRecord['keyword'] == 'layout':
                            layout.setLayout(widget)
                        else:
                            RuntimeError(self.program, 'Can only add a layout to a group')
                    else:
                        if stretch: layout.addLayout(widget, stretch=1)
                        else: layout.addLayout(widget)
                else:
                    if stretch: layout.addWidget(widget, stretch=1)
                    else: layout.addWidget(widget)
        return self.nextPC()

    # Center one window on another
    # center {window2} on {window1}
    def k_center(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['keyword'] == 'window':
                command['window2'] = record['name']
                self.skip('on')
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    if record['keyword'] == 'window':
                        command['window1'] = record['name']
                        self.add(command)
                        return True
        return False
    
    def r_center(self, command):
        window1 = self.getVariable(command['window1'])['window']
        window2 = self.getVariable(command['window2'])['window']
        geo1 = window1.geometry()
        geo2 = window2.geometry()
        geo2.moveCenter(geo1.center())
        window2.setGeometry(geo2)
        return self.nextPC()

    # Declare a checkbox variable
    def k_checkbox(self, command):
        return self.compileVariable(command, 'gui')

    def r_checkbox(self, command):
        return self.nextPC()

    # clear {widget}
    def k_clear(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if self.isWidget(record['keyword']):
                command['name'] = record['name']
                self.add(command)
                return True
        return False
    
    def r_clear(self, command):

        def clearLayout(layout: QLayout) -> None:
            if layout is None:
                return
            while layout.count() > 0:
                item = layout.takeAt(0)
                if item is None:
                    continue
                widget = item.widget()
                if widget is not None:
                    # Delete the widget
                    widget.deleteLater()
                elif item.layout() is not None:
                    # Recursively clear sub-layout
                    clearLayout(item.layout())
                    item.layout().deleteLater()
                # The QLayoutItem will be automatically cleaned up by Qt

        def clearWidget(widget: QWidget) -> None:
            if widget is None:
                return
            # Clear the layout first
            layout = widget.layout()
            if layout is not None:
                clearLayout(layout)
                layout.deleteLater()
            # Clear any remaining child widgets
            child_widgets = widget.findChildren(QWidget, "", Qt.FindChildOption.FindDirectChildrenOnly)
            for child in child_widgets:
                child.deleteLater()

        widget = self.getWidget(self.getVariable(command['name']))
        clearWidget(widget)  # type: ignore
        return self.nextPC()

        return self.nextPC()

    # close {window}
    def k_close(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['keyword'] == 'window':
                command['name'] = record['name']
                self.add(command)
                return True
        return False
    
    def r_close(self, command):
        self.getVariable(command['name'])['window'].close()
        return self.nextPC()

    # Declare a combobox variable
    def k_combobox(self, command):
        return self.compileVariable(command, 'gui')

    def r_combobox(self, command):
        return self.nextPC()

    # Create a window
    def k_createWindow(self, command):
        title = None
        x = None
        y = None
        w = self.compileConstant(640)
        h = self.compileConstant(480)
        while True:
            token = self.peek()
            if token in ['title', 'at', 'size', 'layout']:
                self.nextToken()
                if token == 'title': title = self.nextValue()
                elif token == 'at':
                    x = self.nextValue()
                    y = self.nextValue()
                elif token == 'size':
                    w = self.nextValue()
                    h = self.nextValue()
                elif token == 'layout':
                    if self.nextIsSymbol():
                        record = self.getSymbolRecord()
                        if record['keyword'] == 'layout':
                            command['layout'] = record['name']
                else: return False
            else: break
        command['title'] = title
        command['x'] = x
        command['y'] = y
        command['w'] = w
        command['h'] = h
        self.add(command)
        return True

    # Create a widget
    def k_createLayout(self, command):
        self.skip('type')
        command['type'] = self.nextToken()
        self.add(command)
        return True

    def k_createGroupBox(self, command):
        if self.peek() == 'title':
            self.nextToken()
            title = self.nextValue()
        else: title = ''
        command['title'] = title
        self.add(command)
        return True

    def k_createLabel(self, command):
        text = self.compileConstant('')
        while True:
            token = self.peek()
            if token == 'text':
                self.nextToken()
                text = self.nextValue()
            elif token == 'size':
                self.nextToken()
                command['size'] = self.nextValue()
            elif token == 'expand':
                self.nextToken()
                command['expand'] = True
            elif token == 'align':
                self.nextToken()
                token = self.nextToken()
                if token in ['left', 'right', 'center', 'centre', 'justify']:
                    command['align'] = token
            else: break
        command['text'] = text
        self.add(command)
        return True

    def k_createPushbutton(self, command):
        while True:
            token = self.peek()
            if token == 'text':
                self.nextToken()
                command['text'] = self.nextValue()
            elif token == 'icon':
                self.nextToken()
                command['icon'] = self.nextValue()
            elif token == 'size':
                self.nextToken()
                command['size'] = self.nextValue()
            else: break
        self.add(command)
        return True

    def k_createCheckBox(self, command):
        if self.peek() == 'text':
            self.nextToken()
            text = self.nextValue()
        else: text = self.compileConstant('')
        command['text'] = text
        self.add(command)
        return True

    def k_createLineEdit(self, command):
        text = self.compileConstant('')
        size = self.compileConstant(40)
        while True:
            token = self.peek()
            if token == 'text':
                self.nextToken()
                text = self.nextValue()
            elif token == 'size':
                self.nextToken()
                size = self.nextValue()
            else: break;
        command['size'] = size
        command['text'] = text
        self.add(command)
        return True

    def k_createMultiLineEdit(self, command):
        cols = self.compileConstant(30)
        rows = self.compileConstant(5)
        while True:
            next = self.peek()
            if next == 'cols':
                self.nextToken()
                cols = self.nextValue()
            elif next == 'rows':
                self.nextToken()
                rows = self.nextValue()
            else: break;
        command['cols'] = cols
        command['rows'] = rows
        self.add(command)
        return True

    def k_createWidget(self, command):
        self.add(command)
        return True

    def k_createDialog(self, command):
        if self.peek() == 'on':
            self.nextToken()
            if self.nextIsSymbol():
                command['window'] = self.getSymbolRecord()['name']
        else: command['window'] = None
        while True:
            if self.peek() == 'type':
                self.nextToken()
                dialogType = self.nextToken()
                if dialogType in self.dialogTypes(): command['type'] = dialogType
                else: return False
            elif self.peek() == 'title':
                self.nextToken()
                command['title'] = self.nextValue()
            elif self.peek() == 'prompt':
                self.nextToken()
                command['prompt'] =  self.nextValue()
            elif self.peek() == 'value':
                self.nextToken()
                command['value'] =  self.nextValue()
            elif self.peek() == 'with':
                self.nextToken()
                command['layout'] =  self.nextToken()
            else: break
        if not 'title' in command: command['title'] = self.compileConstant('')
        if not 'value' in command: command['value'] = self.compileConstant('')
        if not 'prompt' in command: command['prompt'] = self.compileConstant('')
        self.add(command)
        return True

    def k_createMessageBox(self, command):
        if self.peek() == 'on':
            self.nextToken()
            if self.nextIsSymbol():
                command['window'] = self.getSymbolRecord()['name']
        else: command['window'] = None
        style = 'question'
        title = ''
        message = ''
        while True:
            if self.peek() == 'style':
                self.nextToken()
                style = self.nextToken()
            elif self.peek() == 'title':
                self.nextToken()
                title = self.nextValue()
            elif self.peek() == 'message':
                self.nextToken()
                message = self.nextValue()
            else: break
        command['style'] = style
        command['title'] = title
        command['message'] = message
        self.add(command)
        return True

    def k_create(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            command['name'] = record['name']
            keyword = record['keyword']
            if keyword == 'window': return self.k_createWindow(command)
            elif keyword in ['listbox', 'combobox', 'widget']: return self.k_createWidget(command)
            elif keyword == 'layout': return self.k_createLayout(command)
            elif keyword == 'group': return self.k_createGroupBox(command)
            elif keyword == 'label': return self.k_createLabel(command)
            elif keyword == 'pushbutton': return self.k_createPushbutton(command)
            elif keyword == 'checkbox': return self.k_createCheckBox(command)
            elif keyword == 'lineinput': return self.k_createLineEdit(command)
            elif keyword == 'multiline': return self.k_createMultiLineEdit(command)
            elif keyword == 'dialog': return self.k_createDialog(command)
            elif keyword == 'messagebox': return self.k_createMessageBox(command)
        return False
    
    def r_createWindow(self, command, record):
        window = QMainWindow()
        title = self.getRuntimeValue(command['title'])
        if title == None: title = 'EasyCoder Main Window'
        window.setWindowTitle(title)
        w = self.getRuntimeValue(command['w'])
        h = self.getRuntimeValue(command['h'])
        x = command['x']
        y = command['y']
        if hasattr(self.program, 'screenWidth'): screenWidth = self.program.screenWidth
        else: screenWidth = self.program.parent.program.screenWidth
        if hasattr(self.program, 'screenHeight'): screenHeight = self.program.screenHeight
        else: screenHeight = self.program.parent.program.screenHeight
        if x == None: x = (screenWidth - w) / 2
        else: x = self.getRuntimeValue(x)
        if y == None: y = (screenHeight - h) / 2
        else: y = self.getRuntimeValue(x)
        window.setGeometry(x, y, w, h)
        record['window'] = window
        return self.nextPC()
    
    def r_createLayout(self, command, record):
        layoutType = command['type']
        if layoutType == 'QHBoxLayout': layout = QHBoxLayout()
        elif layoutType == 'QGridLayout': layout = QGridLayout()
        elif layoutType == 'QStackedLayout': layout = QStackedLayout()
        else: layout = QVBoxLayout()
        layout.setContentsMargins(5,0,5,0)
        record['widget'] = layout
        return self.nextPC()
    
    def r_createGroupBox(self, command, record):
        group = QGroupBox(self.getRuntimeValue(command['title']))
        group.setAlignment(Qt.AlignmentFlag.AlignLeft)
        record['widget'] = group
        return self.nextPC()
    
    def r_createLabel(self, command, record):
        label = QLabel(str(self.getRuntimeValue(command['text'])))
        label.setStyleSheet("""
            background-color: transparent;
            border: none;
        """)
        if 'size' in command:
            fm = label.fontMetrics()
            c = label.contentsMargins()
            w = fm.horizontalAdvance('m') * self.getRuntimeValue(command['size']) +c.left()+c.right()
            label.setMaximumWidth(w)
        if 'align' in command:
            alignment = command['align']
            if alignment == 'left': label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            elif alignment == 'right': label.setAlignment(Qt.AlignmentFlag.AlignRight)
            elif alignment in ['center', 'centre']: label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            elif alignment == 'justify': label.setAlignment(Qt.AlignmentFlag.AlignJustify)
        if 'expand' in command:
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setWidget(record, label)
        return self.nextPC()
    
    def r_createPushbutton(self, command, record):
        if 'size' in command:
            size = self.getRuntimeValue(command['size'])
        else: size = None
        if 'icon' in command:
            iconPath = self.getRuntimeValue(command['icon'])
            pixmap = QPixmap(iconPath)
            if pixmap.isNull():
                RuntimeError(self.program, f'Icon not found: {iconPath}')
            icon = pixmap.scaledToHeight(size if size != None else 24, Qt.TransformationMode.SmoothTransformation)
            pushbutton = QPushButton()
            pushbutton.setIcon(icon)
            pushbutton.setIconSize(icon.size())
        elif 'text' in command:
            text = self.getRuntimeValue(command['text'])
            pushbutton = QPushButton(text)
            pushbutton.setAccessibleName(text)
            if size != None:
                fm = pushbutton.fontMetrics()
                c = pushbutton.contentsMargins()
                w = fm.horizontalAdvance('m') * self.getRuntimeValue(command['size']) + c.left()+c.right()
                pushbutton.setMaximumWidth(w)
        self.putSymbolValue(record, pushbutton)
        self.setWidget(record, pushbutton)
        return self.nextPC()
    
    def r_createCheckBox(self, command, record):
        checkbox = QCheckBox(self.getRuntimeValue(command['text']))
        checkbox.setStyleSheet("""
            QCheckBox::indicator {
                border: 1px solid black;
                border-radius: 3px;
                background: white;
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:checked {
                background: #0078d7;
            }
            QCheckBox {
                border: none;
                background: transparent;
            }
        """)
        checkbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.setWidget(record, checkbox)
        return self.nextPC()
    
    def r_createLineEdit(self, command, record):
        lineinput = self.ClickableLineEdit()
        lineinput.setText(self.getRuntimeValue(command['text']))
        fm = lineinput.fontMetrics()
        m = lineinput.textMargins()
        c = lineinput.contentsMargins()
        w = fm.horizontalAdvance('x') * self.getRuntimeValue(command['size']) +m.left()+m.right()+c.left()+c.right()
        lineinput.setMaximumWidth(w)
        self.setWidget(record, lineinput)
        return self.nextPC()
    
    def r_createMultiLineEdit(self, command, record):
        textinput = self.ClickablePlainTextEdit()
        fontMetrics = textinput.fontMetrics()
        charWidth = fontMetrics.horizontalAdvance('x')
        charHeight = fontMetrics.height()
        textinput.setFixedWidth(charWidth * self.getRuntimeValue(command['cols']))
        textinput.setFixedHeight(charHeight * self.getRuntimeValue(command['rows']))
        self.setWidget(record, textinput)
        return self.nextPC()
    
    def r_createListWidget(self, command, record):
        self.setWidget(record, QListWidget())
        return self.nextPC()
    
    def r_createComboBox(self, command, record):
        self.setWidget(record, QComboBox())
        return self.nextPC()
    
    def r_createWidget(self, command, record):
        self.setWidget(record, QWidget())
        return self.nextPC()
    
    def r_createDialog(self, command, record):

        class ECDialog(QDialog):
            def __init__(self, parent, record):
                super().__init__(parent)
                self.record = record
            
            def showEvent(self, event):
                super().showEvent(event)
                QTimer.singleShot(100, self.afterShown)
            
            def afterShown(self):
                if 'action' in self.record: self.record['action']()

        win = command['window']
        if win != None:
            win = self.getVariable(win)['window']
        dialog = ECDialog(win, record)
        dialogType = command['type'].lower()
        dialog.dialogType = dialogType  # type: ignore
        mainLayout = QVBoxLayout(dialog)
        if dialogType == 'generic':
            dialog.setFixedWidth(500)
            dialog.setFixedHeight(500)
            dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            dialog.setModal(True)
            dialog.setStyleSheet('background-color: white;border:1px solid black;')

            border = Border()
            border.tickClicked.connect(dialog.accept)
            border.closeClicked.connect(dialog.reject)
            mainLayout.addWidget(border)
            if 'layout' in command:
                layout = self.getVariable(command['layout'])['widget']
                mainLayout.addLayout(layout)
            dialog.setLayout(mainLayout)
        else:
            dialog.setWindowTitle(self.getRuntimeValue(command['title']))
            prompt = self.getRuntimeValue(command['prompt'])
            if dialogType == 'confirm':
                mainLayout.addWidget(QLabel(prompt))
            elif dialogType == 'lineedit':
                mainLayout.addWidget(QLabel(prompt))
                dialog.lineEdit = self.ClickableLineEdit(dialog)  # type: ignore
                dialog.value = self.getRuntimeValue(command['value'])  # type: ignore
                dialog.lineEdit.setText(dialog.value)  # type: ignore
                mainLayout.addWidget(dialog.lineEdit)  # type: ignore
            elif dialogType == 'multiline':
                mainLayout.addWidget(QLabel(prompt))
                dialog.textEdit = self.ClickablePlainTextEdit(self)  # type: ignore
                dialog.textEdit.setText(dialog.value)  # type: ignore
                mainLayout.addWidget(dialog.textEdit)  # type: ignore
            buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttonBox.accepted.connect(dialog.accept)
            buttonBox.rejected.connect(dialog.reject)
            mainLayout.addWidget(buttonBox, alignment=Qt.AlignmentFlag.AlignHCenter)
        record['dialog'] = dialog
        return self.nextPC()
    
    # Creates a message box but doesn't run it
    def r_createMessageBox(self, command, record):
        data = {}
        data['window'] = command['window']
        data['style'] = command['style']
        data['title'] = self.getRuntimeValue(command['title'])
        data['message'] = self.getRuntimeValue(command['message'])
        record['data'] = data
        return self.nextPC()

    def r_create(self, command):
        record = self.getVariable(command['name'])
        keyword = record['keyword']
        if keyword == 'window': return self.r_createWindow(command, record)
        elif keyword == 'layout': return self.r_createLayout(command, record)
        elif keyword == 'group': return self.r_createGroupBox(command, record)
        elif keyword == 'label': return self.r_createLabel(command, record)
        elif keyword == 'pushbutton': return self.r_createPushbutton(command, record)
        elif keyword == 'checkbox': return self.r_createCheckBox(command, record)
        elif keyword == 'lineinput': return self.r_createLineEdit(command, record)
        elif keyword == 'multiline': return self.r_createMultiLineEdit(command, record)
        elif keyword == 'listbox': return self.r_createListWidget(command, record)
        elif keyword == 'combobox': return self.r_createComboBox(command, record)
        elif keyword == 'widget': return self.r_createWidget(command, record)
        elif keyword == 'dialog': return self.r_createDialog(command, record)
        elif keyword == 'messagebox': return self.r_createMessageBox(command, record)
        return None

    # Declare a dialog variable
    def k_dialog(self, command):
        return self.compileVariable(command, 'gui')

    def r_dialog(self, command):
        return self.nextPC()

    # Disable a widget
    def k_disable(self, command):
        if self.nextIsSymbol():
            command['name'] = self.getSymbolRecord()['name']
            self.add(command)
            return True
        return False
    
    def r_disable(self, command):
        self.getWidget(self.getVariable(command['name'])).setEnabled(False)  # type: ignore
        return self.nextPC()

    # Enable a widget
    def k_enable(self, command):
        if self.nextIsSymbol():
            command['name'] = self.getSymbolRecord()['name']
            self.add(command)
            return True
        return False
    
    def r_enable(self, command):
        self.getWidget(self.getVariable(command['name'])).setEnabled(True)  # type: ignore
        return self.nextPC()

    # Create a group box
    def k_group(self, command):
        return self.compileVariable(command, 'gui')

    def r_group(self, command):
        return self.nextPC()

    # hide {widget}
    def k_hide(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if self.isWidget(record['keyword']):
                command['widget'] = record['name']
                self.add(command)
                return True
        return False
        
    def r_hide(self, command):
        record = self.getVariable(command['widget'])
        if 'widget' in record: self.getWidget(record).hide()  # type: ignore
        return self.nextPC()

    # Initialize the graphics environment
    # Unused: def k_init(self, command):
    
    def r_init(self, command):
        self.app = QApplication(sys.argv)
        screen = QApplication.screens()[0].size().toTuple()
        self.program.screenWidth = screen[0]  # type: ignore
        self.program.screenHeight = screen[1]  # type: ignore
        print(f'Screen: {self.program.screenWidth}x{self.program.screenHeight}')
        # return self.nextPC()
        def on_last_window_closed():
            self.program.kill()
        def init():
            self.program.flush(self.nextPC())
        def flush():
            if not self.blocked:
                if self.runOnTick != 0:
                    self.program.run(self.runOnTick)
                self.program.flushCB()
        timer = QTimer()
        timer.timeout.connect(flush)
        timer.start(10)
        QTimer.singleShot(500, init)
        if self.program.debugging: self.program.debugger = Debugger(self.program)
        self.app.lastWindowClosed.connect(on_last_window_closed)
        self.app.exec()

    # Declare a label variable
    def k_label(self, command):
        return self.compileVariable(command, 'gui')

    def r_label(self, command):
        return self.nextPC()

    # Declare a layout variable
    def k_layout(self, command):
        return self.compileVariable(command, 'gui')

    def r_layout(self, command):
        return self.nextPC()

    # Declare a line input variable
    def k_lineinput(self, command):
        return self.compileVariable(command, 'gui')

    def r_lineinput(self, command):
        return self.nextPC()

    # Declare a listbox input variable
    def k_listbox(self, command):
        return self.compileVariable(command, 'gui')

    def r_listbox(self, command):
        return self.nextPC()

    # Declare a messagebox variable
    def k_messagebox(self, command):
        return self.compileVariable(command)

    def r_messagebox(self, command):
        return self.nextPC()

    # Declare a multiline input variable
    def k_multiline(self, command):
        return self.compileVariable(command, 'gui')

    def r_multiline(self, command):
        return self.nextPC()

    # on click {pushbutton}/{lineinput}/{multiline}
    # on select {combobox}/{listbox}
    # on tick
    def k_on(self, command):
        def setupOn():
            command['goto'] = self.getCodeSize() + 2
            self.add(command)
            self.nextToken()
            # Step over the click handler
            pcNext = self.getCodeSize()
            cmd = {}
            cmd['domain'] = 'core'
            cmd['lino'] = command['lino']
            cmd['keyword'] = 'gotoPC'
            cmd['goto'] = 0
            cmd['debug'] = False
            self.add(cmd)
            # This is the click handler
            self.compileOne()
            cmd = {}
            cmd['domain'] = 'core'
            cmd['lino'] = command['lino']
            cmd['keyword'] = 'stop'
            cmd['debug'] = False
            self.add(cmd)
            # Fixup the goto
            self.getCommandAt(pcNext)['goto'] = self.getCodeSize()

        token = self.nextToken()
        command['type'] = token
        if token == 'click':
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] in ['pushbutton', 'lineinput', 'multiline']:
                    command['name'] = record['name']
                    setupOn()
                    return True
        elif token == 'select':
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] in ['combobox', 'listbox']:
                    command['name'] = record['name']
                    setupOn()
                    return True
        elif token == 'tick':
            command['tick'] = True
            command['runOnTick'] = self.getCodeSize() + 2
            self.add(command)
            self.nextToken()
            # Step over the on tick action
            pcNext = self.getCodeSize()
            cmd = {}
            cmd['domain'] = 'core'
            cmd['lino'] = command['lino']
            cmd['keyword'] = 'gotoPC'
            cmd['goto'] = 0
            cmd['debug'] = False
            self.add(cmd)
            # This is the on tick handler
            self.compileOne()
            cmd = {}
            cmd['domain'] = 'core'
            cmd['lino'] = command['lino']
            cmd['keyword'] = 'stop'
            cmd['debug'] = False
            self.add(cmd)
            # Fixup the goto
            self.getCommandAt(pcNext)['goto'] = self.getCodeSize()
            return True
        return False
    
    def r_on(self, command):
        def run(widget, record):
            for i, w in enumerate(record['widget']):
                if w == widget:
                    record['index'] = i
                    self.run(command['goto'])
                    return

        if command['type'] == 'tick':
            self.runOnTick = command['runOnTick']
        else:
            record = self.getVariable(command['name'])
            widget = self.getWidget(record)
            keyword = record['keyword']
            if keyword == 'pushbutton':
                handler = partial(run, widget, record)
                widget.clicked.connect(handler)  # type: ignore
            elif keyword == 'combobox':
                widget.currentIndexChanged.connect(lambda: self.run(command['goto']))  # type: ignore
            elif keyword == 'listbox':
                widget.itemClicked.connect(lambda: self.run(command['goto']))  # type: ignore
        return self.nextPC()

    # Declare a pushbutton variable
    def k_pushbutton(self, command):
        return self.compileVariable(command, 'gui')

    def r_pushbutton(self, command):
        return self.nextPC()

    # remove [the] [current/selected] [item] [from/in] {combobox}/{listbox}
    def k_remove(self, command):
        command['variant'] = None
        self.skip('the')
        self.skip(['current', 'selected'])
        self.skip('item')
        self.skip(['from', 'in'])
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['keyword'] == 'combobox':
                command['variant'] = 'current'
                command['name'] = record['name']
                self.add(command)
                return True
            elif record['keyword'] == 'listbox':
                command['variant'] = 'current'
                command['name'] = record['name']
                self.add(command)
                return True
        return False
        
    def r_remove(self, command):
        variant = command['variant']
        record = self.getVariable(command['name'])
        if variant == 'current':
            if record['keyword'] == 'combobox':
                widget = self.getWidget(record)
                widget.removeItem(widget.currentIndex())  # type: ignore
            if record['keyword'] == 'listbox':
                widget = self.getWidget(record)
                selectedItem = widget.currentItem()  # type: ignore
                if selectedItem:
                    row = widget.row(selectedItem)  # type: ignore
                    widget.takeItem(row)  # type: ignore
        return self.nextPC()

    # select index {n} [of] {combobox]}
    # select {name} [in] {combobox}
    def k_select(self, command):
        if self.nextIs('index'):
            command['index'] = self.nextValue()
            self.skip('of')
        else:
            command['name'] = self.getValue()
            self.skip('in')
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['keyword'] == 'combobox':
                command['widget'] = record['name']
                self.add(command)
                return True
        return False
    
    def r_select(self, command):
        widget = self.getWidget(self.getVariable(command['widget']))
        if 'index' in command:
            index = self.getRuntimeValue(command['index'])
        else:
            name = self.getRuntimeValue(command['name'])
            index = widget.findText(name, Qt.MatchFlag.MatchFixedString)  # type: ignore
        if index >= 0:
            widget.setCurrentIndex(index)  # type: ignore
        return self.nextPC()

    # set [the] width/height [of] {widget} [to] {value}
    # set [the] layout of {window}/{widget} to {layout}
    # set [the] spacing of {layout} to {value}
    # set [the] text [of] {label}/{button}/{lineinput}/{multiline} [to] {text}
    # set [the] color [of] {label}/{button}/{lineinput}/{multiline} [to] {color}
    # set [the] state [of] {checkbox} [to] {state}
    # set [the] style of {widget} to {style}
    # set {listbox} to {list}
    # set blocked true/false
    def k_set(self, command):
        self.skip('the')
        token = self.nextToken()
        command['what'] = token
        if token in ['width', 'height']:
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['extra'] == 'gui':
                    command['name'] = record['name']
                    self.skip('to')
                    command['value'] = self.nextValue()
                    self.add(command)
                    return True
        elif token == 'layout':
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                keyword = record['keyword']
                if keyword in ['window', 'widget']:
                    command['name'] = record['name']
                    self.skip('to')
                    if self.nextIsSymbol():
                        record = self.getSymbolRecord()
                        if record['keyword'] == 'layout':
                            command['layout'] = record['name']
                            self.add(command)
                            return True
        elif token == 'spacing':
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'layout':
                    command['name'] = record['name']
                    self.skip('to')
                    command['value'] = self.nextValue()
                    self.add(command)
                    return True
        elif token == 'text':
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] in ['label', 'pushbutton', 'lineinput', 'multiline', 'element']:
                    command['name'] = record['name']
                    self.skip('to')
                    command['value'] = self.nextValue()
                    self.add(command)
                    return True
        elif token == 'state':
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'checkbox':
                    command['name'] = record['name']
                    self.skip('to')
                    if self.peek() == 'checked':
                        command['value'] = self.compileConstant(True)
                        self.nextToken()
                    elif self.peek() == 'unchecked':
                        command['value'] = self.compileConstant(False)
                        self.nextToken()
                    else: command['value'] = self.nextValue()
                    self.add(command)
                    return True
        elif token == 'style':
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['extra'] == 'gui':
                    command['name'] = record['name']
                    self.skip('to')
                    command['value'] = self.nextValue()
                    self.add(command)
                    return True
        elif token == 'alignment':
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['extra'] == 'gui':
                    command['name'] = record['name']
                    self.skip('to')
                    flags = []
                    while self.peek() in ['left', 'hcenter', 'right', 'top', 'vcenter', 'bottom', 'center']:
                        flags.append(self.nextToken())
                    command['value'] = flags
                    self.add(command)
                    return True
        elif token == 'style':
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'label':
                    command['name'] = record['name']
                    self.skip('to')
                    command['value'] = self.nextValue()
                    self.add(command)
                    return True
        elif token == 'color':
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'label':
                    command['name'] = record['name']
                    self.skip('to')
                    command['value'] = self.nextValue()
                    self.add(command)
                    return True
        elif token == 'background':
            self.skip('color')
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] in ['label', 'pushbutton', 'lineinput', 'multiline']:
                    command['name'] = record['name']
                    self.skip('to')
                    command['value'] = self.nextValue()
                    self.add(command)
                    return True
        elif token == 'blocked':
            self.blocked = True if self.nextToken() == 'true' else False
            return True
        elif self.isSymbol():
            record = self.getSymbolRecord()
            if record['keyword'] == 'listbox':
                command['what'] = 'listbox'
                command['name'] = record['name']
                self.skip('to')
                command['value'] = self.nextValue()
                self.add(command)
                return True
        return False
    
    def r_set(self, command):
        what = command['what']
        if what == 'height':
            widget = self.getWidget(self.getVariable(command['name']))
            widget.setFixedHeight(self.getRuntimeValue(command['value']))  # type: ignore
        elif what == 'width':
            widget = self.getWidget(self.getVariable(command['name']))
            widget.setFixedWidth(self.getRuntimeValue(command['value']))  # type: ignore
        elif what == 'layout':
            record = self.getVariable(command['layout'])
            layout = record['widget']
            record = self.getVariable(command['name'])
            keyword = record['keyword']
            if keyword == 'window':
                window = record['window']
                container = QWidget()
                container.setLayout(layout)
                window.setCentralWidget(container)
            elif keyword == 'widget':
                widget = self.getWidget(record)
                widget.setLayout(layout)  # type: ignore
        elif what == 'spacing':
            layout = self.getWidget(self.getVariable(command['name']))
            layout.setSpacing(self.getRuntimeValue(command['value']))  # type: ignore
        elif what == 'text':
            record = self.getVariable(command['name'])
            widget = self.getWidget(record)
            text = self.getRuntimeValue(command['value'])
            keyword = record['keyword']
            setText = getattr(widget, "setText", None)
            if callable(setText):
                widget.setText(text)  # type: ignore
            elif keyword == 'multiline':
                widget.setPlainText(text)  # type: ignore
            if record['keyword'] == 'pushbutton':
                widget.setAccessibleName(text)  # type: ignore
        elif what == 'state':
            record = self.getVariable(command['name'])
            if record['keyword'] == 'checkbox':
                state = self.getRuntimeValue(command['value'])
                self.getWidget(record).setChecked(state)  # type: ignore
        elif what == 'alignment':
            widget = self.getVariable(command['name'])['widget']
            flags = command['value']
            alignment = 0
            for flag in flags:
                if flag == 'left': alignment |= Qt.AlignmentFlag.AlignLeft
                elif flag == 'hcenter': alignment |= Qt.AlignmentFlag.AlignHCenter
                elif flag == 'right': alignment |= Qt.AlignmentFlag.AlignRight
                elif flag == 'top': alignment |= Qt.AlignmentFlag.AlignTop
                elif flag == 'vcenter': alignment |= Qt.AlignmentFlag.AlignVCenter
                elif flag == 'bottom': alignment |= Qt.AlignmentFlag.AlignBottom
                elif flag == 'center': alignment |= Qt.AlignmentFlag.AlignCenter
            widget.setAlignment(alignment)
        elif what == 'style':
            record = self.getVariable(command['name'])
            widget = self.getWidget(record)
            styles = self.getRuntimeValue(command['value'])
            widget.setStyleSheet(styles)  # type: ignore
        elif what == 'color':
            record = self.getVariable(command['name'])
            widget = self.getWidget(record)
            color = self.getRuntimeValue(command['value'])
            widget.setStyleSheet(f"color: {color};")  # type: ignore
        elif what == 'background-color':
            record = self.getVariable(command['name'])
            widget = self.getWidget(record)
            bg_color = self.getRuntimeValue(command['value'])
            widget.setStyleSheet(f"background-color: {bg_color};")  # type: ignore
        elif what == 'listbox':
            record = self.getVariable(command['name'])
            widget = self.getWidget(record)
            value = self.getRuntimeValue(command['value'])
            widget.clear()  # type: ignore
            widget.addItems(value)  # type: ignore
        return self.nextPC()

    # show {window}
    # show {dialog}
    # show {widget}
    # show {messagebox} giving {result}}
    def k_show(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            keyword = record['keyword']
            if keyword == 'window':
                command['window'] = record['name']
                self.add(command)
                return True
            elif keyword == 'dialog':
                command['dialog'] = record['name']
                self.add(command)
                return True
            elif self.isWidget(keyword):
                command['name'] = record['name']
                self.add(command)
                return True
            elif keyword == 'messagebox':
                command['messagebox'] = record['name']
                self.skip('giving')
                if self.nextIsSymbol():
                    command['result'] = self.getSymbolRecord()['name']
                    self.add(command)
                    return True
        return False
        
    def r_show(self, command):
        if 'messagebox' in command:
            data = self.getVariable(command['messagebox'])['data']
            symbolRecord = self.getVariable(command['result'])
            window = self.getVariable(data['window'])['window']
            style = data['style']
            title = data['title']
            message = data['message']
            if style == 'question':
                choice = QMessageBox.question(window, title, message)
                result = 'Yes' if choice == QMessageBox.StandardButton.Yes else 'No'
            elif style == 'yesnocancel':
                choice = QMessageBox.question(
                    window, 
                    title, 
                    message,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                )
                if choice == QMessageBox.StandardButton.Yes: 
                    result = 'Yes'
                elif choice == QMessageBox.StandardButton.No:
                    result = 'No'
                else:
                    result = 'Cancel'
            elif style == 'warning':
                choice = QMessageBox.warning(window, title, message)
                if choice == QMessageBox.StandardButton.Ok: result = 'OK'
                else: result = ''
            else: result = 'Cancel'
            v = {}
            v['type'] = 'text'
            v['content'] = result
            self.putSymbolValue(symbolRecord, v)
        elif 'window' in command:
            window = self.getVariable(command['window'])['window']
            window.show()
        elif 'dialog' in command:
            record = self.getVariable(command['dialog'])
            dialog = record['dialog']
            if dialog.dialogType == 'generic':
                record['result'] =  dialog.exec()
            elif dialog.dialogType == 'confirm':
                record['result'] = True if dialog.exec() == QDialog.DialogCode.Accepted else False
            elif dialog.dialogType == 'lineedit':
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    record['result'] = dialog.lineEdit.text()  # type: ignore
                else: record['result'] = dialog.value  # type: ignore
            elif dialog.dialogType == 'multiline':
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    record['result'] = dialog.textEdit.toPlainText()  # type: ignore
                else: record['result'] = dialog.value  # type: ignore
        elif 'name' in command:
            record = self.getVariable(command['name'])
            if 'widget' in record: self.getWidget(record).show()  # type: ignore
        return self.nextPC()

    # Start the graphics
    def k_start(self, command):
        if self.nextIs('graphics'):
            self.add(command)
            return True
        return False
        
    def r_start(self, command):
        return self.nextPC()

    # Declare a widget variable
    def k_widget(self, command):
        return self.compileVariable(command, 'gui')

    def r_widget(self, command):
        return self.nextPC()

    # Declare a window variable
    def k_window(self, command):
        return self.compileVariable(command)

    def r_window(self, command):
        return self.nextPC()
    
    #############################################################################
    # Compile a value in this domain
    def compileValue(self):
        value = {}
        value['domain'] = self.getName()
        token = self.getToken()
        if self.isSymbol():
            record = self.getSymbolRecord()
            if record['extra'] == 'gui':
                if self.isWidget(record['keyword']):
                    value['name'] = token
                    value['type'] = 'symbol'
                    return value

        else:
            if self.tokenIs('the'): token = self.nextToken()
            if token == 'count':
                self.skip('of')
                if self.nextIsSymbol():
                    value['type'] = 'symbol'
                    record = self.getSymbolRecord()
                    keyword = record['keyword']
                    if keyword in ['combobox', 'listbox']:
                        value['type'] = 'count'
                        value['name'] = record['name']
                        return value
            
            elif token == 'current':
                self.skip('item')
                self.skip('in')
                if self.nextIsSymbol():
                    value['type'] = 'symbol'
                    record = self.getSymbolRecord()
                    keyword = record['keyword']
                    if keyword == 'listbox':
                        value['type'] = 'current'
                        value['name'] = record['name']
                        return value

        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        return value

    #############################################################################
    # Value handlers

    # This is used by the expression evaluator to get the value of a symbol
    def v_symbol(self, symbolRecord):
        symbolRecord = self.getVariable(symbolRecord['name'])
        keyword = symbolRecord['keyword']
        if keyword == 'pushbutton':
            pushbutton = self.getWidget(symbolRecord)
            v = {}
            v['type'] = 'text'
            v['content'] = pushbutton.accessibleName()  # type: ignore
            return v
        elif keyword == 'lineinput':
            lineinput = self.getWidget(symbolRecord)
            v = {}
            v['type'] = 'text'
            v['content'] = lineinput.displayText()  # type: ignore
            return v
        elif keyword == 'multiline':
            multiline = self.getWidget(symbolRecord)
            v = {}
            v['type'] = 'text'
            v['content'] = multiline.toPlainText()  # type: ignore
            return v
        elif keyword == 'combobox':
            combobox = self.getWidget(symbolRecord)
            v = {}
            v['type'] = 'text'
            v['content'] = combobox.currentText()  # type: ignore
            return v
        elif keyword == 'listbox':
            listbox = self.getWidget(symbolRecord)
            content = listbox.currentItem().text()  # type: ignore
            v = {}
            v['type'] = 'text'
            v['content'] = content
            return v
        elif keyword == 'checkbox':
            checkbox =self.getWidget(symbolRecord)
            content = checkbox.isChecked()  # type: ignore
            v = {}
            v['type'] = 'boolean'
            v['content'] = content
            return v
        elif keyword == 'dialog':
            content = symbolRecord['result']
            v = {}
            v['type'] = 'text'
            v['content'] = content
            return v
        return None

    def v_count(self, v):
        record = self.getVariable(v['name'])
        keyword = record['keyword']
        widget = self.getWidget(record)
        if keyword in ['combobox', 'listbox']: content = widget.count()  # type: ignore
        value = {}
        value['type'] = 'int'
        value['content'] = content
        return value

    def v_current(self, v):
        record = self.getVariable(v['name'])
        keyword = record['keyword']
        widget = self.getWidget(record)
        if keyword == 'listbox': content = widget.currentItem().text()  # type: ignore
        value = {}
        value['type'] = 'text'
        value['content'] = content
        return value

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = Object()
        condition.negate = False
        return None

    #############################################################################
    # Condition handlers

    #############################################################################
    # Force the application to exit
    def force_exit(self):
        QApplication.quit()  # Gracefully close the application
        sys.exit(0)          # Force a complete system exit