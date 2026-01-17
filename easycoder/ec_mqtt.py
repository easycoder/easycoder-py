from easycoder import Handler, ECObject, ECValue, RuntimeError
import paho.mqtt.client as mqtt
import time
import threading
import json
 
#############################################################################
# MQTT client class
class MQTTClient():
    def __init__(self):
        super().__init__()

    def create(self, program, clientID, broker, port, topics):
        self.program = program
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.topics = topics
        self.onConnectPC = None
        self.onMessagePC = None
        self.timeout = False
        self.messages = {}
        self.chunked_messages = {}  # Store incoming chunked messages {topic: {part_num: data}}
        self.chunk_confirmations = {}  # Store confirmations for sent chunks
        self.confirmation_lock = threading.Lock()
        self.chunk_size = 1024  # Default chunk size
        self.chunking_strategy = 'rapid_fire'  # 'sequential' or 'rapid_fire'
        self.last_send_time = None  # Time taken for last message transmission (seconds)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.clientID) # type: ignore
    
        # Setup callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        print(f"Client {self.clientID} connected")
        for item in self.topics:
            topic = self.program.getObject(self.program.getVariable(item))
            self.client.subscribe(topic.getName(), qos=topic.getQoS())
            print(f"Subscribed to topic: {topic.getName()} with QoS {topic.getQoS()}")

        if self.onConnectPC is not None:
            self.program.run(self.onConnectPC)
            self.program.flushCB()
    
    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode('utf-8')
        topic = msg.topic
        
        # Check if this is a chunk confirmation
        if payload.startswith('confirm:'):
            # Extract confirmation info: "confirm: <total_chunks> <total_bytes>"
            parts = payload.split()
            if len(parts) >= 2:
                with self.confirmation_lock:
                    self.chunk_confirmations['received'] = True
            return
        
        # Check if this is a chunked message (format: "!part!<n> <total><data>")
        if payload.startswith('!part!'):
            # Extract: "!part!<n> <total><data>"
            header_end = payload.find(' ', 6)  # Find space after part number
            if header_end > 6:
                try:
                    part_num = int(payload[6:header_end])  # Extract part number
                    # Find next space to get total_chunks
                    total_end = payload.find(' ', header_end + 1)
                    if total_end > header_end:
                        total_chunks = int(payload[header_end + 1:total_end])
                        data = payload[total_end + 1:]  # Rest is data
                        
                        # Initialize chunked message storage if this is part 0
                        if part_num == 0:
                            self.chunked_messages[topic] = {}
                        
                        # Store this chunk with its part number
                        if topic in self.chunked_messages:
                            self.chunked_messages[topic][part_num] = data
                            print(f"Received chunk {part_num}/{total_chunks - 1} on topic {topic}")
                except (ValueError, IndexError):
                    pass
            return
            
        elif payload.startswith('!last!'):
            # Final chunk: "!last!<total><data>"
            try:
                # Find where the total ends and data begins (first space after !last!)
                space_pos = payload.find(' ', 6)
                if space_pos > 6:
                    total_chunks = int(payload[6:space_pos])
                    data = payload[space_pos + 1:]  # Rest is data
                    
                    # Initialize topic storage if not present (single chunk case)
                    if topic not in self.chunked_messages:
                        self.chunked_messages[topic] = {}
                    
                    # Store the last chunk
                    self.chunked_messages[topic][total_chunks - 1] = data
                    
                    # Verify all chunks are present
                    expected_parts = set(range(total_chunks))
                    received_parts = set(self.chunked_messages[topic].keys())
                    
                    if expected_parts == received_parts:
                        # All chunks received - assemble complete message
                        message_parts = [self.chunked_messages[topic][i] for i in sorted(self.chunked_messages[topic].keys())]
                        complete_message = ''.join(message_parts)
                        del self.chunked_messages[topic]
                        
                        # Send single confirmation
                        confirmation = f"confirm: {total_chunks} {len(complete_message)}"
                        self.client.publish(topic, confirmation, qos=1)
                        print(f"All chunks received for topic {topic} ({len(complete_message)} bytes total). Confirmation sent.")
                        
                        # Store and trigger callback with complete message
                        self.message = {"topic": topic, "payload": complete_message}
                        
                        if self.onMessagePC is not None:
                            print(f'Complete chunked message received ({len(complete_message)} bytes).\nResume program at PC {self.onMessagePC}')
                            self.program.run(self.onMessagePC)
                            self.program.flushCB()
                    else:
                        missing = expected_parts - received_parts
                        print(f"Warning: Missing chunks {missing} for topic {topic}")
            except (ValueError, IndexError):
                pass
            return
        
        # Regular non-chunked message
        callerID = client._client_id.decode()
        print(f"Non-chunked message received on topic {topic}: {payload}")
        self.message = {"topic": topic, "payload": payload}
        if self.onMessagePC is not None:
            print(f'Resume program at PC {self.onMessagePC}')
            self.program.run(self.onMessagePC)
            self.program.flushCB()
    
    def getMessageTopic(self):
        return self.message.topic # type: ignore
    
    def getReceivedMessage(self):
        return self.message

    def onMessage(self, pc):
        self.onMessagePC = pc

    def sendMessage(self, topic, message, qos, chunk_size=0):
        """Send a message, optionally chunked if chunk_size > 0
        
        Uses self.chunking_strategy to select between:
        - 'sequential': Wait for confirmation of each chunk (slower, more reliable)
        - 'rapid_fire': Send all chunks rapidly, wait for single final confirmation (faster)
        
        Stores transmission time in self.last_send_time (seconds)
        """
        send_start = time.time()
        
        # If chunk_size is 0, send message as-is (no chunking)
        if chunk_size == 0:
            print(f'Send MQTT message to topic {topic} with QoS {qos}: {message}')
            self.client.publish(topic, message, qos=qos)
            self.last_send_time = time.time() - send_start
            return
        
        # Send message in chunks using selected strategy
        message_len = len(message)
        num_chunks = (message_len + chunk_size - 1) // chunk_size
        
        print(f'Sending message ({message_len} bytes) in {num_chunks} chunks using {self.chunking_strategy} strategy')
        
        if self.chunking_strategy == 'sequential':
            self._send_sequential(topic, message, qos, chunk_size, num_chunks)
        else:  # rapid_fire
            self._send_rapid_fire(topic, message, qos, chunk_size, num_chunks)
        
        self.last_send_time = time.time() - send_start
        print(f'Message transmission complete in {self.last_send_time:.3f} seconds')
    
    def _send_sequential(self, topic, message, qos, chunk_size, num_chunks):
        """Send chunks one at a time, waiting for confirmation of each"""
        for i in range(num_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, len(message))
            chunk_data = message[start:end]
            
            # Prepare chunk with header: "!part!<n> <total><data>" or "!last!<total><data>"
            if i == num_chunks - 1:
                chunk_msg = f"!last!{num_chunks} {chunk_data}"
            else:
                chunk_msg = f"!part!{i} {num_chunks} {chunk_data}"
            
            # Clear confirmation flag
            with self.confirmation_lock:
                self.chunk_confirmations.clear()
            
            # Send the chunk
            self.client.publish(topic, chunk_msg, qos=qos)
            print(f"Sent chunk {i}/{num_chunks - 1}: {len(chunk_data)} bytes")
            
            # Wait for confirmation (with timeout)
            timeout = 5.0  # 5 second timeout
            start_wait = time.time()
            while True:
                with self.confirmation_lock:
                    if self.chunk_confirmations.get('received', False):
                        print(f"Chunk {i} confirmed")
                        break
                
                if time.time() - start_wait > timeout:
                    print(f"Warning: Timeout waiting for confirmation of chunk {i}")
                    break
                    
                time.sleep(0.01)  # Small sleep to avoid busy waiting
    
    def _send_rapid_fire(self, topic, message, qos, chunk_size, num_chunks):
        """Send all chunks as rapidly as possible, wait for single final confirmation"""
        print(f"[Rapid-fire] Sending all {num_chunks} chunks as fast as possible...")
        
        # Send all chunks rapidly
        for i in range(num_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, len(message))
            chunk_data = message[start:end]
            
            # Prepare chunk with header: "!part!<n> <total><data>" or "!last!<total><data>"
            if i == num_chunks - 1:
                chunk_msg = f"!last!{num_chunks} {chunk_data}"
            else:
                chunk_msg = f"!part!{i} {num_chunks} {chunk_data}"
            
            # Send without waiting
            self.client.publish(topic, chunk_msg, qos=qos)
            print(f"Sent chunk {i}/{num_chunks - 1} to topic {topic} with QoS {qos}: {chunk_msg}")
        
        # Now wait for single final confirmation
        print(f"[Rapid-fire] All chunks sent. Waiting for confirmation...")
        timeout = 10.0  # 10 second timeout for all chunks to be processed
        start_wait = time.time()
        while True:
            with self.confirmation_lock:
                if self.chunk_confirmations.get('received', False):
                    print(f"[Rapid-fire] Confirmation received")
                    break
            
            if time.time() - start_wait > timeout:
                print(f"Warning: Timeout waiting for final confirmation")
                self.timeout = True
                break
                
            time.sleep(0.05)  # Slightly longer sleep since we're just waiting for one confirmation
    
    # Start the MQTT client loop
    def run(self):
        self.client.connect(self.broker, int(self.port), 60)
        self.client.loop_start()
        
