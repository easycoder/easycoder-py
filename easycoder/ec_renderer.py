# renderer.py

import sys, json
import tkinter as tk
from PIL import *

elements = {}
zlist = []
images = {}
onTick = None

# Set the canvas
def setCanvas(c):
    global canvas
    canvas = c

# Get the canvas
def getCanvas():
    global canvas
    return canvas

def createScreen(values):
    global screen, canvas, screenLeft, screenTop, running
    running = True
    screen = tk.Tk()
    screen.title('EasyCoder')
    # screen.attributes('-fullscreen', True)

    # screen.overrideredirect(True)
    width = values['width']['content'] if 'width' in values else 600
    height = values['height']['content'] if 'height' in values else 800
    screenLeft = int((screen.winfo_screenwidth() - width) / 2)
    screenTop = int((screen.winfo_screenheight() - height) / 2)
    if 'left' in values:
        screenLeft = values['left']['content']
    if 'top' in values:
        screenTop = values['top']['content'] 

    geometry = str(width) + 'x' + str(height) + '+' + str(screenLeft) + '+' + str(screenTop) 
    screen.geometry(geometry)

    # Handle a click in the screen
    def onClick(event):
        global screenLeft, screenTop, zlist
        x = event.x
        y = event.y
        # print('Clicked at : '+ str(x) +","+ str(y))
        for i in range(1, len(zlist) + 1):
            element = zlist[-i]
            id = list(element)[0]
            values = element[id]
            x1 = values['left']
            x2 = x1 + values['width']
            y1 = values['top']
            y2 = y1 + values['height']
            if x >= x1 and x < x2 and y >= y1 and y < y2:
                if id in elements:
                    element = elements[id]
                    if 'cb' in element:
                        element['cb']()
                        break
                else:
                    RuntimeError(None, f'Element \'{id}\' does not exist')

    screen.bind('<Button-1>', onClick)

    fill = values['fill']['content'] if 'fill' in values else 'white'
    canvas = tk.Canvas(master=screen, width=width, height=height, bg=fill)
    canvas.place(x=0, y=0)
    setCanvas(canvas)

# Close the screen
def closeScreen():
    global screen
    screen.destroy()

# Set up a click handler in an element
def setOnClick(id, cb):
    global elements
    if id in elements:
        elements[id]['cb'] = cb
    else:
        RuntimeError(None, f'Element \'{id}\' does not exist')
    return

# Set up the tick handler
def setOnTick(cb):
    global onTick
    onTick = cb

# Show the screen and issue tick callbacks
def showScreen():
    global screen, onTick
    def afterCB(screen):
        if onTick != None:
            onTick()
        screen.after(100, lambda: afterCB(screen))
    screen.after(1000, lambda: afterCB(screen))
    screen.mainloop()
    sys.exit()

