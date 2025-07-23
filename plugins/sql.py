from easycoder import Handler, FatalError, RuntimeError, json

class SQL(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'sql'

    #############################################################################
    # Keyword handlers

    # create {table} {name} [with ...]
    # {name} {flag(s)} {type} [default {value}] [and ..]
    def k_create(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['keyword'] == 'table':
                command['target'] = record['name']
                command['tableName'] = self.nextValue()
                keys = []
                while self.peek() in ['key', 'include']:
                    item = {}
                    token = self.nextToken()
                    if token == 'include':
                        item['include'] = self.nextValue()
                    else:
                        item['name'] = self.nextValue()
                        token = self.peek()
                        if token == 'primary':
                            item['primary'] = True
                            self.nextToken()
                        if token == 'secondary':
                            item['secondary'] = True
                            self.nextToken()
                        elif token == 'required':
                            item['required'] = True
                            self.nextToken()
                        elif token == 'auto':
                            item['required'] = True
                            self.nextToken()
                        item['type'] = self.nextToken()
                        if self.peek() in ['default', '=']:
                            self.nextToken()
                            item['default'] = self.nextValue()
                        elif self.peek() == 'check':
                            self.nextToken()
                            item['check'] = self.nextValue()
                    keys.append(item)
                command['keys'] = keys
                self.add(command)
                return True
        return False

    def r_create(self, command):
        record = self.getVariable(command['target'])
        self.putSymbolValue(record, command)
        return self.nextPC()

    def k_get(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['hasValue']:
                command['target'] = record['name']
                self.skip('from')
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    if record['keyword'] == 'table':
                        command['entity'] = record['name']
                        if self.peek() == 'as':
                            self.nextToken()
                            command['form'] = self.nextToken()
                        else: command['form'] = 'sql'
                        self.add(command)
                return True
        return False

    def r_get(self, command):
        target = self.getVariable(command['target'])
        entity = self.getVariable(command['entity'])
        form = command['form']
        keyword = entity['keyword']
        if keyword == 'table':
            value = self.getSymbolValue(entity)
            tableName = self.getRuntimeValue(value['tableName'])
            output = []
            if form == 'sql':
                # -------------------------------------------------------------
                # Here are the rules for generating SQL
                output.append(f'DROP TABLE IF EXISTS {tableName} CASCADE;')
                output.append(f'CREATE TABLE {tableName} {{')
                secondary = False
                includes = []
                keys = entity['value'][entity['index']]['keys']
                for index, key in enumerate(keys):
                    item = []
                    if 'include' in key:
                        name = self.getRuntimeValue(key['include'])
                        includes.append(f'{name}_id')
                        item = f'{name}_id BIGINT REFERENCES {name}'
                    else:
                        if 'secondary' in key:
                            secondary = True
                            output.append('  id BIGSERIAL PRIMARY KEY,')
                        item.append(self.getRuntimeValue(key['name']))
                        type = key['type']
                        if type == 'string': type = 'text'
                        elif type == 'datetime': type = 'timestamptz'
                        elif type == 'u64': type = 'bigint'
                        item.append(type.upper())
                        if secondary:
                            item.append('UNIQUE NOT NULL')
                            secondary = False
                        if 'primary' in key: item.append('PRIMARY KEY')
                        if 'required' in key: item.append('NOT NULL')
                        if 'default' in key:
                            default = self.getRuntimeValue(key['default'])
                            item.append(f'DEFAULT \'{default}\'')
                        if 'check' in key:
                            check = self.getRuntimeValue(key['check'])
                            item.append(f'CHECK ({check})')
                        item = ' '.join(item)
                    if index < len(keys) - 1 or len(includes) > 0: item = f'{item},'
                    output.append(f'  {item}')
                if len(includes) > 0:
                    includes = ', '.join(includes)
                    item = f'  PRIMARY KEY ({includes})'
                    output.append(item)
                output.append('};')
                # -------------------------------------------------------------
            v = {}
            v['type'] = 'text'
            v['content'] = '\n'.join(output)
            self.putSymbolValue(target, v)
        return self.nextPC()

    def k_table(self, command):
        return self.compileVariable(command, False)

    def r_table(self, command):
        return self.nextPC()

    #############################################################################
    # Compile a value in this domain
    def compileValue(self):
        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        return value

    #############################################################################
    # Value handlers

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers
