from easycoder import Object, FatalError, RuntimeError
from easycoder import Handler
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
            command['style'] = self.nextValue()
            self.add(command)
            return True
        return False

    def r_create(self, command):
        self.keyboard = Object()
        style = self.getRuntimeValue(command['style'])
        with open(f'plugins/keyboards/{style}.json') as f: s = f.read()
        self.keyboard.layout = json.loads(s)
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
    # render keyboard at {left} {bottom} width {width} using {button image}
    def k_render(self, command):
        if self.nextIs('keyboard'):
            token = self.peek()
            while token in ['at', 'width', 'using']:
                    self.nextToken()
                    if token == 'at':
                        command['x'] = self.nextValue()
                        command['y'] = self.nextValue()
                    elif token == 'width':
                        command['w'] = self.nextValue()
                    elif token == 'using':
                        command['u'] = self.nextValue()
                    token = self.peek()
            self.add(command)
            return True
        return False

    def r_render(self, command):
        x = getActual(self.getRuntimeValue(command['x']))
        y = getActual(self.getRuntimeValue(command['y']))
        w = getActual(self.getRuntimeValue(command['w']))
        u = self.getRuntimeValue(command['u'])
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
                button['type'] = 'ellipse'
                button['left'] = bx
                button['bottom'] = by
                button['width'] = bs
                button['height'] = bs
                button['fill'] = 'magenta'
                label = {}
                label['type'] = 'text'
                label['left'] = '25w'
                label['bottom'] = '25h'
                label['width'] = '50w'
                label['height'] = '50h'
                label['text'] = id
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
