# renderer.py

import sys, json
import tkinter as tk
from PIL import Image, ImageTk

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
            x2 = x1 + values['width'] + getScreenLeft(values['parent'])
            y1 = values['top'] + getScreenTop(values['parent'])
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

    def renderIntoRectangle(widgetType, values, parent, args):
        global zlist
        left = getValue(args, values['left']) if 'left' in values else 10
        screenLeft = left + getScreenLeft(parent)
        top = getValue(args, values['top']) if 'top' in values else 10
        screenTop = top + getScreenTop(parent)
        width = getValue(args, values['width']) if 'width' in values else 100
        height = getValue(args, values['height']) if 'height' in values else 100
        right = screenLeft + width
        bottom = screenTop + height
        fill = values['fill'] if 'fill' in values else None
        outline = values['outline'] if 'outline' in values else None
        if outline != None:
            outlineWidth = getValue(args, values['outlineWidth']) if 'outlineWidth' in values else 1
        else:
            outlineWidth = 0
        if widgetType == 'rectangle':
            widgetId = getCanvas().create_rectangle(screenLeft, screenTop, right, bottom, fill=fill, outline=outline, width=outlineWidth)
        elif widgetType == 'ellipse':
            widgetId = getCanvas().create_oval(screenLeft, screenTop, right, bottom, fill=fill, outline=outline, width=outlineWidth)
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
            "parent": parent,
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
                        childSpec = renderWidget(child, widgetSpec, args)
                        widgetSpec['children'].append(childSpec['name'])
            else:
                child = values[children]
                childSpec = renderWidget(child, widgetSpec, args)
                widgetSpec['children'].append(childSpec['name'])
        return widgetSpec
   
    def renderText(values, parent, args):
        left = getValue(args, values['left']) if 'left' in values else 10
        screenLeft = left + getScreenLeft(parent)
        top = getValue(args, values['top']) if 'top' in values else 10
        screenTop = top + getScreenTop(parent)
        width = getValue(args, values['width']) if 'width' in values else 100
        height = getValue(args, values['height']) if 'height' in values else 100
        shape = getValue(args, values['shape']) if 'shape' in values else 'rectangle'
        outline = getValue(args, values['outline']) if 'outline' in values else None
        color = getValue(args, values['color']) if 'color' in values else None
        text = getValue(args, values['text']) if 'text' in values else ''
        fontFace = getValue(args, values['fontFace']) if 'fontFace' in values else 'Helvetica'
        fontWeight = getValue(args, values['fontWeight']) if 'fontWeight' in values else 'normal'
        fontTop = int(round(screenTop + height/2))
        if 'fontSize' in values:
            fontSize = getValue(args, values['fontSize'])
            fontTop = int(round(screenTop + height/2 - fontSize/4))
        else:
            fontSize = int(round(height*2/5) if shape == 'ellipse' else round(height*3/5))
            fontTop -= int(round(screenTop + height/2 - fontSize/5))
        adjust = int(round(fontSize/5)) if shape == 'ellipse' else 0
        align = getValue(args, values['align']) if 'align' in values else 'center'
        if align == 'left':
            xoff = int(round(fontSize/5))
            anchor = 'w'
        elif align == 'right':
            xoff = width - int(round(fontSize/5))
            anchor = 'e'
        else:
            xoff = int(round(width/2))
            anchor = 'center'
        if xoff < 3:
            xoff = 3
        xoff -= int(round(fontSize/4))
        textId = canvas.create_text(screenLeft + xoff, fontTop + adjust, fill=color, font=f'"{fontFace}" {fontSize} {fontWeight}', text=text, anchor=anchor)
        if 'name' in values:
            widgetName = getValue(args, values['name'])
        else:
            widgetName = None
        widgetSpec = {
            "type": "text",
            "name": widgetName,
            "id": textId,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "parent": parent
        }
        elements[widgetName] = widgetSpec
        zlist.append({widgetName: widgetSpec})
        return widgetSpec

    def renderImage(values, parent, args):
        global images
        left = getValue(args, values['left']) if 'left' in values else 10
        screenLeft = left + getScreenLeft(parent)
        top = getValue(args, values['top']) if 'top' in values else 10
        screenTop = top + getScreenTop(parent)
        width = getValue(args, values['width']) if 'width' in values else 100
        source = getValue(args, values['source']) if 'source' in values else None
        if 'name' in values:
            widgetName = values['name']
        else:
            widgetName = None
        if source == None:
            raise(Exception(f'No image source given for \'{id}\''))
        img = (Image.open(source))
        height = int(round(img.height * width / img.width))
        resized_image= img.resize((width, height), Image.LANCZOS)
        new_image= ImageTk.PhotoImage(resized_image)
        imageid = getCanvas().create_image(screenLeft, screenTop, anchor='nw', image=new_image)
        images[widgetName] = {'id': imageid, "image": new_image}
        widgetSpec = {
            "type": "image",
            "nme": widgetName,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "source": source,
            "parent": parent
        }
        elements[widgetName] = widgetSpec
        zlist.append({widgetName: widgetSpec})
        return widgetSpec

    # Create a canvas or render a widget
    def renderWidget(widget, parent, args):
        widgetType = widget['type']
        if widgetType in ['rectangle', 'ellipse']:
            return renderIntoRectangle(widgetType, widget, parent, args)
        elif widgetType == 'text':
            return renderText(widget, parent, args)
        elif widgetType == 'image':
            return renderImage(widget, parent, args)

    # Render a complete specification
    def renderSpec(spec, parent, args):
        widgets = spec['#']
        # If a list, iterate it
        if type(widgets) is list:
            for widget in widgets:
                renderWidget(spec[widget], parent, args)
        # Otherwise, process the single widget
        else:
            renderWidget(spec[widgets], parent, args)

    # Main entry point
    if parent != screen:
        RuntimeError(None, 'Can\'t yet render into parent widget')

    # If it'a string, process it
    if type(spec) is str:
        renderSpec(json.loads(spec), None, {})

    # If it's a 'dict', extract the spec and the args
    if type(spec) is dict:
        args = spec['args']
        spec = json.loads(spec['spec'])
        renderSpec(spec, None, args)

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

# Get the screen left position of an element
def getScreenLeft(element):
    if element == None:
        return 0
    return element['left'] + getScreenLeft(element['parent'])

# Get the screen top position of an element
def getScreenTop(element):
    if element == None:
        return 0
    return element['top'] + getScreenTop(element['parent'])
