import sys

class FatalError:
	def __init__(self, compiler, message):
		compiler.showWarnings()
		lino = compiler.tokens[compiler.index].lino
		script = compiler.script.lines[lino].strip()
		print(f'Compile error in {compiler.program.name} at line {lino + 1} ({script}): {message}')
		sys.exit()

class NoValueError(FatalError):
	def __init__(self, compiler, record):
		super().__init__(compiler, 'Variable {record["name"]} does not hold a value')

class AssertionError:
	def __init__(self, program, msg=None):
		code = program.code[program.pc]
		lino = code['lino']
		script = program.script.lines[lino].strip()
		message = f'Assertion Error in {program.name} at line {lino + 1}'
		if msg != None:
			message += f': {msg}'
		print(message)
		sys.exit()

class RuntimeError:
	def __init__(self, program, message):
		if program == None:
			sys.exit(f'Runtime Error: {message}')
		else:
			code = program.code[program.pc]
			lino = code['lino']
			script = program.script.lines[lino].strip()
			print(f'Runtime Error in {program.name} at line {lino + 1} ({script}): {message}')
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
	
class Condition():
	negate = False

class Object():
    pass
