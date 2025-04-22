import sys
from easycoder import Handler, FatalError, RuntimeError
from PySide6.QtCore import Qt, QTimer
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
    QSizePolicy
)

class Graphics(Handler):

    class MainWindow(QMainWindow):

        def __init__(self):
            super().__init__()

    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'pyside6'

    def closeEvent(self):
        print('window closed')

    #############################################################################
    # Keyword handlers

    # Add a widget to a layout
    # add [stretch] {widget} to {layout}
    # add stretch to {layout}
    def k_add(self, command):
        command['stretch'] = False
        if self.nextIs('stretch'):
            if self.peek() == 'to':
                command['widget'] = 'stretch'
            elif self.nextIsSymbol():
                record = self.getSymbolRecord()
                command['widget'] = record['name']
                command['stretch'] = True
            else: return False
        elif self.isSymbol():
            record = self.getSymbolRecord()
            command['widget'] = record['name']
        else: return False
        if self.nextIs('to'):
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                command['layout'] = record['name']
                self.add(command)
                return True
        return False
    
    def r_add(self, command):
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

    # Declare a checkbox variable
    def k_checkbox(self, command):
        return self.compileVariable(command, False)

    def r_checkbox(self, command):
        return self.nextPC()

    # Close a window
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

    # Create a window
    def k_createWindow(self, command):
        command['title'] = 'Default'
        command['x'] = self.compileConstant(100)
        command['y'] = self.compileConstant(100)
        command['w'] = self.compileConstant(640)
        command['h'] = self.compileConstant(480)
        while True:
            token = self.peek()
            if token in ['title', 'at', 'size']:
                self.nextToken()
                if token == 'title': command['title'] = self.nextValue()
                elif token == 'at':
                    command['x'] = self.nextValue()
                    command['y'] = self.nextValue()
                elif token == 'size':
                    command['w'] = self.nextValue()
                    command['h'] = self.nextValue()
            else: break
        self.add(command)
        return True

    # Create a widget
    def k_createLayout(self, command):
        if self.nextIs('type'):
            command['type'] = self.nextToken()
            self.add(command)
            return True
        return False

    def k_createGroupBox(self, command):
        if self.peek() == 'title':
            self.nextToken()
            title = self.nextValue()
        else: title = ''
        command['title'] = title
        self.add(command)
        return True

    def k_createLabel(self, command):
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
        else: size = 10
        command['size'] = size
        self.add(command)
        return True

    def k_createListWidget(self, command):
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
        return False
    
    def r_createWindow(self, command, record):
        window = self.MainWindow()
        window.setWindowTitle(self.getRuntimeValue(command['title']))
        x = self.getRuntimeValue(command['x'])
        y = self.getRuntimeValue(command['y'])
        w = self.getRuntimeValue(command['w'])
        h = self.getRuntimeValue(command['h'])
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
            w = fm.horizontalAdvance('x') * self.getRuntimeValue(command['size']) +c.left()+c.right()
            label.setMaximumWidth(w)
        record['widget'] = label
        return self.nextPC()
    
    def r_createPushbutton(self, command, record):
        pushbutton = QPushButton(self.getRuntimeValue(command['text']))
        if 'size' in command:
            fm = pushbutton.fontMetrics()
            c = pushbutton.contentsMargins()
            w = fm.horizontalAdvance('x') * self.getRuntimeValue(command['size']) +c.left()+c.right()
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
        return None

    # Create a group box
    def k_groupbox(self, command):
        return self.compileVariable(command, False)

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
        return self.nextPC()

    # Declare a label variable
    def k_label(self, command):
        return self.compileVariable(command, False)

    def r_label(self, command):
        return self.nextPC()

    # Declare a layout variable
    def k_layout(self, command):
        return self.compileVariable(command, False)

    def r_layout(self, command):
        return self.nextPC()

    # Declare a line input variable
    def k_lineinput(self, command):
        return self.compileVariable(command, False)

    def r_lineinput(self, command):
        return self.nextPC()

    # Declare a listbox input variable
    def k_listbox(self, command):
        return self.compileVariable(command, False)

    def r_listbox(self, command):
        return self.nextPC()

    # Handle events
    def k_on(self, command):
        if self.nextIs('click'):
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'pushbutton':
                    command['name'] = record['name']
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
                    self.addCommand(cmd)
                    # This is the click handler
                    self.compileOne()
                    cmd = {}
                    cmd['domain'] = 'core'
                    cmd['lino'] = command['lino']
                    cmd['keyword'] = 'stop'
                    cmd['debug'] = False
                    self.addCommand(cmd)
                    # Fixup the link
                    self.getCommandAt(pcNext)['goto'] = self.getPC()
                    return True
        return False
    
    def r_on(self, command):
        pushbutton = self.getVariable(command['name'])['widget']
        pushbutton.clicked.connect(lambda: self.run(command['goto']))
        return self.nextPC()

    # Declare a pushbutton variable
    def k_pushbutton(self, command):
        return self.compileVariable(command, False)

    def r_pushbutton(self, command):
        return self.nextPC()

    # Clean exit
    def on_last_window_closed(self):
        print("Last window closed! Performing cleanup...")
        self.program.kill()

    # This is called every 10ms to keep the main application running
    def flush(self):
        self.program.flushCB()

    # Resume execution at the line following 'start graphics'
    def resume(self):
        self.program.flush(self.nextPC())

    # Set something
    def k_set(self, command):
        token = self.nextToken()
        if token == 'the': token = self.nextToken()
        if token == 'height':
            command['property'] = token
            if self.nextToken() == 'of':
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    keyword = record['keyword']
                    if keyword == 'groupbox':
                        command['name'] = record['name']
                        if self.nextIs('to'):
                            command['value'] = self.nextValue()
                            self.add(command)
                            return True
        return False
    
    def r_set(self, command):
        property = command['property']
        if property == 'height':
            groupbox = self.getVariable(command['name'])['widget']
            groupbox.setFixedHeight(self.getRuntimeValue(command['value']))
        return self.nextPC()

    # Show a window with a specified layout
    # show {name} in {window}}
    def k_show(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['keyword'] == 'layout':
                command['layout'] = record['name']
                if self.nextIs('in'):
                    if self.nextIsSymbol():
                        record = self.getSymbolRecord()
                        if record['keyword'] == 'window':
                            command['window'] = record['name']
                            self.add(command)
                            return True
        return False
        
    def r_show(self, command):
        layoutRecord = self.getVariable(command['layout'])
        windowRecord = self.getVariable(command['window'])
        window = windowRecord['window']
        container = QWidget()
        container.setLayout(layoutRecord['widget'])
        window.setCentralWidget(container)
        window.show()
        return self.nextPC()

    # Start the graphics
    def k_start(self, command):
        if self.nextIs('graphics'):
            self.add(command)
            return True
        return False
        
    def r_start(self, command):
        timer = QTimer()
        timer.timeout.connect(self.flush)
        timer.start(10)
        QTimer.singleShot(500, self.resume)
        self.app.lastWindowClosed.connect(self.on_last_window_closed)
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
        value['domain'] = 'rbr'
        if self.tokenIs('the'):
            self.nextToken()
        token = self.getToken()
        if token == 'xxxxx':
            return value

        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        return value

    #############################################################################
    # Value handlers

    def v_xxxxx(self, v):
        value = {}
        return value

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers
