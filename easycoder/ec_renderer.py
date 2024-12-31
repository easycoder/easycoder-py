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

    def getRealPos(self):
        spec = self.spec
        pos = spec.realpos
        if spec.parent != None:
            pos = Vector(pos) + spec.parent.realpos
        return pos

    def getPos(self):
        spec = self.spec
        pos = spec.pos
        if spec.parent != None:
            pos = Vector(pos) + spec.parent.pos
        return pos

    def setPos(self, pos):
        self.spec.realpos = pos
        self.spec.item.pos = pos
    
    # Called when the parent moves
    def repos(self):
        spec = self.spec
        spec.item.pos = Vector(spec.realpos) + spec.parent.realpos
            
    def getRealSize(self):
        return self.spec.realsize
            
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
        # Get a real position or size value
        def getReal(val):
            if isinstance(val, str):
                c = val[-1]
                if c in ['w', 'h']:
                    val = int(val[0:len(val)-1])
                    if spec.parent == None:
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

        with self.canvas:
            if hasattr(spec, 'fill'):
                c = spec.fill
                if isinstance(c, str):
                    c = colormap[c]
                    Color(c[0], c[1], c[2])
                else:
                    Color(c[0]/255, c[1]/255, c[2]/255)
            pos = (getReal(spec.pos[0]), getReal(spec.pos[1]))
            spec.realpos = pos
            size = (getReal(spec.size[0]), getReal(spec.size[1]))
            spec.realsize = size
            if spec.parent != None:
                pos = Vector(pos) + spec.parent.realpos
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
                label = CoreLabel(text=spec.text, font_size=1000, halign='center', valign='center')
                label.refresh()
                text = label.texture
                item = Rectangle(pos=pos, size=size, texture=text)
            elif spec.type == 'image':
                item = AsyncImage(pos=pos, size=size, source=spec.source)
            spec.item = item
            self.addElement(spec.id, spec)
    
    def moveElementBy(self, id, dist):
        element = self.getElement(id)
        if element != None:
            element.setPos(Vector(element.getRealPos()) + dist)
            for id in element.getChildren():
                self.getElement(id).repos()
        return
    
    def moveElementTo(self, id, pos):
        element = self.getElement(id)
        if element != None:
            self.moveElementBy(id, Vector(pos) - element.getRealPos())
        return

    def on_touch_down(self, touch):
        tp = touch.pos
        x = tp[0]
        y = tp[1]
        for element in reversed(self.zlist):
            if element.cb != None:
                spec = element.spec
                pos = self.getRealPos()
                if spec.parent != None:
                    pos = Vector(pos) + spec.parent.getRealPos()
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

    def getUI(self):
        return self.ui
    
    def request_close(self):
        print('close window')
        Window.close()
    
    def flushQueue(self, dt):
        self.flush()
    
    def build(self):
        Clock.schedule_interval(self.flushQueue, 0.01)
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
