from .ec_classes import FatalError, RuntimeError, Object
from .ec_handler import Handler
from .ec_gutils import GUtils
import PySimpleGUI as psg
import json

class Graphics(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)
        self.utils = GUtils()

    def getName(self):
        return 'graphics'

    #############################################################################
    # Keyword handlers

    def k_add(self, command):
        token = self.nextToken()
        if self.isSymbol():
            symbolRecord = self.getSymbolRecord()
            name = symbolRecord['name']
            keyword = symbolRecord['keyword']
            if keyword == 'layout':
                command['args'] = name
            elif keyword in ['column', 'frame', 'tab']:
                command['name'] = name
                command['type'] = token
                if self.peek() == 'to':
                    command['args'] = []
                else:
                    command['args'] = self.utils.getArgs(self)
        else:
            command['type'] = token
            command['args'] = self.utils.getArgs(self)
        if self.nextIs('to'):
            if self.nextIsSymbol():
                symbolRecord = self.getSymbolRecord()
                if symbolRecord['keyword'] in ['column', 'frame', 'layout', 'tab']:
                    command['target'] = symbolRecord['name']
                    self.addCommand(command)
                    return True
        return False

    def r_add(self, command):
        target = self.getVariable(command['target'])
        type = command['type']
        args = command['args']
        param= None
        if not 'layout' in target:
            target['layout'] = []
        if args[0] == '{':
            if type in ['Column', 'Frame', 'Tab']:
                record = self.getVariable(command['name'])
                param = record['layout']
            layout = json.loads(self.getRuntimeValue(json.loads(args)))
            default = self.utils.getDefaultArgs(type)
            for n in range(0, len(layout)):
                args = self.utils.decode(default, layout[n])
            item = self.utils.createElement(type, param, args)
            target['layout'].append(item)
        else:
            v = self.getVariable(args)
            target['layout'].append(v['layout'])
        return self.nextPC()

    def k_capture(self, command):
        if self.nextIs('event'):
            if self.nextIs('as'):
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    command['target'] = record['name']
                    self.addCommand(command)
                    return True
        return False

    def r_capture(self, command):
        target = self.getVariable(command['target'])
        self.putSymbolValue(target, self.getConstant(self.eventValues))
        return self.nextPC()

    def k_close(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['keyword'] == 'window':
                command['target'] = symbolRecord['name']
                self.add(command)
                return True
        return False

    def r_close(self, command):
        target = self.getVariable(command['target'])
        target['window'].close()
        return self.nextPC()

    def k_column(self, command):
        return self.compileVariable(command)

    def r_column(self, command):
        return self.nextPC()

    # create {window} layout {layout}
    # create {element} {args...}
    def k_create(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            type = symbolRecord['keyword']
            command['type'] = type
            command['name'] = symbolRecord['name']
            if type == 'window':
                command['title'] = self.nextValue()
                if self.nextIs('layout'):
                    if self.nextIsSymbol():
                        symbolRecord = self.getSymbolRecord()
                        if symbolRecord['keyword'] == 'layout':
                            command['layout'] = symbolRecord['name']
                            self.addCommand(command)
                            return True
        return False

    def r_create(self, command):
        type = command['type']
        record = self.getVariable(command['name'])
        if type == 'window':
            layout = self.getVariable(command['layout'])
            title = self.getRuntimeValue(command['title'])
            record['window'] = psg.Window(title, layout['layout'], finalize=True)
            record['eventHandlers'] = {}
            self.program.windowRecord = record
            self.program.run(self.nextPC())
            self.mainLoop()
            # self.program.kill()
            return 0
        else:
            RuntimeError(self.program, 'Variable is not a window or an element')

    def k_init(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['keyword'] in ['column', 'frame', 'layout', 'tab']:
                command['target'] = symbolRecord['name']
                self.add(command)
                return True
        return False

    def r_init(self, command):
        target = self.getVariable(command['target'])
        target['layout'] = []
        return self.nextPC()

    def k_layout(self, command):
        return self.compileVariable(command)

    def r_layout(self, command):
        return self.nextPC()

    def k_on(self, command):
        token = self.nextToken()
        if token == 'event':
            command['key'] = self.nextValue()
            if self.nextIs('in'):
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    if record['keyword'] == 'window':
                        command['window'] = record['name']
                        command['goto'] = self.getPC() + 2
                        self.add(command)
                        self.nextToken()
                        pcNext = self.getPC()
                        cmd = {}
                        cmd['domain'] = 'core'
                        cmd['lino'] = command['lino']
                        cmd['keyword'] = 'gotoPC'
                        cmd['goto'] = 0
                        cmd['debug'] = False
                        self.addCommand(cmd)
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
        key = self.getRuntimeValue(command['key'])
        window = self.getVariable(command['window'])
        window['eventHandlers'][key] = lambda: self.run(command['goto'])
        return self.nextPC()

    def k_popup(self, command):
        command['message'] = self.nextValue()
        self.addCommand(command)
        return True

    def r_popup(self, command):
        psg.popup(self.getRuntimeValue(command['message']))
        return self.nextPC()

    def k_set(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            keyword = record['keyword']
            if keyword == 'layout':
                command['target'] = record['name']
                if self.peek() == 'to':
                    self.nextToken()
                    command['type'] = self.nextToken()
                    command['args'] = self.utils.getArgs(self)
                else: command['args'] = None
                self.addCommand(command)
                return True
            elif keyword == 'event':
                pass
            return False

    def r_set(self, command):
        target = self.getVariable(command['target'])
        target['layout'] = []
        type = command['type']
        args = command['args']
        if args != None:
            if args[0] == '{':
                layout = json.loads(self.getRuntimeValue(json.loads(args)))
                default = self.utils.getDefaultArgs(type)
                for n in range(0, len(layout)):
                    args = self.utils.decode(default, layout[n])
                target['layout'].append(self.utils.createElement(type, args))
            else:
                v = self.getVariable(args)
                target['layout'].append(v['layout'])
        return self.nextPC()

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
            value['name'] = token
            symbolRecord = self.getSymbolRecord()
            keyword = symbolRecord['keyword']
            if keyword == 'event':
                value['type'] = 'symbol'
                return value
            return None

        if self.getToken() == 'the':
            self.nextToken()

        token = self.getToken()
        value['type'] = token

        if token == 'event':
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
        if symbolRecord['keyword'] == 'event':
            return self.getSymbolValue(symbolRecord)
        else:
            return None

    def v_event(self, v):
        v['type'] = 'text'
        v['content'] = self.eventValues
        return v

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers

    #############################################################################
    # The main loop
    def mainLoop(self):
        windowRecord = self.program.windowRecord
        window = windowRecord['window']
        eventHandlers = windowRecord['eventHandlers']
        while True:
            event, values = window.Read(timeout=100)
            if event == psg.WINDOW_CLOSED or event == "EXIT":
                break
            if event == '__TIMEOUT__': self.program.flushCB()
            else:
                if event in eventHandlers:
                    self.eventValues = values
                    eventHandlers[event]()
