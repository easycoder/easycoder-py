import PySimpleGUI as psg
import json

class GUtils:

    # Parse a set of compile-time arguments
    def getArgs(self, handler):
        args = []
        while True:
            key = handler.nextToken()
            value = handler.nextValue()
            value = json.dumps(value)
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
        if type == 'Button': self.getDefaultButton(args)
        elif type == 'Checkbox': self.getDefaultCheckbox(args)
        elif type == 'Column': self.getDefaultColumn(args)
        elif type == 'Frame': self.getDefaultFrame(args)
        elif type == 'Input': self.getDefaultInput(args)
        elif type == 'Listbox': self.getDefaultListbox(args)
        elif type == 'Multiline': self.getDefaultMultiline(args)
        elif type == 'Text': self.getDefaultText(args)
        return args

    # Decode an argument at runtime
    def decode(self, handler, args, text):
        p = text.find('=')
        if p > 0:
            key = text[0:p]
            value = text[p+1:]
            value = json.loads(value)
            if value['type'] == 'symbol':
                record = handler.program.getSymbolRecord(value['name'])
                value = handler.getSymbolValue(record)
            if value != None: value = value['content']
            else: raise Exception('Variable has no value')
            args[key] = value

    # Reduce the event properties to a list of strings
    def getEventProperties(self, window, values):
        keys = values.keys()
        for key in keys:
            v = values[key]
            widget = window.key_dict[key]
            if type(widget) is psg.Listbox:
                # Only pick one from those selected
                v = v[0]
            values[key] = v

    # Create a widget
    def createWidget(self, type, layout, args):
        if type == 'Button': return self.createButton(layout, args)
        elif type == 'Checkbox': return self.createCheckbox(layout, args)
        elif type == 'Column': return self.createColumn(layout, args)
        elif type == 'Frame': return self.createFrame(layout, args)
        elif type == 'Input': return self.createInput(layout, args)
        elif type == 'Listbox': return self.createListbox(layout, args)
        elif type == 'Multiline': return self.createMultiline(layout, args)
        elif type == 'Text': return self.createText(layout, args)
        else: return None

    # Get the current value of a widget
    def getWidgetValue(self, window, key):
        key_dict = window['window'].key_dict
        widget = key_dict[key]
        if type(widget) is psg.Button: return widget.get()
        elif type(widget) is psg.Checkbox: return widget.get()
        elif type(widget) is psg.Column: return widget.get()
        elif type(widget) is psg.Frame: return widget.get()
        elif type(widget) is psg.Input: return widget.get()
        elif type(widget) is psg.Listbox:
            items = widget.get()
            if len(items) > 0:
                return items[0]
            return ''
        elif type(widget) is psg.Multiline: return widget.get()
        elif type(widget) is psg.Text: return widget.get()
        return None

    # Update a property
    def updateProperty(self, element, property, value):
        if property == 'disabled':
            element.update(disabled=value)
        elif property == 'text':
            element.update(text=value)
        elif property == 'value':
            element.update(value=value)
        elif property == 'values':
            element.update(values=value)

    def getSize(self, args):
        size = args['size']
        if size == (None, None):
            return size
        size = size.split()
        return (size[0], size[1])

    def getDefaultButton(self, args):
        args['button_text'] = ''
        args['disabled'] = False
        args['size'] = (None, None)

    def createButton(self, layout, args):
        return psg.Button(button_text=args['button_text'], disabled=args['disabled'], size=self.getSize(args))

    def getDefaultCheckbox(self, args):
        args['text'] = ''
        args['key'] = None
        args['size'] = (None, None)
        args['expand_x'] = False

    def createCheckbox(self, layout, args):
        return psg.Checkbox(args['text'], key=args['key'], expand_x=args['expand_x'], size=self.getSize(args))

    def getDefaultColumn(self, args):
        args['expand_x'] = False
        args['pad'] = (0, 0)

    def createColumn(self, layout, args):
        return psg.Column(layout, expand_x=args['expand_x'], pad=args['pad'])

    def getDefaultFrame(self, args):
        args['title'] = ''
        args['border_width'] = 1
        args['expand_x'] = False
        args['pad'] = (0, 0)

    def createFrame(self, layout, args):
        return psg.Frame(args['title'], layout, border_width=args['border_width'], expand_x=args['expand_x'], pad=args['pad'])

    def getDefaultInput(self, args):
        args['default_text'] = ''
        args['key'] = None
        args['size'] = (None, None)

    def createInput(self, layout, args):
        return psg.Input(default_text=args['default_text'], key=args['key'], size=self.getSize(args))

    def getDefaultListbox(self, args):
        args['list'] = []
        args['key'] = [None]
        args['size'] = '10 2'
        args['pad'] = 1
        args['select_mode'] = None

    def createListbox(self, layout, args):
        return psg.Listbox([], key=args['key'], pad=args['pad'], size=self.getSize(args))

    def getDefaultMultiline(self, args):
        args['default_text'] = ''
        args['key'] = None
        args['size'] = (None, None)

    def createMultiline(self, layout, args):
        return psg.Multiline(default_text=args['default_text'], key=args['key'], size=self.getSize(args))

    def getDefaultText(self, args):
        args['text'] = ''
        args['key'] = None
        args['size'] = (None, None)
        args['expand_x'] = False

    def createText(self, layouts, args):
        return psg.Text(text=args['text'], expand_x=args['expand_x'], key=args['key'], size=self.getSize(args))

