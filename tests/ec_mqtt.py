import time
import uuid
from easycoder import Handler, ECObject, ECValue, RuntimeError
import paho.mqtt.client as mqtt
    
#############################################################################
# MQTT client class
class MQTTClient():
    def __init__(self):
        super().__init__()

    def create(self, program=None, clientID='EasyCoder-MQTT-Hub', broker='EasyCoder-MQTT-Hub', port=1883, topics=None):
        self.program = program
        # Avoid client ID collisions on public brokers
        clientID += f"-{uuid.uuid4().hex[:6]}"
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.topics = [] if topics is None else topics
        self.onMessagePC = None
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.clientID) # type: ignore
        self.client.reconnect_delay_set(min_delay=1, max_delay=5)
    
        # Setup callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, reason_code, properties):
        print(f"Client {self.clientID} connected")
        if self.program is None:
            for item in self.topics:
                self.client.subscribe(item.get('name'), qos=item.get('qos', 1))
                print(f"Subscribe to topic: {item} (program is None)")
        else:
            for item in self.topics:
                topic = self.program.getObject(self.program.getVariable(item))
                self.client.subscribe(topic.getName(), qos=topic.getQOS())
                print(f"Subscribed to topic: {topic.getName()} with QoS {topic.getQOS()}")

    def on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        try:
            code_val = reason_code.value if hasattr(reason_code, 'value') else reason_code
        except Exception:
            code_val = reason_code
        print(f"Disconnected: reason_code={code_val}") 

    def on_message(self, client, userdata, msg):
        # print(f"Message received on topic {msg.topic}: {msg.payload.decode()}")
        if self.program is None:
            try:
                payload = msg.payload.decode('utf-8')
            except Exception:
                payload = msg.payload
            print(f"[standalone] {msg.topic}: {payload}")
        elif self.onMessagePC is not None:
            self.message = msg
            if self.program is not None:
                self.program.run(self.onMessagePC)
                self.program.flushCB()
    
    def getMessageTopic(self):
        return self.message.topic
    
    def getMessagePayload(self):
        return self.message.payload.decode('utf-8')

    def onMessage(self, pc):
        self.onMessagePC = pc
    
    def sendMessage(self, topic, message, qos):
        self.client.publish(topic, message, qos=qos)
    
    def run(self):
        self.client.connect(self.broker, int(self.port), 60)
        self.client.loop_start()
        
###############################################################################
# An MQTT topic
class ECTopic(ECObject):
    def __init__(self):
        super().__init__()

    def create(self, name, qos=1):
        super().__init__()
        super().setName(name)
        self.qos = qos

    def getName(self):
        return super().getName()

    def getQOS(self):
        return self.qos

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

    # init {topic} name {name} qos {qos}
    def k_init(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            self.checkObjectType(record, ECTopic)
            command['topic'] = record['name']
            self.skip('name')
            command['name'] = self.nextValue()
            self.skip('qos')
            command['qos'] = self.nextValue()
            self.add(command)
            return True
        return False

    def r_init(self, command):
        record = self.getVariable(command['topic'])
        topic = ECTopic()
        topic.create(self.textify(command['name']), qos=int(self.textify(command['qos'])))
        record['object'] = topic
        return self.nextPC()

    # mqtt id {clientID} broker {broker} port {port} topics {topic} [and {topic} ...]
    def k_mqtt(self, command):
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
            elif token == 'topics':
                self.nextToken()
                topics = []
                while self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    self.checkObjectType(record, ECTopic())
                    topics.append(record['name'])
                    if self.peek() == 'and': self.nextToken()
                    else:break
                command['topics'] = topics
            else:
                self.add(command)
                return True
        return False

    def r_mqtt(self, command):
        if hasattr(self.program, 'mqttClient'):
            raise RuntimeError(self.program, 'MQQT client already defined')
        clientID = self.textify(command['clientID'])
        broker = self.textify(command['broker'])
        port = self.textify(command['port'])
        topics = command['topics']
        client = MQTTClient()
        client.create(self.program, clientID, broker, port, topics)
        client.run()
        self.program.mqttClient = client
        return self.nextPC()

    # on mqtt message {action}
    def k_on(self, command):
        token = self.peek()
        if token == 'mqtt':
            self.nextToken()
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
        self.program.mqttClient.onMessage(self.nextPC()+1)
        return command['goto']

    # send {message} to {topic}
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
        if not hasattr(self.program, 'mqttClient'):
            raise RuntimeError(self.program, 'No MQTT client defined')
        topic = self.getObject(self.getVariable(command['to']))
        message = self.textify(command['message'])
        self.program.mqttClient.sendMessage(topic.getName(), message, topic.getQOS())
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
        token = self.nextToken()
        if token == 'mqtt':
            value = ECValue(domain=self.getName())
            token = self.nextToken()
            if token in ['topic', 'message']:
                value.setType(token)
                return value
        else:
            return self.getValue()
        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        return value

    #############################################################################
    # Value handlers

    def v_message(self, v):
        return self.program.mqttClient.getMessagePayload()

    def v_topic(self, v):
        return self.program.mqttClient.getMessageTopic()

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers

if __name__ == '__main__':

    clientID = 'EasyCoder-MQTT-Hub'
    broker = 'test.mosquitto.org'
    port = 1883
    request = {'name': '38:54:39:34:62:d7/request', 'qos': 1}
    response = {'name': '38:54:39:34:62:d7/response', 'qos': 1}
    topics = [request]

    client = MQTTClient()
    client.create(program=None, clientID=clientID, broker=broker, port=port, topics=topics)
    client.run()

    print(f"Subscribed to {request['name']} on {broker}:{port}. Waiting for messages (Ctrl+C to exit)...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        client.client.loop_stop()