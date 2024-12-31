# screenspec.py

from json import loads
from .ec_renderer import Object

class ScreenSpec():

    # Get an attribute of an element
    def getAttribute(self, id, attribute):
        element = self.ui.getElement(id)
        return element[attribute]

    # Render a single widget
    def createWidget(self, widget, parent):
        spec = Object()
        type = widget['type']
        spec.type = type
        spec.id = widget['id']
        spec.pos = (widget['left'], widget['bottom'])
        spec.size = (widget['width'], widget['height'])
        if widget.get('fill') != None:
            spec.fill = widget['fill']
        if widget.get('text') != None:
            spec.text = widget['text']
        if widget.get('fontSize') != None:
            spec.fontSize = widget['fontSize']
        if widget.get('source') != None:
            spec.source = widget['source']
        if widget.get('color') != None:
            spec.color = widget['color']
        spec.parent = parent
        spec.children = []
        self.ui.createElement(spec)

        if '#' in widget:
            children = widget['#']
            if isinstance(children, list):
                for item in children:
                    if item in widget:
                        child = widget[item]
                        childSpec = self.createWidget(child, spec)
                        spec.children.append(childSpec.id)
                    else:
                        raise Exception(f'Child \'{item}\' is missing')
            else:
                child = widget[children]
                childSpec = self.createWidget(child, spec)
                spec.children.append(childSpec.id)

        return spec

    # Render a complete specification
    def renderSpec(self, spec, parent):
        widgets = spec['#']
        # If a list, iterate it
        if isinstance(widgets, list):
            for widget in widgets:
                self.createWidget(spec[widget], parent)
        # Otherwise, process the single widget
        else:
            self.createWidget(spec[widgets], parent)

    # Render a graphic specification
    def render(self, spec, ui):
        self.ui = ui

        # If it'a string, process it
        if isinstance(spec, str):
            self.renderSpec(loads(spec), None)

        # If it's a 'dict', extract the spec and the args
        elif isinstance(spec, dict):
            spec = loads(spec['spec'])
            self.renderSpec(spec, None)

        else:
            raise Exception('Spec is an unknown type')
