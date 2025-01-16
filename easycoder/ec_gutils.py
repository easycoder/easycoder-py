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
        if type == 'Text':
            args['text'] = '(empty)'
            args['expand_x'] = False
        elif type == 'Input':
            args['key'] = None
            args['size'] = (None, None)
        elif type == 'Button':
            args['button_text'] = '(empty)'
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
    def createElement(self, type, args):
        if type == 'Text': return psg.Text(text=args['text'], expand_x=args['expand_x'])
        elif type == 'Input':
            size = args['size'].split()
            size = (size[0], size[1])
            return psg.Input(key=args['key'], size=size)
        elif type == 'Button': return psg.Button(button_text=args['button_text'])
        else: return None
