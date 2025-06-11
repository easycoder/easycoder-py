import time, json, sys
from copy import deepcopy
from collections import deque
from .ec_classes import Script, Token, FatalError, RuntimeError, Object
from .ec_compiler import Compiler
from .ec_core import Core
import importlib
from importlib.metadata import version

# Flush the queue
def flush():
	global queue
	while len(queue):
		item = queue.popleft()
		item.program.flush(item.pc)

class Program:

	def __init__(self, argv):
		global queue
		print(f'EasyCoder version {version("easycoder")}')
		if len(argv) == 0:
			print('No script supplied')
			exit()
		self.classes=[Core]
		scriptName = argv

		f = open(scriptName, 'r')
		source = f.read()
		f.close()
		queue = deque()
		self.argv = argv
		self.domains = []
		self.domainIndex = {}
		self.name = '<anon>'
		self.code = []
		self.symbols = {}
		self.onError = 0
		self.pc = 0
		self.debugStep = False
		self.stack = []
		self.script = Script(source)
		self.compiler = Compiler(self)
		self.value = self.compiler.value
		self.condition = self.compiler.condition
		self.graphics = None
		self.processClasses()
		self.externalControl = False
		self.ticker = 0
		self.running = True

	# This is called at 10msec intervals by the GUI code
	def flushCB(self):
		self.ticker += 1
		flush()

	def start(self, parent=None, module = None, exports=[]):
		self.parent = parent
		self.exports = exports
		if module != None:
			module['child'] = self
		startCompile = time.time()
		self.tokenise(self.script)
		if self.compiler.compileFrom(0, []):
			finishCompile = time.time()
			s = len(self.script.lines)
			t = len(self.script.tokens)
			print(f'Compiled {self.name}: {s} lines ({t} tokens) in ' +
				f'{round((finishCompile - startCompile) * 1000)} ms')
			for name in self.symbols.keys():
				record = self.code[self.symbols[name]]
				if name[-1] != ':' and not record['used']:
					print(f'Variable "{name}" not used')
			else:
				print(f'Run {self.name}')
				self.run(0)
		else:
			self.compiler.showWarnings()

		# If this is the main script and there's no graphics, run a main loop
		if parent == None and self.externalControl == False:
			while True:
				if self.running == True:
					flush()
					time.sleep(0.01)
				else:
					break

	# Import a plugin
	def importPlugin(self, source):
		args=source.split(':')
		if len(args)<2:
			RuntimeError(None, f'Invalid plugin spec "{source}"')
		idx=args[0].rfind('/')
		if idx<0:
			sys.path.append('.')
			module=args[0]
		else:
			sys.path.append(args[0][0:idx])
			module=args[0][idx+1:len(args[0])]
		module = module.replace('/','.').replace('.py','')
		module = importlib.import_module(module)
		plugin = getattr(module, args[1])
		self.classes.append(plugin)
		self.processClasses()

	# Process the class list to get the domains
	def processClasses(self):
		self.domains=[]
		for clazz in self.classes:
			handler = clazz(self.compiler)
			self.domains.append(handler)
			self.domainIndex[handler.getName()] = handler

	# Get the domain list
	def getDomains(self):
		return self.domains

	def getSymbolRecord(self, name):
		try:
			target = self.code[self.symbols[name]]
			if target['import'] != None:
				target = target['import']
			return target
		except:
			RuntimeError(self, f'Unknown symbol \'{name}\'')

	def doValue(self, value):
		if value == None:
			RuntimeError(self, f'Undefined value (variable not initialized?)')

		result = {}
		valType = value['type']
		if valType in ['boolean', 'int', 'text', 'object']:
			result = value
		elif valType == 'cat':
			content = ''
			for part in value['value']:
				val = self.doValue(part)
				if val == None:
					val = ''
				if val != '':
					val = str(val['content'])
					if val == None:
						val = ''
					content += val
			result['type'] = 'text'
			result['content'] = content
		elif valType == 'symbol':
			name = value['name']
			symbolRecord = self.getSymbolRecord(name)
			if symbolRecord['hasValue']:
				handler = self.domainIndex[symbolRecord['domain']].valueHandler('symbol')
				result = handler(symbolRecord)
			else:
				# Call the given domain to handle a value
				domain = self.domainIndex[value['domain']]
				handler = domain.valueHandler(value['type'])
				if handler: result = handler(value)
		else:
			# Call the given domain to handle a value
			domain = self.domainIndex[value['domain']]
			handler = domain.valueHandler(value['type'])
			if handler: result = handler(value)

		return result

	def constant(self, content, numeric):
		result = {}
		result['type'] = 'int' if numeric else 'text'
		result['content'] = content
		return result

	def evaluate(self, value):
		if value == None:
			result = {}
			result['type'] = 'text'
			result['content'] = ''
			return result

		result = self.doValue(value)
		if result:
			return result
		return None

	def getValue(self, value):
		return self.evaluate(value).content

	def getRuntimeValue(self, value):
		if value is None:
			return None
		v = self.evaluate(value)
		if v != None:
			content = v['content']
			if v['type'] == 'boolean':
				return True if content else False
			if v['type'] in ['int', 'float', 'text', 'object']:
				return content
			return ''
		return None

	def getSymbolValue(self, symbolRecord):
		if len(symbolRecord['value']) == 0:
			return None
		value = symbolRecord['value'][symbolRecord['index']]
		copy = deepcopy(value)
		return copy

	def putSymbolValue(self, symbolRecord, value):
		if symbolRecord['locked']:
			name = symbolRecord['name']
			RuntimeError(self, f'Symbol "{name}" is locked')
		if symbolRecord['value'] == None or symbolRecord['value'] == []:
			symbolRecord['value'] = [value]
		else:
			index = symbolRecord['index']
			if index == None:
				index = 0
			symbolRecord['value'][index] = value

	def encode(self, value):
		return value

	def decode(self, value):
		return value

	# Tokenise the script
	def tokenise(self, script):
		token = ''
		literal = False
		for lino in range(0, len(script.lines)):
			line = script.lines[lino]
			length = len(line)
			if length == 0:
				continue
			# Look for the first non-space
			n = 0
			while n < length and line[n].isspace():
				n += 1
			# The whole line may be empty
			if n == length:
				if literal:
					token += '\n'
				continue
			# If in an unfinished literal, the first char must be a backtick to continue adding to it
			if literal:
				if line[n] != '`':
					# Close the current token
					if len(token) > 0:
						script.tokens.append(Token(lino, token))
						token = ''
						literal = False
				n += 1
			for n in range(n, length):
				c = line[n]
				# Test if we are in a literal
				if not literal:
					if c.isspace():
						if len(token) > 0:
							script.tokens.append(Token(lino, token))
							token = ''
						continue
					elif c == '!':
						break
				# Test for the start or end of a literal
				if c == '`':
					if literal:
						token += c
						literal = False
					else:
						token += c
						literal = True
						m = n
						continue
				else:
					token += c
			if len(token) > 0:
				if literal:
					token += '\n'
				else:
					script.tokens.append(Token(lino, token))
					token = ''
		return

	def releaseParent(self):
		if self.parent.waiting and self.parent.program.running:
			self.parent.waiting = False
			self.parent.program.run(self.parent.pc)

	# Flush the queue
	def flush(self, pc):
		global queue
		self.pc = pc
		while self.running:
			command = self.code[self.pc]
			domainName = command['domain']
			if domainName == None:
				self.pc += 1
			else:
				keyword = command['keyword']
				if self.debugStep and command['debug']:
					lino = command['lino'] + 1
					line = self.script.lines[command['lino']].strip()
					print(f'{self.name}: Line {lino}: {domainName}:{keyword}:  {line}')
				domain = self.domainIndex[domainName]
				handler = domain.runHandler(keyword)
				if handler:
					command = self.code[self.pc]
					command['program'] = self
					self.pc = handler(command)
					# Deal with 'exit'
					if self.pc == -1:
						queue = deque()
						if self.parent != None:
							self.releaseParent()
						self.running = False
						break
					elif self.pc == None or self.pc == 0 or self.pc >= len(self.code):
						break

	# Run the script at a given PC value
	def run(self, pc):
		global queue
		item = Object()
		item.program = self
		item.pc = pc
		queue.append(item)

	def kill(self):
		self.running = False
		if self.parent != None: self.parent.program.kill()

	def setExternalControl(self):
		self.externalControl = True

	def nonNumericValueError(self):
		FatalError(self.compiler, 'Non-numeric value')

	def variableDoesNotHoldAValueError(self, name):
		raise FatalError(self.compiler, f'Variable "{name}" does not hold a value')

	def noneValueError(self, name):
		raise FatalError(self.compiler, f'Value is None')

	def compare(self, value1, value2):
		val1 = self.evaluate(value1)
		val2 = self.evaluate(value2)
		if val1 == None or val2 == None:
			return 0
		v1 = val1['content']
		v2 = val2['content']
		if v1 == None and v2 != None or v1 != None and v2 == None:
			return 0
		if v1 != None and val1['type'] == 'int':
			if not val2['type'] == 'int':
				if type(v2) is str:
					try:
						v2 = int(v2)
					except:
						lino = self.code[self.pc]['lino'] + 1
						RuntimeError(None, f'Line {lino}: \'{v2}\' is not an integer')
		else:
			if v2 != None and val2['type'] == 'int':
				v2 = str(v2)
			if v1 == None:
				v1 = ''
			if v2 == None:
				v2 = ''
		if type(v1) == int:
			if type(v2) != int:
				v1 = f'{v1}'
		if type(v2) == int:
			if type(v1) != int:
				v2 = f'{v2}'
		if v1 > v2:
			return 1
		if v1 < v2:
			return -1
		return 0

	# Set up a message handler
	def onMessage(self, pc):
		self.onMessagePC = pc

	# Handle a message from our parent program
	def handleMessage(self, message):
		self.message = message
		self.run(self.onMessagePC)

# This is the program launcher
def Main():
	if (len(sys.argv) > 1):
		Program(sys.argv[1]).start()
	else:
		print('Syntax: easycoder <scriptname> [plugins]')

if __name__ == '__main__':
    Main()

