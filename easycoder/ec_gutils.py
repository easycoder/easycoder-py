import PySimpleGUI as psg
import json

class GUtils:

    # Parse a set of compile-time arguments
    def getArgs(self, handler):
        args = []
        while True:
            key = handler.nextToken()
            value = json.dumps(handler.nextValue())
            args.append(f'{key}={value}')
            if handler.peek() == 'and':
                handler.nextToken()
            else: break
        v = {}
        v['type'] = 'text'
        v['content'] = json.dumps(args)
        return json.dumps(v)

    # Get the default args for a graphic element
    def getDefaultArgs(self, type):
        args = {}
        if type == 'Button':
            args['button_text'] = '(empty)'
            args['size'] = (None, None)
        if type == 'Checkbox':
            args['text'] = ''
            args['key'] = None
            args['size'] = (None, None)
            args['expand_x'] = False
        elif type == 'Column':
            args['expand_x'] = False
            args['pad'] = (0, 0)
        elif type == 'Input':
            args['key'] = None
            args['size'] = (None, None)
        elif type == 'Multiline':
            args['default_text'] = ''
            args['key'] = None
            args['size'] = (None, None)
        elif type == 'Text':
            args['text'] = '(empty)'
            args['size'] = (None, None)
            args['expand_x'] = False
        return args

    # Decode an argument at runtime
    def decode(self, args, text):
        p = text.find('=')
        if p > 0:
            key = text[0:p]
            value = json.loads(text[p+1:])['content']
            args[key] = value
            return args
        return None

    # Create an element
    def createElement(self, type, param, args):
        if type == 'Button':
            size = self.getSize(args)
            return psg.Button(button_text=args['button_text'], size=size)
        if type == 'Checkbox':
            size = self.getSize(args)
            return psg.Checkbox(args['text'], key=args['key'], expand_x=args['expand_x'], size=size)
        if type == 'Column':
            return psg.Column(param, expand_x=args['expand_x'], pad=args['pad'])
        elif type == 'Input':
            size = self.getSize(args)
            return psg.Input(key=args['key'], size=size)
        elif type == 'Multiline':
            size = self.getSize(args)
            return psg.Multiline(default_text=args['default_text'], key=args['key'], size=size)
        elif type == 'Text':
            size = self.getSize(args)
            return psg.Text(text=args['text'], size=size, expand_x=args['expand_x'])
        else: return None

    def getSize(self, args):
        size = args['size']
        if size == (None, None):
            return size
        size = size.split()
        return (size[0], size[1])
