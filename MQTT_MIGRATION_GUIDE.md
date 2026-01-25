# MQTT Plugin Migration Guide: Python to JavaScript

This guide helps you understand the architectural differences between the Python and JavaScript implementations of the EasyCoder MQTT plugin.

## File Structure

| Python | JavaScript |
|--------|------------|
| `easycoder/ec_mqtt.py` | `mqtt.js` |
| `tests/mqtt.ecs` | `mqtt_example.ecs` |
| Built-in to core | Plugin file |

## Dependencies

### Python Version
```python
import paho.mqtt.client as mqtt
import threading
import json
```

Install with: `pip install paho-mqtt`

### JavaScript Version
```html
<!-- Browser -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>

<!-- Node.js -->
npm install mqtt
```

## Class Structure Comparison

### Python MQTTClient Class

```python
class MQTTClient():
    def __init__(self):
        super().__init__()
        
    def create(self, program, clientID, broker, port, topics):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=clientID)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
    
    def on_connect(self, client, userdata, flags, reason_code, properties):
        # Handle connection
        
    def on_message(self, client, userdata, msg):
        # Handle messages
```

### JavaScript MQTTClient Class

```javascript
MQTTClient: class {
    constructor() {
        // Initialize
    }
    
    create(program, clientID, broker, port, topics) {
        const url = `mqtt://${this.broker}:${this.port}`;
        this.client = mqtt.connect(url, { clientId: this.clientID });
        this.client.on('connect', () => this.onConnect());
        this.client.on('message', (topic, payload) => this.onMessage(topic, payload));
    }
    
    onConnect() {
        // Handle connection
    }
    
    onMessage(topic, payload) {
        // Handle messages  
    }
}
```

**Key Differences:**
- Python uses callback methods with multiple parameters
- JavaScript uses arrow functions and closures
- Python runs client loop in background thread
- JavaScript is event-driven (no explicit threading needed)

## Handler Pattern Comparison

### Python Handler Structure

```python
class MQTT(Handler):
    def __init__(self, compiler):
        Handler.__init__(self, compiler)
    
    def getName(self):
        return 'mqtt'
    
    # Compile handler
    def k_mqtt(self, command):
        # Parse syntax
        self.add(command)
        return True
    
    # Runtime handler  
    def r_mqtt(self, command):
        # Execute command
        return self.nextPC()
```

### JavaScript Handler Structure

```javascript
MQTT: {
    compile: compiler => {
        // Parse syntax
        compiler.addCommand(command);
        return true;
    },
    
    run: program => {
        // Execute command
        return command.pc + 1;
    }
}
```

**Key Differences:**
- Python uses class methods with `k_` and `r_` prefixes
- JavaScript uses object literals with `compile` and `run` properties
- Python handlers inherit from `Handler` base class
- JavaScript handlers are standalone objects

## Dispatcher Pattern

### Python
```python
# Domain handler is class-based
# Methods are called directly via reflection
def compile(self):
    handler = self.keywordHandler(keyword)
    return handler(command)
```

### JavaScript
```javascript
// Explicit dispatcher function
getHandler: (name) => {
    switch (name) {
        case 'init': return EasyCoder_MQTT.Init;
        case 'mqtt': return EasyCoder_MQTT.MQTT;
        // ...
        default: return null;
    }
}
```

## Message Chunking

Both versions implement the same chunking protocol but with different implementations:

### Python
```python
def sendMessage(self, topic, message, qos, chunk_size=0):
    message_bytes = message_str.encode('utf-8')
    num_chunks = (message_len + chunk_size - 1) // chunk_size
    
    for i in range(num_chunks):
        start = i * chunk_size
        end = min(start + chunk_size, len(message_bytes))
        chunk_data = message_bytes[start:end]
        
        if i == num_chunks - 1:
            header = f"!last!{num_chunks} ".encode('ascii')
        else:
            header = f"!part!{i} {num_chunks} ".encode('ascii')
        
        chunk_msg = header + chunk_data
        self.client.publish(topic, chunk_msg, qos=qos)
```

### JavaScript
```javascript
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
    }
}
```

**Key Differences:**
- Python uses `bytes` and `.encode()/.decode()`
- JavaScript uses `TextEncoder`/`TextDecoder` APIs
- Same protocol: `!part!N TOTAL data` and `!last!TOTAL data`

## Value Compilation

### Python
```python
def compileValue(self):
    token = self.getToken()
    if token == 'the':
        token = self.nextToken()
    if self.isSymbol():
        record = self.getSymbolRecord()
        object = self.getObject(record)
        if isinstance(object, ECTopic):
            return ECValue(domain=self.getName(), 
                         type='topic', 
                         content=record['name'])
    elif token == 'mqtt':
        token = self.nextToken()
        if token == 'message':
            return ECValue(domain=self.getName(), 
                         type='mqtt', 
                         content=token)
    return None
