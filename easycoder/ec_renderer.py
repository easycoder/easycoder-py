from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.uix.label import CoreLabel
from kivy.uix.image import AsyncImage
from kivy.core.window import Window
from kivy.utils import colormap
from kivy.clock import Clock
from kivy.vector import Vector
import math, os

ec_ui = None

def getUI():
    global ec_ui
    return ec_ui

# Get an actual screeen position or size value from a specified value
# such as {n}w/h, where w/h are percentages
# e.g. 25w or 50h
def getActual(val, spec=None):
    if isinstance(val, str):
        c = val[-1]
        if c in ['w', 'h']:
            val = int(val[0:len(val)-1])
            if spec == None or spec.parent == None:
                if c == 'w':
                    n = Window.width
                else:
                    n = Window.height
            else:
                if c == 'w':
                    n = spec.parent.realsize[0]
                else:
                    n = spec.parent.realsize[1]
            return val * n / 100
    return val

class Element():

    def __init__(self, type, spec):
        self.type = type
        self.spec = spec
        self.visible= True
        self.actionCB = None

    def getRelativePosition(self):
        spec = self.spec
        x = getActual(spec.pos[0], spec)
        y = getActual(spec.pos[1], spec)
        return Vector(x, y)

    def getType(self):
        return self.spec.type

    def getID(self):
        return self.spec.id

    def getPos(self):
        spec = self.spec
        pos = spec.realpos
        if spec.parent != None:
            pos = self.getRelativePosition() + spec.parent.realpos
        return pos

    def setPos(self, pos):
        if self.visible:
            # Update the spec
            self.spec.realpos = pos
            # Update the displayed item
            self.spec.item.pos = pos

    def getSize(self):
        return self.spec.realsize

    def setSize(self, size):
        self.spec.realsize = size
        self.spec.item.size = size

    def setVisible(self, vis):
        self.visible = vis
        if vis:
            self.setPos(self.spec.realpos)
        else:
            self.spec.item.pos = (Window.width, self.getPos()[1])

    def getChildren(self):
        return self.spec.children

