import sys
from easycoder import Handler, FatalError, RuntimeError
from PySide6.QtCore import QTimer
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
    QWidget
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
    def k_add(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            command['widget'] = record['name']
            if self.nextIs('to'):
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    command['layout'] = record['name']
                    self.add(command)
                    return True
        return False
    
    def r_add(self, command):
        widgetRecord = self.getVariable(command['widget'])
        layoutRecord = self.getVariable(command['layout'])
        if widgetRecord['keyword'] == 'layout':
            layoutRecord['widget'].addLayout(widgetRecord['widget'])
        else:
            layoutRecord['widget'].addWidget(widgetRecord['widget'])
        return self.nextPC()

    # Create a window
    def k_createWindow(self, command):
        command['title'] = 'Default'
        command['x'] = 100
        command['y'] = 100
        command['w'] = 640
        command['h'] = 480
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

    def k_createLabel(self, command):
        if self.peek() == 'text':
            self.nextToken()
            text = self.nextValue()
        else: text = ''
        command['text'] = text
        self.add(command)
        return True

    def k_createPushbutton(self, command):
        if self.peek() == 'text':
            self.nextToken()
            text = self.nextValue()
        else: text = ''
        command['text'] = text
        self.add(command)
        return True

    def k_create(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            command['name'] = record['name']
            keyword = record['keyword']
            if keyword == 'window': return self.k_createWindow(command)
            elif keyword == 'layout': return self.k_createLayout(command)
            elif keyword == 'label': return self.k_createLabel(command)
            elif keyword == 'pushbutton': return self.k_createPushbutton(command)
        return False
    
    def r_createWindow(self, command, record):
        window = self.MainWindow()
        window.setWindowTitle(self.getRuntimeValue(command['title']))
        x = self.getRuntimeValue(command['x'])
        y = self.getRuntimeValue(command['y'])
        w = self.getRuntimeValue(command['w'])
        h = self.getRuntimeValue(command['h'])
        if x != None and y != None and w != None and h != None: 
            window.setGeometry(x, y, w, h)
        record['window'] = window
        return self.nextPC()
    
    def r_createLayout(self, command, record):
        type = command['type']
        if type == 'QHBoxLayout': layout = QHBoxLayout()
        elif type == 'QGridLayout': layout = QGridLayout()
        elif type == 'QStackedLayout': layout = QStackedLayout()
        else: layout = QVBoxLayout()
        record['widget'] = layout
        return self.nextPC()
    
    def r_createLabel(self, command, record):
        label = QLabel(self.getRuntimeValue(command['text']))
        record['widget'] = label
        return self.nextPC()
    
    def r_createPushbutton(self, command, record):
        pushbutton = QPushButton(self.getRuntimeValue(command['text']))
        record['widget'] = pushbutton
        return self.nextPC()

    def r_create(self, command):
        record = self.getVariable(command['name'])
        keyword = record['keyword']
        if keyword == 'window': return self.r_createWindow(command, record)
        elif keyword == 'layout': return self.r_createLayout(command, record)
        elif keyword == 'label': return self.r_createLabel(command, record)
        elif keyword == 'pushbutton': return self.r_createPushbutton(command, record)
        return None

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
