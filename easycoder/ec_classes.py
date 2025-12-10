import sys, paramiko
from typing import Optional, Any

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

###############################################################################
# This is the set of generic EasyCoder objects (values and variables)

###############################################################################
# A multipurpose value object. Holds a single value, with domain and type information
class ECValue():
    def __init__(self, domain: Optional[str] = None, type: Optional[str] = None, 
                 content: Any = None, name: Optional[str] = None):
        object.__setattr__(self, 'domain', domain)
        object.__setattr__(self, 'type', type)
        object.__setattr__(self, 'content', content)
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'properties', {})
        object.__setattr__(self, 'locked', False)
        object.__setattr__(self, '_attrs', {})  # Store dynamic attributes
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Allow setting any attribute dynamically."""
        if name in ('domain', 'type', 'content', 'name', 'properties', 'locked', '_attrs'):
            object.__setattr__(self, name, value)
        else:
            # Store dynamic attributes in _attrs dict
            self._attrs[name] = value
    
    def __getattr__(self, name: str) -> Any:
        """Retrieve dynamic attributes or return None if not found."""
        if name == '_attrs':
            return object.__getattribute__(self, '_attrs')
        return self._attrs.get(name)
    
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
        self.locked: bool = False
        self.elements: int = 0
        self.index: Optional[int] = None
        self.values: Optional[list] = None
        self.name: Optional[str] = None

    # Set the index for the variable
    def setIndex(self, index: int) -> None:
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
        if isinstance(value, ECValue): value.setName(self.name)
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

    # Set up the SSH connection
    def setup(self, host=None, user=None, password=None):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(host, username=user, password=password, timeout=10) # type: ignore
            self.setValue(ssh)
            self.sftp = ssh.open_sftp()
            return True
        except:
            return False
    
    # Get the SFTP client
    def getSFTP(self):
        return self.sftp

###############################################################################
# A stack variable
class ECStack(ECObject):

    def __init__(self):
        super().__init__()
        self.values: Optional[list[list[Any]]] = None  # List of stacks, each holding any type
    
    def push(self, item: Any) -> None:
        if self.values is None:
            self.index = 0
            self.elements = 1
            self.values = [[]]
        assert self.index is not None  # Type narrowing: index is always set when values exists
        self.values[self.index].append(item)
    
    def pop(self) -> Any:
        if self.values is None or self.index is None or self.values[self.index] is None or len(self.values[self.index]) == 0:
            return None
        return self.values[self.index].pop()