###############################################################################
# An MQTT topic
class ECTopic(ECObject):
    def __init__(self):
        super().__init__()

    def getName(self):
        v = self.getValue()
        if v is None:
            return ""
        if v is None:
            return ""
        return v['name']
    
    def getQoS(self):
        v = self.getValue()
        if v is None:
            return 0
        if v is None:
            return 0
        return int(v['qos'])
    
    def textify(self):
        v = self.getValue()
        if v is None:
            return ""
        return f'{{"name": "{v["name"]}", "qos": {v["qos"]}}}'

###############################################################################
###############################################################################
# The MQTT compiler and runtime handlers
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
            name =self.nextValue()
            command['name'] = name
            self.skip('qos')
            command['qos'] = self.nextValue()
            self.add(command)
            return True
        return False

    def r_init(self, command):
        record = self.getVariable(command['topic'])
        topic = ECTopic()
        value = {}
        value['name'] = self.textify(command['name'])
        value['qos'] = int(self.textify(command['qos']))
        topic.setValue(value)
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
            event = self.nextToken()
            if event in ['connect', 'message']:
                command['event'] = event
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
        event = command['event']
        if event == 'connect':
            self.program.mqttClient.onConnectPC = self.nextPC()+1
        elif event == 'message':
            self.program.mqttClient.onMessagePC = self.nextPC()+1
        return command['goto']

    # send {message} to {topic}
    def k_send(self, command):
        if self.nextIs('mqtt'):
            command['message'] = self.nextValue()
            self.skip('to')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                self.checkObjectType(record, MQTTClient)
                command['to'] = record['name']
                token = self.peek()
                if token == 'with':
                    self.nextToken()
                    while True:
                        token = self.nextToken()
                        if token == 'qos':
                            command['qos'] = self.nextValue()
                        if self.peek() == 'and':
                            self.nextToken()
                        else:
                            break
            self.add(command)
            return True
        return False

    def r_send(self, command):
        if not hasattr(self.program, 'mqttClient'):
            raise RuntimeError(self.program, 'No MQTT client defined')
        topic = self.getObject(self.getVariable(command['to']))
        message = self.textify(command['message'])
        if 'qos' in command:
            qos = int(self.textify(command['qos']))
        else:
            qos = topic.getQoS()
        self.program.mqttClient.sendMessage(topic.getName(), message, qos, chunk_size=100)
        if self.program.mqttClient.timeout:
            return 0
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
        token = self.getToken()
        if token == 'the':
            token = self.nextToken()
        if self.isSymbol():
            record = self.getSymbolRecord()
            object = self.getObject(record)
            if isinstance(object, ECTopic):
                return ECValue(domain=self.getName(), type='symbol', content=record['name'])
            else: return None
        else:
            if token == 'mqtt':
                token = self.nextToken()
                if token == 'message':
                    return ECValue(domain=self.getName(), type='mqtt', content=token)
            # else:
            #     return self.getValue()
        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        return value

    #############################################################################
    # Value handlers

    def v_message(self, v):
        return self.program.mqttClient.message
    
    def v_mqtt(self, v):
        content = v.getContent()
        if content == 'message':
            return self.program.mqttClient.message
        return None

    def v_topic(self, v):
        topic = self.getObject(self.getVariable(self.textify(v.getContent())))
        return f'{{"name": "{topic.getName()}", "qos": {topic.getQOS()}}}'

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers
