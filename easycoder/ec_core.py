import json, math, hashlib, threading, sys, os, subprocess, time
import numbers, base64, binascii, random, requests, paramiko
import token
from copy import deepcopy
from psutil import Process
from datetime import datetime
from .ec_classes import (
    FatalError,
    RuntimeWarning,
    RuntimeError,
    RuntimeAssertionError,
    NoValueError,
    NoValueRuntimeError,
    Object,
    ECObject,
    ECVariable,
    ECFile,
    ECStack,
    ECSSH,
    ECValue
)

from .ec_handler import Handler

class Core(Handler):

    def __init__(self, compiler):
        super().__init__(compiler)
        self.encoding = 'utf-8'

    def getName(self):
        return 'core'
    
    def noSymbolWarning(self):
        self.warning(f'Symbol "{self.getToken()}" not found')
    
    def processOr(self, command, orHere):
        self.add(command)
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
            skip = self.getCodeSize()
            self.add(cmd)
            # Process the 'or'
            self.getCommandAt(orHere)['or'] = self.getCodeSize()
            self.compileOne()
            # Fixup the skip
            self.getCommandAt(skip)['goto'] = self.getCodeSize()

    #############################################################################
    # Keyword handlers

    # Arithmetic add
    # add {value} to {variable}
    # add {value1} to {value2} giving {variable}
    def k_add(self, command):
        # Get the (first) value
        command['value1'] = self.nextValue()
        if command['value1'] == None: return False
        self.skip('to')
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if not isinstance(record['object'], ECVariable): return False
            # If 'giving' comes next, this variable is the second value
            if self.peek() == 'giving':
                v2 = ECValue(domain=self.getName(), type='symbol', content=record['name'])
                command['value2'] = v2
                self.nextToken()
                # Now get the target variable
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    self.checkObjectType(record, ECVariable)
                    command['target'] = record['name']
                self.add(command)
                return True
            else:
                # Here the variable is the target
                command['target'] = record['name']
                if record['object'].isMutable():
                    self.add(command)
                    return True
        else:
            # Here we have 2 values so 'giving' must come next
            command['value2'] = self.getValue()
            if self.nextToken() == 'giving':
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    self.checkObjectType(record, ECVariable)
                    command['target'] = record['name']
                self.add(command)
                return True
            # raise FatalError(self.compiler, 'Cannot add values: target variable expected')
        return False

    def r_add(self, command):
        value1 = self.getRuntimeValue(command['value1'])
        value2 = self.getRuntimeValue(command['value2']) if 'value2' in command else None
        target = self.getVariable(command['target'])
        # Check that the target variable is mutable. If not, it's not an arithmetic add
        # If value2 exists, we are adding two values and storing the result in target
        if value2 != None:
            # add X to Y giving Z
            targetValue = ECValue(domain=self.getName(), type='int', content=value1 + value2)
        else:
            # add X to Y
            targetValue = self.getSymbolValue(target)
            targetValue.setContent(targetValue.getContent() + value1)
        self.putSymbolValue(target, targetValue)
        return self.nextPC()

    # Append a value to an array
    # append {value} to {array}
    def k_append(self, command):
        command['value'] = self.nextValue()
        if self.nextIs('to'):
            if self.nextIsSymbol():
                symbolRecord = self.getSymbolRecord()
                self.program.checkObjectType(symbolRecord['object'], ECVariable)
                command['target'] = symbolRecord['name']
                self.add(command)
                return True
        return False

    def r_append(self, command):
        value = self.getRuntimeValue(command['value'])
        target = self.getVariable(command['target'])
        content = target['object'].getContent()
        items = [] if content == None else content
        if not type(items) == list:
            RuntimeError(self.program, f'{command["target"]} is not a JSON list')
        items.append(value)
        self.putSymbolValue(target, items)
        return self.nextPC()

    #assert {condition} [with {message}]
    def k_assert(self, command):
        command['test'] = self.nextCondition()
        if self.peek() == 'with':
            self.nextToken()
            command['with'] = self.nextValue()
        else:
            command['with'] = None
        self.add(command)
        return True

    def r_assert(self, command):
        test = self.program.condition.testCondition(command['test'])
        if test:
            return self.nextPC()
        RuntimeAssertionError(self.program, self.getRuntimeValue(command['with']))

    # Begin a block
    def k_begin(self, command):
        if self.nextToken() == 'end':
            cmd = {}
            cmd['domain'] = 'core'
            cmd['keyword'] = 'end'
            cmd['debug'] = True
            cmd['lino'] = command['lino']
            self.add(cmd)
            return self.nextPC()
        else:
            return self.compileFromHere(['end'])

    # clear {variable}
    def k_clear(self, command):
        if self.nextIsSymbol():
            target = self.getSymbolRecord()
            command['target'] = target['name']
            if target['keyword'] == 'ssh':
                self.add(command)
                return True
            if isinstance(target['object'], ECVariable):
                self.add(command)
                return True
        return False

    def r_clear(self, command):
        target = self.getVariable(command['target'])
        if target['keyword'] == 'ssh':
            target['ssh'] = None
        else:
            self.putSymbolValue(target, ECValue(domain=self.getName(), type='boolean', content=False))
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
        if token == 'compile':
            self.compiler.debugCompile = True
            self.nextToken()
            return True
        elif token in ['step', 'stop', 'program', 'custom']:
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
        if command['mode'] == 'compile':
            self.program.debugStep = True
        elif command['mode'] == 'step':
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
            self.checkObjectType(symbolRecord['object'], ECVariable)
            command['target'] = symbolRecord['name']
            self.add(command)
            return True
        return False

    def r_decrement(self, command):
        return self.incdec(command, '-')

    # Delete a file or a property
    # delete file {filename}
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
                if isinstance(record['object'], ECObject):
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
            if filename != None:
                if os.path.isfile(filename): os.remove(filename)
        elif type == 'property':
            key = self.getRuntimeValue(command['key'])
            symbolRecord = self.getVariable(command['var'])
            value = self.getSymbolValue(symbolRecord)
            content = value.getContent()
            content.pop(key, None)
            value.setContent(content)
            self.putSymbolValue(symbolRecord, value)
        elif type == 'element':
            key = self.getRuntimeValue(command['key'])
            symbolRecord = self.getVariable(command['var'])
            value = self.getSymbolValue(symbolRecord)
            content = value.getContent()
            if isinstance(key, int):
                if key >= 0 and key < len(content): del(content[key])
            elif isinstance(key, str):
                if key in content: content.remove(key)
            else: RuntimeError(self.program, f'Index {key} out of range')
            value.setContent(content)
            self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    # Arithmetic divide
    # divide {variable} by {value}
    # divide {value1} by {value2} giving {variable}
    def k_divide(self, command):
        # Get the (first) item. If it's a symbol, it may be the target variable
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            self.checkObjectType(record, ECVariable)
            # Hold onto the variable and its value
            variable1 = record['name']
            value1 = self.getValue()
        else:
            # Here we have a value
            value1 = self.getValue()
            variable1 = None
        self.skip('by')
        command['value2'] = self.nextValue()
        # if 'giving' comes next, the target is the next value
        if self.peek() == 'giving':
            self.nextToken()
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                self.checkObjectType(record, ECVariable)
                command['target'] = record['name']
                command['value1'] = value1
                self.add(command)
                return True
        else:
            # Here the first variable is the target
            if variable1 != None:
                command['target'] = variable1
                self.add(command)
                return True
        return False

    def r_divide(self, command):
        value1 = self.getRuntimeValue(command['value1']) if 'value1' in command else None
        value2 = self.getRuntimeValue(command['value2'])
        target = self.getVariable(command['target'])
        # Check that the target variable can hold a value
        self.checkObjectType(target, ECVariable)
        # If value1 exists, we are adding two values and storing the result in target
        if value1 != None:
            # divide X by Y giving Z
            targetValue = ECValue(domain=self.getName(), type='int', content=value1 // value2)
        else:
            # divide X by Y
            targetValue = self.getSymbolValue(target)
            targetValue.setContent(targetValue.getContent() // value2)
        self.putSymbolValue(target, targetValue)
        return self.nextPC()

    # download [binary] {url} to {path}
    def k_download(self, command):
        if self.nextIs('binary'):
            command['binary'] = True
            self.nextToken()
        else: command['binary'] = False
        command['url'] = self.getValue()
        self.skip('to')
        command['path'] = self.nextValue()
        self.add(command)
        return True
    
    def r_download(self, command):
        binary = command['binary']
        url = self.getRuntimeValue(command['url'])
        path = self.getRuntimeValue(command['path'])
        mode = 'wb' if binary else 'w'
        response = requests.get(url, stream=True)
        with open(path, mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)
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
        if self.program.parent == None and self.program.graphics != None:
            self.program.graphics.force_exit(None)
        return -1

    # Declare a file variable
    def k_file(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECFile')

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

    # get {variable) from {url} [or {command}]
    def k_get(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if isinstance(symbolRecord['object'], ECObject):
                command['target'] = self.getToken()
            else:
                NoValueError(self.compiler, symbolRecord)
        if self.nextIs('from'):
            if self.nextIs('url'):
                url = self.nextValue()
                if url != None:
                    command['url'] = url
                    command['or'] = None
                    get = self.getCodeSize()
                    if self.peek() == 'timeout':
                        self.nextToken()
                        command['timeout'] = self.nextValue()
                    else:
                        timeout = ECValue(type = 'int', content = 5)
                        command['timeout'] = timeout
                    self.processOr(command, get)
                    return True
        return False

    def r_get(self, command):
        global errorCode, errorReason
        retval = ECValue(type='str')
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
        retval.setContent(response.text)
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
        if label in self.symbols:
            address = self.symbols[label]
            self.stack.append(self.nextPC())
            return address
        RuntimeError(self.program, f'There is no label "{label}"')
        return None

    # if <condition> <action> [else <action>]
    def k_if(self, command):
        command['condition'] = self.nextCondition()
        self.add(command)
        self.nextToken()
        pcElse = self.getCodeSize()
        cmd = {}
        cmd['lino'] = command['lino']
        cmd['domain'] = 'core'
        cmd['keyword'] = 'gotoPC'
        cmd['goto'] = 0
        cmd['debug'] = False
        self.add(cmd)
        # Get the 'then' code
        self.compileOne()
        if self.peek() == 'else':
            self.nextToken()
            # Add a 'goto' to skip the 'else'
            pcNext = self.getCodeSize()
            cmd = {}
            cmd['lino'] = command['lino']
            cmd['domain'] = 'core'
            cmd['keyword'] = 'gotoPC'
            cmd['goto'] = 0
            cmd['debug'] = False
            self.add(cmd)
            # Fixup the link to the 'else' branch
            self.getCommandAt(pcElse)['goto'] = self.getCodeSize()
            # Process the 'else' branch
            self.nextToken()
            self.compileOne()
            # Fixup the pcNext 'goto'
            self.getCommandAt(pcNext)['goto'] = self.getCodeSize()
        else:
            # We're already at the next command
            self.getCommandAt(pcElse)['goto'] = self.getCodeSize()
        return True

    def r_if(self, command):
        test = self.program.condition.testCondition(command['condition'])
        if test:
            self.program.pc += 2
        else:
            self.program.pc += 1
        return self.program.pc

    # Import one or more variables
    def k_import(self, command):
        self.add(command)
        imports = []
        while True:
            vartype = self.nextToken()
            for domain in self.program.getDomains():
                handler = domain.keywordHandler(vartype)
                if handler != None:
                    variable = {}
                    if not handler(variable):
                        raise RuntimeError(self.program, f'Failed to handle variable type "{vartype}"')
                    imports.append(variable)
            if self.peek() != 'and':
                break
            self.nextToken()
        command['imports'] = imports
        return True

    def r_import(self, command):
        exports = self.program.exports
        imports = command['imports']
        if len(imports) < len(exports):
            RuntimeError(self.program, 'Too few imports')
        elif len(imports) > len(exports):
            RuntimeError(self.program, 'Too many imports')
        for n in range(0, len(imports)):
            exportRecord = exports[n]
            importRecord = imports[n]
            if importRecord['classname'] != exportRecord['classname']:
                raise RuntimeError(self.program, f'Import {n} does not match export (wrong type)')
            name = importRecord['name']
            importRecord.clear()
            importRecord['name'] = name
            importRecord['domain'] = exportRecord['domain']
            importRecord['keyword'] = exportRecord['keyword']
            importRecord['import'] = exportRecord
        return self.nextPC()

    # Increment a variable
    def k_increment(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            self.checkObjectType(symbolRecord['object'], ECVariable)
            command['target'] = symbolRecord['name']
            self.add(command)
            return True
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
        value = self.getRuntimeValue(command['value'])
        symbolRecord = self.getVariable(command['target'])
        symbolRecord['object'].setIndex(value)
        return self.nextPC()

    # Input a value from the terminal
    # input {variable} [with {prompt}]
    def k_input(self, command):
        # get the variable
        if self.nextIsSymbol():
            command['target'] = self.getToken()
            value = ECValue(domain=self.getName(), type='str', content=': ')
            command['prompt'] = value
            if self.peek() == 'with':
                self.nextToken()
                command['prompt'] = self.nextValue()
            self.add(command)
            return True
        return False

    def r_input(self, command):
        symbolRecord = self.getVariable(command['target'])
        prompt = command['prompt'].getValue()
        value = ECValue(domain=self.getName(), type='str', content=prompt+input(prompt))
        self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    # 1 Load a plugin. This is done at compile time.
    # 2 Load text from a file or ssh
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
            if isinstance(symbolRecord['object'], ECVariable):
                command['target'] = symbolRecord['name']
                if self.nextIs('from'):
                    if self.nextIsSymbol():
                        record = self.getSymbolRecord()
                        if record['keyword'] == 'ssh':
                            command['ssh'] = record['name']
                            command['path'] = self.nextValue()
                        else:
                            command['file'] = self.getValue()
                    else:
                        command['file'] = self.getValue()
                    command['or'] = None
                    load = self.getCodeSize()
                    self.processOr(command, load)
                    return True
        else:
            FatalError(self.compiler, f'I don\'t understand \'{self.getToken()}\'')
        return False

    def r_load(self, command):
        errorReason = None
        target = self.getVariable(command['target'])
        if 'ssh' in command:
            ssh = self.getVariable(command['ssh'])
            path = self.getRuntimeValue(command['path'])
            sftp = ssh['sftp']
            try:
                with sftp.open(path, 'r') as remote_file: content = remote_file.read().decode()
            except:
                errorReason = f'Unable to read from {path}'
                if command['or'] != None:
                    print(f'Exception "{errorReason}": Running the "or" clause')
                    return command['or']
                else:
                    RuntimeError(self.program, f'Error: {errorReason}')
        else:
            filename = self.getRuntimeValue(command['file'])
            try:
                with open(filename) as f: content = f.read()
            except:
                errorReason = f'Unable to read from {filename}'

        if errorReason:
            if command['or'] != None:
                print(f'Exception "{errorReason}": Running the "or" clause')
                return command['or']
            else:
                RuntimeError(self.program, f'Error: {errorReason}')
        value = ECValue(domain=self.getName(), type='str', content=content)
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
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECObject')

    def r_module(self, command):
        return self.nextPC()

    # Arithmetic multiply
    # multiply {variable} by {value}
    # multiply {value1} by {value2} giving {variable}
    def k_multiply(self, command):
        # Get the (first) item. If it's a symbol, it may be the target variable
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            self.checkObjectType(record, ECVariable)
            # Hold onto the variable and its value
            variable1 = record['name']
            value1 = self.getValue()
        else:
            # Here we have a value
            value1 = self.getValue()
            variable1 = None
        self.skip('by')
        command['value2'] = self.nextValue()
        # if 'giving' comes next, the target is the next value
        if self.peek() == 'giving':
            self.nextToken()
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                self.checkObjectType(record, ECVariable)
                command['target'] = record['name']
                command['value1'] = value1
                self.add(command)
                return True
        else:
            # Here the first variable is the target
            if variable1 != None:
                command['target'] = variable1
                self.add(command)
                return True
        return False

    def r_multiply(self, command):
        value1 = self.getRuntimeValue(command['value1']) if 'value1' in command else None
        value2 = self.getRuntimeValue(command['value2'])
        target = self.getVariable(command['target'])
        # Check that the target variable can hold a value
        self.checkObjectType(target, ECVariable)
        # If value1 exists, we are adding two values and storing the result in target
        if value1 != None:
            # multiply X by Y giving Z
            targetValue = ECValue(domain=self.getName(), type='int', content=value1 * value2)
        else:
            # multiply X by Y
            targetValue = self.getSymbolValue(target)
            targetValue.setContent(targetValue.getContent() * value2)
        self.putSymbolValue(target, targetValue)
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
        value.setContent(value.getContent() * -1)
        self.putSymbolValue(symbolRecord, value)
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
            self.add(cmd)
            # Add the action and a 'stop'
            self.compileOne()
            cmd = {}
            cmd['domain'] = 'core'
            cmd['lino'] = command['lino']
            cmd['keyword'] = 'stop'
            cmd['debug'] = False
            self.add(cmd)
            # Fixup the link
            command['goto'] = self.getCodeSize()
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
            record = self.getSymbolRecord()
            self.checkObjectType(record, ECObject)
            command['target'] = record['name']
            if self.peek() == 'from':
                self.nextToken()
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    self.checkObjectType(record, ECStack)
                    command['from'] = record['name']
                    self.add(command)
                    return True
        return False

    def r_pop(self, command):
        symbolRecord = self.getVariable(command['target'])
        stackRecord = self.getVariable(command['from'])
        value = stackRecord['object'].pop()
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
        post = self.getCodeSize()
        self.processOr(command, post)
        return True

    def r_post(self, command):
        global errorCode, errorReason
        retval = ECValue(domain=self.getName(), type='str', content = '')
        value = self.getRuntimeValue(command['value'])
        url = self.getRuntimeValue(command['url'])
        try:
            response = requests.post(url, value, timeout=5)
            retval.setContent(response.text) # type: ignore
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
#        while len(lino) < 5: lino = f' {lino}'
        if value == None: value = '<empty>'
        if 'log' in command:
            print(f'{datetime.now().time()}:{self.program.name}:{lino}->{value}')
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
        value = deepcopy(self.evaluate(command['value']))
        stackRecord = self.getVariable(command['to'])
        stackRecord['object'].push(value)
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
                    self.checkObjectType(symbolRecord['object'], ECVariable)
                    command['or'] = None
                    self.processOr(command, self.getCodeSize())
                    return True
                else:
                    FatalError(self.compiler, f'Symbol {self.getToken()} is not a variable')
        return False

    def r_put(self, command):
        value = self.evaluate(command['value'])
#        if value == None:
#            if command['or'] != None:
#                return command['or']
#            else:
#                RuntimeError(self.program, f'Error: could not compute value')
        symbolRecord = self.getVariable(command['target'])
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
            self.checkObjectType(symbolRecord['object'], ECVariable)
            if self.peek() == 'from':
                self.nextToken()
                if self.nextIsSymbol():
                    fileRecord = self.getSymbolRecord()
                    self.checkObjectType(fileRecord['object'], ECFile)
                    command['target'] = symbolRecord['name']
                    command['file'] = fileRecord['name']
                    self.add(command)
                    return True
            return False
        FatalError(self.compiler, f'Symbol "{self.getToken()}" has not been declared')
        return False

    def r_read(self, command):
        symbolRecord = self.getVariable(command['target'])
        fileRecord = self.getVariable(command['file'])
        line = command['line']
        file = fileRecord['file']
        if file.mode == 'r':
            content = file.readline().split('\n')[0] if line else file.read()
            value = ECValue(domain=self.getName(), type='str', content=content)
            self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    # Release the parent script
    def k_release(self, command):
        if self.nextIs('parent'):
            self.add(command)
        return True

    def r_release(self, command):
        self.program.releaseParent()
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
        content = self.getSymbolValue(templateRecord).getContent()
        original = self.getRuntimeValue(command['original'])
        replacement = self.getRuntimeValue(command['replacement'])
        content = content.replace(original, str(replacement))
        value = ECValue(domain=self.getName(), type='str', content=content)
        self.putSymbolValue(templateRecord, value)
        return self.nextPC()

    # Reset a variable
    def k_reset(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            command['target'] = symbolRecord['name']
            self.add(command)
            return True
        return False

    def r_reset(self, command):
        symbolRecord = self.getVariable(command['target'])
        symbolRecord['object'].reset()
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
                else: FatalError(self.compiler, f'Symbol \'name\' is not a module')
            else: FatalError(self.compiler, 'Module name expected after \'as\'')
        else: FatalError(self.compiler, '\'as {module name}\' expected')
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

    # Save a value to a file
    def k_save(self, command):
        command['content'] = self.nextValue()
        self.skip('to')
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['keyword'] == 'ssh':
                command['ssh'] = record['name']
                command['path'] = self.nextValue()
            else:
                command['file'] = self.getValue()
        else:
            command['file'] = self.getValue()
        command['or'] = None
        save = self.getCodeSize()
        self.processOr(command, save)
        return True

    def r_save(self, command):
        errorReason = None
        content = self.getRuntimeValue(command['content'])
        if 'ssh' in command:
            ssh = self.getVariable(command['ssh'])
            path = self.getRuntimeValue(command['path'])
            sftp = ssh['sftp']
            if path.endswith('.json'): content = json.dumps(content)
            try:
                with sftp.open(path, 'w') as remote_file: remote_file.write(content)
            except:
                errorReason = 'Unable to write to {path}'
                if command['or'] != None:
                    print(f'Exception "{errorReason}": Running the "or" clause')
                    return command['or']
                else:
                    RuntimeError(self.program, f'Error: {errorReason}')
        else:
            filename = self.getRuntimeValue(command['file'])
            try:
                with open(filename, 'w') as f: f.write(content)
            except:
                errorReason = f'Unable to write to {filename}'

        if errorReason:
            if command['or'] != None:
                print(f'Exception "{errorReason}": Running the "or" clause')
                return command['or']
            else:
                RuntimeError(self.program, f'Error: {errorReason}')
        return self.nextPC()

    # Provide a name for the script
    def k_script(self, command):
        self.program.name = self.nextToken()
        return True

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
    # set {ssh} host {host} user {user} password {password}
    # set the elements of {variable} to {value}
    # set element/property of {variable} to {value}
    def k_set(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            command['target'] = record['name']
            if record['keyword'] == 'ssh':
                host = None
                user = None
                password = None
                while True:
                    token = self.peek()
                    if token == 'host':
                        self.nextToken()
                        host = self.nextValue()
                    elif token == 'user':
                        self.nextToken()
                        user = self.nextValue()
                    elif token == 'password':
                        self.nextToken()
                        password = self.nextValue()
                    else: break
                command['host'] = host
                command['user'] = user
                command['password'] = password
                command['type'] = 'ssh'
                self.add(command)
                return True
            elif isinstance(record['object'], ECVariable):
                command['type'] = 'set'
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
        
        elif token == 'path':
            command['path'] = self.nextValue()
            self.add(command)
            return True

        return False

    def r_set(self, command):
        cmdType = command['type']
        if cmdType == 'set':
            target = self.getVariable(command['target'])
            self.putSymbolValue(target, ECValue(domain=self.getName(), type='boolean', content=True))
            return self.nextPC()

        elif cmdType == 'elements':
            symbolRecord = self.getVariable(command['name'])
            elements = self.getRuntimeValue(command['elements'])
            self.checkObjectType(symbolRecord['object'], ECObject)
            symbolRecord['object'].setElements(elements)
            return self.nextPC()

        elif cmdType == 'element':
            value = self.getRuntimeValue(command['value'])
            index = self.getRuntimeValue(command['index'])
            target = self.getVariable(command['target'])
            val = self.getSymbolValue(target)
            content = val.getContent()
            if content == '':
                content = []
            # else:
            # 	content = json.loads(content)
            content[index] = value
            val.setContent(content)
            self.putSymbolValue(target, val)
            return self.nextPC()

        elif cmdType == 'encoding':
            self.encoding = self.getRuntimeValue(command['encoding'])
            return self.nextPC()

        elif cmdType == 'path':
            path = self.getRuntimeValue(command['path'])
            os.chdir(path)
            return self.nextPC()

        elif cmdType == 'property':
            name = self.getRuntimeValue(command['name'])
            value = self.evaluate(command['value'])
            record = self.getVariable(command['target'])
            variable = record['object']
            content = variable.getContent()
            if content == None: content = {}
            elif not isinstance(content, dict): raise RuntimeError(self.program, f'{record["name"]} is not a dictionary')
            content[name] = self.getRuntimeValue(value)
            variable.setContent(ECValue(domain=self.getName(), type='dict', content=content))
            return self.nextPC()
        
        elif cmdType == 'ssh':
            target = self.getVariable(command['target'])
            host = self.getRuntimeValue(command['host'])
            user = self.getRuntimeValue(command['user'])
            password = self.getRuntimeValue(command['password'])
            ssh = paramiko.SSHClient()
            target['ssh'] = ssh
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(host, username=user, password=password, timeout=10)
                target['sftp'] = ssh.open_sftp()
            except:
                target['error'] = f'Unable to connect to {host} (timeout)'
            return self.nextPC()

    # Shuffle a JSON list
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
        content = value.getContent()
        if isinstance(content, list):
            random.shuffle(content)
            value.setContent(content)
            self.putSymbolValue(symbolRecord, value)
            return self.nextPC()
        RuntimeError(self.program, f'{symbolRecord["name"]} is not a list')

    # Split a string into a variable with several elements
    # split {variable} on {value}
    def k_split(self, command):
        if self.nextIsSymbol():
            symbolRecord = self.getSymbolRecord()
            if isinstance(symbolRecord['object'], ECObject):
                command['target'] = symbolRecord['name']
                value = ECValue(domain=self.getName(), type='str', content='\n')
                command['on'] = value
                if self.peek() == 'on':
                    self.nextToken()
                    if self.peek() == 'tab':
                        value.setContent('\t')
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
        content = value.getContent().split(self.getRuntimeValue(command['on']))
        elements = len(content)
        object = target['object']
        object.setElements(elements)
        
        for n in range(0, elements):
            val = ECValue(domain=self.getName(), type='str', content=content[n])
            object.setIndex(n)
            object.setValue(val)
        object.setIndex(0)

        return self.nextPC()

    # Declare an SSH connection variable
    def k_ssh(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECSSH')

    def r_ssh(self, command):
        return self.nextPC()

    # Declare a stack variable
    def k_stack(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECStack')

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
    # take {value} from {variable}
    # take {value1} from {value2} giving {variable}
    def k_take(self, command):
        # Get the (first) value
        command['value1'] = self.nextValue()
        self.skip('from')
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            self.checkObjectType(record, ECObject)
            # If 'giving' comes next, this variable is the second value
            if self.peek() == 'giving':
                v2 = ECValue(domain=self.getName(), type='symbol')
                v2.setContent(record['name'])
                command['value2'] = v2
                self.nextToken()
                # Now get the target variable
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    self.checkObjectType(record, ECVariable)
                    command['target'] = record['name']
                self.add(command)
                return True
            else:
                # Here the variable is the target
                command['target'] = record['name']
                self.add(command)
                return True
        else:
            # Here we have 2 values so 'giving' must come next
            command['value2'] = self.getValue()
            if self.nextToken() == 'giving':
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    self.checkObjectType(record, ECVariable)
                    command['target'] = record['name']
                self.add(command)
                return True
            raise FatalError(self.compiler, 'Cannot subtract values: target variable expected')
        return False

    def r_take(self, command):
        value1 = self.getRuntimeValue(command['value1'])
        value2 = self.getRuntimeValue(command['value2']) if 'value2' in command else None
        target = self.getVariable(command['target'])
        # Check that the target variable can hold a value
        self.checkObjectType(target, ECVariable)
        # If value2 exists, we are adding two values and storing the result in target
        if value2 != None:
            # take X from Y giving Z
            targetValue = ECValue(domain=self.getName(), type='int', content=value2 - value1)
        else:
            # take X from Y
            targetValue = self.getSymbolValue(target)
            targetValue.setContent(targetValue.getContent() - value1)
        self.putSymbolValue(target, targetValue)
        return self.nextPC()

    # Toggle a boolean value
    def k_toggle(self, command):
        if self.nextIsSymbol():
            target = self.getSymbolRecord()
            self.checkObjectType(target, ECVariable)
            command['target'] = target['name']
            self.add(command)
            return True
        return False

    def r_toggle(self, command):
        target = self.getVariable(command['target'])
        value = self.getSymbolValue(target)
        val = ECValue(domain=self.getName(), type='boolean', content=not value.getContent())
        self.putSymbolValue(target, val)
        self.add(command)
        return self.nextPC()

    # Trim whitespace from a variable
    def k_trim(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['hasValue']:
                command['name'] = record['name']
                self.add(command)
                return True
        return False

    def r_trim(self, command):
        record = self.getVariable(command['name'])
        value = record['value'][record['index']]
        if value.getType() == 'str':
            content = value.getContent()
            value.setContent(content.strip())
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

    # Use a plugin module
    def k_use(self, command):
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
            token = self.nextToken()
            if token == 'graphics':
                return self.program.useGraphics()
        return False

    # Declare a general-purpose variable
    def k_variable(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECVariable')

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
        test = self.getCodeSize()
        self.add(command)
        # Set up a goto for when the test fails
        fail = self.getCodeSize()
        cmd = {}
        cmd['lino'] = command['lino']
        cmd['domain'] = 'core'
        cmd['keyword'] = 'gotoPC'
        cmd['goto'] = 0
        cmd['debug'] = False
        self.add(cmd)
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
        self.add(cmd)
        # Fixup the 'goto' on completion
        self.getCommandAt(fail)['goto'] = self.getCodeSize()
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
        self.checkObjectType(symbolRecord['object'], ECVariable)
        value = self.getSymbolValue(symbolRecord)
        content = value.getContent()
        if not isinstance(content, int):
            RuntimeError(self.program, f'Variable {symbolRecord["name"]} does not hold an integer')
        if mode == '+': value.setContent(content + 1)
        else: value.setContent(content - 1)
        self.putSymbolValue(symbolRecord, value)
        return self.nextPC()

    #############################################################################
    # Compile a value in this domain
    def compileValue(self):
        value = ECValue(domain=self.getName())
        token = self.getToken()
        if self.isSymbol():
            value.setValue(type='symbol', content=token)
            return value

        value.setType(token)

        if token == 'arg':
            self.nextToken()
            value.setProperty('index', self.getValue())
            return value

        if token in ['cos', 'sin', 'tan']:
            value.setProperty('angle', self.nextValue())
            if self.nextToken() == 'radius':
                value.setProperty('radius', self.nextValue())
                return value
            return None

        if token in ['now', 'today', 'newline', 'tab', 'empty']:
            return value

        if token in ['stringify', 'prettify', 'json', 'lowercase', 'uppercase', 'hash', 'random', 'float', 'integer', 'encode', 'decode']:
            value.setContent(self.nextValue())
            return value

        if (token in ['datime', 'datetime']):
            value.setType('datime')
            value.setProperty('timestamp', self.nextValue())
            if self.peek() == 'format':
                self.nextToken()
                value.setProperty('format', self.nextValue())
            else:
                value.setProperty('format', None)
            return value

        if token == 'element':
            value.setProperty('index', self.nextValue())
            if self.nextToken() == 'of':
                if self.nextIsSymbol():
                    symbolRecord = self.getSymbolRecord()
                    self.checkObjectType(symbolRecord['object'], ECVariable)
                    value.setProperty('target', ECValue(domain=self.getName(), type='symbol', content=symbolRecord['name']))
                    return value
            return None

        if token == 'property':
            value.setProperty('name', self.nextValue())
            if self.nextToken() == 'of':
                if self.nextIsSymbol():
                    symbolRecord = self.getSymbolRecord()
                    object = symbolRecord['object']
                    self.checkObjectType(object, ECObject)
                    if hasattr(object, 'name'):
                        value.setProperty('target', ECValue(domain=self.getName(), type='symbol', content=object.name))
                        return value
                    raise RuntimeError(self.program, f'Object {symbolRecord["name"]} has no attribute "name"')
                    # if object.hasProperties():
                    #     if  object.hasProperty('name'):
                    #         value.setProperty('target', ECValue(domain=self.getName(), type='symbol', content=object.getProperty('name')))
                    #         return value
                    #     raise RuntimeError(self.program, f'Object {symbolRecord["name"]} has no property "name"')
                    # raise FatalError(self.compiler, f'Object {symbolRecord["name"]} has no properties')
            return None

        if token == 'arg':
            value.setContent(self.nextValue())
            if self.getToken() == 'of':
                if self.nextIsSymbol():
                    symbolRecord = self.getSymbolRecord()
                    if symbolRecord['keyword'] == 'variable':
                        value.setProperty('target', symbolRecord['name'])
                        return value
            return None

        if token == 'trim':
            self.nextToken()
            value.setContent(self.getValue())
            return value

        if self.getToken() == 'the':
            self.nextToken()

        token = self.getToken()
        value.setType(token)

        if token == 'args':
           return value

        if token == 'elements':
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    value.setProperty('name', self.getToken())
                    return value
            return None

        if token == 'keys':
            if self.nextIs('of'):
                value.setProperty('name', self.nextValue())
                return value
            return None

        if token == 'count':
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    object = self.getSymbolRecord()['object']
                    if isinstance(object, ECVariable):
                        value.setContent(object)
                        return value
            return None

        if token == 'index':
            if self.nextIs('of'):
                if self.nextIsSymbol():
                    value.setProperty('variable', self.getSymbolRecord()['name'])
                    if self.peek() == 'in':
                        value.setProperty('value', None)
                        value.setType('indexOf')
                        if self.nextIsSymbol():
                            value.setProperty('target', self.getSymbolRecord()['name'])
                            return value
                    else:
                        value.setProperty('name', self.getToken())
                        return value
                else:
                    value.setProperty('value', self.getValue())
                    if self.nextIs('in'):
                        value.setProperty('variable', None)
                        value.setType('indexOf')
                        if self.nextIsSymbol():
                            value.setProperty('target', self.getSymbolRecord()['name'])
                            return value
            return None

        if token == 'value':
            if self.nextIs('of'):
                v = self.nextValue()
                if v !=None:
                    value.setValue(type='valueOf', content=v)
                    return value
            return None

        if token == 'length':
            value.setType('lengthOf')
            if self.nextIs('of'):
                value.setContent(self.nextValue())
                return value
            return None

        if token in ['left', 'right']:
            value.setProperty('count', self.nextValue())
            if self.nextToken() == 'of':
                value.setContent(self.nextValue())
                return value
            return None

        if token == 'from':
            value.setProperty('start', self.nextValue())
            if self.peek() == 'to':
                self.nextToken()
                value.setProperty('to', self.nextValue())
            else:
                value.setProperty('to', None)
            if self.nextToken() == 'of':
                value.setContent(self.nextValue())
                return value

        if token == 'position':
            if self.nextIs('of'):
                value.setProperty('last', False)
                if self.nextIs('the'):
                    if self.nextIs('last'):
                        self.nextToken()
                        value.setProperty('last', True)
                value.setProperty('needle', self.getValue())
                if self.nextToken() == 'in':
                    value.setProperty('haystack', self.nextValue())
                    return value

        if token == 'message':
            return value

        if token == 'timestamp':
            value.setProperty('format', None)
            if self.peek() == 'of':
                self.nextToken()
                value.setProperty('datime', self.nextValue())
                if self.peek() == 'format':
                    self.nextToken()
                    value.setProperty('format', self.nextValue())
            return value

        if token == 'files':
            token = self.nextToken()
            if token in ['in', 'of']:
                value.setProperty('target', self.nextValue())
                return value
            return None

        if token == 'weekday':
            value.setType('weekday')
            return value

        if token == 'mem' or token == 'memory':
            value.setType('memory')
            return value

        if token == 'error':
            token = self.peek()
            if token == 'code':
                self.nextToken()
                value.setProperty('item', 'errorCode')
                return value
            elif token == 'reason':
                self.nextToken()
                value.setProperty('item', 'errorReason')
                return value
            elif token in ['in', 'of']:
                self.nextToken()
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    if isinstance(record['object'], ECSSH):
                        value.setProperty('item', 'sshError')
                        value.setProperty('name', record['name'])
                        return value
            return None

        if token == 'type':
            if self.nextIs('of'):
                value.setProperty('value', self.nextValue())
                return value
            return None

        if token == 'modification':
            if self.nextIs('time'):
                if self.nextIs('of'):
                    value.setProperty('fileName', self.nextValue())
                    return value
            return None

        if token == 'system':
            value.setContent(self.nextValue())
            return value

        if token == 'ticker':
            return value

        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        if self.peek() == 'modulo':
            self.nextToken()
            mv = ECValue(domain=self.getName(), type='modulo', content=value)
            mv.setProperty('modval', self.nextValue())
            return mv

        return value

    #############################################################################
    # Value handlers

    def v_args(self, v):
        return ECValue(domain=self.getName(), type='str', content=json.dumps(self.program.argv))

    def v_arg(self, v):
        index = self.getRuntimeValue(v['index'])
        if index >= len(self.program.argv):
            RuntimeError(self.program, 'Index exceeds # of args')
        return ECValue(domain=self.getName(), type='str', content=self.program.argv[index])

    def v_boolean(self, v):
        value = ECValue(domain=self.getName(), type='boolean', content=v.getContent())

    def v_cos(self, v):
        angle = self.getRuntimeValue(v['angle'])
        radius = self.getRuntimeValue(v['radius'])
        return ECValue(domain=self.getName(), type='int', content=round(math.cos(angle * 0.01745329) * radius))

    def v_count(self, v):
        content = self.getRuntimeValue(v.getContent())
        if content == None: raise RuntimeError(self.program, 'Count: No value provided')
        return ECValue(domain=self.getName(), type='int', content=len(content))

    def v_datime(self, v):
        ts = self.getRuntimeValue(v.getProperty('timestamp'))
        fmt = v.getProperty('format')
        if fmt == None:
            fmt = '%b %d %Y %H:%M:%S'
        else:
            fmt = self.getRuntimeValue(fmt)
        return ECValue(domain=self.getName(), type='str', content=datetime.fromtimestamp(ts/1000).strftime(fmt))

    def v_decode(self, v):
        content = self.getRuntimeValue(v.getContent())
        value = ECValue(domain=self.getName(), type='str')
        if self.encoding == 'utf-8':
            value.setContent(content.decode('utf-8'))
        elif self.encoding == 'base64':
            base64_bytes = content.encode('ascii')
            message_bytes = base64.b64decode(base64_bytes)
            value.setContent(message_bytes.decode('ascii'))
        elif self.encoding == 'hex':
            hex_bytes = content.encode('utf-8')
            message_bytes = binascii.unhexlify(hex_bytes)
            value.setContent(message_bytes.decode('utf-8'))
        else:
            value = v
        return value

    def v_element(self, v):
        index = self.getRuntimeValue(v.getProperty('index'))
        targetName = v.getProperty('target')
        target = self.getVariable(targetName.getContent())
        variable = target['object']
        self.checkObjectType(variable, ECObject)
        content = variable.getContent()
        if not type(content) == list:
            RuntimeError(self.program, f'{targetName} is not a list')
        if index >= len(content):
            RuntimeError(self.program, f'Index out of range in {targetName}')
        targetValue = content[index]
        if isinstance(targetValue, ECValue):
            targetValue = self.getRuntimeValue(targetValue)
        return targetValue

    def v_elements(self, v):
        var = self.getVariable(v.getProperty('name'))
        object = var['object']
        self.checkObjectType(object, ECVariable)
        return ECValue(domain=self.getName(), type='int', content=object.getElements())

    def v_empty(self, v):
        return ECValue(domain=self.getName(), type='str', content=''  )

    def v_encode(self, v):
        content = self.getRuntimeValue(v.getContent())
        value = ECValue(domain=self.getName(), type='str')
        if self.encoding == 'utf-8':
            value.setContent(content.encode('utf-8'))
        elif self.encoding == 'base64':
            data_bytes = content.encode('ascii')
            base64_bytes = base64.b64encode(data_bytes)
            value.setContent(base64_bytes.decode('ascii'))
        elif self.encoding == 'hex':
            data_bytes = content.encode('utf-8')
            hex_bytes = binascii.hexlify(data_bytes)
            value.setContent(hex_bytes.decode('utf-8'))
        else:
            value = v
        return value

    def v_error(self, v):
        global errorCode, errorReason
        value = ECValue(domain=self.getName())
        item = v.getProperty('item')
        if item == 'errorCode':
            value.setValue(type='int', content=errorCode)
        elif item == 'errorReason':
            value.setValue(type='str', content=errorReason)
        elif item == 'sshError':
            record = self.getVariable(v.getProperty('name'))
            value.setValue(type='str', content=record['error'] if 'error' in record else '')
        return value

    def v_files(self, v):
        path = self.getRuntimeValue(v.getProperty('target'))
        return ECValue(domain=self.getName(), type='str', content=json.dumps(os.listdir(path)))

    def v_float(self, v):
        val = self.getRuntimeValue(v.getContent())
        value = ECValue(domain=self.getName(), type='float')
        try:
            value.setContent(float(val))
        except:
            RuntimeWarning(self.program, f'Value cannot be parsed as floating-point')
            value.setContent(0.0)
        return value

    def v_from(self, v):
        content = self.getRuntimeValue(v.getContent())
        start = self.getRuntimeValue(v.getProperty('start'))
        to = self.getRuntimeValue(v.getProperty('to'))
        if start is not None and type(start) != int:
            RuntimeError(self.program, 'Invalid "from" value')
        if to is not None and type(to) != int:
            RuntimeError(self.program, 'Invalid "to" value')
        return ECValue(domain=self.getName(), type='str', content=content[start:] if to == None else content[start:to])

    def v_hash(self, v):
        hashval = self.getRuntimeValue(v.getContent())
        return ECValue(domain=self.getName(), type='str', content=hashlib.sha256(hashval.encode('utf-8')).hexdigest())

    def v_index(self, v):
        return ECValue(domain=self.getName(), type='int', content=self.getVariable(v['name'])['index'])

    def v_indexOf(self, v):
        value = v.getProperty('value')
        if value == None:
            value = self.getSymbolValue(v.getProperty('variable')).getContent()
        else:
            value = self.getRuntimeValue(value)
        target = self.getVariable(v.getProperty('target'))
        data = self.getSymbolValue(target).getContent()
        try: index = data.index(value)
        except: index = -1
        return ECValue(domain=self.getName(), type='int', content=index)

    def v_integer(self, v):
        val = self.getRuntimeValue(v.getValue())
        return ECValue(domain=self.getName(), type='int', content=int(val))

    def v_json(self, v):
        item = self.getRuntimeValue(v.getContent())
        value = ECValue(domain=self.getName())
        try:
            v = json.loads(item)
            if type(v) == list: value.setType('list')
            elif type(v) == dict: value.setType('dict')
            else: value.setType('str')  
            value.setContent(v)
        except:
            value = None
        return value

    def v_keys(self, v):
        value = self.getRuntimeValue(v.getProperty('name'))
        return ECValue(domain=self.getName(), type='list', content=list(value.keys())) # type: ignore

    def v_left(self, v):
        content = self.getRuntimeValue(v.getContent())
        count = self.getRuntimeValue(v.getProperty('count'))
        return ECValue(domain=self.getName(), type='str', content=content[0:count])

    def v_lengthOf(self, v):
        content = self.getRuntimeValue(v.getContent())
        if type(content) == str:
            return ECValue(domain=self.getName(), type='int', content=len(content))
        RuntimeError(self.program, 'Value is not a string')

    def v_lowercase(self, v):
        content = self.getRuntimeValue(v.getValue())
        return ECValue(domain=self.getName(), type='str', content=content.lower())

    def v_memory(self, v):
        process: Process = Process(os.getpid())
        megabytes: float = process.memory_info().rss / (1024 * 1024)
        return ECValue(domain=self.getName(), type='float', content=megabytes)

    def v_message(self, v):
        return ECValue(domain=self.getName(), type='str', content=self.program.message)

    def v_modification(self, v):
        fileName = self.getRuntimeValue(v['fileName'])
        ts = int(os.stat(fileName).st_mtime)
        return ECValue(domain=self.getName(), type='int', content=ts)

    def v_modulo(self, v):
        val = self.getRuntimeValue(v.getContent())
        modval = self.getRuntimeValue(v.getProperty('modval'))
        return ECValue(domain=self.getName(), type='int', content=val % modval)

    def v_newline(self, v):
        return ECValue(domain=self.getName(), type='str', content='\n')

    def v_now(self, v):
        return ECValue(domain=self.getName(), type='int', content=int(time.time()))

    def v_position(self, v):
        needle = self.getRuntimeValue(v.getProperty('needle'))
        haystack = self.getRuntimeValue(v.getProperty('haystack'))
        last = v.getProperty('last')
        return ECValue(domain=self.getName(), type='int', content=haystack.rfind(needle) if last else haystack.find(needle))

    def v_prettify(self, v):
        item = self.getRuntimeValue(v.getContent())
        return ECValue(domain=self.getName(), type='str', content=json.dumps(item, indent=4))

    def v_property(self, v):
        propertyName = v.getProperty('name')
        propertyValue = self.getRuntimeValue(propertyName)
        targetName = v.getProperty('target')
        targetValue = self.getRuntimeValue(targetName)
        try:
            targetObject = json.loads(targetValue)
        except:
            targetObject = targetValue
        if type(targetObject) != dict:
            RuntimeError(self.program, f'{targetName} is not a dictionary')
        if not propertyValue in targetObject:
            RuntimeError(self.program, f'This value does not have the property \'{propertyValue}\'')
        value = targetObject[propertyValue]
        if isinstance(value, ECValue):
            value = self.getRuntimeValue(value)
        return value

    def v_random(self, v):
        limit = self.getRuntimeValue(v.getValue())
        return ECValue(domain=self.getName(), type='int', content=random.randrange(0, limit))

    def v_right(self, v):
        content = self.getRuntimeValue(v.getContent())
        count = self.getRuntimeValue(v.getProperty('count'))
        return ECValue(domain=self.getName(), type='str', content=content[-count:])

    def v_sin(self, v):
        angle = self.getRuntimeValue(v.getProperty('angle'))
        radius = self.getRuntimeValue(v.getProperty('radius'))
        return ECValue(domain=self.getName(), type='int', content=round(math.sin(angle * 0.01745329) * radius))

    def v_stringify(self, v):
        item = self.getRuntimeValue(v.getContent())
        self.checkObjectType(item, (dict, list))
        return ECValue(domain=self.getName(), type='str', content=json.dumps(item))

    # This is used by the expression evaluator to get the value of a symbol
    def v_symbol(self, v):
        name = v.getProperty('name')
        symbolRecord = self.program.getSymbolRecord(name)
        keyword = symbolRecord['keyword']
        if keyword == 'object':
            return symbolRecord['object'].getValue()
        elif keyword == 'variable':
            return self.getSymbolValue(symbolRecord)
        elif keyword == 'ssh':
            return ECValue(domain=self.getName(), type='boolean', content=True if 'ssh' in symbolRecord and symbolRecord['ssh'] != None else False)
        else:
            return None

    def v_system(self, v):
        command = self.getRuntimeValue(v.getContent())
        result = os.popen(command).read()
        return ECValue(domain=self.getName(), type='str', content=result)

    def v_tab(self, v):
        return ECValue(domain=self.getName(), type='str', content='\t')

    def v_tan(self, v):
        angle = self.getRuntimeValue(v['angle'])
        radius = self.getRuntimeValue(v['radius'])
        return ECValue(domain=self.getName(), type='int', content=round(math.tan(angle * 0.01745329) * radius))

    def v_ticker(self, v):
        return ECValue(domain=self.getName(), type='int', content=self.program.ticker)

    def v_timestamp(self, v):
        value = ECValue(domain=self.getName(), type='int')
        fmt = v.getProperty('format')
        if fmt == None:
            value.setContent(int(time.time()))
        else:
            fmt = self.getRuntimeValue(fmt)
            dt = self.getRuntimeValue(v.getProperty('datetime'))
            spec = datetime.strptime(dt, fmt)
            t = datetime.now().replace(hour=spec.hour, minute=spec.minute, second=spec.second, microsecond=0)
            value.setContent(int(t.timestamp()))
        return value

    def v_today(self, v):
        return ECValue(domain=self.getName(), type='int', content=int(datetime.combine(datetime.now().date(),datetime.min.time()).timestamp()) * 1000)

    def v_trim(self, v):
        content = v.getContent()
        content = self.getRuntimeValue(content)
        return ECValue(domain=self.getName(), type='str', content=content.strip())

    def v_type(self, v):
        value = ECValue(domain=self.getName(), type='str')
        val = self.getRuntimeValue(v['value'])
        if val is None:
            value.setContent('none')
        elif type(val) is str:
            value.setContent('str')
        elif type(val) is int:
            value.setContent('numeric')
        elif type(val) is bool:
            value.setContent('boolean')
        elif type(val) is list:
            value.setContent('list')
        elif type(val) is dict:
            value.setContent('dict')
        return value

    def v_uppercase(self, v):
        content = self.getRuntimeValue(v.getContent())
        return ECValue(domain=self.getName(), type='str', content=content.upper())

    def v_valueOf(self, v):
        v = self.getRuntimeValue(v.getContent())
        return ECValue(domain=self.getName(), type='int', content=int(v) if v != '' else 0)
    
    def v_variable(self, v):
        name = v.getContent()
        symbolRecord = self.program.getSymbolRecord(name)
        variable = symbolRecord['object']
        self.checkObjectType(variable, ECVariable)
        value = variable.getValue()
        return value

    def v_weekday(self, v):
        return ECValue(domain=self.getName(), type='int', content=datetime.today().weekday())

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = Object()
        condition.negate = False

        token = self.getToken()

        if token == 'not':
            condition.type = 'not'
            condition.value = self.nextValue()
            return condition

        elif token == 'error':
            self.nextToken()
            self.skip('in')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'ssh':
                    condition.type = 'sshError'
                    condition.target = record['name']
                    return condition
            return None

        elif token == 'file':
            path = self.nextValue()
            condition.path = path
            condition.type = 'exists'
            self.skip('on')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'ssh':
                    condition.type = 'sshExists'
                    condition.target = record['name']
                    token = self.nextToken()
            else: token = self.getToken()
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
        elif type(value) == str or type(value) == list or type(value) == dict:
            comparison = len(value) == 0
        else:
            domainName = condition.value1.domain
            domain = self.program.domainIndex[domainName] # type: ignore
            handler = domain.valueHandler('empty') # type: ignore
            if handler: comparison = self.getRuntimeValue(handler(condition.value1))
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
    
    def c_sshError(self, condition):
        target = self.getVariable(condition.target)
        errormsg = target['error'] if 'error' in target else None
        condition.errormsg = errormsg
        test = errormsg != None
        return not test if condition.negate else test

    def c_sshExists(self, condition):
        path = self.getRuntimeValue(condition.path)
        ssh = self.getVariable(condition.target)
        sftp = ssh['sftp']
        try:
            with sftp.open(path, 'r') as remote_file: remote_file.read().decode()
            comparison = True
        except:
            comparison = False
        return not comparison if condition.negate else comparison

    def c_starts(self, condition):
        value1 = self.getRuntimeValue(condition.value1)
        value2 = self.getRuntimeValue(condition.value2)
        return value1.startswith(value2)

    def c_string(self, condition):
        comparison = type(self.getRuntimeValue(condition.value1)) is str
        return not comparison if condition.negate else comparison
