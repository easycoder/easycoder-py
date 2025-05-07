import json, math, hashlib, threading, os, subprocess, sys, requests, time, numbers, base64, binascii, random
from psutil import Process
from datetime import datetime, timezone
from random import randrange
from .ec_classes import FatalError, RuntimeWarning, RuntimeError, AssertionError, NoValueError, NoValueRuntimeError, Condition, Object
from .ec_handler import Handler
from .ec_timestamp import getTimestamp

class Core(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)
        self.encoding = 'utf-8'

    def getName(self):
        return 'core'
    
    def noSymbolWarning(self):
        self.warning(f'Symbol "{self.getToken()}" not found')

    #############################################################################
    # Keyword handlers

    # Arithmetic add
    # add {value} to {variable}[ giving {variable}]}
    def k_add(self, command):
        # Get the (first) value
        command['value1'] = self.nextValue()
        if self.nextToken() == 'to':
            if self.nextIsSymbol():
                symbolRecord = self.getSymbolRecord()
                if symbolRecord['hasValue']:
                    if self.peek() == 'giving':
                        # This variable must be treated as a second value
                        command['value2'] = self.getValue()
                        self.nextToken()
                        command['target'] = self.nextToken()
                        self.add(command)
                        return True
                    else:
                        # Here the variable is the target
                        command['target'] = self.getToken()
                        self.add(command)
                        return True
                self.warning(f'Core.add: Expected value holder')
            else:
                # Here we have 2 values so 'giving' must come next
                command['value2'] = self.getValue()
                if self.nextToken() == 'giving':
                    command['target'] = self.nextToken()
                    self.add(command)
                    return True
                self.warning(f'Core.add: Expected "giving"')
        return False

    def r_add(self, command):
        value1 = command['value1']
        try:
            value2 = command['value2']
        except:
            value2 = None
        target = self.getVariable(command['target'])
        if not target['hasValue']:
            self.variableDoesNotHoldAValueError(target['name'])
        targetValue = self.getSymbolValue(target)
        if targetValue == None:
            targetValue = {}
            targetValue['content'] = 0
        targetValue['type'] = 'int'
        if value2:
            v1 = int(self.getRuntimeValue(value1))
            v2 = int(self.getRuntimeValue(value2))
            targetValue['content'] = v1 + v2
        else:
