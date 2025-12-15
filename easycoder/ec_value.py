from .ec_classes import ECObject, FatalError, ECValue

# Create a constant
def getConstant(str):
	return ECValue(type='str', content=str)

class Value:

	def __init__(self, compiler):
		self.compiler = compiler
		self.getToken = compiler.getToken
		self.nextToken = compiler.nextToken
		self.peek = compiler.peek
		self.skip = compiler.skip
		self.tokenIs = compiler.tokenIs

	def getItem(self):
		token = self.getToken()
		if not token:
			return None

		value = ECValue()

		if token == 'true':
			value.setValue('boolean', True)
			return value

		if token == 'false':
			value.setValue('boolean', False)
			return value

		# Check for a string constant
		if token[0] == '`':
			if token[len(token) - 1] == '`':
				value.setValue(type='str', content=token[1 : len(token) - 1])
				return value
			FatalError(self.compiler, f'Unterminated string "{token}"')
			return None

		# Check for a numeric constant
		if token.isnumeric() or (token[0] == '-' and token[1:].isnumeric):
			val = eval(token)
			if isinstance(val, int):
				value.setValue('int', val)
				return value
			FatalError(self.compiler, f'{token} is not an integer')

		# See if any of the domains can handle it
		mark = self.compiler.getIndex()
		for domain in self.compiler.program.getDomains():
			item = domain.compileValue()
			if item != None: return item
			self.compiler.rewindTo(mark)
		# self.compiler.warning(f'I don\'t understand \'{token}\'')
		return None

	# Get something starting following 'the'
	def getTheSomething(self):
		self.nextToken()  # consume 'the'
		value = ECValue()
		if self.getToken() == 'cat':
			self.nextToken()  # consume 'cat'
			self.skip('of')
			self.nextToken()
			item = self.getItem()
			value.setType('cat')
			items = [item]
			while self.peek() in ['cat', 'and']:
				self.nextToken()
				self.nextToken()
				element = self.getItem()
				if element != None:
					items.append(element) # pyright: ignore[reportOptionalMemberAccess]
			value.setContent(items)
		return value
	
	# Compile a value
	def compileValue(self):
		token = self.getToken()
		if token == 'the': value = self.getTheSomething()
		else:
			item = self.getItem()
			if item == None:
				self.compiler.warning(f'ec_value.compileValue: Cannot get the value of "{token}"')
				return None
			if item.getType() == 'symbol':
				object = self.compiler.getSymbolRecord(item.getContent())['object']
				if not object.hasRuntimeValue(): return None

			value = ECValue()
			if self.peek() == 'cat':
				value = self.getTheSomething()
			else:
				value = item

	# See if any domain has something to add to the value
		for domain in self.compiler.program.getDomains():
			value = domain.modifyValue(value)

		return value

	def compileConstant(self, token):
		value = ECValue()
		if type(token) == 'str':
			token = eval(token)
		if isinstance(token, int):
			value.setValue(type='int', content=token)
			return value
		if isinstance(token, float):
			value.setValue(type='float', content=token)
			return value
		value.setValue(type='str', content=token)
		return value
