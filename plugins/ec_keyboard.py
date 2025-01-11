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
    # render keyboard {face) [and {face)...] at {left} {bottom} width {width}
    def k_render(self, command):
        if self.nextIs('keyboard'):
            faces = []
            while True:
                faces.append(self.nextValue())
                token = self.peek()
                if token != 'and': break
                self.nextToken()
            command['faces'] = json.dumps(faces)
            x = getConstant('10w')
            y = getConstant('10h')
            w = getConstant('50w')
            token = self.peek()
            while token in ['at', 'width']:
                    self.nextToken()
                    if token == 'at':
                        x = self.nextValue()
                        y = self.nextValue()
                    elif token == 'width':
                        w = self.nextValue()
                    token = self.peek()
            command['x'] = x
            command['y'] = y
            command['w'] = w
            self.add(command)
            return True
        return False

    def r_render(self, command):
        self.keyboard = Object()
        faces = json.loads(command['faces'])
        self.keyboard.faces = []
        for f in range(0, len(faces)):
            with open(f'{self.getRuntimeValue(faces[f])}') as f: spec = f.read()
            self.keyboard.faces.append(json.loads(spec))
        layout = self.keyboard.faces[0]
        x = getActual(self.getRuntimeValue(command['x']))
        y = getActual(self.getRuntimeValue(command['y']))
        w = getActual(self.getRuntimeValue(command['w']))
        # Scan the keyboard layout to find the longest row
        max = 0
        rows = layout['rows']
        nrows = len(rows)
        for r in range(0, nrows):
            row = rows[r]
            # Count the number of buttons
            count = 0.0
            for n in range(0, len(row)):
                key = row[n]
                if 'span' in key: count += float(key['span'])
                else: count += 1.0
            if count > max: max = count
        # Divide the keyboard width by the number of buttons to get the button size
        # The basic key is a square (1:1)
        bs = w / max
        # Compute the keyboard height
        h = bs * nrows
        # Build the spec
        spec = {}
        spec['type'] = 'image'
        spec['id'] = 'face'
        spec['source'] = layout['face']
        spec['left'] = x
        spec['bottom'] = y
        spec['width'] = w
        spec['height'] = h
        buttons = []
        list = []
        spans = [0] * nrows
        by = h
        for r in range(0, nrows):
            by -= bs
            row = rows[r]
            bx = 0
            for b in range(0, len(row)):
                button = row[b]
                id = button['id']
                if 'span' in button: span = float(button['span'])
                else: span = 1.0
                width = bs * span
                button['type'] = 'hotspot'
                button['left'] = bx
                button['bottom'] = by
                button['width'] = width
                button['height'] = bs
                button['parent'] = spec
                buttons.append(button)
                list.append(id)
                bx += width
            spans[r] = round(bx)
        # Check the rows are all the same length
        for r in range(1, nrows):
            if spans[r] != spans[0]:
                RuntimeError(self.program, f'Row {r} has a different span to previous row(s)')
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
