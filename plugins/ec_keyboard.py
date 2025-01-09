from easycoder import Object, FatalError, RuntimeError
from easycoder import Handler
from easycoder import getConstant
from easycoder.ec_screenspec import ScreenSpec
from easycoder.ec_renderer import getActual, getUI
import json

class Keyboard(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)
        self.keyboard = None
        self.key = None
        self.onTap = None

    def getName(self):
        return 'keyboard'

    #############################################################################
    # Keyword handlers

    # Create a keyboard
    def k_create(self, command):
        if self.nextIs('keyboard'):
            command['template'] = self.nextValue()
            buttonStyle = 'ellipse'
            buttonTemplate = None
            buttonTextWidth = getConstant('50w')
            buttonTextHeight = getConstant('50h')
            buttonTextColor = getConstant('black')
            buttonTextX = getConstant('center')
            buttonTextY = getConstant('center')
            buttonColor = getConstant('white')
            buttonFont = None
            while True:
                token = self.peek()
                if token == 'button':
                    self.nextToken()
                    token = self.nextToken()
                    if token == 'style':
                        token = self.nextToken()
                        if token in ['ellipse', 'rectangle', 'image']:
                            buttonStyle = token
                        else: RuntimeError(self.program, f'Unknown style \'token\'')
                    elif token == 'color':
                        buttonColor = self.nextValue()
                    elif token == 'font':
                        buttonFont = self.nextValue()
                    elif token == 'template':
                        buttonTemplate = self.nextValue()
                    elif token == 'text':
                        token = self.nextToken()
                        if token =='width':
                            buttonTextWidth = self.nextValue()
                        elif token == 'height':
                            buttonTextHeight = self.nextValue()
                        elif token == 'color':
                            buttonTextColor = self.nextValue()
                        elif token == 'x':
                            buttonTextX = self.nextValue()
                        elif token == 'y':
                            buttonTextY = self.nextValue()
                        else: RuntimeError(self.program, f'Unknown property \'token\'')
                else:
                    break
            command['button-style'] = buttonStyle
            command['button-template'] = buttonTemplate
            command['button-text-width'] = buttonTextWidth
            command['button-text-height'] = buttonTextHeight
            command['button-text-color'] = buttonTextColor
            command['button-text-x'] = buttonTextX
            command['button-text-y'] = buttonTextY
            command['button-color'] = buttonColor
            command['button-font'] = buttonFont
            self.add(command)
            return True
        return False

    def r_create(self, command):
        self.keyboard = Object()
        template = self.getRuntimeValue(command['template'])
        with open(f'{template}') as f: s = f.read()
        self.keyboard.layout = json.loads(s)
        self.keyboard.buttonStyle = command['button-style']
        self.keyboard.buttonTemplate = self.getRuntimeValue(command['button-template'])
        self.keyboard.buttonTextWidth =  self.getRuntimeValue(command['button-text-width'])
        self.keyboard.buttonTextHeight =  self.getRuntimeValue(command['button-text-height'])
        self.keyboard.buttonTextColor =  self.getRuntimeValue(command['button-text-color'])
        self.keyboard.buttonTextX =  self.getRuntimeValue(command['button-text-x'])
        self.keyboard.buttonTextY =  self.getRuntimeValue(command['button-text-y'])
        self.keyboard.buttonColor =  self.getRuntimeValue(command['button-color'])
        self.keyboard.buttonFont =  self.getRuntimeValue(command['button-font'])
        return self.nextPC()

    # on click/tap keyboard
    def k_on(self, command):
        token = self.nextToken()
        if token in ['click', 'tap']:
            if self.nextIs('keyboard'):
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

     # Set a handler
    def r_on(self, command):
        self.onTap = command['goto']
        return self.nextPC()

    # Render a keyboard
    # render keyboard at {left} {bottom} width {width}
    def k_render(self, command):
        if self.nextIs('keyboard'):
            token = self.peek()
            while token in ['at', 'width']:
                    self.nextToken()
                    if token == 'at':
                        command['x'] = self.nextValue()
                        command['y'] = self.nextValue()
                    elif token == 'width':
                        command['w'] = self.nextValue()
                    token = self.peek()
            self.add(command)
            return True
        return False

    def r_render(self, command):
        x = getActual(self.getRuntimeValue(command['x']))
        y = getActual(self.getRuntimeValue(command['y']))
        w = getActual(self.getRuntimeValue(command['w']))
        # Scan the keyboard layout to find the longest row
        max = 0
        nrows = len(self.keyboard.layout)
        for r in range(0, nrows):
            row = self.keyboard.layout[r]
            # Count the number of buttons
            if len(row) > max: max = len(row)
        # Divide the keyboard width by the number of buttons to get the button size
        bs = w / max
        # Compute the keyboard height
        h = bs * nrows
        # Build the spec
        buttons = []
        list = []
        by = y
        for r in reversed(range(0, nrows)):
            row = self.keyboard.layout[r]
            bx = x
            for b in range(0, len(row)):
                button = row[b]
                id = button['id']
                button['type'] = self.keyboard.buttonStyle
                button['source'] = self.keyboard.buttonTemplate
                button['left'] = bx
                button['bottom'] = by
                button['width'] = bs
                button['height'] = bs
                button['fill'] = self.keyboard.buttonColor
                label = {}
                label['type'] = 'text'
                label['left'] = self.keyboard.buttonTextX
                label['bottom'] = self.keyboard.buttonTextY
                label['width'] = self.keyboard.buttonTextWidth
                label['height'] = self.keyboard.buttonTextHeight
                label['text'] = id
                label['color'] = self.keyboard.buttonTextColor
                button['#'] = 'Label'
                button['Label'] = label
                buttons.append(button)
                list.append(id)
                bx += bs
            by += bs
        spec = {}
        spec['#'] = list
        for n in range(0, len(list)):
            spec[list[n]] = buttons[n]

        spec['font'] = self.keyboard.buttonFont
        try:
            ScreenSpec().render(spec, None)
        except Exception as e:
            RuntimeError(self.program, e)

        # Add a callback to each button
        def oncb(id):
            self.key = id
            if self.onTap != None:
                self.program.run(self.onTap)
        for b in range(0, len(list)):
            id = list[b]
            getUI().setOnClick(id, id, oncb)

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
        if self.tokenIs('the'):
            self.nextToken()
        kwd = self.getToken()

        if kwd == 'key':
            value['type'] = kwd
            return value
        return None

    #############################################################################
    # Value handlers

    def v_key(self, v):
        value = {}
        value['type'] = 'text'
        value['content'] = self.key
        return value

    #############################################################################
    # Compile a condition in this domain
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers
