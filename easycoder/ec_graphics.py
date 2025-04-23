from .ec_classes import FatalError, RuntimeError
from .ec_handler import Handler
from .ec_gutils import GUtils
import PySimpleGUI as psg
import json
from copy import deepcopy

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
                    command['args'] = name
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
        def create(type, layout, args2, target):
            args = self.utils.getDefaultArgs(type)
            for n in range(0, len(args2)):
                try:
                    self.utils.decode(self, args, args2[n])
                except Exception as e:
                    RuntimeError(self.program, e)
            item = self.utils.createWidget(type, layout, args)
            target['layout'].append(item)

        target = self.getVariable(command['target'])
        type = command['type']
        args = command['args']
        if not 'layout' in target:
            target['layout'] = []
        if len(args) > 0 and args[0] == '{':
            args = json.loads(self.getRuntimeValue(json.loads(args)))
            if type in ['Column', 'Frame', 'Tab']:
                record = self.getVariable(command['name'])
                layout = record['layout']
                create(type, layout, args, target)
            else:
                create(type, None, args, target)
        else:
            if type in ['Column', 'Frame', 'Tab']:
                record = self.getVariable(command['name'])
                layout = record['layout']
                create(type, layout, args, target)
            else:
               v = self.getVariable(args)
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

    def k_column(self, command):
        return self.compileVariable(command)

    def r_column(self, command):
        return self.nextPC()

    # create layout {name} from {spec}
    # create {window} layout {layout}
    def k_create(self, command):
        token = self.nextToken()
        if token == 'layout':
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'layout':
                    command['layout'] = record['name']
                    if self.nextIs('from'):
                        command['spec'] = self.nextValue()
                        self.addCommand(command)
                        return True
        elif self.isSymbol():
            symbolRecord = self.getSymbolRecord()
            command['name'] = symbolRecord['name']
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
        def processItem(name, item):
            print(name, item['type'])
            children = item['#']
            if isinstance(children, list):
                print("List")
                for child in children:
                    print(child)
            else:
                print("Single:", children)

        if 'spec' in command:
            spec = self.getRuntimeValue(command['spec'])
            layout = self.getVariable(command['layout'])
            for key in spec.keys():
                item = spec[key]
                print(key, item['type'])
                if item['type'] == 'column':
                    for child in item['#']: processItem(child, item[child])
            return self.nextPC()
        else:
            record = self.getVariable(command['name'])
            title = self.getRuntimeValue(command['title'])
            layout = self.getVariable(command['layout'])['layout']
            window = psg.Window(title, layout, finalize=True)
            record['window'] = window
            record['eventHandlers'] = {}
            self.program.run(self.nextPC())
            self.mainLoop(record)
            return 0

    def k_frame(self, command):
        return self.compileVariable(command)

    def r_frame(self, command):
        return self.nextPC()

    # get {variable} from popup {type} {message} {title}
    def k_get(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['hasValue']:
                command['target'] = self.getToken()
            else:
                FatalError(self.compiler, f'Variable "{symbolRecord["name"]}" does not hold a value')
            if symbolRecord['hasValue']:
                if self.nextIs('from'):
                    if self.nextIs('popup'):
                        command['ptype'] = self.nextToken()
                        command['message'] = self.nextValue()
                        command['title'] = self.nextValue()
                        self.addCommand(command)
                        return True
        return False

    def r_get(self, command):
        target = self.getVariable(command['target'])
        ptype = command['ptype']
        if ptype == 'text':
            text = psg.popup_get_text(self.getRuntimeValue(command['message']), title=self.getRuntimeValue(command['title']))
        elif ptype == 'ok-cancel':
            text = psg.popup_ok_cancel(self.getRuntimeValue(command['message']), title=self.getRuntimeValue(command['title']))
        elif ptype == 'yes-no':
            text = psg.popup_yes_no(self.getRuntimeValue(command['message']), title=self.getRuntimeValue(command['title']))
        else:
            return None
        v = {}
        v['type'] = 'text'
        v['content'] = text
        self.program.putSymbolValue(target, v)
        return self.nextPC()

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

    # popup {message} {title}
    def k_popup(self, command):
        command['message'] = self.nextValue()
        command['title'] = self.nextValue()
        self.addCommand(command)
        return True

    def r_popup(self, command):
        psg.popup(self.getRuntimeValue(command['message']), title=self.getRuntimeValue(command['title']))
        return self.nextPC()

    def k_refresh(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['keyword'] == 'window':
                command['target'] = symbolRecord['name']
                self.add(command)
                return True
        return False

    def r_refresh(self, command):
        target = self.getVariable(command['target'])
        target['window'].refresh()
        return self.nextPC()

    # set property {property} of {key} in {window} to {value}
    def k_set(self, command):
        if self.nextIs('property'):
            command['property'] = self.nextValue()
            if self.nextIs('of'):
                command['key'] = self.nextValue()
                if self.nextIs('in'):
                    if self.nextIsSymbol():
                        record = self.getSymbolRecord()
                        if record['keyword'] == 'window':
                            name = record['name']
                            command['window'] = name
                            if self.nextIs('to'):
                                command['value'] = self.nextValue()
                                self.add(command)
                            return True
                        else: RuntimeError(self.program, f'\'{name}\' is not a window variable')
                    else: RuntimeError(self.program, 'No window variable given')
        return False

    def r_set(self, command):
        property = self.getRuntimeValue(command['property'])
        key = self.getRuntimeValue(command['key'])
        windowRecord = self.getVariable(command['window'])
        window = windowRecord['window']
        value = self.getRuntimeValue(command['value'])
        self.utils.updateProperty(window[key], property, value)
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

        if token == 'property':
            value['property'] = self.nextValue()
            if self.nextIs('of'):
                if self.nextToken() == 'the':
                    if self.nextIs('event'):
                        return value
            return None

        if token == 'value':
            if self.nextIs('of'):
                if self.nextIs('key'):
                    value['key'] = self.nextValue()
                    if self.nextIs('in'):
                        if self.nextIsSymbol():
                            record = self.getSymbolRecord()
                            if record['keyword'] == 'window':
                                value['window'] = record['name']
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
        window = self.eventValues['window']
        values = self.eventValues['values']
        self.utils.getEventProperties(window, values)
        v['type'] = 'text'
        v['content'] = values
        return v

    def v_property(self, v):
        property = self.getRuntimeValue(v['property'])
        window = self.eventValues['window']
        values = self.eventValues['values']
        self.utils.getEventProperties(window, values)
        v['type'] = 'text'
        v['content'] = values[property]
        return v

    def v_value(self, v):
        key = self.getRuntimeValue(v['key'])
        window = self.getVariable(v['window'])
        value = self.utils.getWidgetValue(window, key)
        if value == None: RuntimeError(self.program, 'getWidgetValue: unimplemented widget type')
        v = deepcopy(v)
        v['type'] = 'text'
        v['content'] = value
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
    def mainLoop(self, windowRecord):
        window = windowRecord['window']
        eventHandlers = windowRecord['eventHandlers']
        while True:
            event, values = window.Read(timeout=100)
            if event == psg.WIN_CLOSED or event == "EXIT":
                del window
                break
            if event == '__TIMEOUT__': self.program.flushCB()
            else:
                if event in eventHandlers:
                    self.eventValues = {}
                    self.eventValues['values'] = values
                    self.eventValues['window'] = window
                    eventHandlers[event]()
                    pass