```

### JavaScript
```javascript
value: {
    compile: compiler => {
        let token = compiler.getToken();
        
        if (token === 'the') {
            token = compiler.nextToken();
        }
        
        if (compiler.isSymbol()) {
            const record = compiler.getSymbolRecord();
            if (record.object instanceof EasyCoder_MQTT.ECTopic) {
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
    }
}
```

**Key Differences:**
- Python uses `ECValue` class for return values
- JavaScript uses plain object literals
- Python uses `isinstance()` for type checking
- JavaScript uses `instanceof` operator

## Runtime Value Retrieval

### Python
```python
def v_mqtt(self, v):
    content = v.getContent()
    if content == 'message':
        return self.program.mqttClient.message
    return None
```

### JavaScript
```javascript
value: {
    get: (program, value) => {
        if (value.type === 'mqtt') {
            if (value.content === 'message') {
                return program.mqttClient.getReceivedMessage();
            }
        }
        return null;
    }
}
```

## Error Handling

### Python
```python
def r_send(self, command):
    if not hasattr(self.program, 'mqttClient'):
        raise RuntimeError(self.program, 'No MQTT client defined')
    
    if action == None:
        raise RuntimeError(self.program, 'MQTT send command missing action field')
```

### JavaScript
```javascript
Send: {
    run: program => {
        if (!program.mqttClient) {
            program.runtimeError(command.lino, 'No MQTT client defined');
        }
        
        if (!payload.action) {
            program.runtimeError(command.lino, 'MQTT send command missing action field');
        }
    }
}
```

## Event Handling

### Python (Threading-based)
```python
def on_connect(self, client, userdata, flags, reason_code, properties):
    # Runs in MQTT client thread
    if self.onConnectPC is not None:
        self.program.run(self.onConnectPC)
        self.program.flushCB()  # Flush callback queue

def run(self):
    self.client.connect(self.broker, int(self.port), 60)
    self.client.loop_start()  # Start background thread
```

### JavaScript (Event-driven)
```javascript
onConnect() {
    // Runs in event loop
    if (this.onConnectPC !== null) {
        this.program.run(this.onConnectPC);
    }
}

create(program, clientID, broker, port, topics) {
    this.client = mqtt.connect(url, options);
    // No explicit loop needed - event-driven
}
```

## Integration with EasyCoder Core

### Python
- Part of main package in `easycoder/ec_mqtt.py`
- Imported in `easycoder/__init__.py`
- Automatically available via `from .ec_mqtt import *`
- Handler registered in program initialization

### JavaScript  
- Standalone plugin file `mqtt.js`
- Self-registering: `EasyCoder.domain.mqtt = EasyCoder_MQTT`
- Must be loaded after core EasyCoder and MQTT.js
- Plugin discovered via domain namespace

## Testing

### Python
```python
# Run built-in test
python -m easycoder.ec_mqtt

# Or via EasyCoder script
easycoder tests/mqtt.ecs
```

### JavaScript
```html
<!-- Include and test in browser -->
<script src="mqtt.js"></script>
<script>
    // Test directly or via EasyCoder script
    // See mqtt_test.html
</script>
```

## Common Pitfalls

### Python → JavaScript

1. **No automatic type conversion**
   - Python: `int(value)` works on strings
   - JavaScript: Use `parseInt()` or `Number()`

2. **Array/Object handling**
   - Python: `dict` and `list` are distinct
   - JavaScript: Everything is an object; use `[]` for arrays

3. **String encoding**
   - Python: Explicit `.encode('utf-8')`
   - JavaScript: Use `TextEncoder`/`TextDecoder`

4. **Threading**
   - Python: Explicit threads for background work
   - JavaScript: Event loop handles async operations

5. **Error types**
   - Python: `RuntimeError`, `NoValueError`, etc.
   - JavaScript: Generic `Error` or program's error methods

## EasyCoder Script Compatibility

The EasyCoder script syntax is **100% identical** between Python and JavaScript:

```easycoder
topic Request
init Request name `test/topic` qos 1
mqtt id `Client` broker `test.mosquitto.org` port 1883 subscribe Request
on mqtt message begin
    put the mqtt message into Message
end
send mqtt `hello` to Request
```

This script will run unchanged in both Python and JavaScript implementations!

## Summary

| Aspect | Python | JavaScript |
|--------|--------|------------|
| **Language paradigm** | Class-based OOP | Prototype/functional |
| **Handler pattern** | Methods with `k_`/`r_` prefix | Object literals |
| **Concurrency** | Threading | Event loop |
| **MQTT library** | paho-mqtt | MQTT.js |
| **Type system** | Dynamic + type hints | Dynamic |
| **Integration** | Built-in module | External plugin |
| **Platform** | CLI/Desktop | Browser/Node.js |
| **Script syntax** | ✓ Identical | ✓ Identical |

The JavaScript version maintains full functional parity with the Python version while adapting to JavaScript's event-driven architecture and browser/Node.js environments.