#            if targetValue['type'] != 'int' and targetValue['content'] != None:
#                self.nonNumericValueError()
            v = self.getRuntimeValue(targetValue)
            v = int(v)
            v1 = int(self.getRuntimeValue(value1))
            if v1 == None:
                v1 = 0
            targetValue['content'] = v + v1
        self.putSymbolValue(target, targetValue)
        return self.nextPC()

    # Append a value to an array
    # append {value} to {array}
    def k_append(self, command):
        command['value'] = self.nextValue()
        if self.nextIs('to'):
            if self.nextIsSymbol():
                symbolRecord = self.getSymbolRecord()
                if symbolRecord['hasValue']:
                    command['target'] = symbolRecord['name']
                    self.add(command)
                    return True
                self.warning(f'Core.append: Variable {symbolRecord["name"]} does not hold a value')
        return False

    def r_append(self, command):
        value = self.getRuntimeValue(command['value'])
        target = self.getVariable(command['target'])
        val = self.getSymbolValue(target)
        content = val['content']
        if content == '':
            content = []
        content.append(value)
        val['content'] = content
        self.putSymbolValue(target, val)
        return self.nextPC()

    # Define an array
    def k_array(self, command):
        return self.compileVariable(command)

    def r_array(self, command):
        return self.nextPC()

    # Assertion
    #assert {condition} [with {message}]
    def k_assert(self, command):
        command['test'] = self.nextCondition()
        if self.peek() == 'with':
            self.nextToken()
            command['with'] = self.nextValue()
        else:
            command['with'] = None
        self.addCommand(command)
        return True

    def r_assert(self, command):
        test = self.program.condition.testCondition(command['test'])
        if test:
            return self.nextPC()
        AssertionError(self.program, self.getRuntimeValue(command['with']))

    # Begin a block
    def k_begin(self, command):
        if self.nextToken() == 'end':
            cmd = {}
            cmd['domain'] = 'core'
            cmd['keyword'] = 'end'
            cmd['debug'] = True
            cmd['lino'] = command['lino']
            self.addCommand(cmd)
            return self.nextPC()
        else:
            return self.compileFromHere(['end'])

    # Clear (set false)
    # clear {variable}
    def k_clear(self, command):
        if self.nextIsSymbol():
            target = self.getSymbolRecord()
            if target['hasValue']:
                command['target'] = target['name']
                self.add(command)
                return True
        return False

    def r_clear(self, command):
        target = self.getVariable(command['target'])
        val = {}
        val['type'] = 'boolean'
        val['content'] = False
        self.putSymbolValue(target, val)
        return self.nextPC()

    # Close a file
    # close {file}
    def k_close(self, command):
        if self.nextIsSymbol():
            fileRecord = self.getSymbolRecord()
            if fileRecord['keyword'] == 'file':
                command['file'] = fileRecord['name']
                self.add(command)
                return True
        return False

    def r_close(self, command):
        fileRecord = self.getVariable(command['file'])
        fileRecord['file'].close()
        return self.nextPC()

    #Create directory
    # create directory {name}
    def k_create(self, command):
        if self.nextIs('directory'):
            command['item'] = 'directory'
            command['path'] = self.nextValue()
            self.add(command)
            return True
        return False

    def r_create(self, command):
        if command['item'] == 'directory':
            path = self.getRuntimeValue(command['path'])
            if not os.path.exists(path):
                os.makedirs(path)
        return self.nextPC()

    # Debug the script
    def k_debug(self, command):
        token = self.peek()
        if token in ['step', 'stop', 'program', 'custom']:
            command['mode'] = token
            self.nextToken()
        elif token == 'stack':
            command['mode'] = self.nextToken()
            if (self.nextIsSymbol()):
                command['stack'] = self.getToken()
                if self.peek() == 'as':
                    self.nextToken()
                    command['as'] = self.nextValue()
                else:
                    command['as'] = 'Stack'
            else:
                return False
        else:
            command['mode'] = None
        self.add(command)
        return True

    def r_debug(self, command):
        if command['mode'] == 'step':
            self.program.debugStep = True
        elif command['mode'] == 'stop':
            self.program.debugStep = False
        elif command['mode'] == 'program':
            for item in self.code:
                print(json.dumps(item, indent = 2))
        elif command['mode'] == 'stack':
            stackRecord = self.getVariable(command['stack'])
            value = self.getSymbolValue(stackRecord)
            print(f'{self.getRuntimeValue(command["as"])}:',json.dumps(self.getSymbolValue(stackRecord), indent = 2))
        elif command['mode'] == 'custom':
            # Custom debugging code goes in here
            record = self.getVariable('Script')
            print('(Debug) Script:',record)
            value = self.getRuntimeValue(record)
            print('(Debug) Value:',value)
            pass
        return self.nextPC()

    # Decrement a variable
    # decrement {variable}
    def k_decrement(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['hasValue']:
                command['target'] = self.getToken()
                self.add(command)
                return True
            self.warning(f'Core.decrement: Variable {symbolRecord["name"]} does not hold a value')
        return False

    def r_decrement(self, command):
        return self.incdec(command, '-')

    # Delete a file or a property
    # delete {filename}
    # delete property {value} of {variable}
    # delete element {name} of {variable}
    def k_delete(self, command):
        token = self.nextToken( )
        command['type'] = token
        if token == 'file':
            command['filename'] = self.nextValue()
            self.add(command)
            return True
        elif token in ['property', 'element']:
            command['key'] = self.nextValue()
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['hasValue']:
                    command['var'] = record['name']
                    self.add(command)
                    return True
                NoValueError(self.compiler, record)
            self.warning(f'Core.delete: variable expected; got {self.getToken()}')
        else:
            self.warning(f'Core.delete: "file", "property" or "element" expected; got {token}')
        return False

    def r_delete(self, command):
        type = command['type']
        if type == 'file':
            filename = self.getRuntimeValue(command['filename'])
            if os.path.isfile(filename):
                print('Deleting',filename)
                os.remove(filename)
        elif type == 'property':
            key = self.getRuntimeValue(command['key'])
            symbolRecord = self.getVariable(command['var'])
            value = self.getSymbolValue(symbolRecord)
            content = value['content']
            content.pop(key, None)
            value['content'] = content
            self.putSymbolValue(symbolRecord, value)
        elif type == 'element':
            key = self.getRuntimeValue(command['key'])
            symbolRecord = self.getVariable(command['var'])
            value = self.getSymbolValue(symbolRecord)
            content = value['content']
            content.remove(key)
            value['content'] = content
            self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    # Arithmetic division
    # divide {variable} by {value}[ giving {variable}]}
    def k_divide(self, command):
        # Get the (first) value
        command['value1'] = self.nextValue()
        if self.nextToken() == 'by':
            command['value2'] = self.nextValue()
            if self.peek() == 'giving':
                self.nextToken()
                if (self.nextIsSymbol()):
                    command['target'] = self.getToken()
                    self.add(command)
                    return True
                FatalError(self.compiler, 'Symbol expected')
            else:
                # First value must be a variable
                if command['value1']['type'] == 'symbol':
                    command['target'] = command['value1']['name']
                    self.add(command)
                    return True
                FatalError(self.compiler, 'First value must be a variable')
        return False

    def r_divide(self, command):
        value1 = command['value1']
        try:
            value2 = command['value2']
        except:
            value2 = None
        target = self.getVariable(command['target'])
        if not target['hasValue']:
            self.variableDoesNotHoldAValueError(target['name'])
            return None
        value = self.getSymbolValue(target)
        if value == None:
            value = {}
        value['type'] = 'int'
        if value2:
            v1 = int(self.getRuntimeValue(value1))
            v2 = int(self.getRuntimeValue(value2))
            value['content'] = int(v1/v2)
        else:
            if value['type'] != 'int' and value['content'] != None:
                self.nonNumericValueError(self.compiler, command['lino'])
            v = int(self.getRuntimeValue(value))
            v1 = int(self.getRuntimeValue(value1))
            value['content'] = int(v/v1)
        self.putSymbolValue(target, value)
        return self.nextPC()

    # Dummy command for testing
    def k_dummy(self, command):
        self.add(command)
        return True

    def r_dummy(self, command):
        return self.nextPC()

    # Match a begin
    def k_end(self, command):
        self.add(command)
        return True

    def r_end(self, command):
        return self.nextPC()

    # Exit the script
    def k_exit(self, command):
        self.add(command)
        return True

    def r_exit(self, command):
        if self.program.graphics != None:
            self.program.graphics.force_exit()
        return -1

    # Declare a file variable
    def k_file(self, command):
        return self.compileVariable(command, False)

    def r_file(self, command):
        return self.nextPC()

    # Fork to a label
    def k_fork(self, command):
        if self.peek() == 'to':
            self.nextToken()
        command['fork'] = self.nextToken()
        self.add(command)
        return True

    def r_fork(self, command):
        next = self.nextPC()
        label = command['fork']
        try:
            label = self.symbols[label + ':']
        except:
            RuntimeError(self.program, f'There is no label "{label + ":"}"')
            return None
        self.run(label)
        return next

    # Issue a REST GET request
    # get {variable) from {url} [or {command}]
    def k_get(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['hasValue']:
                command['target'] = self.getToken()
            else:
                NoValueError(self.compiler, symbolRecord)
        if self.nextIs('from'):
            if self.nextIs('url'):
                url = self.nextValue()
                if url != None:
                    command['url'] = url
                    command['or'] = None
                    get = self.getPC()
                    if self.peek() == 'timeout':
                        self.nextToken()
                        command['timeout'] = self.nextValue()
                    else:
                        timeout = {}
                        timeout['type'] = 'int'
                        timeout['content'] = 5
                        command['timeout'] = timeout
                    self.addCommand(command)
                    if self.peek() == 'or':
                        self.nextToken()
                        self.nextToken()
                        # Add a 'goto' to skip the 'or'
                        cmd = {}
                        cmd['lino'] = command['lino']
                        cmd['domain'] = 'core'
                        cmd['keyword'] = 'gotoPC'
                        cmd['goto'] = 0
                        cmd['debug'] = False
                        skip = self.getPC()
                        self.addCommand(cmd)
                        # Process the 'or'
                        self.getCommandAt(get)['or'] = self.getPC()
                        self.compileOne()
                        # Fixup the skip
                        self.getCommandAt(skip)['goto'] = self.getPC()
                    return True
        return False

    def r_get(self, command):
        global errorCode, errorReason
        retval = {}
        retval['type'] = 'text'
        retval['numeric'] = False
        url = self.getRuntimeValue(command['url'])
        target = self.getVariable(command['target'])
        response = json.loads('{}')
        try:
            timeout = self.getRuntimeValue(command['timeout'])
            response = requests.get(url, auth = ('user', 'pass'), timeout=timeout)
            if response.status_code >= 400:
                errorCode = response.status_code
                errorReason = response.reason
                if command['or'] != None:
                    return command['or']
                else:
                    RuntimeError(self.program, f'Error code {errorCode}: {errorReason}')
        except Exception as e:
            errorReason = str(e)
            if command['or'] != None:
                return command['or']
            else:
                RuntimeError(self.program, f'Error: {errorReason}')
        retval['content'] = response.text
        self.program.putSymbolValue(target, retval)
        return self.nextPC()

    # Go to a label
    def k_go(self, command):
        if self.peek() == 'to':
            self.nextToken()
            return self.k_goto(command)

    def k_goto(self, command):
        command['keyword'] = 'goto'
        command['goto'] = self.nextToken()
        self.add(command)
        return True

    def r_goto(self, command):
        label = f'{command["goto"]}:'
        try:
            if self.symbols[label]:
                return self.symbols[label]
        except:
            pass
        RuntimeError(self.program, f'There is no label "{label}"')
        return None

    def r_gotoPC(self, command):
        return command['goto']

    # Call a subroutine
    def k_gosub(self, command):
        if self.peek() == 'to':
            self.nextToken()
        command['gosub'] = self.nextToken()
        self.add(command)
        return True

    def r_gosub(self, command):
        label = command['gosub'] + ':'
        address = self.symbols[label]
        if address != None:
            self.stack.append(self.nextPC())
            return address
        RuntimeError(self.program, f'There is no label "{label + ":"}"')
        return None

    # if <condition> <action> [else <action>]
    def k_if(self, command):
        command['condition'] = self.nextCondition()
        self.addCommand(command)
        self.nextToken()
        pcElse = self.getPC()
        cmd = {}
        cmd['lino'] = command['lino']
        cmd['domain'] = 'core'
        cmd['keyword'] = 'gotoPC'
        cmd['goto'] = 0
        cmd['debug'] = False
        self.addCommand(cmd)
        # Get the 'then' code
        self.compileOne()
        if self.peek() == 'else':
            self.nextToken()
            # Add a 'goto' to skip the 'else'
            pcNext = self.getPC()
            cmd = {}
            cmd['lino'] = command['lino']
            cmd['domain'] = 'core'
            cmd['keyword'] = 'gotoPC'
            cmd['goto'] = 0
            cmd['debug'] = False
            self.addCommand(cmd)
            # Fixup the link to the 'else' branch
            self.getCommandAt(pcElse)['goto'] = self.getPC()
            # Process the 'else' branch
            self.nextToken()
            self.compileOne()
            # Fixup the pcNext 'goto'
            self.getCommandAt(pcNext)['goto'] = self.getPC()
        else:
            # We're already at the next command
            self.getCommandAt(pcElse)['goto'] = self.getPC()
        return True

    def r_if(self, command):
        test = self.program.condition.testCondition(command['condition'])
        if test:
            self.program.pc += 2
        else:
            self.program.pc += 1
        return self.program.pc

    def k_import(self, command):
        if self.peek() == 'plugin':
            # Import a plugin
            self.nextToken()
            clazz = self.nextToken()
            if self.nextIs('from'):
                source = self.nextToken()
                self.program.importPlugin(f'{source}:{clazz}')
                return True
            return False
        else:
            # Import one or more variables
            imports = []
            while True:
                keyword = self.nextToken()
                name = self.nextToken()
                item = [keyword, name]
                imports.append(item)
                self.symbols[name] = self.getPC()
                variable = {}
                variable['domain'] = None
                variable['name'] = name
                variable['keyword'] = keyword
                variable['import'] = None
                self.addCommand(variable)
                if self.peek() != 'and':
                    break
                self.nextToken()
            command['imports'] = json.dumps(imports)
            self.add(command)
            return True

    def r_import(self, command):
        exports = self.program.exports
        imports = json.loads(command['imports'])
        if len(imports) < len(exports):
            RuntimeError(self.program, 'Too few imports')
        elif len(imports) > len(exports):
            RuntimeError(self.program, 'Too many imports')
        for n in range(0, len(imports)):
            exportRecord = exports[n]
            exportKeyword = exportRecord['keyword']
            name = imports[n][1]
            symbolRecord = self.program.getSymbolRecord(name)
            symbolKeyword = symbolRecord['keyword']
            if symbolKeyword != exportKeyword:
                RuntimeError(self.program, f'Import {n} ({symbolKeyword}) does not match export {n} ({exportKeyword})')
            symbolRecord['import'] = exportRecord
        return self.nextPC()

    # Increment a variable
    def k_increment(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['hasValue']:
                command['target'] = self.getToken()
                self.add(command)
                return True
            self.warning(f'Core.increment: Variable {symbolRecord["name"]} does not hold a value')
        return False

    def r_increment(self, command):
        return self.incdec(command, '+')

    # Index to a specified element in a variable
    # index {variable} to {value}
    def k_index(self, command):
        # get the variable
        if self.nextIsSymbol():
            command['target'] = self.getToken()
            if self.nextToken() == 'to':
                # get the value
                command['value'] = self.nextValue()
                self.add(command)
                return True
        return False

    def r_index(self, command):
        symbolRecord = self.getVariable(command['target'])
        symbolRecord['index'] = self.getRuntimeValue(command['value'])
        return self.nextPC()

    # Initialise a stack, array or object
    def k_init(self, command):
        # get the variable
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            keyword = symbolRecord['keyword']
            if keyword in ['stack','array', 'object']:
                command['keyword'] = keyword
                command['target'] = symbolRecord['name']
                return True
        return False

    def r_init(self, command):
        symbolRecord = self.getVariable(command['target'])
        keyword = command['keyword']
        if keyword in ['stack', 'array']:
            self.putSymbolValue(symbolRecord, json.loads('[]'))
        elif keyword == 'object':
            self.putSymbolValue(symbolRecord, json.loads('{}'))
        else:
            RuntimeError(self.program, f"Inappropriate variable type '{keyword}'")
        return self.nextPC()

    # Inout a value from the terminal
    # input {variable} [with {prompt}]
    def k_input(self, command):
        # get the variable
        if self.nextIsSymbol():
            command['target'] = self.getToken()
            value = {}
            value['type'] = 'text'
            value['numeric'] = 'false'
            value['content'] = ': '
            command['prompt'] = value
            if self.peek() == 'with':
                self.nextToken()
                command['prompt'] = self.nextValue()
            self.add(command)
            return True
        return False

    def r_input(self, command):
        symbolRecord = self.getVariable(command['target'])
        prompt = command['prompt']['content']
        value = {}
        value['type'] = 'text'
        value['numeric'] = False
        value['content'] = prompt+input(prompt)
        self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    # 1 Load a plugin. This is done at compile time.
    # 2 Load text from a file
    def k_load(self, command):
        self.nextToken()
        if self.tokenIs('plugin'):
            clazz = self.nextToken()
            if self.nextIs('from'):
                source = self.nextToken()
                self.program.importPlugin(f'{source}:{clazz}')
                return True
        elif self.isSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['hasValue']:
                command['target'] = symbolRecord['name']
                if self.nextIs('from'):
                    command['file'] = self.nextValue()
                    self.add(command)
                    return True
        else:
            FatalError(self.compiler, f'I don\'t understand \'{self.getToken()}\'')
        return False

    def r_load(self, command):
        target = self.getVariable(command['target'])
        filename = self.getRuntimeValue(command['file'])
        try:
            with open(filename) as f: content = f.read()
        except:
            content = ''
        try:
            if filename.endswith('.json'): content = json.loads(content)
        except:
            RuntimeError(self.program, 'Bad or null JSON string')
        value = {}
        value['type'] = 'text'
        value['content'] = content
        self.putSymbolValue(target, value)
        return self.nextPC()

    # Lock a variable
    def k_lock(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            command['target'] = symbolRecord['name']
            self.add(command)
            return True
        return False

    def r_lock(self, command):
        target = self.getVariable(command['target'])
        target['locked'] = True
        return self.nextPC()

    # Log a message
    def k_log(self, command):
        command['log'] = True
        command['keyword'] = 'print'
        return self.k_print(command)

    # Declare a module variable
    def k_module(self, command):
        return self.compileVariable(command)

    def r_module(self, command):
        return self.nextPC()

    # Arithmetic multiply
    # multiply {variable} by {value}[ giving {variable}]}
    def k_multiply(self, command):
        # Get the (first) value
        command['value1'] = self.nextValue()
        if self.nextToken() == 'by':
            command['value2'] = self.nextValue()
            if self.peek() == 'giving':
                self.nextToken()
                if (self.nextIsSymbol()):
                    command['target'] = self.getToken()
                    self.add(command)
                    return True
                FatalError(self.compiler, 'Symbol expected')
            else:
                # First value must be a variable
                if command['value1']['type'] == 'symbol':
                    command['target'] = command['value1']['name']
                    self.add(command)
                    return True
                FatalError(self.compiler, 'First value must be a variable')
        return False

    def r_multiply(self, command):
        value1 = command['value1']
        try:
            value2 = command['value2']
        except:
            value2 = None
        target = self.getVariable(command['target'])
        if not target['hasValue']:
            self.variableDoesNotHoldAValueError(target['name'])
            return None
        value = self.getSymbolValue(target)
        if value == None:
            value = {}
        value['type'] = 'int'
        if value2:
            v1 = int(self.getRuntimeValue(value1))
            v2 = int(self.getRuntimeValue(value2))
            value['content'] = v1*v2
        else:
            if value['type'] != 'int' and value['content'] != None:
                self.nonNumericValueError()
                return None
            v = int(self.getRuntimeValue(value))
            v1 = int(self.getRuntimeValue(value1))
            value['content'] = v*v1
        self.putSymbolValue(target, value)
        return self.nextPC()

    # Negate a variable
    def k_negate(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['hasValue']:
                command['target'] = self.getToken()
                self.add(command)
                return True
            self.warning(f'Core.negate: Variable {symbolRecord["name"]} does not hold a value')
        return False

    def r_negate(self, command):
        symbolRecord = self.getVariable(command['target'])
        if not symbolRecord['hasValue']:
            NoValueRuntimeError(self.program, symbolRecord)
            return None
        value = self.getSymbolValue(symbolRecord)
        if value == None:
            RuntimeError(self.program, f'{symbolRecord["name"]} has not been initialised')
        value['content'] *= -1
        self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    # Define an object variable
    def k_object(self, command):
        return self.compileVariable(command)

    def r_object(self, command):
        return self.nextPC()

    # on message {action}
    def k_on(self, command):
        if self.nextIs('message'):
            self.nextToken()
            command['goto'] = 0
            self.add(command)
            cmd = {}
            cmd['domain'] = 'core'
            cmd['lino'] = command['lino']
            cmd['keyword'] = 'gotoPC'
            cmd['goto'] = 0
            cmd['debug'] = False
            self.addCommand(cmd)
            # Add the action and a 'stop'
            self.compileOne()
            cmd = {}
            cmd['domain'] = 'core'
            cmd['lino'] = command['lino']
            cmd['keyword'] = 'stop'
            cmd['debug'] = False
            self.addCommand(cmd)
            # Fixup the link
            command['goto'] = self.getPC()
            return True
        return False

    def r_on(self, command):
        self.program.onMessage(self.nextPC()+1)
        return command['goto']

    # Open a file
    # open {file} for reading/writing/appending
    def k_open(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            command['target'] = symbolRecord['name']
            command['path'] = self.nextValue()
            if symbolRecord['keyword'] == 'file':
                if self.peek() == 'for':
                    self.nextToken()
                    token = self.nextToken()
                    if token == 'appending':
                        mode = 'a'
                    elif token == 'reading':
                        mode = 'r'
                    elif token == 'writing':
                        mode = 'w'
                    else:
                        FatalError(self.compiler, 'Unknown file open mode {self.getToken()}')
                        return False
                    command['mode'] = mode
                else:
                    command['mode'] = 'r'
                self.add(command)
                return True
            else:
                FatalError(self.compiler, f'Variable "{self.getToken()}" is not a file')
        else:
            self.warning(f'Core.open: Variable "{self.getToken()}" not declared')
        return False

    def r_open(self, command):
        symbolRecord = self.getVariable(command['target'])
        path = self.getRuntimeValue(command['path'])
        if command['mode'] == 'r' and os.path.exists(path) or command['mode'] != 'r':
            symbolRecord['file'] = open(path, command['mode'])
            return self.nextPC()
        RuntimeError(self.program, f"File {path} does not exist")

    # Pop a value from a stack
    # pop {variable} from {stack}
    def k_pop(self, command):
        if (self.nextIsSymbol()):
            symbolRecord = self.getSymbolRecord()
            command['target'] = symbolRecord['name']
            if self.peek() == 'from':
                self.nextToken()
                if self.nextIsSymbol():
                    command['from'] = self.getToken()
                    self.add(command)
                    return True
        return False

    def r_pop(self, command):
        symbolRecord = self.getVariable(command['target'])
        if not symbolRecord['hasValue']:
            NoValueRuntimeError(self.program, symbolRecord)
        stackRecord = self.getVariable(command['from'])
        stack = self.getSymbolValue(stackRecord)
        v = stack.pop()
        self.putSymbolValue(stackRecord, stack)
        value = {}
        value['type'] = 'int' if type(v) == int else 'text'
        value['content'] = v
        self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    # Perform an HTTP POST
    # post {value} to {url} [giving {variable}] [or {command}]
    def k_post(self, command):
        if self.nextIs('to'):
            command['value'] = self.getConstant('')
            command['url'] = self.getValue()
        else:
            command['value'] = self.getValue()
            if self.nextIs('to'):
                command['url'] = self.nextValue()
        if self.peek() == 'giving':
            self.nextToken()
            command['result'] = self.nextToken()
        else:
            command['result'] = None
        command['or'] = None
        post = self.getPC()
        self.addCommand(command)
        if self.peek() == 'or':
            self.nextToken()
            self.nextToken()
            # Add a 'goto' to skip the 'or'
            cmd = {}
            cmd['lino'] = command['lino']
            cmd['domain'] = 'core'
            cmd['keyword'] = 'gotoPC'
            cmd['goto'] = 0
            cmd['debug'] = False
            skip = self.getPC()
            self.addCommand(cmd)
            # Process the 'or'
            self.getCommandAt(post)['or'] = self.getPC()
            self.compileOne()
            # Fixup the skip
            self.getCommandAt(skip)['goto'] = self.getPC()
        return True

    def r_post(self, command):
        global errorCode, errorReason
        retval = {}
        retval['type'] = 'text'
        retval['numeric'] = False
        value = self.getRuntimeValue(command['value'])
        url = self.getRuntimeValue(command['url'])
        try:
            response = requests.post(url, value, timeout=5)
            retval['content'] = response.text
            if response.status_code >= 400:
                errorCode = response.status_code
                errorReason = response.reason
                if command['or'] != None:
                    print(f'Error {errorCode} {errorReason}: Running the "or" clause')
                    return command['or']
                else:
                    RuntimeError(self.program, f'Error code {errorCode}: {errorReason}')
        except Exception as e:
            errorReason = str(e)
            if command['or'] != None:
                print(f'Exception "{errorReason}": Running the "or" clause')
                return command['or']
            else:
                RuntimeError(self.program, f'Error: {errorReason}')
        if command['result'] != None:
            result = self.getVariable(command['result'])
            self.program.putSymbolValue(result, retval)
        return self.nextPC()

    # Print a value
    def k_print(self, command):
        value = self.nextValue()
        if value != None:
            command['value'] = value
            self.add(command)
            return True
        FatalError(self.compiler, 'I can\'t print this value')
        return False

    def r_print(self, command):
        value = self.getRuntimeValue(command['value'])
        program = command['program']
        code = program.code[program.pc]
        lino = str(code['lino'] + 1)
        while len(lino) < 5: lino = f' {lino}'
        if value == None: value = '<empty>'
        if 'log' in command:
            print(f'{datetime.now().time()}:{lino}-> {value}')
        else:
            print(value)
        return self.nextPC()

    # Push a value onto a stack
    # push {value} to/onto {stack}
    def k_push(self, command):
        value = self.nextValue()
        command['value'] = value
        peekValue = self.peek()
        if peekValue in ['onto', 'to']:
            self.nextToken()
            if self.nextIsSymbol():
                symbolRecord = self.getSymbolRecord()
                command['to'] = symbolRecord['name']
                self.add(command)
                return True
        return False

    def r_push(self, command):
        value = self.getRuntimeValue(command['value'])
        stackRecord = self.getVariable(command['to'])
        if stackRecord['keyword'] != 'stack':
            RuntimeError(self.program, f'{stackRecord["name"]} is not a stack')
            return -1
        stack = stackRecord['value'][stackRecord['index']]
        if stack == None:
            stack = [value]
        else:
            stack.append(value)
        self.putSymbolValue(stackRecord, stack)
        return self.nextPC()

    # put {value} into {variable}
    def k_put(self, command):
        value = self.nextValue()
        if value != None:
            command['value'] = value
            if self.nextIs('into'):
                if self.nextIsSymbol():
                    symbolRecord = self.getSymbolRecord()
                    command['target'] = symbolRecord['name']
                    if 'hasValue' in symbolRecord and symbolRecord['hasValue'] == False:
                        FatalError(self.compiler, f'Symbol {symbolRecord["name"]} is not a value holder')
                    else:
                        self.add(command)
                        return True
                else:
                    FatalError(self.compiler, f'Symbol {self.getToken()} is not a variable')
        return False

    def r_put(self, command):
        value = self.evaluate(command['value'])
        if value == None:
            return -1
        symbolRecord = self.getVariable(command['target'])
        if not symbolRecord['hasValue']:
            NoValueRuntimeError(self.program, symbolRecord)
            return -1
        self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    # Read from a file
    # read {variable} from {file}
    def k_read(self, command):
        if self.peek() == 'line':
            self.nextToken()
            command['line'] = True
        else:
            command['line'] = False
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['hasValue']:
                if self.peek() == 'from':
                    self.nextToken()
                    if self.nextIsSymbol():
                        fileRecord = self.getSymbolRecord()
                        if fileRecord['keyword'] == 'file':
                            command['target'] = symbolRecord['name']
                            command['file'] = fileRecord['name']
                            self.add(command)
                            return True
            FatalError(self.compiler, f'Symbol "{symbolRecord["name"]}" is not a value holder')
            return False
        FatalError(self.compiler, f'Symbol "{self.getToken()}" has not been declared')
        return False

    def r_read(self, command):
        symbolRecord = self.getVariable(command['target'])
        fileRecord = self.getVariable(command['file'])
        line = command['line']
        file = fileRecord['file']
        if file.mode == 'r':
            value = {}
            content = file.readline().split('\n')[0] if line else file.read()
            value['type'] = 'text'
            value['numeric'] = False
            value['content'] = content
            self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    # Replace a substring
    #replace {value} with {value} in {variable}
    def k_replace(self, command):
        original = self.nextValue()
        if self.peek() == 'with':
            self.nextToken()
            replacement = self.nextValue()
            if self.nextIs('in'):
                if self.nextIsSymbol():
                    templateRecord = self.getSymbolRecord()
                    command['original'] = original
                    command['replacement'] = replacement
                    command['target'] = templateRecord['name']
                    self.add(command)
                    return True
        return False

    def r_replace(self, command):
        templateRecord = self.getVariable(command['target'])
        content = self.getSymbolValue(templateRecord)['content']
        original = self.getRuntimeValue(command['original'])
        replacement = self.getRuntimeValue(command['replacement'])
        content = content.replace(original, str(replacement))
        value = {}
        value['type'] = 'text'
        value['numeric'] = False
        value['content'] = content
        self.putSymbolValue(templateRecord, value)
        return self.nextPC()

    # Release the parent script
    def k_release(self, command):
        if self.nextIs('parent'):
            self.add(command)
        return True

    def r_release(self, command):
        self.program.releaseParent()
        return self.nextPC()

    # Return from subroutine
    def k_return(self, command):
        self.add(command)
        return True

    def r_return(self, command):
        return self.stack.pop()

    # Compile and run a script
    # run {path} [as {module}] [with {variable} [and {variable}...]]
    def k_run(self, command):
        try:
            command['path'] = self.nextValue()
        except Exception as e:
            self.warning(f'Core.run: Path expected')
            return False
        if self.nextIs('as'):
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'module':
                    name = record['name']
                    command['module'] = name
                else: RuntimeError(self.program, f'Symbol \'name\' is not a module')
            else: RuntimeError(self.program, 'Module name expected after \'as\'')
        else: RuntimeError(self.program, '\'as {module name}\' expected')
        exports = []
        if self.peek() == 'with':
            self.nextToken()
            while True:
                name = self.nextToken()
                record = self.getSymbolRecord()
                exports.append(name)
                if self.peek() != 'and':
                    break
                self.nextToken()
        command['exports'] = json.dumps(exports)
        self.add(command)
        return True

    def r_run(self, command):
        module = self.getVariable(command['module'])
        path = self.getRuntimeValue(command['path'])
        exports = json.loads(command['exports'])
        for n in range(0, len(exports)):
            exports[n] = self.getVariable(exports[n])
        module['path'] = path
        parent = Object()
        parent.program = self.program
        parent.pc = self.nextPC()
        parent.waiting = True
        p = self.program.__class__
        p(path).start(parent, module, exports)
        return 0

    # Provide a name for the script
    def k_script(self, command):
        self.program.name = self.nextToken()
        return True

    # Save a value to a file
    def k_save(self, command):
        command['content'] = self.nextValue()
        if self.nextIs('to'):
            command['file'] = self.nextValue()
            self.add(command)
            return True
        return False

    def r_save(self, command):
        content = self.getRuntimeValue(command['content'])
        filename = self.getRuntimeValue(command['file'])
        if filename.endswith('.json'): content = json.dumps(content)
        with open(filename, 'w') as f: f.write(content)
        return self.nextPC()

    # Send a message to a module
    def k_send(self, command):
        command['message'] = self.nextValue()
        if self.nextIs('to'):
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'module':
                    command['module'] = record['name']
                    self.add(command)
                    return True
        return False

    def r_send(self, command):
        message = self.getRuntimeValue(command['message'])
        module = self.getVariable(command['module'])
        module['child'].handleMessage(message)
        return self.nextPC()

    # Set a value
    # set {variable}
    # set the elements of {variable} to {value}
    # set element/property of {variable} to {value}
    def k_set(self, command):
        if self.nextIsSymbol():
            target = self.getSymbolRecord()
            if target['hasValue']:
                command['type'] = 'set'
                command['target'] = target['name']
                self.add(command)
                return True
            return False

        token = self.getToken()
        if token == 'the':
            token = self.nextToken()
        command['type'] = token

        if token == 'elements':
            self.nextToken()
            if self.peek() == 'of':
                self.nextToken()
            if self.nextIsSymbol():
                command['name'] = self.getToken()
                if self.peek() == 'to':
                    self.nextToken()
                command['elements'] = self.nextValue()
                self.add(command)
                return True

        elif token == 'encoding':
            if self.nextIs('to'):
                command['encoding'] = self.nextValue()
                self.add(command)
                return True

        elif token == 'property':
            command['name'] = self.nextValue()
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    command['target'] = self.getSymbolRecord()['name']
                    if self.nextIs('to'):
                        value = self.nextValue()
                        if value == None:
                            FatalError(self.compiler, 'Unable to get a value')
                        command['value'] = value
                        self.add(command)
                        return True

        elif token == 'element':
            command['index'] = self.nextValue()
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    command['target'] = self.getSymbolRecord()['name']
                    if self.nextIs('to'):
                        command['value'] = self.nextValue()
                        self.add(command)
                        return True
        return False

    def r_set(self, command):
        cmdType = command['type']
        if cmdType == 'set':
            target = self.getVariable(command['target'])
            val = {}
            val['type'] = 'boolean'
            val['content'] = True
            self.putSymbolValue(target, val)
            return self.nextPC()

        elif cmdType == 'elements':
            symbolRecord = self.getVariable(command['name'])
            elements = self.getRuntimeValue(command['elements'])
            currentElements = symbolRecord['elements']
            currentValue = symbolRecord['value']
            if currentValue == None:
                currentValue = [None]
            newValue = [None] * elements
            if elements > currentElements:
                for index, value in enumerate(currentValue):
                    newValue[index] = value
            elif elements < currentElements:
                for index, value in enumerate(currentValue):
                    if index < elements:
                        newValue[index] = value
            symbolRecord['elements'] = elements
            symbolRecord['value'] = newValue
            symbolRecord['index'] = 0
            return self.nextPC()

        elif cmdType == 'element':
            value = self.getRuntimeValue(command['value'])
            index = self.getRuntimeValue(command['index'])
            target = self.getVariable(command['target'])
            val = self.getSymbolValue(target)
            content = val['content']
            if content == '':
                content = []
            # else:
            # 	content = json.loads(content)
            content[index] = value
            val['content'] = content
            self.putSymbolValue(target, val)
            return self.nextPC()

        elif cmdType == 'encoding':
            self.encoding = self.getRuntimeValue(command['encoding'])
            return self.nextPC()

        elif cmdType == 'property':
            value = self.getRuntimeValue(command['value'])
            name = self.getRuntimeValue(command['name'])
            target = command['target']
            targetVariable = self.getVariable(target)
            val = self.getSymbolValue(targetVariable)
            try:
                content = val['content']
            except:
                RuntimeError(self.program, f'{target} is not an object')
            if content == '':
                content = {}
            try:
                content[name] = value
            except:
                RuntimeError(self.program, f'{target} is not an object')
            val['content'] = content
            self.putSymbolValue(targetVariable, val)
            return self.nextPC()

    # Shuffle a list
    def k_shuffle(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['hasValue']:
                command['target'] = self.getToken()
                self.add(command)
                return True
            self.warning(f'Core.negate: Variable {symbolRecord["name"]} does not hold a value')
        return False

    def r_shuffle(self, command):
        symbolRecord = self.getVariable(command['target'])
        if not symbolRecord['hasValue']:
            NoValueRuntimeError(self.program, symbolRecord)
            return None
        value = self.getSymbolValue(symbolRecord)
        if value == None:
            RuntimeError(self.program, f'{symbolRecord["name"]} has not been initialised')
        content = value['content']
        if isinstance(content, list):
            random.shuffle(content)
            value['content'] = content
            self.putSymbolValue(symbolRecord, value)
            return self.nextPC()
        RuntimeError(self.program, f'{symbolRecord["name"]} is not a list')

    # Split a string into a variable with several elements
    # split {variable} on {value}
    def k_split(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if symbolRecord['hasValue']:
                command['target'] = symbolRecord['name']
                value = {}
                value['type'] = 'text'
                value['numeric'] = 'false'
                value['content'] = '\n'
                command['on'] = value
                if self.peek() == 'on':
                    self.nextToken()
                    if self.peek() == 'tab':
                        value['content'] = '\t'
                        self.nextToken()
                    else:
                        command['on'] = self.nextValue()
                self.add(command)
                return True
        else: self.noSymbolWarning()
        return False

    def r_split(self, command):
        target = self.getVariable(command['target'])
        value = self.getSymbolValue(target)
        content = value['content'].split(self.getRuntimeValue(command['on']))
        elements = len(content)
        target['elements'] = elements
        target['value'] = [None] * elements

        for index, item in enumerate(content):
            element = {}
            element['type'] = 'text'
            element['numeric'] = 'false'
            element['content'] = item
            target['value'][index] = element

        return self.nextPC()

    # Declare a stack variable
    def k_stack(self, command):
        return self.compileVariable(command)

    def r_stack(self, command):
        return self.nextPC()

    # Stop the current execution thread
    def k_stop(self, command):
        self.add(command)
        return True

    def r_stop(self, command):
        return 0

    # Issue a system call
    # system {command}
    def k_system(self, command):
        background = False
        token = self.nextToken()
        if token == 'background':
            self.nextToken()
            background = True
        value = self.getValue()
        if value != None:
            command['value'] = value
            command['background'] = background
            self.add(command)
            return True
        FatalError(self.compiler, 'I can\'t give this command')
        return False

    def r_system(self, command):
        value = self.getRuntimeValue(command['value'])
        if value != None:
            if command['background']:
                subprocess.Popen(["sh",value,"&"])
            else:
                os.system(value)
            return self.nextPC()

    # Arithmetic subtraction
    # take {value} from {variable}[ giving {variable}]}
    def k_take(self, command):
        # Get the (first) value
        command['value1'] = self.nextValue()
        if self.nextToken() == 'from':
            if self.nextIsSymbol():
                symbolRecord = self.getSymbolRecord()
                if symbolRecord['hasValue']:
                    if self.peek() == 'giving':
                        # This variable must be treated as a second value
                        command['value2'] = self.getValue()
                        self.nextToken()
                        command['target'] = self.nextToken()
                        self.add(command)
                        return True
                    else:
                        # Here the variable is the target
                        command['target'] = self.getToken()
                        self.add(command)
                        return True
                self.warning(f'Core.take: Expected value holder')
            else:
                # Here we have 2 values so 'giving' must come next
                command['value2'] = self.getValue()
                if self.nextToken() == 'giving':
                    if (self.nextIsSymbol()):
                        command['target'] = self.getToken()
                        self.add(command)
                        return True
                    else:
                        FatalError(self.compiler, f'\'{self.getToken()}\' is not a symbol')
                else:
                    self.warning(f'Core.take: Expected "giving"')
        return False

    def r_take(self, command):
        value1 = command['value1']
        try:
            value2 = command['value2']
        except:
            value2 = None
        target = self.getVariable(command['target'])
        if not target['hasValue']:
            self.variableDoesNotHoldAValueError(target['name'])
            return None
        value = self.getSymbolValue(target)
        if value == None:
            value = {}
        value['type'] = 'int'
        if value2:
            v1 = int(self.getRuntimeValue(value1))
            v2 = int(self.getRuntimeValue(value2))
            value['content'] = v2-v1
        else:
            v = int(self.getRuntimeValue(value))
            v1 = int(self.getRuntimeValue(value1))
            value['content'] = v-v1
        self.putSymbolValue(target, value)
        return self.nextPC()

    # Toggle a boolean value
    def k_toggle(self, command):
        if self.nextIsSymbol():
            target = self.getSymbolRecord()
            if target['hasValue']:
                command['target'] = target['name']
                self.add(command)
                return True
        return False

    def r_toggle(self, command):
        target = self.getVariable(command['target'])
        value = self.getSymbolValue(target)
        val = {}
        val['type'] = 'boolean'
        val['content'] = not value['content']
        self.putSymbolValue(target, val)
        self.add(command)
        return self.nextPC()

    # Truncate a file
    def k_truncate(self, command):
        if self.nextIsSymbol():
            fileRecord = self.getSymbolRecord()
            if fileRecord['keyword'] == 'file':
                command['file'] = fileRecord['name']
                self.add(command)
                return True
        return False

    def r_truncate(self, command):
        fileRecord = self.getVariable(command['file'])
        fileRecord['file'].truncate()
        return self.nextPC()

    # Unlock a variable
    def k_unlock(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            command['target'] = symbolRecord['name']
            self.add(command)
            return True
        return False

    def r_unlock(self, command):
        target = self.getVariable(command['target'])
        target['locked'] = False
        return self.nextPC()

    def k_use(self, command):
        if self.nextIs('graphics'):
            print('Loading graphics module')
            from .ec_pyside import Graphics
            self.program.graphics = Graphics
            self.program.classes.append(Graphics)
            self.program.processClasses()
            return True

    # Declare a general-purpose variable
    def k_variable(self, command):
        return self.compileVariable(command, True)

    def r_variable(self, command):
        return self.nextPC()

    # Pause for a specified time
    def k_wait(self, command):
        command['value'] = self.nextValue()
        multipliers = {}
        multipliers['milli'] = 1
        multipliers['millis'] = 1
        multipliers['tick'] = 10
        multipliers['ticks'] = 10
        multipliers['second'] = 1000
        multipliers['seconds'] = 1000
        multipliers['minute'] = 60000
        multipliers['minutes'] = 60000
        command['multiplier'] = multipliers['second']
        token = self.peek()
        if token in multipliers:
            self.nextToken()
            command['multiplier'] = multipliers[token]
        self.add(command)
        return True

    def r_wait(self, command):
        value = self.getRuntimeValue(command['value']) * command['multiplier']
        next = self.nextPC()
        threading.Timer(value/1000.0, lambda: (self.run(next))).start()
        return 0

    # while <condition> <action>
    def k_while(self, command):
        code = self.nextCondition()
        if code == None:
            return None
        # token = self.getToken()
        command['condition'] = code
        test = self.getPC()
        self.addCommand(command)
        # Set up a goto for when the test fails
        fail = self.getPC()
        cmd = {}
        cmd['lino'] = command['lino']
        cmd['domain'] = 'core'
        cmd['keyword'] = 'gotoPC'
        cmd['goto'] = 0
        cmd['debug'] = False
        self.addCommand(cmd)
        # Do the body of the while
        self.nextToken()
        if self.compileOne() == False:
            return False
        # Repeat the test
        cmd = {}
        cmd['lino'] = command['lino']
        cmd['domain'] = 'core'
        cmd['keyword'] = 'gotoPC'
        cmd['goto'] = test
        cmd['debug'] = False
        self.addCommand(cmd)
        # Fixup the 'goto' on completion
        self.getCommandAt(fail)['goto'] = self.getPC()
        return True

    def r_while(self, command):
        test = self.program.condition.testCondition(command['condition'])
        if test:
            self.program.pc += 2
        else:
            self.program.pc += 1
        return self.program.pc

    # Write to a file
    def k_write(self, command):
        if self.peek() == 'line':
            self.nextToken()
            command['line'] = True
        else:
            command['line'] = False
        command['value'] = self.nextValue()
        if self.peek() == 'to':
            self.nextToken()
            if self.nextIsSymbol():
                fileRecord = self.getSymbolRecord()
                if fileRecord['keyword'] == 'file':
                    command['file'] = fileRecord['name']
                    self.add(command)
                    return True
        return False

    def r_write(self, command):
        value = self.getRuntimeValue(command['value'])
        fileRecord = self.getVariable(command['file'])
        file = fileRecord['file']
        if file.mode in ['w', 'w+', 'a', 'a+']:
            file.write(f'{value}')
            if command['line']:
                file.write('\n')
        return self.nextPC()

    #############################################################################
    # Support functions

    def incdec(self, command, mode):
        symbolRecord = self.getVariable(command['target'])
        if not symbolRecord['hasValue']:
            NoValueRuntimeError(self.program, symbolRecord)
        value = self.getSymbolValue(symbolRecord)
        if value == None:
            RuntimeError(self.program, f'{symbolRecord["name"]} has not been initialised')
        if mode == '+':
            value['content'] += 1
        else:
            value['content'] -= 1
        self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    #############################################################################
    # Compile a value in this domain
    def compileValue(self):
        value = {}
        value['domain'] = self.getName()
        token = self.getToken()
        if self.isSymbol():
            value['name'] = token
            symbolRecord = self.getSymbolRecord()
            keyword = symbolRecord['keyword']

            if keyword == 'module':
                value['type'] = 'module'
                return value

            if keyword == 'variable':
                value['type'] = 'symbol'
                return value
            return None

        value['type'] = token

        if token == 'arg':
            self.nextToken()
            value['index'] = self.getValue()
            return value

        if token in ['cos', 'sin', 'tan']:
            value['angle'] = self.nextValue()
            if self.nextToken() == 'radius':
                value['radius'] = self.nextValue()
                return value
            return None

        if token in ['now', 'today', 'newline', 'tab', 'empty']:
            return value

        if token in ['stringify', 'prettify', 'json', 'lowercase', 'uppercase', 'hash', 'random', 'float', 'integer', 'encode', 'decode']:
            value['content'] = self.nextValue()
            return value

        if (token in ['datime', 'datetime']):
            value['type'] = 'datime'
            value['timestamp'] = self.nextValue()
            if self.peek() == 'format':
                self.nextToken()
                value['format'] = self.nextValue()
            else:
                value['format'] = None
            return value

        if token == 'element':
            value['index'] = self.nextValue()
            if self.nextToken() == 'of':
                if self.nextIsSymbol():
                    symbolRecord = self.getSymbolRecord()
                    if symbolRecord['hasValue']:
                        value['target'] = symbolRecord['name']
                        return value
                self.warning(f'Core.compileValue: Token {symbolRecord["name"]} does not hold a value')
            return None

        if token == 'property':
            value['name'] = self.nextValue()
            if self.nextToken() == 'of':
                if self.nextIsSymbol():
                    symbolRecord = self.getSymbolRecord()
                    if symbolRecord['hasValue']:
                        value['target'] = symbolRecord['name']
                        return value
                    NoValueError(self.compiler, symbolRecord)
            return None

        if token == 'arg':
            value['content'] = self.nextValue()
            if self.getToken() == 'of':
                if self.nextIsSymbol():
                    symbolRecord = self.getSymbolRecord()
                    if symbolRecord['keyword'] == 'variable':
                        value['target'] = symbolRecord['name']
                        return value
            return None

        if token == 'trim':
            self.nextToken()
            value['content'] = self.getValue()
            return value

        if self.getToken() == 'the':
            self.nextToken()

        token = self.getToken()
        value['type'] = token

        if token == 'args':
           return value

        if token == 'elements':
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    value['name'] = self.getToken()
                    return value
            return None

        if token == 'keys':
            if self.nextIs('of'):
                value['name'] = self.nextValue()
                return value
            return None

        if token == 'count':
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    if self.getSymbolRecord()['hasValue']:
                        value['name'] = self.getToken()
                        return value
            return None

        if token == 'index':
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    value['variable'] = self.getSymbolRecord()['name']
                    if self.peek() == 'in':
                        value['value'] = None
                        value['type'] = 'indexOf'
                        if self.nextIsSymbol():
                            value['target'] = self.getSymbolRecord()['name']
                            return value
                    else:
                        value['name'] = self.getToken()
                        return value
                else:
                    value['value'] = self.getValue()
                    if self.nextIs('in'):
                        value['variable'] = None
                        value['type'] = 'indexOf'
                        if self.nextIsSymbol():
                            value['target'] = self.getSymbolRecord()['name']
                            return value
            return None

        if token == 'value':
            if self.nextIs('of'):
                v = self.nextValue()
                if v !=None:
                    value['type'] = 'valueOf'
                    value['content'] = v
                    return value
            return None

        if token == 'length':
            value['type'] = 'lengthOf'
            if self.nextIs('of'):
                value['content'] = self.nextValue()
                return value
            return None

        if token in ['left', 'right']:
            value['count'] = self.nextValue()
            if self.nextToken() == 'of':
                value['content'] = self.nextValue()
                return value
            return None

        if token == 'from':
            value['start'] = self.nextValue()
            if self.peek() == 'to':
                self.nextToken()
                value['to'] = self.nextValue()
            else:
                value['to'] = None
            if self.nextToken() == 'of':
                value['content'] = self.nextValue()
                return value

        if token == 'position':
            if self.nextIs('of'):
                value['last'] = False
                if self.nextIs('the'):
                    if self.nextIs('last'):
                        self.nextToken()
                        value['last'] = True
                value['needle'] = self.getValue()
                if self.nextToken() == 'in':
                    value['haystack'] = self.nextValue()
                    return value

        if token == 'message':
            return value

        if token == 'timestamp':
            value['format'] = None
            if self.peek() == 'of':
                self.nextToken()
                value['datime'] = self.nextValue()
                if self.peek() == 'format':
                    self.nextToken()
                    value['format'] = self.nextValue()
            return value

        if token == 'files':
            token = self.nextToken()
            if token in ['in', 'of']:
                value['target'] = self.nextValue()
                return value
            return None

        if token == 'weekday':
            value['type'] = 'weekday'
            return value

        if token == 'mem' or token == 'memory':
            value['type'] = 'memory'
            return value

        if token == 'error':
            if self.peek() == 'code':
                self.nextToken()
                value['item'] = 'errorCode'
                return value
            if self.peek() == 'reason':
                self.nextToken()
                value['item'] = 'errorReason'
                return value

        if token == 'type':
            if self.nextIs('of'):
                value['value'] = self.nextValue()
                return value
            return None

        if token == 'modification':
            if self.nextIs('time'):
                if self.nextIs('of'):
                    value['fileName'] = self.nextValue()
                    return value
            return None

        if token == 'system':
            value['command'] = self.nextValue()
            return value

        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        if self.peek() == 'modulo':
            self.nextToken()
            mv = {}
            mv['domain'] = 'core'
            mv['type'] = 'modulo'
            mv['content'] = value
            mv['modval'] = self.nextValue()
            value = mv

        return value

    #############################################################################
    # Value handlers

    def v_args(self, v):
        value = {}
        value['type'] = 'text'
        value['content'] = json.dumps(self.program.argv)
        return value

    def v_arg(self, v):
        value = {}
        value['type'] = 'text'
        index = self.getRuntimeValue(v['index'])
        if index >= len(self.program.argv):
            RuntimeError(self.program, 'Index exceeds # of args')
        value['content'] = self.program.argv[index]
        return value

    def v_boolean(self, v):
        value = {}
        value['type'] = 'boolean'
        value['content'] = v['content']
        return value

    def v_cos(self, v):
        angle = self.getRuntimeValue(v['angle'])
        radius = self.getRuntimeValue(v['radius'])
        value = {}
        value['type'] = 'int'
        value['content'] = round(math.cos(angle * 0.01745329) * radius)
        return value

    def v_count(self, v):
        variable = self.getVariable(v['name'])
        content = variable['value'][variable['index']]['content']
        value = {}
        value['type'] = 'int'
        value['content'] = len(content)
        return value

    def v_datime(self, v):
        ts = self.getRuntimeValue(v['timestamp'])
        fmt = v['format']
        if fmt == None:
            fmt = '%b %d %Y %H:%M:%S'
        else:
            fmt = self.getRuntimeValue(fmt)
        value = {}
        value['type'] = 'text'
        value['content'] = datetime.fromtimestamp(ts/1000).strftime(fmt)
        return value

    def v_decode(self, v):
        content = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'text'
        if self.encoding == 'utf-8':
            value['content'] = content.decode('utf-8')
        elif self.encoding == 'base64':
            base64_bytes = content.encode('ascii')
            message_bytes = base64.b64decode(base64_bytes)
            value['content'] = message_bytes.decode('ascii')
        elif self.encoding == 'hex':
            hex_bytes = content.encode('utf-8')
            message_bytes = binascii.unhexlify(hex_bytes)
            value['content'] = message_bytes.decode('utf-8')
        else:
            value = v
        return value

    def v_element(self, v):
        index = self.getRuntimeValue(v['index'])
        target = self.getVariable(v['target'])
        val = self.getSymbolValue(target)
        content = val['content']
        value = {}
        value['type'] = 'int' if isinstance(content, int) else 'text'
        if type(content) == list:
            try:
                value['content'] = content[index]
                return value
            except:
                RuntimeError(self.program, 'Index out of range')
        # lino = self.program.code[self.program.pc]['lino']
        RuntimeError(self.program, 'Item is not a list')

    def v_elements(self, v):
        var = self.getVariable(v['name'])
        value = {}
        value['type'] = 'int'
        value['content'] = var['elements']
        return value

    def v_empty(self, v):
        value = {}
        value['type'] = 'text'
        value['content'] = ''
        return value

    def v_encode(self, v):
        content = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'text'
        if self.encoding == 'utf-8':
            value['content'] = content.encode('utf-8')
        elif self.encoding == 'base64':
            data_bytes = content.encode('ascii')
            base64_bytes = base64.b64encode(data_bytes)
            value['content'] = base64_bytes.decode('ascii')
        elif self.encoding == 'hex':
            data_bytes = content.encode('utf-8')
            hex_bytes = binascii.hexlify(data_bytes)
            value['content'] = hex_bytes.decode('utf-8')
        else:
            value = v
        return value

    def v_error(self, v):
        global errorCode, errorReason
        value = {}
        if v['item'] == 'errorCode':
            value['type'] = 'int'
            value['content'] = errorCode
        elif v['item'] == 'errorReason':
            value['type'] = 'text'
            value['content'] = errorReason
        return value

    def v_files(self, v):
        v = self.getRuntimeValue(v['target'])
        value = {}
        value['type'] = 'text'
        value['content'] = os.listdir(v)
        return value

    def v_float(self, v):
        val = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'float'
        try:
            value['content'] = float(val)
        except:
            RuntimeWarning(self.program, f'Value cannot be parsed as floating-point')
            value['content'] = 0.0
        return value

    def v_from(self, v):
        content = self.getRuntimeValue(v['content'])
        start = self.getRuntimeValue(v['start'])
        to = v['to']
        if not to == None:
            to = self.getRuntimeValue(to)
        value = {}
        value['type'] = 'text'
        if to == None:
            value['content'] = content[start:]
        else:
            value['content'] = content[start:to]
        return value

    def v_hash(self, v):
        hashval = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'text'
        value['content'] = hashlib.sha256(hashval.encode('utf-8')).hexdigest()
        return value

    def v_index(self, v):
        value = {}
        value['type'] = 'int'
        value['content'] = self.getVariable(v['name'])['index']
        return value

    def v_indexOf(self, v):
        value = v['value']
        if value == None:
            value = self.getSymbolValue(v['variable'])['content']
        else:
            value = self.getRuntimeValue(value)
        target = self.getVariable(v['target'])
        data = self.getSymbolValue(target)['content']
        index = -1
        for n in range(0, len(data)):
            if data[n] == value:
                index = n
                break
        retval = {}
        retval['type'] = 'int'
        retval['content'] = index
        return retval

    def v_integer(self, v):
        val = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'int'
        value['content'] = int(val)
        return value

    def v_json(self, v):
        item = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'object'
        try:
            value['content'] = json.loads(item)
        except:
            RuntimeError(self.program, 'Cannot encode value')
        return value

    def v_keys(self, v):
        value = {}
        value['type'] = 'int'
        value['content'] = list(self.getRuntimeValue(v['name']).keys())
        return value

    def v_left(self, v):
        content = self.getRuntimeValue(v['content'])
        count = self.getRuntimeValue(v['count'])
        value = {}
        value['type'] = 'text'
        value['content'] = content[0:count]
        return value

    def v_lengthOf(self, v):
        content = self.getRuntimeValue(v['content'])
        if type(content) == str:
            value = {}
            value['type'] = 'int'
            value['content'] = len(content)
            return value
        RuntimeError(self.program, 'Value is not a string')

    def v_lowercase(self, v):
        content = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'text'
        value['content'] = content.lower()
        return value

    def v_memory(self, v):
        process: Process = Process(os.getpid())
        megabytes: float = process.memory_info().rss / (1024 * 1024)
        value = {}
        value['type'] = 'float'
        value['content'] = megabytes
        return value

    def v_message(self, v):
        value = {}
        value['type'] = 'text'
        value['content'] = self.program.message
        return value

    def v_modification(self, v):
        fileName = self.getRuntimeValue(v['fileName'])
        ts = int(os.stat(fileName).st_mtime)
        value = {}
        value['type'] = 'int'
        value['content'] = ts
        return value

    def v_modulo(self, v):
        val = self.getRuntimeValue(v['content'])
        modval = self.getRuntimeValue(v['modval'])
        value = {}
        value['type'] = 'int'
        value['content'] = val % modval
        return value

    def v_newline(self, v):
        value = {}
        value['type'] = 'text'
        value['content'] = '\n'
        return value

    def v_now(self, v):
        value = {}
        value['type'] = 'int'
        value['content'] = getTimestamp(time.time())
        return value

    def v_position(self, v):
        needle = self.getRuntimeValue(v['needle'])
        haystack = self.getRuntimeValue(v['haystack'])
        last = v['last']
        value = {}
        value['type'] = 'int'
        value['content'] = haystack.rfind(needle) if last else haystack.find(needle)
        return value

    def v_prettify(self, v):
        item = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'text'
        value['content'] = json.dumps(item, indent=4)
        return value

    def v_property(self, v):
        propertyValue = self.getRuntimeValue(v['name'])
        if 'target' in v:
            targetName = v['target']
            target = self.getVariable(targetName)
            targetValue = self.getRuntimeValue(target)
        else:
            targetValue = self.getRuntimeValue(v['value'])
        try:
            val = targetValue[propertyValue]
        except:
            RuntimeError(self.program, f'This value does not have the property \'{propertyValue}\'')
            return None
        value = {}
        value['content'] = val
        if isinstance(v, numbers.Number):
            value['type'] = 'int'
        else:
            value['type'] = 'text'
        return value

    def v_random(self, v):
        limit = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'int'
        value['content'] = randrange(0, limit)
        return value

    def v_right(self, v):
        content = self.getRuntimeValue(v['content'])
        count = self.getRuntimeValue(v['count'])
        value = {}
        value['type'] = 'text'
        value['content'] = content[-count:]
        return value

    def v_sin(self, v):
        angle = self.getRuntimeValue(v['angle'])
        radius = self.getRuntimeValue(v['radius'])
        value = {}
        value['type'] = 'int'
        value['content'] = round(math.sin(angle * 0.01745329) * radius)
        return value

    def v_stringify(self, v):
        item = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'text'
        value['content'] = json.dumps(item)
        return value

    # This is used by the expression evaluator to get the value of a symbol
    def v_symbol(self, symbolRecord):
        if symbolRecord['keyword'] == 'variable':
            return self.getSymbolValue(symbolRecord)
        else:
            return None

    def v_system(self, v):
        command = self.getRuntimeValue(v['command'])
        result = os.popen(command).read()
        value = {}
        value['type'] = 'text'
        value['content'] = result
        return value

    def v_tab(self, v):
        value = {}
        value['type'] = 'text'
        value['content'] = '\t'
        return value

    def v_tan(self, v):
        angle = self.getRuntimeValue(v['angle'])
        radius = self.getRuntimeValue(v['radius'])
        value = {}
        value['type'] = 'int'
        value['content'] = round(math.tan(angle * 0.01745329) * radius)
        return value

    def v_timestamp(self, v):
        value = {}
        value['type'] = 'int'
        fmt = v['format']
        if fmt == None:
            value['content'] = int(time.time())
        else:
            fmt = self.getRuntimeValue(fmt)
            dt = self.getRuntimeValue(v['datime'])
            spec = datetime.strptime(dt, fmt)
            t = datetime.now().replace(hour=spec.hour, minute=spec.minute, second=spec.second, microsecond=0)
            value['content'] = int(t.timestamp())
        return value

    def v_today(self, v):
        value = {}
        value['type'] = 'int'
        value['content'] = int(datetime.combine(datetime.now().date(),datetime.min.time()).timestamp())*1000
        return value

    def v_trim(self, v):
        v = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'text'
        value['content'] = v.strip()
        return value

    def v_type(self, v):
        value = {}
        value['type'] = 'text'
        val = self.getRuntimeValue(v['value'])
        if val is None:
            value['content'] = 'none'
        elif type(val) is str:
            value['content'] = 'text'
        elif type(val) is int:
            value['content'] = 'numeric'
        elif type(val) is bool:
            value['content'] = 'boolean'
        elif type(val) is list:
            value['content'] = 'list'
        elif type(val) is dict:
            value['content'] = 'object'
        return value

    def v_uppercase(self, v):
        content = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'text'
        value['content'] = content.upper()
        return value

    def v_valueOf(self, v):
        v = self.getRuntimeValue(v['content'])
        value = {}
        value['type'] = 'int'
        value['content'] = int(v)
        return value

    def v_weekday(self, v):
        value = {}
        value['type'] = 'int'
        value['content'] = datetime.today().weekday()
        return value

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = Condition()

        if self.getToken() == 'not':
            condition.type = 'not'
            condition.value = self.nextValue()
            return condition

        if self.getToken() == 'file':
            path = self.nextValue()
            condition.path = path
            condition.type = 'exists'
            token = self.nextToken()
            if token == 'exists':
                return condition
            elif token == 'does':
                if self.nextIs('not'):
                    if self.nextIs('exist'):
                        condition.negate = not condition.negate
                        return condition
            return None

        value = self.getValue()
        if value == None:
            return None

        condition.value1 = value
        token = self.peek()
        condition.type = token

        if token == 'has':
            self.nextToken()
            if self.nextToken() == 'property':
                prop = self.nextValue()
                condition.type = 'hasProperty'
                condition.property = prop
                return condition
            return None

        if token == 'does':
            self.nextToken()
            if self.nextIs('not'):
                token = self.nextToken()
                if token == 'have':
                    if self.nextToken() == 'property':
                        prop = self.nextValue()
                        condition.type = 'hasProperty'
                        condition.property = prop
                        condition.negate = not condition.negate
                        return condition
                elif token == 'include':
                    value = self.nextValue()
                    condition.type = 'includes'
                    condition.value2 = value
                    condition.negate = not condition.negate
                    return condition
            return None

        if token in ['starts', 'ends']:
            self.nextToken()
            if self.nextToken() == 'with':
                condition.value2 = self.nextValue()
                return condition

        if token == 'includes':
            condition.value2 = self.nextValue()
            return condition

        if token == 'is':
            token = self.nextToken()
            if self.peek() == 'not':
                self.nextToken()
                condition.negate = True
            token = self.nextToken()
            condition.type = token
            if token in ['numeric', 'string', 'boolean', 'none', 'list', 'object', 'even', 'odd', 'empty']:
                return condition
            if token in ['greater', 'less']:
                if self.nextToken() == 'than':
                    condition.value2 = self.nextValue()
                    return condition
            condition.type = 'is'
            condition.value2 = self.getValue()
            return condition

        if condition.value1:
            # It's a boolean if
            condition.type = 'boolean'
            return condition

        self.warning(f'Core.compileCondition: I can\'t get a conditional:')
        return None

    def isNegate(self):
        token = self.getToken()
        if token == 'not':
            self.nextToken()
            return True
        return False

    #############################################################################
    # Condition handlers

    def c_boolean(self, condition):
        value = self.getRuntimeValue(condition.value1)
        if type(value) == bool:
            return not value if condition.negate else value
        elif type(value) == int:
            return True if condition.negate else False
        elif type(value) == str:
            if value.lower() == 'true':
                return False if condition.negate else True
            elif value.lower() == 'false':
                return True if condition.negate else False
            else:
                return True if condition.negate else False
        return False

    def c_empty(self, condition):
        value = self.getRuntimeValue(condition.value1)
        if value == None:
            comparison = True
        else:
            comparison = len(value) == 0
        return not comparison if condition.negate else comparison

    def c_ends(self, condition):
        value1 = self.getRuntimeValue(condition.value1)
        value2 = self.getRuntimeValue(condition.value2)
        return value1.endswith(value2)

    def c_even(self, condition):
        return self.getRuntimeValue(condition.value1) % 2 == 0

    def c_exists(self, condition):
        path = self.getRuntimeValue(condition.path)
        comparison = os.path.exists(path)
        return not comparison if condition.negate else comparison

    def c_greater(self, condition):
        comparison = self.program.compare(condition.value1, condition.value2)
        return comparison <= 0 if condition.negate else comparison > 0

    def c_hasProperty(self, condition):
        value = self.getRuntimeValue(condition.value1)
        prop = self.getRuntimeValue(condition.property)
        try:
            value[prop]
            hasProp = True
        except:
            hasProp = False
        return not hasProp if condition.negate else hasProp

    def c_includes(self, condition):
        value1 = self.getRuntimeValue(condition.value1)
        value2 = self.getRuntimeValue(condition.value2)
        includes = value2 in value1
        return not includes if condition.negate else includes

    def c_is(self, condition):
        comparison = self.program.compare(condition.value1, condition.value2)
        return comparison != 0 if condition.negate else comparison == 0

    def c_less(self, condition):
        comparison = self.program.compare(condition.value1, condition.value2)
        return comparison >= 0 if condition.negate else comparison < 0

    def c_list(self, condition):
        comparison = type(self.getRuntimeValue(condition.value1)) is list
        return not comparison if condition.negate else comparison

    def c_numeric(self, condition):
        comparison = type(self.getRuntimeValue(condition.value1)) is int
        return not comparison if condition.negate else comparison

    def c_none(self, condition):
        comparison = self.getRuntimeValue(condition.value1) is None
        return not comparison if condition.negate else comparison

    def c_not(self, condition):
        return not self.getRuntimeValue(condition.value)

    def c_object(self, condition):
        comparison = type(self.getRuntimeValue(condition.value1)) is dict
        return not comparison if condition.negate else comparison

    def c_odd(self, condition):
        return self.getRuntimeValue(condition.value1) % 2 == 1

    def c_starts(self, condition):
        value1 = self.getRuntimeValue(condition.value1)
        value2 = self.getRuntimeValue(condition.value2)
        return value1.startswith(value2)

    def c_string(self, condition):
        comparison = type(self.getRuntimeValue(condition.value1)) is str
        return not comparison if condition.negate else comparison
