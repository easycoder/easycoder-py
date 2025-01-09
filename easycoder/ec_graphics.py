from .ec_classes import FatalError, RuntimeError, Object
from .ec_handler import Handler
from .ec_screenspec import ScreenSpec
from .ec_renderer import Renderer, getUI
from .ec_program import flush

class Graphics(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)
        self.windowCreated = False

    def getName(self):
        return 'graphics'

    #############################################################################
    # Keyword handlers

    def k_attach(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            command['name'] = record['name']
            if self.nextIs('to'):
                value = self.nextValue()
                record['id'] = value
                command['id'] = value
            self.add(command)
        return True

    def r_attach(self, command):
        targetRecord = self.getVariable(command['name'])
        keyword = targetRecord['keyword']
        id = self.getRuntimeValue(command['id'])
        uiElement = getUI().getElement(id)
        if uiElement == None:
            FatalError(self.program.compiler, f'There is no screen element with id \'{id}\'')
            return -1
        if uiElement.getType() != keyword:
            etype = uiElement['type']
            FatalError(self.program.compiler, f'Mismatched element type: "{etype}" and "{keyword}"')
        self.putSymbolValue(targetRecord, {'type': 'text', 'content': id})
        return self.nextPC()

    # close window
    def k_close(self, command):
        if (self.nextIs('window')):
            self.add(command)
            return True
        return False

    def r_close(self, command):
        self.renderer.stop()
        return 0

    # create window/ellipse/rectangle//text/image
    def k_create(self, command):
        token = self.nextToken()
        if (token == 'window'):
            t = {}
            t['type'] = 'text'
            t['content'] = 'EasyCoder'
            width = self.compileConstant(640)
            height = self.compileConstant(480)
            left = self.compileConstant(100)
            top = self.compileConstant(100)
            r = self.compileConstant(255)
            g = self.compileConstant(255)
            b = self.compileConstant(255)
            fullscreen = False
            borderless = False
            while True:
                token = self.peek()
                if token == 'title':
                    self.nextToken()
                    t = self.nextValue()
                elif token == 'fullscreen':
                    fullscreen = True
                    self.nextToken()
                elif token == 'borderless':
                    borderless = True
                    self.nextToken()
                elif token == 'at':
                    self.nextToken()
                    left = self.nextValue()
                    top = self.nextValue()
                elif token == 'size':
                    self.nextToken()
                    width = self.nextValue()
                    height = self.nextValue()
                elif token == 'fill':
                    self.nextToken()
                    if self.nextIs('color'):
                        r = self.nextValue()
                        g = self.nextValue()
                        b = self.nextValue()
                else:
                    break
            command['type'] = 'window'
            command['title'] = t
            command['pos'] = (left, top)
            command['size'] = (width, height)
            command['fill'] = (r, g, b)
            command['fullscreen'] = fullscreen
            command['borderless'] = borderless
            self.add(command)
            return True

        elif self.isSymbol():
            record = self.getSymbolRecord()
            command['target'] = record['name']
            type = record['keyword']
            command['type'] = type
            if type in ['ellipse', 'rectangle', 'image']:
                self.getElementData(type, command)
                for item in ['width', 'height', 'left', 'bottom', 'r', 'g', 'b']:
                    if command[item] == None:
                        FatalError(self.program.compiler, f'Missing property \'{item}\'')
                return True
            elif type == 'text':
                self.getElementData(type, command)
                for item in ['width', 'height', 'left', 'bottom', 'r', 'g', 'b', 'text']:
                    if command[item] == None:
                        FatalError(self.program.compiler, f'Missing property \'{item}\'')
            else: return False
            self.add(command)
            record['elementID'] = command['id']
        return False

    def getElementData(self, type, command):
        width = None
        height = None
        left = None
        bottom = None
        r = None
        g = None
        b = None
        text = None
        source = None
        id = self.nextValue()
        while True:
            token = self.peek()
            if token == 'size':
                self.nextToken()
                width = self.nextValue()
                height = self.nextValue()
            elif token == 'at':
                self.nextToken()
                left = self.nextValue()
                bottom = self.nextValue()
            elif token == 'fill':
                self.nextToken()
                r = self.nextValue()
                g = self.nextValue()
                b = self.nextValue()
            elif token == 'text':
                self.nextToken()
                text = self.nextValue()
            elif token == 'source':
                self.nextToken()
                source = self.nextValue()
            else:
                break
        command['id'] = id
        command['type'] = type
        if width != None:
            command['width'] = width
        if height != None:
            command['height'] = height
        if left!= None:
            command['left'] = left
        if bottom != None:
            command['bottom'] = bottom
        if r != None:
            command['r'] = r
        if g != None:
            command['g'] = g
        if b != None:
            command['b'] = b
        if text != None:
            command['text'] = text
        if source != None:
            command['source'] = source

    def r_create(self, command):
        try:
            type = command['type']
            if type == 'window':
                if self.windowCreated == True:
                    RuntimeError(self.program, 'A window has already been created')
                self.windowSpec = Object()
                self.windowSpec.title = command['title']['content']
                self.windowSpec.fullscreen = command['fullscreen']
                self.windowSpec.borderless = command['borderless']
                self.windowSpec.flush = flush
                self.windowSpec.kill = self.program.kill
                self.windowSpec.pos = (self.getRuntimeValue(command['pos'][0]), self.getRuntimeValue(command['pos'][1]))
                self.windowSpec.size = (self.getRuntimeValue(command['size'][0]), self.getRuntimeValue(command['size'][1]))
                self.windowSpec.fill = (self.getRuntimeValue(command['fill'][0])/255, self.getRuntimeValue(command['fill'][1])/255, self.getRuntimeValue(command['fill'][2])/255)
                self.windowCreated = True
                self.renderer = Renderer()
                self.renderer.init(self.windowSpec)
                self.program.setExternalControl()
                self.program.run(self.nextPC())
                self.renderer.run()
            else:
                element = getUI().createWidget(self.getWidgetSpec(command))
                print(element)
        except Exception as e:
            RuntimeError(self.program, e)
        return self.nextPC()

    def getWidgetSpec(self, command):
        spec = Object()
        spec.id = self.getRuntimeValue(command['id'])
        spec.type = command['type']
        spec.w = self.getRuntimeValue(command['width'])
        spec.h = self.getRuntimeValue(command['height'])
        spec.x = self.getRuntimeValue(command['left'])
        spec.y = self.getRuntimeValue(command['bottom'])
        spec.r = self.getRuntimeValue(command['r'])/255
        spec.g = self.getRuntimeValue(command['g'])/255
        spec.b = self.getRuntimeValue(command['b'])/255
        return spec

    def k_ellipse(self, command):
        return self.compileVariable(command)

    def r_ellipse(self, command):
        return self.nextPC()

    # Hide an element
    def k_hide(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            type = record['keyword']
            if self.isGraphicType(type):
                command['target'] = record['id']
                self.add(command)
                return True
        return False

    def r_hide(self, command):
        getUI().setVisible(self.getRuntimeValue(command['target']), False)
        return self.nextPC()

    def k_image(self, command):
        return self.compileVariable(command)

    def r_image(self, command):
        return self.nextPC()

    # move an element
    def k_move(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            type = record['keyword']
            if self.isGraphicType(type):
                command['target'] = record['id']
                token = self.nextToken()
                if token == 'to':
                    command['x'] = self.nextValue()
                    command['y'] = self.nextValue()
                    self.add(command)
                    return True
                elif token == 'by':
                    command['keyword'] = 'moveBy'
                    command['dx'] = self.nextValue()
                    command['dy'] = self.nextValue()
                    self.add(command)
                    return True
        return False

    def r_move(self, command):
        pos = (self.getRuntimeValue(command['x']), self.getRuntimeValue(command['y']))
        getUI().moveElementTo(self.getRuntimeValue(command['target']), pos)
        return self.nextPC()

    def r_moveBy(self, command):
        dist = (self.getRuntimeValue(command['dx']), self.getRuntimeValue(command['dy']))
        getUI().moveElementBy(self.getRuntimeValue(command['target']), dist)
        return self.nextPC()

    # on click/tap {element} {action}
    def k_on(self, command):
        token = self.nextToken()
        if token in ['click', 'tap']:
            command['type'] = 'tap'
            if self.nextIsSymbol():
                target = self.getSymbolRecord()
            else:
                Warning(f'{self.getToken()} is not a screen element')
                return False
            command['target'] = target['name']
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

     # Set a handler on every element
    def r_on(self, command):
        pc = command['goto']
        if command['type'] == 'tap':
            record = self.getVariable(command['target'])
            def oncb(data):
                record['index'] = data.index
                self.run(data.pc)
            keyword = record['keyword']
            if self.isGraphicType(keyword):
                for index in range(0, record['elements']):
                    id = record['value'][index]['content']
                    data = Object()
                    data.pc = pc
                    data.index = index
                    getUI().setOnClick(id, data, oncb)
            else:
                name = record['name']
                RuntimeError(self.program, f'{name} is not a clickable object')
        return self.nextPC()

    def k_rectangle(self, command):
        return self.compileVariable(command)

    def r_rectangle(self, command):
        return self.nextPC()

    # render spec {spec}
    def k_render(self, command):
        if self.nextToken() in ['specification', 'spec']:
            command['spec'] = self.nextValue()
            command['parent'] = None
            if self.peek() == 'in':
                self.nextToken()
                if self.nextIsSymbol():
                    command['parent'] = self.getSymbolRecord()['name']
            self.add(command)
            return True
        return False

    def r_render(self, command):
        spec = self.getRuntimeValue(command['spec'])
        parent = command['parent']
        if parent !=None:
            parent = self.getVariable(command['parent'])
        try:
            ScreenSpec().render(spec, parent)
        except Exception as e:
            RuntimeError(self.program, e)
        return self.nextPC()

    # Set something
    def k_set(self, command):
        if self.nextIs('attribute'):
            command['attribute'] = self.nextValue()
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    if self.isGraphicType(record['keyword']):
                        command['target'] = record['name']
                        if self.nextIs('to'):
                            command['value'] = self.nextValue()
                            self.addCommand(command)
                            return True
                    else:
                        rtype = record['type']
                        FatalError(self.program.compiler, f'Invalid type: {rtype}')
                else:
                    token = self.getToken()
                    FatalError(self.program.compiler, f'{token} is not a variable')
        return False

    def r_set(self, command):
        attribute = self.getRuntimeValue(command['attribute'])
        target = self.getVariable(command['target'])
        id = target['value'][target['index']]['content']
        value = self.getRuntimeValue(command['value'])
        getUI().setAttribute(id, attribute, value)
        return self.nextPC()

    # Show an element (restore it to its current position)
    def k_show(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            type = record['keyword']
            if self.isGraphicType(type):
                command['target'] = record['id']
                self.add(command)
                return True
        return False

    def r_show(self, command):
        getUI().setVisible(self.getRuntimeValue(command['target']), True)
        return self.nextPC()

    def k_text(self, command):
        return self.compileVariable(command)

    def r_text(self, command):
        return self.nextPC()

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        return value

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
            if keyword == 'graphic':
                value['type'] = 'symbol'
                return value
            return None

        if self.tokenIs('the'):
            self.nextToken()
        kwd = self.getToken()
        value['type'] = kwd
        if kwd == 'attribute':
            attribute = self.nextValue()
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    if self.isGraphicType(record['keyword']):
                        value['attribute'] = attribute
                        value['target'] = record['name']
                        return value
        elif kwd == 'window':
            attribute = self.nextToken()
            if attribute in ['left', 'top', 'width', 'height']:
                value['attribute'] = attribute
                return value
        return None

    #############################################################################
    # Test if a graphic type

    def isGraphicType(self, type):
        return type in ['ellipse', 'rectangle', 'text', 'image']

    #############################################################################
    # Value handlers

    def v_attribute(self, v):
        try:
            attribute = self.getRuntimeValue(v['attribute'])
            target = self.getVariable(v['target'])
            val = self.getSymbolValue(target)
            v = getUI().getAttribute(val['content'], attribute)
            value = {}
            value['type'] = 'int'
            value['content'] = int(round(v))
            return value
        except Exception as e:
            RuntimeError(self.program, e)

    # This is used by the expression evaluator to get the value of a symbol
    def v_symbol(self, symbolRecord):
        result = {}
        if symbolRecord['keyword'] == 'graphic':
            symbolValue = self.getSymbolValue(symbolRecord)
            return symbolValue
        else:
            return None

    def v_window(self, v):
        try:
            attribute = v['attribute']
            value = {}
            value['type'] = 'int'
            value['content'] = int(round(getUI().getWindowAttribute(attribute)))
            return value
        except Exception as e:
            RuntimeError(self.program, e)

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers
