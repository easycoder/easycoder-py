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
        elements = []
        while True:
            if self.nextIsSymbol():
                symbolRecord = self.getSymbolRecord()
                name = symbolRecord['name']
                if 'iselement' in symbolRecord:
                    elements.append(name)
                    if self.peek() != 'and': break
                else: FatalError(self.program.compiler, f'"{name}" is not a graphic element')
            else: FatalError(self.program.compiler, f'Element expected; got "{self.getToken()}"')
            self.nextToken()
        command['elements'] = json.dumps(elements)
        if self.nextIs('to'):
            if self.nextIsSymbol():
                symbolRecord = self.getSymbolRecord()
                if symbolRecord['keyword'] == 'layout':
                    command['target'] = symbolRecord['name']
                    self.addCommand(command)
                    return True
        return False

    def r_add(self, command):
        target = self.getVariable(command['target'])
        elements = json.loads(command['elements'])
        if not 'layout' in target:
            target['layout'] = []
        for element in elements:
            v = self.getVariable(element)
            target['layout'].append(v['layout'])
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
            elif type[0:2] == 'g_':
                command['args'] = self.compileConstant(self.utils.getArgs(self))
                self.addCommand(command)
                return True
        return False

    def r_create(self, command):
        type = command['type']
        record = self.getVariable(command['name'])
        if type == 'window':
            layout = self.getVariable(command['layout'])
            title = self.getRuntimeValue(command['title'])
            self.program.window = psg.Window(title, layout['layout'], finalize=True)
            self.program.run(self.nextPC())
            self.mainLoop()
            self.program.kill()
            return 0
        elif 'iselement' in record:
            layout = json.loads(self.getRuntimeValue(command['args']))
            args = self.utils.getDefaultArgs(type)
            content = json.loads(layout['content'])
            for n in range(0, len(content)):
                args = self.utils.decode(args, content[n])
            element = self.utils.createElement(type, args)
            record['layout'] = element
            return self.nextPC()
        else:
            RuntimeError(self.program, 'Variable is not a window or an element')

    def k_g_button(self, command):
        command['iselement'] = True
        return self.compileVariable(command)

    def r_g_button(self, command):
        return self.nextPC()

    def k_g_input(self, command):
        command['iselement'] = True
        return self.compileVariable(command)

    def r_g_input(self, command):
        return self.nextPC()

    def k_g_text(self, command):
        command['iselement'] = True
        return self.compileVariable(command)

    def r_g_text(self, command):
        return self.nextPC()

    def k_init(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['keyword'] == 'layout':
                command['target'] = record['name']
                if self.peek() == 'with':
                    self.nextToken()
                    if self.nextIsSymbol():
                        record = self.getSymbolRecord()
                        name = record['name']
                        if record['iselement']:
                            command['args'] = name
                        else: FatalError(self.program.compiler, f'\'{name}\' is not a graphic element')
                    else:
                        command['type'] = self.getToken()
                        command['args'] = self.utils.getArgs(self)
                else: command['args'] = None
                self.addCommand(command)
                return True
            return False

    def r_init(self, command):
        record = self.getVariable(command['target'])
        record['layout'] = []
        type = command['type']
        args = command['args']
        if args != None:
            if args[0] == '{':
                layout = json.loads(self.getRuntimeValue(json.loads(args)))
                args = self.utils.getDefaultArgs(type)
                for n in range(0, len(layout)):
                    args = self.utils.decode(args, layout[n])
                record['layout'].append(self.utils.createElement(type, args))
            else:
                v = self.getVariable(args)
                record['layout'].append(v['layout'])
        return self.nextPC()

    def k_layout(self, command):
        command['iselement'] = True
        return self.compileVariable(command)

    def r_layout(self, command):
        return self.nextPC()

    def k_on(self, command):
        token = self.nextToken()
        command['type'] = token
        if token == 'click':
            command['event'] = token
            if self.peek() == 'in':
                self.nextToken()
            if self.nextIs('screen'):
                command['target'] = None
            elif self.isSymbol():
                target = self.getSymbolRecord()
                command['target'] = target['name']
            else:
                FatalError(self.program.compiler, f'{self.getToken()} is not a screen element')
                return False
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
        elif token == 'tick':
            command['event'] = token
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
        pc = command['goto']
        if command['type'] == 'click':
            event = command['event']
            if event == 'click':
                target = command['target']
                if target == None:
                    value = 'screen'
                else:
                    widget = self.getVariable(target)
                value = widget['value'][widget['index']]
                self.renderer.setOnClick(value['content'], lambda: self.run(pc))
        return self.nextPC()

    def k_popup(self, command):
        command['message'] = self.nextValue()
        self.addCommand(command)
        return True

    def r_popup(self, command):
        psg.popup(self.getRuntimeValue(command['message']))
        return self.nextPC()

    def k_set(self, command):
        return True

    def r_set(self, command):
        return self.nextPC()

    def k_window(self, command):
        return self.compileVariable(command)

    def r_window(self, command):
        return self.nextPC()

    #############################################################################
    # Compile a value in this domain
    def compileValue(self):
        value = {}
        value['domain'] = 'graphics'
        token = self.getToken()
        if self.isSymbol():
            return None

        if self.tokenIs('the'):
            self.nextToken()
        token = self.getToken()

        value['type'] = token

        if token == 'test':
            name = self.nextToken()
            value = {}
            value['type'] = 'text'
            value['content'] = 'test'
            return value

        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        return value

    #############################################################################
    # Value handlers

    def v_test(self, v):
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
        while True:
            event, values = self.program.window.Read(timeout=100)
            if event == psg.WINDOW_CLOSED or event == "EXIT":
                break
            if event == '__TIMEOUT__': self.program.flushCB()
            else:
                print(event, values)
