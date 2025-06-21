import sys
from easycoder import Handler, RuntimeError
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
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
    QListWidget,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTimeEdit,
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
    QDialogButtonBox
)

class Graphics(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)
        self.blocked = False
        self.runOnTick = 0

    def getName(self):
        return 'graphics'

    def closeEvent(self):
        print('window closed')
    
    def isWidget(self, keyword):
        return keyword in ['layout', 'groupbox', 'label', 'pushbutton', 'checkbox', 'lineinput', 'listbox', 'combobox']

    #############################################################################
    # Keyword handlers

    # (1) add {value} to {widget}
    # (2) add {widget} to {layout}
    # (3) add stretch {widget} to {layout}
    # (4) add stretch to {layout}
    def k_add(self, command):
        def addToLayout():
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                command['layout'] = record['name']
                self.add(command)
                return True
            return False

        command['stretch'] = False
        if self.nextIs('stretch'):
            # It's either (3) or (4)
            self.nextToken()
            if self.tokenIs('to'):
                # (4)
                command['widget'] = 'stretch'
                return addToLayout()
            # (3)
            if self.isSymbol():
                record = self.getSymbolRecord()
                command['widget'] = record['name']
                command['stretch'] = True
                if self.nextIs('to'):
                    return addToLayout()
            return False

        # Here it's either (1) or (2)
        elif self.isSymbol():
            record = self.getSymbolRecord()
            if record['extra'] == 'gui':
                if self.isWidget(record['keyword']):
                    if self.peek() == 'to':
                        # (2)
                        record = self.getSymbolRecord()
                        command['widget'] = record['name']
                        self.nextToken()
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
            widget = self.getVariable(command['widget'])
            if widget['keyword'] in ['listbox', 'combobox']:
                widget['widget'].addItem(value)
        else:
            layoutRecord = self.getVariable(command['layout'])
            widget = command['widget']
            if widget == 'stretch':
                layoutRecord['widget'].addStretch()
            else:
                widgetRecord = self.getVariable(widget)
                layoutRecord = self.getVariable(command['layout'])
                widget = widgetRecord['widget']
                layout = layoutRecord['widget']
                stretch = command['stretch']
                if widgetRecord['keyword'] == 'layout':
                    if layoutRecord['keyword'] == 'groupbox':
                        if widgetRecord['keyword'] == 'layout':
                            layout.setLayout(widget)
                        else:
                            RuntimeError(self.program, 'Can only add a layout to a groupbox')
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
        return self.compileVariable(command, False, 'gui')

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
        self.getVariable(command['name'])['widget'].clear()
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
        return self.compileVariable(command, False, 'gui')

    def r_combobox(self, command):
        return self.nextPC()

    # Create a window
    def k_createWindow(self, command):
        command['title'] = 'Default'
        x = None
        y = None
        w = self.compileConstant(640)
        h = self.compileConstant(480)
        while True:
            token = self.peek()
            if token in ['title', 'at', 'size', 'layout']:
                self.nextToken()
                if token == 'title': command['title'] = self.nextValue()
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
        text = ''
        while True:
            token = self.peek()
            if token == 'text':
                self.nextToken()
                text = self.nextValue()
            elif token == 'size':
                self.nextToken()
                command['size'] = self.nextValue()
            else: break
        command['text'] = text
        self.add(command)
        return True

    def k_createCheckBox(self, command):
        if self.peek() == 'text':
            self.nextToken()
            text = self.nextValue()
        else: text = ''
        command['text'] = text
        self.add(command)
        return True

    def k_createLineEdit(self, command):
        if self.peek() == 'size':
            self.nextToken()
            size = self.nextValue()
        else: size = self.compileConstant(10)
        command['size'] = size
        self.add(command)
        return True

    def k_createListWidget(self, command):
        self.add(command)
        return True

    def k_createComboBox(self, command):
        self.add(command)
        return True

    def k_createDialog(self, command):
        if self.peek() == 'on':
            self.nextToken()
            if self.nextIsSymbol():
                command['window'] = self.getSymbolRecord()['name']
        else: command['window'] = None
        title = ''
        while True:
            if self.peek() == 'title':
                self.nextToken()
                title = self.nextValue()
            elif self.peek() == 'layout':
                self.nextToken()
                if self.nextIsSymbol():
                    command['layout'] = self.getSymbolRecord()['name']
            else: break
        command['title'] = title
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
            elif keyword == 'layout': return self.k_createLayout(command)
            elif keyword == 'groupbox': return self.k_createGroupBox(command)
            elif keyword == 'label': return self.k_createLabel(command)
            elif keyword == 'pushbutton': return self.k_createPushbutton(command)
            elif keyword == 'checkbox': return self.k_createCheckBox(command)
            elif keyword == 'lineinput': return self.k_createLineEdit(command)
            elif keyword == 'listbox': return self.k_createListWidget(command)
            elif keyword == 'combobox': return self.k_createComboBox(command)
            elif keyword == 'dialog': return self.k_createDialog(command)
            elif keyword == 'messagebox': return self.k_createMessageBox(command)
        return False
    
    def r_createWindow(self, command, record):
        window = QMainWindow()
        window.setWindowTitle(self.getRuntimeValue(command['title']))
        w = self.getRuntimeValue(command['w'])
        h = self.getRuntimeValue(command['h'])
        x = command['x']
        y = command['y']
        if x == None: x = (self.program.screenWidth - w) / 2
        else: x = self.getRuntimeValue(x)
        if y == None: y = (self.program.screenHeight - h) / 2
        else: y = self.getRuntimeValue(x)
        window.setGeometry(x, y, w, h)
        record['window'] = window
        return self.nextPC()
    
    def r_createLayout(self, command, record):
        type = command['type']
        if type == 'QHBoxLayout': layout = QHBoxLayout()
        elif type == 'QGridLayout': layout = QGridLayout()
        elif type == 'QStackedLayout': layout = QStackedLayout()
        else: layout = QVBoxLayout()
        layout.setContentsMargins(5,0,5,0)
        record['widget'] = layout
        return self.nextPC()
    
    def r_createGroupBox(self, command, record):
        groupbox = QGroupBox(self.getRuntimeValue(command['title']))
        groupbox.setAlignment(Qt.AlignLeft)
        record['widget'] = groupbox
        return self.nextPC()
    
    def r_createLabel(self, command, record):
        label = QLabel(self.getRuntimeValue(command['text']))
        if 'size' in command:
            fm = label.fontMetrics()
            c = label.contentsMargins()
            w = fm.horizontalAdvance('m') * self.getRuntimeValue(command['size']) +c.left()+c.right()
            label.setMaximumWidth(w)
        if 'align' in command:
            alignment = command['align']
            if alignment == 'left': label.setAlignment(Qt.AlignLeft)
            elif alignment == 'right': label.setAlignment(Qt.AlignRight)
            elif alignment in ['center', 'centre']: label.setAlignment(Qt.AlignHCenter)
            elif alignment == 'justify': label.setAlignment(Qt.AlignJustify)
        record['widget'] = label
        return self.nextPC()
    
    def r_createPushbutton(self, command, record):
        text = self.getRuntimeValue(command['text'])
        pushbutton = QPushButton(text)
        pushbutton.setAccessibleName(text)
        if 'size' in command:
            fm = pushbutton.fontMetrics()
            c = pushbutton.contentsMargins()
            w = fm.horizontalAdvance('m') * self.getRuntimeValue(command['size']) +c.left()+c.right()
            pushbutton.setMaximumWidth(w)
        record['widget'] = pushbutton
        return self.nextPC()
    
    def r_createCheckBox(self, command, record):
        checkbox = QCheckBox(self.getRuntimeValue(command['text']))
        record['widget'] = checkbox
        return self.nextPC()
    
    def r_createLineEdit(self, command, record):
        lineinput = QLineEdit()
        fm = lineinput.fontMetrics()
        m = lineinput.textMargins()
        c = lineinput.contentsMargins()
        w = fm.horizontalAdvance('x') * self.getRuntimeValue(command['size']) +m.left()+m.right()+c.left()+c.right()
        lineinput.setMaximumWidth(w)
        record['widget'] = lineinput
        return self.nextPC()
    
    def r_createListWidget(self, command, record):
        record['widget'] = QListWidget()
        return self.nextPC()
    
    def r_createComboBox(self, command, record):
        record['widget'] = QComboBox()
        return self.nextPC()
    
    def r_createDialog(self, command, record):
        layout = self.getVariable(command['layout'])['widget']
        dialog = QDialog()
        dialog.setWindowTitle(self.getRuntimeValue(command['title']))
        dialog.buttonBox = QDialogButtonBox((QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        dialog.buttonBox.accepted.connect(dialog.accept)
        dialog.buttonBox.rejected.connect(dialog.reject)
        layout.addWidget(dialog.buttonBox)
        dialog.setLayout(layout)
        record['dialog'] = dialog
        return self.nextPC()
    
    # Creates a message box but doesn'r run it
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
        elif keyword == 'groupbox': return self.r_createGroupBox(command, record)
        elif keyword == 'label': return self.r_createLabel(command, record)
        elif keyword == 'pushbutton': return self.r_createPushbutton(command, record)
        elif keyword == 'checkbox': return self.r_createCheckBox(command, record)
        elif keyword == 'lineinput': return self.r_createLineEdit(command, record)
        elif keyword == 'listbox': return self.r_createListWidget(command, record)
        elif keyword == 'combobox': return self.r_createComboBox(command, record)
        elif keyword == 'dialog': return self.r_createDialog(command, record)
        elif keyword == 'messagebox': return self.r_createMessageBox(command, record)
        return None

    # Declare a dialog variable
    def k_dialog(self, command):
        return self.compileVariable(command, False)

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
        self.getVariable(command['name'])['widget'].setEnabled(False)
        return self.nextPC()

    # Enable a widget
    def k_enable(self, command):
        if self.nextIsSymbol():
            command['name'] = self.getSymbolRecord()['name']
            self.add(command)
            return True
        return False
    
    def r_enable(self, command):
        self.getVariable(command['name'])['widget'].setEnabled(True)
        return self.nextPC()

    # Create a group box
    def k_groupbox(self, command):
        return self.compileVariable(command, False, 'gui')

    def r_groupbox(self, command):
        return self.nextPC()

    # Initialize the graphics environment
    def k_init(self, command):
        if self.nextIs('graphics'):
            self.add(command)
            return True
        return False
    
    def r_init(self, command):
        self.app = QApplication(sys.argv)
        screen = QApplication.screens()[0].size().toTuple()
        self.program.screenWidth = screen[0]
        self.program.screenHeight = screen[1]
        print(f'Screen: {self.program.screenWidth}x{self.program.screenHeight}')
        return self.nextPC()

    # Declare a label variable
    def k_label(self, command):
        return self.compileVariable(command, False, 'gui')

    def r_label(self, command):
        return self.nextPC()

    # Declare a layout variable
    def k_layout(self, command):
        return self.compileVariable(command, False, 'gui')

    def r_layout(self, command):
        return self.nextPC()

    # Declare a line input variable
    def k_lineinput(self, command):
        return self.compileVariable(command, False, 'gui')

    def r_lineinput(self, command):
        return self.nextPC()

    # Declare a listbox input variable
    def k_listbox(self, command):
        return self.compileVariable(command, False, 'gui')

    def r_listbox(self, command):
        return self.nextPC()

    # Declare a messagebox variable
    def k_messagebox(self, command):
        return self.compileVariable(command, False)

    def r_messagebox(self, command):
        return self.nextPC()

    # on click {pushbutton}
    # on select {combobox}/{listbox}
    # on tick
    def k_on(self, command):
        def setupOn():
            command['goto'] = self.getPC() + 2
            self.add(command)
            self.nextToken()
            # Step over the click handler
            pcNext = self.getPC()
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
            self.getCommandAt(pcNext)['goto'] = self.getPC()

        token = self.nextToken()
        command['type'] = token
        if token == 'click':
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'pushbutton':
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
            command['runOnTick'] = self.getPC() + 2
            self.add(command)
            self.nextToken()
            # Step over the on tick action
            pcNext = self.getPC()
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
            self.getCommandAt(pcNext)['goto'] = self.getPC()
            return True
        return False
    
    def r_on(self, command):
        if command['type'] == 'tick':
            self.runOnTick = command['runOnTick']
        else:
            record = self.getVariable(command['name'])
            widget = record['widget']
            keyword = record['keyword']
            if keyword == 'pushbutton':
                widget.clicked.connect(lambda: self.run(command['goto']))
            elif keyword == 'combobox':
                widget.currentIndexChanged.connect(lambda: self.run(command['goto']))
            elif keyword == 'listbox':
                widget.itemClicked.connect(lambda: self.run(command['goto']))
        return self.nextPC()

    # Declare a pushbutton variable
    def k_pushbutton(self, command):
        return self.compileVariable(command, False, 'gui')

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
                widget = record['widget']
                widget.removeItem(widget.currentIndex())
            if record['keyword'] == 'listbox':
                widget = record['widget']
                selectedItem = widget.currentItem()
                if selectedItem:
                    row = widget.row(selectedItem)
                    widget.takeItem(row)
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
        widget = self.getVariable(command['widget'])['widget']
        if 'index' in command:
            index = self.getRuntimeValue(command['index'])
        else:
            name = self.getRuntimeValue(command['name'])
            index = widget.findText(name, Qt.MatchFixedString)
        if index >= 0:
            widget.setCurrentIndex(index)
        return self.nextPC()

    # set [the] width/height [of] {widget} [to] {value}
    # set [the] layout of {window} to {layout}
    # set [the] spacing of {layout} to {value}
    # set [the] text [of] {label}/{button}/{lineinput} [to] {text}
    # set [the] color [of] {label}/{button}/{lineinput} [to] {color}
    # set [the] state [of] {checkbox} [to] {color}
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
                if record['keyword'] == 'window':
                    command['name'] = record['name']
                    self.skip('to')
                    if self.nextIsSymbol():
                        record = self.getSymbolRecord()
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
                if record['keyword'] in ['label', 'pushbutton', 'lineinput']:
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
                if record['keyword'] in ['label', 'pushbutton', 'lineinput']:
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
            widget = self.getVariable(command['name'])['widget']
            widget.setFixedHeight(self.getRuntimeValue(command['value']))
        elif what == 'width':
            widget = self.getVariable(command['name'])['widget']
            widget.setFixedWidth(self.getRuntimeValue(command['value']))
        elif what == 'layout':
            window = self.getVariable(command['name'])['window']
            content = self.getVariable(command['layout'])['widget']
            container = QWidget()
            container.setLayout(content)
            window.setCentralWidget(container)
        elif what == 'spacing':
            layout = self.getVariable(command['name'])['widget']
            layout.setSpacing(self.getRuntimeValue(command['value']))
        elif what == 'text':
            record = self.getVariable(command['name'])
            widget = self.getVariable(command['name'])['widget']
            text = self.getRuntimeValue(command['value'])
            widget.setText(text)
            if record['keyword'] == 'pushbutton':
                widget.setAccessibleName(text)
        elif what == 'state':
            widget = self.getVariable(command['name'])['widget']
            state = self.getRuntimeValue(command['value'])
            widget.setChecked(state)
        elif what == 'color':
            widget = self.getVariable(command['name'])['widget']
            color = self.getRuntimeValue(command['value'])
            widget.setStyleSheet(f"color: {color};")
        elif what == 'background-color':
            widget = self.getVariable(command['name'])['widget']
            bg_color = self.getRuntimeValue(command['value'])
            widget.setStyleSheet(f"background-color: {bg_color};")
        elif what == 'listbox':
            widget = self.getVariable(command['name'])['widget']
            value = self.getRuntimeValue(command['value'])
            widget.clear()
            widget.addItems(value)
        return self.nextPC()

    # show {window}
    # show {dialog}
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
                result = 'Yes' if choice == QMessageBox.Yes else 'No'
            elif style == 'yesnocancel':
                choice = QMessageBox.question(
                    window, 
                    title, 
                    message,
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                if choice == QMessageBox.Yes: 
                    result = 'Yes'
                elif choice == QMessageBox.No:
                    result = 'No'
                else:
                    result = 'Cancel'
            elif style == 'warning':
                choice = QMessageBox.warning(window, title, message)
                if choice == QMessageBox.Ok: result = 'OK'
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
            dialog = self.getVariable(command['dialog'])['dialog']
            dialog.exec()
        return self.nextPC()

    # Start the graphics
    def k_start(self, command):
        if self.nextIs('graphics'):
            self.add(command)
            return True
        return False
        
    def r_start(self, command):
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
        self.app.lastWindowClosed.connect(on_last_window_closed)
        self.app.exec()

    # Declare a window variable
    def k_window(self, command):
        return self.compileVariable(command, False)

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
            pushbutton = symbolRecord['widget']
            v = {}
            v['type'] = 'text'
            v['content'] = pushbutton.accessibleName()
            return v
        elif keyword == 'lineinput':
            lineinput = symbolRecord['widget']
            v = {}
            v['type'] = 'text'
            v['content'] = lineinput.displayText()
            return v
        elif keyword == 'combobox':
            combobox = symbolRecord['widget']
            v = {}
            v['type'] = 'text'
            v['content'] = combobox.currentText()
            return v
        elif keyword == 'listbox':
            listbox = symbolRecord['widget']
            content = listbox.currentItem().text()
            v = {}
            v['type'] = 'text'
            v['content'] = content
            return v
        elif keyword == 'checkbox':
            checkbox = symbolRecord['widget']
            content = checkbox.isChecked()
            v = {}
            v['type'] = 'boolean'
            v['content'] = content
            return v
        return None

    def v_count(self, v):
        record = self.getVariable(v['name'])
        keyword = record['keyword']
        widget = record['widget']
        if keyword in ['combobox', 'listbox']: content = widget.count()
        value = {}
        value['type'] = 'int'
        value['content'] = content
        return value

    def v_current(self, v):
        record = self.getVariable(v['name'])
        keyword = record['keyword']
        widget = record['widget']
        if keyword == 'listbox': content = widget.currentItem().text()
        value = {}
        value['type'] = 'text'
        value['content'] = content
        return value

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers

    #############################################################################
    # Force the application to exit
    def force_exit(self):
        QApplication.quit()  # Gracefully close the application
        sys.exit(0)          # Force a complete system exit
