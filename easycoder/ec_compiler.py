from .ec_classes import FatalError
from .ec_value import Value
from .ec_condition import Condition

class Compiler:

	def __init__(self, program):
		self.program = program
		self.value = Value(self)
		self.condition = Condition(self)
		self.marker = 0
		self.script = self.program.script
		self.tokens = self.script.tokens
		self.symbols = self.program.symbols
		self.code = self.program.code
		self.program.compiler = self
		self.compileConstant = self.value.compileConstant
		self.debugCompile = False
		self.valueTypes = {}

	# Get the current code size. Used during compilation
	def getCodeSize(self):
		return len(self.program.code)

	# Get the current index (the program counter)
	def getIndex(self):
		return self.index

	# Move the index along
	def next(self):
		self.index += 1

	# Get the current token
	def getToken(self):
		if self.index >= len(self.tokens):
			FatalError(self, 'Premature end of script')
		return self.tokens[self.index].token

	# Get the next token
	def nextToken(self):
		self.index += 1
		return self.getToken()

	# Peek ahead to see the next token without advancing the index
	def peek(self):
		try:
			return self.tokens[self.index + 1].token
		except:
			return None

	# Get a constant
	def getConstant(self, token):
		self.index += 1
		return self.compileConstant(token)

	# Get a value
	def getValue(self):
		return self.value.compileValue()

	# Get the next value
	def nextValue(self):
		self.index += 1
		return self.value.compileValue()

	# Get a condition
	def getCondition(self):
		return self.condition.compileCondition()

	# Get the next condition
	def nextCondition(self):
		self.index += 1
		return self.condition.compileCondition()

	# Test if the current token has a specified value
	def tokenIs(self, value):
		return self.getToken() == value

	# Test if the next token has the specified value
	def nextIs(self, value):
		return self.nextToken() == value

	# Get the command at a given pc in the code list
	def getCommandAt(self, pc):
		return self.program.code[pc]

	# Add a command to the code list
	def addCommand(self, command):
		command['bp'] = False
		self.code.append(command)

	# Test if the current token is a symbol
	def isSymbol(self):
		token = self.getToken()
		try:
			self.symbols[token]
		except:
			return False
		return True

	# Test if the next token is a symbol
	def nextIsSymbol(self):
		self.next()
		return self.isSymbol()
	
	# Skip the next token if it matches the value given
	def skip(self, token):
		next = self.peek()
		if type(token) == list:
			for item in token:
				if next == item:
					self.nextToken()
					return
		elif next == token: self.nextToken()

	# Rewind to a given position in the code list
	def rewindTo(self, index):
		self.index = index

	# Get source line number containing the current token
	def getLino(self):
		if self.index >= len(self.tokens):
			return 0
		return self.tokens[self.index].lino

	# Issue a warning
	def warning(self, message):
		self.warnings.append(f'Warning at line {self.getLino() + 1} of {self.program.name}: {message}')

	# Print all warnings
	def showWarnings(self):
		for warning in self.warnings:
			print(warning)

	# Get the symbol record for the current token (assumes it is a symbol name)
	def getSymbolRecord(self):
		token = self.getToken()
		if not token in self.symbols:
			FatalError(self, f'Undefined symbol name "{token}"')
			return None
		symbol = self.symbols[token]
		if symbol == None: return None
		symbolRecord = self.code[symbol]
		symbolRecord['used'] = True
		return symbolRecord

	# Add a value type
	def addValueType(self):
		self.valueTypes[self.getToken()] = True

	# Test if a given value is in the value types list
	def hasValue(self, type):
		return type in self.valueTypes

	# Compile a program label (a symbol ending with ':')
	def compileLabel(self, command):
		return self.compileSymbol(command, self.getToken())

	# Compile a variable
	def compileVariable(self, command, extra=None):
		return self.compileSymbol(command, self.nextToken(), extra)

	# Compile a symbol
	def compileSymbol(self, command, name, extra=None):
		try:
			v = self.symbols[name]
		except:
			v = None
		if v:
			FatalError(self, f'Duplicate symbol name "{name}"')
			return False
		self.symbols[name] = self.getCodeSize()
		command['program'] = self.program
		command['type'] = 'symbol'
		command['name'] = name
		command['elements'] = 1
		command['index'] = 0
		command['value'] = [None]
		command['used'] = False
		command['debug'] = False
		command['import'] = None
		command['locked'] = False
		command['extra'] = extra
		if 'keyword' in command: command['hasValue'] = self.hasValue(command['keyword'])
		self.addCommand(command)
		return True

	# Compile the current token
	def compileToken(self):
		self.warnings = []
		token = self.getToken()
#		print(f'Compile {token}')
		if not token:
			return False
		if len(self.code) == 0:
			if self.program.parent == None and self.program.usingGraphics:
				cmd = {'domain': 'graphics', 'keyword': 'init', 'debug': False}
				self.code.append(cmd)
		mark = self.getIndex()
		for domain in self.program.getDomains():
			handler = domain.keywordHandler(token)
			if handler:
				command = {}
				command['domain'] = domain.getName()
				command['lino'] = self.tokens[self.index].lino
				command['keyword'] = token
				command['type'] = None
				command['debug'] = True
				result = handler(command)
				if result:
					return result
				else:
					self.rewindTo(mark)
			else:
				self.rewindTo(mark)
		FatalError(self, f'Unable to compile this "{token}" command')

	# Compile a single command
	def compileOne(self):
		keyword = self.getToken()
		if not keyword:
			return False
#		print(f'Compile keyword "{keyword}"')
		if keyword.endswith(':'):
			command = {}
			command['domain'] = None
			command['lino'] = self.tokens[self.index].lino
			return self.compileLabel(command)
		else:
			return self.compileToken()

	# Compile the script
	def compileFrom(self, index, stopOn):
		self.index = index
		while True:
			token = self.tokens[self.index]
#			keyword = token.token
			if self.debugCompile: print(self.script.lines[token.lino])
#			if keyword != 'else':
			if self.compileOne() == True:
				if self.index == len(self.tokens) - 1:
					return True
				token = self.nextToken()
				if token in stopOn:
					return True
			else:
				return False

	# Compile fom the current location, stopping on any of a list of tokens
	def compileFromHere(self, stopOn):
		return self.compileFrom(self.getIndex(), stopOn)

	# Compile from the start of the script
	def compileFromStart(self):
		return self.compileFrom(0, [])