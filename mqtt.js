/**
 * EasyCoder MQTT Plugin for JavaScript
 * 
 * Provides MQTT client functionality with support for:
 * - Topic declaration and subscription
 * - MQTT client connection
 * - Message publishing and receiving
 * - Message chunking for large payloads
 * - Event handlers (on connect, on message)
 * 
 * Based on the Python implementation in ec_mqtt.py
 * Requires: MQTT.js library (https://github.com/mqttjs/MQTT.js)
 */

const EasyCoder_MQTT = {

    name: `EasyCoder_MQTT`,

    // MQTT Client class
    MQTTClient: class {
        constructor() {
            this.clientID = null;
            this.broker = null;
            this.port = null;
            this.topics = [];
            this.client = null;
            this.onConnectPC = null;
            this.onMessagePC = null;
            this.message = null;
            this.chunkedMessages = {};  // Store incoming chunked messages
            this.chunkSize = 1024;      // Default chunk size
            this.lastSendTime = null;   // Time for last transmission
        }

        create(program, clientID, broker, port, topics) {
            this.program = program;
            this.clientID = clientID;
            this.broker = broker;
            this.port = port;
            this.topics = topics;

            // Create MQTT client (requires mqtt.js library)
            const url = `mqtt://${this.broker}:${this.port}`;
            this.client = mqtt.connect(url, {
                clientId: this.clientID
            });

            // Setup event handlers
            this.client.on('connect', () => this.onConnect());
            this.client.on('message', (topic, payload) => this.onMessage(topic, payload));
        }

        onConnect() {
            console.log(`Client ${this.clientID} connected`);
            
            // Subscribe to all topics
            for (const topicName of this.topics) {
                const topicRecord = this.program.getSymbolRecord(topicName);
                const topic = topicRecord.object;
                const qos = topic.getQoS();
                this.client.subscribe(topic.getName(), { qos });
                console.log(`Subscribed to topic: ${topic.getName()} with QoS ${qos}`);
            }

            // Run the on-connect handler if defined
            if (this.onConnectPC !== null) {
                this.program.run(this.onConnectPC);
            }
        }

        onMessage(topic, payload) {
            const message = payload.toString('utf-8');

            // Check if this is a chunked message
            if (message.startsWith('!part!')) {
                // Extract: "!part!<n> <total> <data>"
                const headerEnd = message.indexOf(' ', 6);
                if (headerEnd > 6) {
                    try {
                        const partNum = parseInt(message.substring(6, headerEnd));
                        const totalEnd = message.indexOf(' ', headerEnd + 1);
                        if (totalEnd > headerEnd) {
                            const totalChunks = parseInt(message.substring(headerEnd + 1, totalEnd));
                            const data = message.substring(totalEnd + 1);

                            // Initialize chunked message storage if this is part 0
                            if (partNum === 0) {
                                this.chunkedMessages[topic] = {};
                            }

                            // Store this chunk
                            if (this.chunkedMessages[topic]) {
                                this.chunkedMessages[topic][partNum] = data;
                                console.log(`Received chunk ${partNum}/${totalChunks - 1} on topic ${topic}`);
                            }
                        }
                    } catch (e) {
                        console.error('Error parsing chunked message:', e);
                    }
                }
                return;
            } 
            else if (message.startsWith('!last!')) {
                // Final chunk: "!last!<total> <data>"
                try {
                    const spacePos = message.indexOf(' ', 6);
                    if (spacePos > 6) {
                        const totalChunks = parseInt(message.substring(6, spacePos));
                        const data = message.substring(spacePos + 1);

                        // Initialize if not present
                        if (!this.chunkedMessages[topic]) {
                            this.chunkedMessages[topic] = {};
                        }

                        // Store the last chunk
                        this.chunkedMessages[topic][totalChunks - 1] = data;

                        // Verify all chunks are present
                        const expectedParts = new Set();
                        for (let i = 0; i < totalChunks; i++) {
                            expectedParts.add(i);
                        }
                        const receivedParts = new Set(Object.keys(this.chunkedMessages[topic]).map(k => parseInt(k)));

                        // Check if we have all chunks
                        if (expectedParts.size === receivedParts.size && 
                            [...expectedParts].every(p => receivedParts.has(p))) {
                            // Assemble complete message
                            const messageParts = [];
                            for (let i = 0; i < totalChunks; i++) {
                                messageParts.push(this.chunkedMessages[topic][i]);
                            }
                            const completeMessage = messageParts.join('');
                            delete this.chunkedMessages[topic];

                            // Parse as JSON if possible
                            try {
                                this.message = JSON.parse(completeMessage);
                                // Try to parse nested message field
                                try {
                                    this.message.message = JSON.parse(this.message.message);
                                } catch (e) {
                                    // Leave message as string
                                }
                            } catch (e) {
                                this.message = completeMessage;
                            }

                            // Run the on-message handler if defined
                            if (this.onMessagePC !== null) {
                                this.program.run(this.onMessagePC);
                            }
                        } else {
                            console.warn('Warning: Missing chunks for topic ' + topic);
                        }
                    }
                } catch (e) {
                    console.error('Error assembling chunked message:', e);
                }
                return;
            }

            // Regular non-chunked message
            try {
                this.message = JSON.parse(message);
                try {
                    this.message.message = JSON.parse(this.message.message);
                } catch (e) {
                    // Leave message as string
                }
            } catch (e) {
                this.message = message;
            }

            // Run the on-message handler if defined
            if (this.onMessagePC !== null) {
                this.program.run(this.onMessagePC);
            }
        }

        getReceivedMessage() {
            return this.message;
        }

        sendMessage(topic, message, qos, chunkSize) {
            const sendStart = Date.now();
            chunkSize = chunkSize || 1024;

            // Convert message to string
            let messageStr;
            if (typeof message === 'string') {
                messageStr = message;
            } else {
                messageStr = String(message);
            }

            // Convert to UTF-8 bytes
            const encoder = new TextEncoder();
            const messageBytes = encoder.encode(messageStr);
            const messageLen = messageBytes.length;
            const numChunks = Math.ceil(messageLen / chunkSize);

            console.log(`Sending message (${messageLen} bytes) in ${numChunks} chunks of size ${chunkSize} to topic ${topic} with QoS ${qos}`);

            this._sendRapidFire(topic, messageBytes, qos, chunkSize, numChunks);

            this.lastSendTime = (Date.now() - sendStart) / 1000;
            console.log(`Message transmission complete in ${this.lastSendTime.toFixed(3)} seconds`);
        }

        _sendRapidFire(topic, messageBytes, qos, chunkSize, numChunks) {
            const decoder = new TextDecoder();
            
            for (let i = 0; i < numChunks; i++) {
                const start = i * chunkSize;
                const end = Math.min(start + chunkSize, messageBytes.length);
                const chunkData = messageBytes.slice(start, end);

                let header;
                if (i === numChunks - 1) {
                    header = `!last!${numChunks} `;
                } else {
                    header = `!part!${i} ${numChunks} `;
                }

                const chunkMsg = header + decoder.decode(chunkData);
                this.client.publish(topic, chunkMsg, { qos });
                console.log(`Sent chunk ${i}/${numChunks - 1} to topic ${topic} with QoS ${qos}: ${chunkMsg.length} bytes`);
            }
        }
    },

    // ECTopic class - represents an MQTT topic
    ECTopic: class {
        constructor() {
            this.value = null;
        }

        setValue(value) {
            this.value = value;
        }

        getValue() {
            return this.value;
        }

        getName() {
            if (!this.value) return '';
            return this.value.name || '';
        }

        getQoS() {
            if (!this.value) return 0;
            return parseInt(this.value.qos) || 0;
        }

        textify() {
            if (!this.value) return '';
            return JSON.stringify({
                name: this.value.name,
                qos: this.value.qos
            });
        }
    },

    /////////////////////////////////////////////////////////////////////////////
    // Command: init {topic} name {name} qos {qos}
    Init: {
        compile: compiler => {
            const lino = compiler.getLino();
            if (compiler.nextIsSymbol()) {
                const record = compiler.getSymbolRecord();
                const topic = record.name;
                compiler.skip('name');
                const name = compiler.nextValue();
                compiler.skip('qos');
                const qos = compiler.nextValue();
                
                compiler.addCommand({
                    domain: 'mqtt',
                    keyword: 'init',
                    lino,
                    topic,
                    name,
                    qos
                });
                return true;
            }
            return false;
        },

        run: program => {
            const command = program[program.pc];
            const record = program.getSymbolRecord(command.topic);
            const topic = new EasyCoder_MQTT.ECTopic();
            const value = {
                name: program.getValue(command.name),
                qos: parseInt(program.getValue(command.qos))
            };
            topic.setValue(value);
            record.object = topic;
            return command.pc + 1;
        }
    },

    /////////////////////////////////////////////////////////////////////////////
    // Command: mqtt id {clientID} broker {broker} port {port} subscribe {topic} [and {topic} ...]
    MQTT: {
        compile: compiler => {
            const lino = compiler.getLino();
            const command = {
                domain: 'mqtt',
                keyword: 'mqtt',
                lino,
                requires: {}
            };

            while (true) {
                const token = compiler.peek();
                if (token === 'id') {
                    compiler.next();
                    command.clientID = compiler.nextValue();
                } else if (token === 'broker') {
                    compiler.next();
                    command.broker = compiler.nextValue();
                } else if (token === 'port') {
                    compiler.next();
                    command.port = compiler.nextValue();
                } else if (token === 'subscribe') {
                    compiler.next();
                    const topics = [];
                    while (compiler.nextIsSymbol()) {
                        const record = compiler.getSymbolRecord();
                        topics.push(record.name);
                        if (compiler.peek() === 'and') {
                            compiler.next();
                        } else {
                            break;
                        }
                    }
                    command.topics = topics;
                } else if (token === 'action') {
                    compiler.next();
                    const action = compiler.nextToken();
                    const reqList = [];
                    if (compiler.nextIs('requires')) {
                        while (true) {
                            reqList.push(compiler.nextToken());
                            if (compiler.peek() === 'and') {
                                compiler.next();
                            } else {
                                break;
                            }
                        }
                    }
                    command.requires[action] = reqList;
                } else {
                    break;
                }
            }

            compiler.addCommand(command);
            return true;
        },

        run: program => {
            const command = program[program.pc];
            
            if (program.mqttClient) {
                program.runtimeError(command.lino, 'MQTT client already defined');
            }

            const clientID = program.getValue(command.clientID);
            const broker = program.getValue(command.broker);
            const port = program.getValue(command.port);
            const topics = command.topics;

            const client = new EasyCoder_MQTT.MQTTClient();
            client.create(program, clientID, broker, port, topics);
            program.mqttClient = client;
            program.mqttRequires = command.requires;

            return command.pc + 1;
        }
    },

    /////////////////////////////////////////////////////////////////////////////
    // Command: on mqtt (connect|message) {action}
    On: {
        compile: compiler => {
            const lino = compiler.getLino();
            const token = compiler.peek();
            
            if (token === 'mqtt') {
                compiler.next();
                const event = compiler.nextToken();
                
                if (event === 'connect' || event === 'message') {
                    compiler.next();
                    
                    const command = {
                        domain: 'mqtt',
                        keyword: 'on',
                        lino,
                        event,
                        goto: 0
                    };
                    compiler.addCommand(command);

                    // Add a goto placeholder
                    compiler.addCommand({
                        domain: 'core',
                        keyword: 'goto',
                        lino,
                        goto: 0
                    });

                    // Compile the action
                    compiler.compileOne();

                    // Add a stop command
                    compiler.addCommand({
                        domain: 'core',
                        keyword: 'stop',
                        lino
                    });

                    // Fix up the goto
                    command.goto = compiler.getPC();
                    return true;
                }
            }
            return false;
        },

        run: program => {
            const command = program[program.pc];
            const event = command.event;
            
            if (event === 'connect') {
                program.mqttClient.onConnectPC = command.pc + 2;
            } else if (event === 'message') {
                program.mqttClient.onMessagePC = command.pc + 2;
            }
            
            return command.goto;
        }
    },

    /////////////////////////////////////////////////////////////////////////////
    // Command: send mqtt {message} to {topic} [with qos {qos}] [sender {sender}] [action {action}] [topics {topics}] [message {message}]
    Send: {
        compile: compiler => {
            const lino = compiler.getLino();
            const command = {
                domain: 'mqtt',
                keyword: 'send',
                lino,
                qos: 1  // default QoS
            };

            // First check for "send mqtt" or "send to"
            if (compiler.nextIs('to')) {
                if (compiler.nextIsSymbol()) {
                    const record = compiler.getSymbolRecord();
                    command.to = record.name;

                    // Parse optional parameters
                    while (true) {
                        const token = compiler.peek();
                        if (token === 'sender' || token === 'action' || 
                            token === 'topics' || token === 'qos' || token === 'message') {
                            compiler.next();
                            
                            if (token === 'sender') {
                                if (compiler.nextIsSymbol()) {
                                    const rec = compiler.getSymbolRecord();
                                    command.sender = rec.name;
                                }
                            } else if (token === 'action') {
                                command.action = compiler.nextValue();
                            } else if (token === 'topics') {
                                command.topics = compiler.nextValue();
                            } else if (token === 'qos') {
                                command.qos = compiler.nextValue();
                            } else if (token === 'message') {
                                command.message = compiler.nextValue();
                            }
                        } else {
                            break;
                        }
                    }

                    compiler.addCommand(command);
                    return true;
                }
            } else {
                // Format: send mqtt {message} to {topic}
                command.message = compiler.nextValue();
                compiler.skip('to');
                
                if (compiler.nextIsSymbol()) {
                    const record = compiler.getSymbolRecord();
                    command.to = record.name;
                    
                    const token = compiler.peek();
                    if (token === 'with') {
                        compiler.next();
                        while (true) {
                            const tok = compiler.nextToken();
                            if (tok === 'qos') {
                                command.qos = compiler.nextValue();
                            }
                            if (compiler.peek() === 'and') {
                                compiler.next();
                            } else {
                                break;
                            }
                        }
                    }
                    
                    compiler.addCommand(command);
                    return true;
                }
            }
            
            return false;
        },

        run: program => {
            const command = program[program.pc];
            
            if (!program.mqttClient) {
                program.runtimeError(command.lino, 'No MQTT client defined');
            }

            const topicRecord = program.getSymbolRecord(command.to);
            const topic = topicRecord.object;
            const qos = command.qos ? parseInt(program.getValue(command.qos)) : 1;

            // Build payload
            const payload = {};
            
            if (command.sender) {
                const senderRecord = program.getSymbolRecord(command.sender);
                payload.sender = senderRecord.object.textify();
            }
            
            payload.action = command.action ? program.getValue(command.action) : null;
            payload.topics = command.topics ? program.getValue(command.topics) : null;
            payload.message = command.message ? program.getValue(command.message) : null;

            // Validate required fields
            if (!payload.action) {
                program.runtimeError(command.lino, 'MQTT send command missing action field');
            }

            // Check action requirements
            if (program.mqttRequires && program.mqttRequires[payload.action]) {
                const requires = program.mqttRequires[payload.action];
                for (const item of requires) {
                    if (!payload[item]) {
                        program.runtimeError(command.lino, `MQTT send command missing required field: ${item}`);
                    }
                }
            }

            const topicName = topic.getName();
            program.mqttClient.sendMessage(topicName, JSON.stringify(payload), qos, 1024);

            return command.pc + 1;
        }
    },

    /////////////////////////////////////////////////////////////////////////////
    // Command: topic {name}
    Topic: {
        compile: compiler => {
            const lino = compiler.getLino();
            compiler.addValueType();
            return compiler.compileVariable({
                domain: 'mqtt',
                keyword: 'topic',
                lino
            }, 'ECTopic');
        },

        run: program => {
            const command = program[program.pc];
            return command.pc + 1;
        }
    },

    /////////////////////////////////////////////////////////////////////////////
    // Value handlers
    value: {
        compile: compiler => {
            let token = compiler.getToken();
            
            if (token === 'the') {
                token = compiler.nextToken();
            }

            if (compiler.isSymbol()) {
                const record = compiler.getSymbolRecord();
                if (record.object && record.object instanceof EasyCoder_MQTT.ECTopic) {
                    return {
                        domain: 'mqtt',
                        type: 'topic',
                        content: record.name
                    };
                }
            } else if (token === 'mqtt') {
                token = compiler.nextToken();
                if (token === 'message') {
                    return {
                        domain: 'mqtt',
                        type: 'mqtt',
                        content: 'message'
                    };
                }
            }

            return null;
        },

        get: (program, value) => {
            if (value.type === 'mqtt') {
                if (value.content === 'message') {
                    return program.mqttClient.getReceivedMessage();
                }
            } else if (value.type === 'topic') {
                const record = program.getSymbolRecord(value.content);
                const topic = record.object;
                return topic.textify();
            }
            return null;
        }
    },

    /////////////////////////////////////////////////////////////////////////////
    // Condition handlers
    condition: {
        compile: () => {
            return {};
        },

        test: () => {
            return false;
        }
    },

    /////////////////////////////////////////////////////////////////////////////
    // Dispatcher - routes keywords to handlers
    getHandler: (name) => {
        switch (name) {
            case 'init':
                return EasyCoder_MQTT.Init;
            case 'mqtt':
                return EasyCoder_MQTT.MQTT;
            case 'on':
                return EasyCoder_MQTT.On;
            case 'send':
                return EasyCoder_MQTT.Send;
            case 'topic':
                return EasyCoder_MQTT.Topic;
            default:
                return null;
        }
    },

    /////////////////////////////////////////////////////////////////////////////
    // Main compile handler
    compile: (compiler) => {
        const token = compiler.getToken();
        const handler = EasyCoder_MQTT.getHandler(token);
        
        if (!handler) {
            return false;
        }
        
        return handler.compile(compiler);
    },

    /////////////////////////////////////////////////////////////////////////////
    // Main run handler
    run: (program) => {
        const command = program[program.pc];
        const handler = EasyCoder_MQTT.getHandler(command.keyword);
        
        if (!handler) {
            program.runtimeError(command.lino, `Unknown keyword '${command.keyword}' in 'mqtt' package`);
        }
        
        return handler.run(program);
    }
};

// Register the MQTT domain
if (typeof EasyCoder !== 'undefined') {
    EasyCoder.domain.mqtt = EasyCoder_MQTT;
}
