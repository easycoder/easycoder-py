from easycoder import Handler, ECObject, ECValue, ECDictionary, FatalError, RuntimeError
import paho.mqtt.client as mqtt
    
#############################################################################
# MQTT client class
class MQTTClient():
    def __init__(self):
        super().__init__()

    def create(self, program, clientID, broker, port, request, response):
        self.program = program
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.request = request
        self.response = response
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.clientID) # type: ignore
    
        # Setup callbacks
        self.client.on_connect = self.onConnect
        self.client.on_message = self.onMessage

    def onConnect(self, client, userdata, flags, reason_code, properties):
        print(f"Client {self.clientID} connected")
        self.client.subscribe(self.request.name, qos=self.request.qos)
    
    def onMessage(self, client, userdata, msg):
        print(msg.payload.decode())
    
    def sendMessage(self, text):
        self.client.publish(self.response.name, text, qos=self.response.qos)
    
    def run(self):
        self.client.connect(self.broker, int(self.port), 60)
        self.client.loop_start()
        
###############################################################################
# An MQTT hub
class ECHub(ECObject):
    def __init__(self):
        super().__init__()
    
    def create(self, program, clientID, broker, port, request, response):
        self.client = MQTTClient()
        self.client.create(program, clientID, broker, port, request, response)
    
    def onMessage(self, client, userdata, msg):
        print(f"Topic: {msg.topic}\nMessage: {msg.payload.decode()}")
        # Echo message back to response topic
        self.client.sendMessage(msg.payload.decode())
        
###############################################################################
# An MQTT spoke
class ECSpoke(ECObject):
    def __init__(self):
        super().__init__()
    
    def create(self, program, clientID, broker, port, request, response):
        self.client = MQTTClient()
        self.client.create(program, clientID, broker, port, request, response)
        if hasattr(program.handler, 'spoke'):
            raise FatalError(program, 'Only one MQTT spoke can be defined per program')
        program.handler.spoke = self

    def onMessage(self, client, userdata, msg):
        print(f"Topic: {msg.topic}\nMessage: {msg.payload.decode()}")
        # Echo message back to response topic
        self.client.sendMessage(msg.payload.decode())
        
###############################################################################
# An MQTT topic
class ECTopic(ECObject):
    def __init__(self):
        super().__init__()

###############################################################################
# The MQTT compiler and rutime handlers
class MQTT(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)
        self.spoke = None

    def getName(self):
        return 'mqtt'

    #############################################################################
    # Keyword handlers

    # create {hub/spoke} id {clientID} broker {broker} port {port} request {topic} response {topic}
    def k_create(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            self.checkObjectType(record, MQTTClient)
            command['client'] = record['name']
            while True:
                token = self.peek()
                if token == 'id':
                    self.nextToken()
                    command['clientID'] = self.nextValue()
                elif token == 'broker':
                    self.nextToken()
                    command['broker'] = self.nextValue()
                elif token == 'port':
                    self.nextToken()
                    command['port'] = self.nextValue()
                elif token == 'request':
                    self.nextToken()
                    if self.nextIsSymbol():
                        record = self.getSymbolRecord()
                        self.checkObjectType(record, ECDictionary())
                        command['request'] = self.nextValue()
                    else: return False
                elif token == 'response':
                    self.nextToken()
                    if self.nextIsSymbol():
                        record = self.getSymbolRecord()
                        self.checkObjectType(record, ECDictionary())
                        command['response'] = self.nextValue()
                    else: return False
                else:
                    break
            self.add(command)
            return True
        return False

    def r_create(self, command):
        record = self.getVariable(command['client'])
        clientID = self.textify(command['clientID'])
        broker = self.textify(command['broker'])
        port = self.textify(command['port'])
        request = self.getObject(self.getVariable(command['request']))
        response = self.getObject(self.getVariable(command['response']))
        object = self.getObject(record)
        if isinstance(object, ECHub):
            client = ECHub()
            client.create(self.program, clientID, broker, port, request, response)
        else:
            client = ECSpoke()
            client.create(self.program, clientID, broker, port, request, response)
        client.run()
        return self.nextPC()

    # Declare a hub variable
    def k_hub(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECHub')

    def r_hub(self, command):
        return self.nextPC()

    # Send a message from one client to another
    def k_send(self, command):
        if self.nextIs('mqtt'):
            command['message'] = self.nextValue()
            self.skip('from')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                self.checkObjectType(record, MQTTClient)
                command['from'] = record['name']
            self.skip('to')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                self.checkObjectType(record, MQTTClient)
                command['to'] = record['name']
            self.add(command)
            return True
        return False

    def r_send(self, command):
        if self.spoke == None:
            raise RuntimeError(self.program, 'No MQTT spoke defined')
        topic = self.textify(command['topic'])
        message = self.textify(command['message'])
        self.spoke.sendMessage(topic, message)
        return self.nextPC()

    # Declare a spoke variable
    def k_spoke(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECSpoke')

    def r_spoke(self, command):
        return self.nextPC()

    # Declare a topic variable
    def k_topic(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECTopic')

    def r_topic(self, command):
        return self.nextPC()

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

'''
###############################################################################
# Standalone test code for hub/spoke without EasyCoder
if __name__ == "__main__":
    import time
    
    print(f"\n{'='*40}")
    print(f"MQTT Hub/Spoke Test")
    print(f"{'='*40}\n")
    
    # Create and start hub
    print("1. Creating hub...")
    hub = MQTTClient(
        clientID="Test-Hub",
        broker="test.mosquitto.org",
        port=1883,
        request = {'name': 'EasyCoder-MQTT/request', 'qos': 1},
        response = {'name': 'EasyCoder-MQTT/response', 'qos': 1}
    )
    hub.run()
    time.sleep(2)  # Wait for connection
    
    # Create and start spoke
    print("\n2. Creating spoke...")
    spoke = MQTTClient(
        clientID="Test-Spoke",
        broker="test.mosquitto.org",
        port=1883,
        request = {'name': 'EasyCoder-MQTT/request', 'qos': 1},
        response = {'name': 'EasyCoder-MQTT/response', 'qos': 1}
    )
    spoke.run()
    time.sleep(2)  # Wait for connection
    
    # Send test message
    print("\n3. Sending test message from spoke...")
    spoke.sendMessage('EasyCoder-MQTT/request', "Hello from standalone test!")
    
    # Wait for message to be received
    print("\n4. Waiting for message to arrive at hub...")
    time.sleep(3)
    
    print("\n5. Test complete. If you see 'Topic:' and message above, it worked!")
    print(f"{'='*60}\n")
'''