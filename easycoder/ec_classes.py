import sys

class FatalError(BaseException):
	def __init__(self, compiler, message):
		compiler.showWarnings()
		lino = compiler.tokens[compiler.index].lino
		script = compiler.script.lines[lino].strip()
		print(f'Compile error in {compiler.program.name} at line {lino + 1} ({script}):\n-> {message}')
		sys.exit()

class NoValueError(FatalError):
	def __init__(self, compiler, record):
		super().__init__(compiler, f'Variable {record["name"]} does not hold a value')

class RuntimeAssertionError:
	def __init__(self, program, msg=None):
		code = program.code[program.pc]
		lino = code['lino']
		message = f'Assertion Error in {program.name} at line {lino + 1}'
		if msg != None:
			message += f': {msg}'
		print(message)
		sys.exit()

class RuntimeError(BaseException):
	def __init__(self, program, message):
		if program == None:
			sys.exit(f'Runtime Error: {message}')
		else:
			code = program.code[program.pc]
			lino = code['lino']
			script = program.script.lines[lino].strip()
			print(f'Runtime Error in {program.name} at line {lino + 1} ({script}):\n-> {message}')
			sys.exit()

class NoValueRuntimeError(RuntimeError):
	def __init__(self, program, record):
		super().__init__(program, 'Variable {record["name"]} does not hold a value')

class RuntimeWarning:
	def __init__(self, program, message):
		if program == None:
			print(f'Runtime Warning: {message}')
		else:
			code = program.code[program.pc]
			lino = code['lino']
			script = program.script.lines[lino].strip()
			print(f'Runtime Warning in {program.name} at line {lino + 1} ({script}): {message}')

class Script:
	def __init__(self, source):
		self.lines = source.splitlines()
		self.tokens = []

class Token:
	def __init__(self, lino, token):
		self.lino = lino
		self.token = token
	
class Object():
    """Dynamic object that allows arbitrary attribute assignment"""
    def __setattr__(self, name: str, value) -> None:
        self.__dict__[name] = value
    
    def __getattr__(self, name: str):
        return self.__dict__.get(name)

###############################################################################
# This is the set of generic EasyCoder objects (values and variables)

###############################################################################
# A value object
class ECValue():
    def __init__(self, domain=None, type=None, content=None, name=None):
        self.domain = domain
        self.type = type
        self.content = content
        self.name = name
        self.properties = {}
        self.locked = False
    
    def setDomain(self, domain):
        self.domain = domain
    
    def getDomain(self):
        return self.domain
    
    def setType(self, type):
        self.type = type
    
    def getType(self):
        return self.type
    
    def setContent(self, content):
        self.content = content
    
    def getContent(self):
        return self.content 
    
    def setValue(self, type=None, content=None):
        self.type = type
        self.content = content

    def setProperty(self, key, value):
        self.properties[key] = value

    def getProperty(self, key):
        return self.properties.get(key, None)
    
    def setName(self, name):
        self.name = name
    
    def getName(self):
        return self.name
    
    def lock(self):
        self.locked = True
    
    def isLocked(self):
        return self.locked

###############################################################################
# The base class for all EasyCoder variable types
class ECObject():
    def __init__(self):
        self.locked = False
        self.elements = 0
        self.index = None
        self.values = None
        self.name = None

    # Set the index for the variable
    def setIndex(self, index):
        self.index = index
    
    # Get the index for the variable
    def getIndex(self):
        return self.index
    
    # Lock the variable
    def setLocked(self):
        self.locked = True
    
    # Check if the variable is locked
    def isLocked(self):
        return self.locked

    # Set the value at the current index
    def setValue(self, value):
        if self.values is None:
            self.index = 0
            self.elements = 1
            self.values = [None]
        value.setName(self.name)
        self.values[self.index] = value # type: ignore

    # Get the value at the current index
    def getValue(self):
        if self.values is None: return None
        return self.values[self.index] # type: ignore
    
    # Get all the values
    def getValues(self):
        return self.values

    # Set the number of elements in the variable
    def setElements(self, elements):
        if self.elements == 0:
            self.values = [None] * elements
            self.elements = elements
            self.index = 0
        if elements == self.elements:
            pass
        elif elements > self.elements:
            self.values.extend([None] * (elements - self.elements)) # pyright: ignore[reportOptionalMemberAccess]
        else:
            del self.values[elements:] # pyright: ignore[reportOptionalSubscript]
            self.index = 0
        self.elements = elements
    
    # Get the number of elements in the variable
    def getElements(self):
        return self.elements
    
    # Check if the object has a runtime value. Default is False
    def hasRuntimeValue(self):
        return False
    
    # Check if the object is mutable. Default is False
    def isMutable(self):
        return False
    
    # Check if the object is clearable
    def isClearable(self):
         return False

    # Get the content of the value at the current index
    def getContent(self):
        if not self.hasRuntimeValue(): return None
        v = self.getValue()
        if v is None: return None
        return v.getContent()
    
    # Get the type of the value at the current index
    def getType(self):
        if not self.hasRuntimeValue(): return None
        v = self.getValue()
        if v is None: return None
        return v.getType()

    # Check if the object is empty. Default is True
    def isEmpty(self):
        return True
    
    # Set the name of the object
    def setName(self, name):
        self.name = name
    
    # Get the name of the object
    def getName(self):
        return self.name
    
    # Check if the object can have properties
    def hasProperties(self):
        return False

###############################################################################
# A generic variable object that can hold a mutable value
class ECVariable(ECObject):
    def __init__(self):
        super().__init__()
        self.properties = {}

    # Set the content of the value at the current index
    def setContent(self, content):
        if self.values is None:
            self.index = 0
            self.elements = 1
            self.values = [None]
        self.values[self.index] = content # type: ignore

    # Set the value to a given ECValue
    def setValue(self, value):
        if self.values is None:
            self.index = 0
            self.elements = 1
            self.values = [None]
        if self.index >= self.elements: raise RuntimeError(None, 'Index out of range') # type: ignore
        self.values[self.index] = value # type: ignore
    
    # Report if the object is clearable
    def isClearable(self):
         return True
    
    # This object has a runtime value
    def hasRuntimeValue(self):
        return True
    
    # This object is mutable.
    def isMutable(self):
        return True

    # Reset the object to empty state
    def reset(self):
        self.setValue(ECValue())
    
    # Check if the object can have properties
    def hasProperties(self):
        return True
    
    # Set a specific property on the object
    def setProperty(self, name, value):
        self.properties[name] = value
    
    # Check if the object has a specific property
    def hasProperty(self, name):
        return name in self.properties
    
    # Get a specific property
    def getProperty(self, name):
        return self.properties[name]

###############################################################################
# A file variable
class ECFile(ECObject):
    def __init__(self):
        super().__init__()

###############################################################################
# An SSH variable
class ECSSH(ECObject):
    def __init__(self):
        super().__init__()

###############################################################################
# A stack variable
class ECStack(ECObject):
    def __init__(self):
        super().__init__()
    
    def push(self, item):
        if self.values is None:
            self.index = 0
            self.elements = 1
            self.values = [[]]
        self.values[self.index].append(item) # pyright: ignore[reportOptionalMemberAccess]
    
    def pop(self):
        if self.values is None or not self.values[self.index]:
            return None
        return self.values[self.index].pop()
