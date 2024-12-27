import sys
from .ec_program import Program

# This is the program launcher
def Main():
	print(f'Args: {sys.argv}')
	if (len(sys.argv) > 1):
		Program(sys.argv[1:]).start()
	else:
		print('Syntax: easycoder <scriptname>')
