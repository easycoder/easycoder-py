from .ec_classes import FatalError

# Create a constant
def getConstant(str):
	value = {}
	value['type'] = 'text'
	value['content'] = str
	return value

class Value:

	def __init__(self, compiler):
		self.compiler = compiler
		self.getToken = compiler.getToken
		self.nextToken = compiler.nextToken
		self.peek = compiler.peek
		self.tokenIs = compiler.tokenIs

	def getItem(self):
		token = self.getToken()
		if not token:
			return None

		value = {}

		if token == 'true':
			value['type'] = 'boolean'
			value['content'] = True
			return value

		if token == 'false':
			value['type'] = 'boolean'
			value['content'] = False
			return value

		# Check for a string constant
		if token[0] == '`':
			if token[len(token) - 1] == '`':
				value['type'] = 'text'
				value['content'] = token[1 : len(token) - 1]
				return value
			FatalError(self.compiler, f'Unterminated string "{token}"')
			return None

		# Check for a numeric constant
		if token.isnumeric() or (token[0] == '-' and token[1:].isnumeric):
			val = eval(token)
			if isinstance(val, int):
				value['type'] = 'int'
				value['content'] = val
				return value
			FatalError(self.compiler, f'{token} is not an integer')

		# See if any of the domains can handle it
		mark = self.compiler.getIndex()
		for domain in self.compiler.program.getDomains():
			item = domain.compileValue()
			if item != None:
				return item
			self.compiler.rewindTo(mark)
		# self.compiler.warning(f'I don\'t understand \'{token}\'')
		return None

	def compileValue(self):
		token = self.getToken()
		item = self.getItem()
		if item == None:
			self.compiler.warning(f'ec_value.compileValue: Cannot get the value of "{token}"')
			return None

		value = {}
		if self.peek() == 'cat':
			value['type'] = 'cat'
			value['numeric'] = False
			value['value'] = [item]
			while self.peek() == 'cat':
				self.nextToken()
				self.nextToken()
				item = self.getItem()
				if item != None:
					value['value'].append(item)
		else:
			value = item

	# See if any domain has something to add to the value
		for domain in self.compiler.program.getDomains():
			value = domain.modifyValue(value)

		return value

	def compileConstant(self, token):
		value = {}
		if type(token) == 'str':
			token = eval(token)
		if isinstance(token, int):
			value['type'] = 'int'
			value['content'] = token
			return value
		if isinstance(token, float):
			value['type'] = 'float'
			value['content'] = token
			return value
		value['type'] = 'text'
		value['content'] = token
		return value
