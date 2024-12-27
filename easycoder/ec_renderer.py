from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import CoreLabel
from kivy.uix.image import AsyncImage
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.utils import colormap
from kivy.clock import Clock
from kivy.vector import Vector
import math

class Object():
    pass

class Element():

    def __init__(self, type, spec):
        self.type = type
        self.spec = spec

    def getType(self):
        return self.spec.type

    def getID(self):
        return self.spec.id

    def getPos(self):
        spec = self.spec
        pos = spec.pos
        if spec.parent != None:
            pos = Vector(pos) + spec.parent.pos
        return pos

    def setPos(self, pos):
        self.spec.pos = pos
        self.spec.item.pos = pos
    
    # Called when the parent moves
    def repos(self):
        spec = self.spec
        spec.item.pos = Vector(spec.pos) + spec.parent.pos
            
    def getSize(self):
        return self.spec.size

    def setSize(self, size):
        self.spec.size = size
    
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
        with self.canvas:
            if hasattr(spec, 'fill'):
                c = spec.fill
                if isinstance(c, str):
                    c = colormap[c]
                    Color(c[0], c[1], c[2])
                else:
                    Color(c[0]/255, c[1]/255, c[2]/255)
            pos = spec.pos
            if spec.parent != None:
                pos = Vector(pos) + spec.parent.pos
            if spec.type == 'ellipse':
                item = Ellipse(pos=pos, size=spec.size)
            elif spec.type == 'rectangle':
                item = Rectangle(pos=pos, size=spec.size)
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
                label = CoreLabel(text=spec.text, font_size=1000, halign='center', valign='center')
                label.refresh()
                text = label.texture
                item = Rectangle(pos=spec.pos, size=spec.size, texture=text)
            elif spec.type == 'image':
                item = AsyncImage(pos=spec.pos, size=spec.size, source=spec.source)
            spec.item = item
            self.addElement(spec.id, spec)
    
    def moveElementBy(self, id, dist):
        element = self.getElement(id)
        if element != None:
            element.setPos(Vector(element.getPos()) + dist)
            for id in element.getChildren():
                self.getElement(id).repos()
        return
    
    def moveElementTo(self, id, pos):
        element = self.getElement(id)
        if element != None:
            self.moveElementBy(id, Vector(pos) - element.getPos())
        return

    def on_touch_down(self, touch):
        tp = touch.pos
        x = tp[0]
        y = tp[1]
        for element in reversed(self.zlist):
            if element.cb != None:
                spec = element.spec
                pos = spec.pos
                if spec.parent != None:
                    pos = Vector(pos) + spec.parent.pos
                size = spec.size
                if spec.type == 'ellipse':
                    a = size[0]/2
                    b = size[1]/2
                    ctr = (pos[0] + a, pos[1] +b)
                    h = ctr[0]
                    k = ctr[1]
                    if (math.pow((x - h), 2) / math.pow(a, 2)) + (math.pow((y - k), 2) / math.pow(b, 2)) <= 1:
                        element.cb()
                        break
                elif spec.type in ['rectangle', 'text', 'image']:
                    if tp[0] >= pos[0] and tp[0] < pos[0] + size[0] and tp[1] >= pos[1] and tp[1] < pos[1] + size[1]:
                        element.cb()
                        break
    
    def setOnClick(self, id, callback):
        self.getElement(id).cb = callback

    def getAttribute(self, id, attribute):
        spec = self.getElement(id).spec
        if attribute == 'left':
            return spec.pos[0]
        elif attribute == 'bottom':
            return spec.pos[1]
        elif attribute == 'width':
            return spec.size[0]
        elif attribute == 'height':
            return spec.size[1]
        else:
            raise Exception(f'Unknown attribute: {attribute}')


class Renderer(App):

    def getUI(self):
        return self.ui
    
    def request_close(self):
        print('close window')
        Window.close()
    
    def flushQueue(self, dt):
        self.flush()
    
    def build(self):
        Clock.schedule_interval(self.flushQueue, 0.05)
        self.ui = UI()
        return self.ui

    def init(self, spec):
        self.title = spec.title
        self.flush = spec.flush
        Window.size = spec.size
        Window.left = spec.pos[0]
        Window.top = spec.pos[1]
        Window.clearcolor = spec.fill
        Window.on_request_close=self.request_close