class UI(Widget):

    elements = {}
    zlist = []

    def getElement(self, id):
        if id in self.elements.keys():
            return self.elements[id]
        return None

    def addElement(self, id, spec):
        if id in self.elements.keys():
            raise(Exception(f'Element {id} already exists'))
        element = Element(type, spec)
        element.cb = None
        self.elements[id] = element
        self.zlist.append(element)

    def createElement(self, spec):
        size = (getActual(spec.size[0], spec), getActual(spec.size[1], spec))
        spec.realsize = size
        # Deal with special case of 'center'
        if spec.pos[0] == 'center':
            left = getActual('50w', spec) - spec.realsize[0]/2
        else:
            left = getActual(spec.pos[0], spec)
        if spec.pos[1] == 'center':
            bottom = getActual('50h', spec) - spec.realsize[1]/2
        else:
            bottom = getActual(spec.pos[1], spec)
        pos = (left, bottom)
        spec.realpos = pos
        if spec.parent != None:
            pos = Vector(pos) + spec.parent.realpos
        if spec.type != 'hotspot':
            with self.canvas:
                if hasattr(spec, 'fill'):
                    c = spec.fill
                    if isinstance(c, str):
                        c = colormap[c]
                        Color(c[0], c[1], c[2])
                    else:
                        Color(c[0]/255, c[1]/255, c[2]/255)
                if spec.type == 'ellipse':
                    item = Ellipse(pos=pos, size=size)
                elif spec.type == 'rectangle':
                    item = Rectangle(pos=pos, size=size)
                elif spec.type == 'text':
                    if hasattr(spec, 'color'):
                        c = spec.color
                        if isinstance(c, str):
                            c = colormap[c]
                            Color(c[0], c[1], c[2])
                        else:
                            Color(c[0]/255, c[1]/255, c[2]/255)
                    else:
                        Color(1, 1, 1, 1)
                    if self.font == None:
                        label = CoreLabel(text=spec.text, font_size=1000, halign='center', valign='center')
                    else:
                        label = CoreLabel(text=spec.text, font_context = None, font_name=self.font, font_size=1000, halign='center', valign='center')
                    label.refresh()
                    item = Rectangle(pos=pos, size=size, texture=label.texture)
                elif spec.type == 'image':
                    item = AsyncImage(pos=pos, size=size, source=spec.source)
                spec.item = item
        self.addElement(spec.id, spec)

    def moveElementBy(self, id, dist):
        element = self.getElement(id)
        if element != None:
            element.setPos(Vector(element.getPos()) + dist)
            for id in element.getChildren():
                self.moveElementBy(id, dist)
        return

    def moveElementTo(self, id, pos):
        element = self.getElement(id)
        if element != None:
            self.moveElementBy(id, Vector(pos) - element.getPos())
        return

    def setVisible(self, id, vis):
        element = self.getElement(id)
        if element != None:
            element.setVisible(vis)
            for id in element.getChildren():
                self.setVisible(id, vis)
        return

    def on_touch_down(self, touch):
        tp = touch.pos
        x = tp[0]
        y = tp[1]
        for element in reversed(self.zlist):
            if element.actionCB != None:
                spec = element.spec
                pos = element.getPos()
                size = element.getSize()
                if spec.type == 'ellipse':
                    a = int(size[0])/2
                    b = int(size[1])/2
                    ctr = (pos[0]+a, pos[1]+b)
                    h = ctr[0]
                    k = ctr[1]
                    if (math.pow((x - h), 2) / math.pow(a, 2)) + (math.pow((y - k), 2) / math.pow(b, 2)) <= 1:
                        element.actionCB(element.data)
                        break
                elif spec.type in ['rectangle', 'text', 'image', 'hotspot']:
                    if x >= pos[0] and x < pos[0] + size[0] and y >= pos[1] and y < pos[1] + size[1]:
                        element.actionCB(element.data)
                        break

    def setOnClick(self, id, data, callback):
        element = self.getElement(id)
        element.data = data
        element.actionCB = callback

    def getWindowAttribute(self, attribute):
        if attribute == 'left':
            return Window.left
        elif attribute == 'top':
            return Window.top
        elif attribute == 'width':
            return Window.size[0]
        elif attribute == 'height':
            return Window.size[1]
        else:
            raise Exception(f'Unknown attribute: {attribute}')

    def getAttribute(self, id, attribute):
        spec = self.getElement(id).spec
        if attribute == 'left':
            return spec.realpos[0]
        elif attribute == 'bottom':
            return spec.realpos[1]
        elif attribute == 'width':
            return spec.realsize[0]
        elif attribute == 'height':
            return spec.realsize[1]
        else:
            raise Exception(f'Unknown attribute: {attribute}')

    def setAttribute(self, id, attribute, value):
        spec = self.getElement(id).spec
        if attribute == 'left':
            spec.realpos = (value, spec.realsize[0])
            spec.item.pos = (value, spec.realsize[0])
        elif attribute == 'bottom':
            spec.realpos = (spec.realsize[0], value)
            spec.item.pos = (spec.realsize[0], value)
        elif attribute == 'width':
            spec.realsize = (value, spec.realsize[0])
            spec.item.size = (value, spec.realsize[0])
        elif attribute == 'height':
            spec.realsize = (spec.realsize[0], value)
            spec.item.size = (spec.realsize[0], value)
        else:
            raise Exception(f'Unknown attribute: {attribute}')

class Renderer(App):

    def request_close(self):
        print('close window')
        self.kill()
        Window.close()

    def flushQueue(self, dt):
        self.flush()

    def build(self):
        Clock.schedule_interval(self.flushQueue, 0.01)
        return self.ui

    def init(self, spec):
        global ec_ui
        ec_ui = UI()
        self.ui = ec_ui
        self.title = spec.title
        self.flush = spec.flush
        self.kill = spec.kill
        Window.clearcolor = spec.fill
        Window.on_request_close=self.request_close
        if spec.fullscreen:
            Window.fullscreen = True
        elif spec.borderless:
            Window.borderless = True
        else:
            Window.size = spec.size
            Window.left = spec.pos[0]
            Window.top = spec.pos[1]

class Object():
    pass
