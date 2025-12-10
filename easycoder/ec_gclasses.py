from .ec_classes import ECObject

###############################################################################
# A graphic element variable
class ECGElement(ECObject):
    def __init__(self):
        super().__init__()

###############################################################################
# A widget variable
class ECWidget(ECGElement):
    def __init__(self):
        super().__init__()

###############################################################################
# A widget with a text value
class ECTextWidget(ECWidget):
    def __init__(self):
        super().__init__()
    
    # This type of widget has a runtime value
    def hasRuntimeValue(self):
        return True
    
    # Get the text of the widget
    def getText(self):
        return self.getContent().text() # type: ignore

    # Check if the object is empty
    def isEmpty(self):
        return self.getText() == ""

###############################################################################
# A layout variable
class ECLayout(ECWidget):
    def __init__(self):
        super().__init__()

###############################################################################
# A group variable
class ECGroup(ECWidget):
    def __init__(self):
        super().__init__()

###############################################################################
# A label variable
class ECLabel(ECTextWidget):
    def __init__(self):
        super().__init__()

###############################################################################
# A pushbutton variable
class ECPushButton(ECTextWidget):
    def __init__(self):
        super().__init__()

###############################################################################
# A checkbox variable
class ECCheckBox(ECWidget):
    def __init__(self):
        super().__init__()
    
    # This object has a runtime value
    def hasRuntimeValue(self):
        return True

    # Get the content of the value at the current index
    def getContent(self):
        v = self.getValue()
        if v is None: return None
        return v.getContent().isChecked()

###############################################################################
# A line input variable
class ECLineInput(ECTextWidget):
    def __init__(self):
        super().__init__()
    
    # This object has a runtime value
    def hasRuntimeValue(self):
        return True
    
    # Get the text of the widget
    def getText(self):
        return self.getValue().getContent().text() # type: ignore

    # Get the content of the value at the current index
    def getContent(self):
        v = self.getValue()
        if v is None: return None
        return v.getContent().text()

###############################################################################
# A multiline variable
class ECMultiline(ECTextWidget):
    def __init__(self):
        super().__init__()

###############################################################################
# A listbox variable
class ECListBox(ECWidget):
    def __init__(self):
        super().__init__()
    
    # This type of widget has a runtime value
    def hasRuntimeValue(self):
        return True
    
    # This type of widget is mutable.
    def isMutable(self):
        return True
    
    # This type of widget is clearable
    def isClearable(self):
         return True
    
    # Get the count of items in the list box
    def getCount(self):
        v = self.getContent().count() # type: ignore
        return v
    
    # Get the selected item in the list box
    def getContent(self):
        widget = self.getValue().getContent() # type: ignore
        content = widget.selectedItems()[0].text() if widget.selectedItems() else None
        return content

###############################################################################
# A combo box variable
class ECComboBox(ECWidget):
    def __init__(self):
        super().__init__()
    
    # This type of widget has a runtime value
    def hasRuntimeValue(self):
        return True
    
    # This type of widget is mutable.
    def isMutable(self):
        return True
    
    # This type of widget is clearable
    def isClearable(self):
         return True
    
    # Get the count of items in the combo box
    def getCount(self):
        v = self.getContent().count() # type: ignore
        return v

###############################################################################
# A window variable
class ECWindow(ECGElement):
    def __init__(self):
        super().__init__()

###############################################################################
# A dialog variable
class ECDialog(ECGElement):
    def __init__(self):
        super().__init__()

###############################################################################
# A message box variable
class ECMessageBox(ECGElement):
    def __init__(self):
        super().__init__()
