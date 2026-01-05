from easycoder import Handler, ECValue, ECObject, FatalError, RuntimeError
import paho.mqtt.client as mqtt

###############################################################################
# An MQTT client variable
class ECMQTTClient(ECObject):
    def __init__(self):
        super().__init__()

###############################################################################
# The MQTT compiler and rutime handlers
class MQTT(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'mqtt'

    #############################################################################
    # Keyword handlers

    # mqtt setup {client} {clientID}
    # mqtt run {client} with {broker} port {port}
    def k_mqtt(self, command):
        subcommand = self.nextToken()
        command['subcommand'] = subcommand
        if subcommand == 'setup':
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                self.checkObjectType(record, 'ECMQTTClient')
                command['client'] = record['name']
                command['clientID'] = self.nextValue()
                self.add(command)
                return True
        elif subcommand == 'run':
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                self.checkObjectType(record, 'ECMQTTClient')
                command['client'] = record['name']
                self.skip('with')
                self.skip('broker')
                command['broker'] = self.nextValue()
                self.skip('port')
                command['port'] = self.nextValue()
                self.add(command)
                return True
        return False

    def r_mqtt(self, command):
        subcommand = command['subcommand']
        if subcommand == 'setup':
            record = self.getVariable(command['client'])
            object = self.getObject(record)
            clientID = command['clientID']
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=clientID) # type: ignore
            object.setValue(client)
        elif subcommand == 'run':
            record = self.getVariable(command['client'])
            object = self.getObject(record)
            client = object.getValue()
            broker = self.textify(command['broker'])
            port = int(self.textify(command['port']))
            client.connect(broker, port, 60)
            client.loop_start()
        return self.nextPC()

    # Declare an MQTT client variable
    def k_mqttclient(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECMQTTClient')

    def r_mqttclient(self, command):
        return self.nextPC()

    # on {mqttclient} connect {action}
    # on {mqttclient} message {action}
    def k_on(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            self.checkObjectType(record, ECMQTTClient)
            command['client'] = record['name']
            token = self.nextToken()
            if token not in ['connect', 'message']:
                raise FatalError(self.compiler, f"Expected 'connect' or 'message'; got {token}")
            command['event'] = token
            self.nextToken()
            # Mark the current location
            command['goto'] = 0
            self.add(command)
            # Add a 'gotoPC' to the next command
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
        def onEvent():
            self.program.runFromPC(self.nextPC()+1)
        client = self.getVariable(command['client'])
        object = self.getObject(client)
        mqtt_client = object.getValue()
        if command['event'] == 'connect':
            mqtt_client.on_connect = onEvent
        elif command['event'] == 'message':
            mqtt_client.on_message = onEvent
        return command['goto']

    #############################################################################
    # Compile a value in this domain
    def compileValue(self):
        value = ECValue(domain=self.getName())
        if self.tokenIs('the'):
            self.nextToken()
        token = self.getToken()
        if token in ['mem', 'memory']:
            value.setType('memory')
            return value
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