# Render a graphic specification
def render(spec, parent):
    global elements

    def getValue(args, item):
        if item in args:
            if type(item) == int:
                return item
            return args[item]
        return item

    def renderIntoRectangle(widgetType, values, offset, args):
        global zlist
        left = getValue(args, values['left']) if 'left' in values else 10
        top = getValue(args, values['top']) if 'top' in values else 10
        left = offset['dx'] + left
        top = offset['dy'] + top
        width = getValue(args, values['width']) if 'width' in values else 100
        height = getValue(args, values['height']) if 'height' in values else 100
        right = left + width
        bottom = top + height
        fill = values['fill'] if 'fill' in values else None
        outline = values['outline'] if 'outline' in values else None
        if outline != None:
            outlineWidth = getValue(args, values['outlineWidth']) if 'outlineWidth' in values else 1
        else:
            outlineWidth = 0
        if widgetType == 'rectangle':
            widgetId = getCanvas().create_rectangle(left, top, right, bottom, fill=fill, outline=outline, width=outlineWidth)
        elif widgetType == 'ellipse':
            widgetId = getCanvas().create_oval(left, top, right, bottom, fill=fill, outline=outline, width=outlineWidth)
        else:
            return f'Unknown widget type \'{widgetType}\''
        if 'name' in values:
            widgetName = getValue(args, values['name'])
        else:
            widgetName = None
        widgetSpec = {
            "type": widgetType,
            "name": widgetName,
            "id": widgetId,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "children": []
        }
        elements[widgetName] = widgetSpec
        zlist.append({widgetName: widgetSpec})
        if '#' in values:
            children = values['#']
            if type(children) == list:
                for item in children:
                    if item in values:
                        child = values[item]
                        childSpec = renderWidget(child, {'dx': left, 'dy': top}, args)
                        widgetSpec['children'].append(childSpec['name'])
            else:
                child = values[children]
                childSpec = renderWidget(child, {'dx': left, 'dy': top}, args)
                widgetSpec['children'].append(childSpec['name'])
        return widgetSpec
   
    def renderText(values, offset, args):
        left = getValue(args, values['left']) if 'left' in values else 10
        top = getValue(args, values['top']) if 'top' in values else 10
        left = offset['dx'] + left
        top = offset['dy'] + top
        width = getValue(args, values['width']) if 'width' in values else 100
        height = getValue(args, values['height']) if 'height' in values else 100
        right = left + width
        bottom = top + height
        shape = getValue(args, values['shape']) if 'shape' in values else 'rectangle'
        fill = getValue(args, values['fill']) if 'fill' in values else None
        outline = getValue(args, values['outline']) if 'outline' in values else None
        outlineWidth = getValue(args, values['outlineWidth']) if 'outlineWidth' in values else 0 if outline == None else 1
        color = getValue(args, values['color']) if 'color' in values else None
        text = getValue(args, values['text']) if 'text' in values else ''
        fontFace = getValue(args, values['fontFace']) if 'fontFace' in values else 'Helvetica'
        fontWeight = getValue(args, values['fontWeight']) if 'fontWeight' in values else 'normal'
        fontSize = round(height*2/5) if shape == 'ellipse' else round(height*3/5)
        fontTop = top + height/2
        if 'fontSize' in values:
            fontSize = getValue(args, values['fontSize'])
            fontTop = top + round(fontSize * 5 / 4)
        adjust = round(fontSize/5) if shape == 'ellipse' else 0
        align = getValue(args, values['align']) if 'align' in values else 'center'
        if align == 'left':
            xoff = round(fontSize/5)
            anchor = 'w'
        elif align == 'right':
            xoff = width - round(fontSize/5)
            anchor = 'e'
        else:
            xoff = width/2
            anchor = 'center'
        if xoff < 3:
            xoff = 3
        if shape == 'ellipse':
            containerId = getCanvas().create_oval(left, top, right, bottom, fill=fill, outline=outline, width=outlineWidth)
        else:
            containerId = getCanvas().create_rectangle(left, top, right, bottom, fill=fill, outline=outline, width=outlineWidth)
        textId = canvas.create_text(left + xoff, fontTop + adjust, fill=color, font=f'"{fontFace}" {fontSize} {fontWeight}', text=text, anchor=anchor)
        if 'name' in values:
            widgetName = getValue(args, values['name'])
        else:
            widgetName = None
        widgetSpec = {
            "type": "text",
            "name": widgetName,
            "id": textId,
            "containerId": containerId,
            "left": left,
            "top": top,
            "width": width,
            "height": height
        }
        elements[widgetName] = widgetSpec
        zlist.append({widgetName: widgetSpec})
        return widgetSpec

    def renderImage(values, offset, args):
        global images
        left = getValue(args, values['left']) if 'left' in values else 10
        top = getValue(args, values['top']) if 'top' in values else 10
        left = offset['dx'] + left
        top = offset['dy'] + top
        width = getValue(args, values['width']) if 'width' in values else 100
        height = getValue(args, values['height']) if 'height' in values else 100
        right = left + width
        bottom = top + height
        src = getValue(args, values['src']) if 'src' in values else None
        containerId = getCanvas().create_rectangle(left, top, right, bottom, width=0)
        if 'name' in values:
            widgetName = values['name']
        else:
            widgetName = None
        widgetSpec = {
            "type": "image",
            "nme": widgetName,
            "id": containerId,
            "left": left,
            "top": top,
            "width": width,
            "height": height
        }
        elements[widgetName] = widgetSpec
        zlist.append({widgetName: widgetSpec})
        if src == None:
            raise(Exception(f'No image source given for \'{id}\''))
        img = (Image.open(src))
        resized_image= img.resize((width, height), Image.ANTIALIAS)
        new_image= ImageTk.PhotoImage(resized_image)
        imageid = getCanvas().create_image(left, top, anchor='nw', image=new_image)
        images[containerId] = {'id': imageid, "image": new_image}
        return widgetSpec

    # Create a canvas or render a widget
    def renderWidget(widget, offset, args):
        widgetType = widget['type']
        if widgetType in ['rectangle', 'ellipse']:
            return renderIntoRectangle(widgetType, widget, offset, args)
        elif widgetType == 'text':
            return renderText(widget, offset, args)
        elif widgetType == 'image':
            return renderImage(widget, offset, args)

    # Render a complete specification
    def renderSpec(spec, offset, args):
        widgets = spec['#']
        # If a list, iterate it
        if type(widgets) is list:
            for widget in widgets:
                renderWidget(spec[widget], offset, args)
        # Otherwise, process the single widget
        else:
            renderWidget(spec[widgets], offset, args)

    # Main entry point
    offset = {'dx': 0, 'dy': 0}
    if parent != screen:
        RuntimeError(None, 'Can\'t yet render into parent widget')

    # If it'a string, process it
    if type(spec) is str:
        renderSpec(json.loads(spec), offset, {})

    # If it's a 'dict', extract the spec and the args
    if type(spec) is dict:
        args = spec['args']
        spec = json.loads(spec['spec'])
        renderSpec(spec, offset, args)

# Get the widget whose name is given
def getElement(name):
    global elements
    if name in elements:
        return elements[name]
    else:
        RuntimeError(None, f'Element \'{name}\' does not exist')

# Set the content of a text widget
def setText(name, value):
    getCanvas().itemconfig(getElement(name)['id'], text=value)

# Set the background of a rectangle or ellipse widget
def setBackground(name, value):
    id = getElement(name)['id']
    getCanvas().itemconfig(getElement(name)['id'], fill=value)
    
# Move an element by an amount
def moveElement(name, dx, dy):
    element = getElement(name)
    getCanvas().move(element['id'], dx, dy)
    element['left'] += dx
    element['top'] += dy
    for childName in element['children']:
        element = getElement(childName)
        getCanvas().move(element['id'], dx, dy)

# Move an element to a new location
def moveElementTo(name, left, top):
    element = getElement(name)
    moveElement(name, left - element['left'], top - element['top'])

# Get an attribute of an element
def getAttribute(name, attribute):
    element = getElement(name)
    return element[attribute]
