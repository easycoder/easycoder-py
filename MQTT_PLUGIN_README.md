# EasyCoder MQTT Plugin (JavaScript)

This is a JavaScript implementation of the MQTT plugin for EasyCoder, ported from the Python version ([ec_mqtt.py](easycoder/ec_mqtt.py)).

## Overview

The MQTT plugin provides complete MQTT client functionality for EasyCoder scripts running in JavaScript environments (browser or Node.js). It supports:

- **Topic management** - Declare and configure MQTT topics with QoS levels
- **Client connection** - Connect to MQTT brokers
- **Message publishing** - Send messages with automatic chunking for large payloads
- **Message subscription** - Receive messages with event handlers
- **Message chunking** - Automatic chunking/reassembly for messages over 1KB

## Requirements

This plugin requires the MQTT.js library:

```html
<!-- For browser -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>

<!-- For Node.js -->
npm install mqtt
```

## Installation

1. Include the plugin file in your HTML:
```html
<script src="mqtt.js"></script>
```

2. The plugin automatically registers as `EasyCoder.domain.mqtt` when loaded.

## API Reference

### Commands

#### `topic {name}`
Declares an MQTT topic variable.

**Example:**
```
topic Request
topic Response
```

#### `init {topic} name {name} qos {qos}`
Initializes a topic with its MQTT topic name and Quality of Service level.

**Parameters:**
- `{topic}` - Topic variable to initialize
- `name {name}` - MQTT topic name (string)
- `qos {qos}` - Quality of Service level (0, 1, or 2)

**Example:**
```
init Request
    name `device/sensor/temperature`
    qos 1
```

#### `mqtt id {clientID} broker {broker} port {port} subscribe {topic} [and {topic} ...]`
Creates and connects an MQTT client to a broker.

**Parameters:**
- `id {clientID}` - Unique client identifier
- `broker {broker}` - MQTT broker hostname
- `port {port}` - MQTT broker port (usually 1883)
- `subscribe {topic}` - Topic(s) to subscribe to

**Optional:**
- `action {action} requires {field} [and {field} ...]` - Define required fields for message actions

**Example:**
```
mqtt
    id `MyClient123`
    broker `test.mosquitto.org`
    port 1883
    subscribe Response and Status
    action query requires message
    action command requires sender and topics
```

#### `on mqtt (connect|message) {action}`
Defines event handlers for MQTT events.

**Events:**
- `connect` - Triggered when client successfully connects to broker
- `message` - Triggered when a message is received on subscribed topics

**Example:**
```
on mqtt connect
    begin
        print `Connected to broker`
    end

on mqtt message
    begin
        put the mqtt message into Message
        print `Received:` Message
    end
```

#### `send mqtt {message} to {topic} [with qos {qos}]`
Sends a message to an MQTT topic (simple format).

**Parameters:**
- `{message}` - Message content (string or variable)
- `to {topic}` - Topic to send to
- `with qos {qos}` - Optional QoS level (default: 1)

**Example:**
```
variable Data
put `Hello, MQTT!` into Data
send mqtt Data to Request with qos 2
```

#### `send mqtt to {topic} action {action} [sender {sender}] [topics {topics}] [message {message}] [qos {qos}]`
Sends a structured message (JSON format with metadata).

**Parameters:**
- `to {topic}` - Topic to send to
- `action {action}` - Action type (validated against requirements)
- `sender {sender}` - Optional sender topic
- `topics {topics}` - Optional topics list
- `message {message}` - Optional message content
- `qos {qos}` - Optional QoS level

**Example:**
```
send mqtt to Request
    action `query`
    sender ResponseTopic
    topics `sensor/data`
    message `get_temperature`
    qos 1
```

### Values

#### `the mqtt message`
Returns the last received MQTT message. The message is automatically parsed as JSON if possible.

**Example:**
```
variable ReceivedData
on mqtt message
    begin
        put the mqtt message into ReceivedData
        print ReceivedData
    end
```

#### `{topic}` value
When used as a value, a topic variable returns its JSON representation:
```json
{"name": "topic/name", "qos": 1}
```

## Message Chunking

The plugin automatically chunks large messages (>1KB) to ensure reliable transmission:

- Messages are split into 1KB chunks by default
- Each chunk is prefixed with metadata: `!part!<n> <total> <data>` or `!last!<total> <data>`
- Chunks are reassembled automatically on receipt
- Transmission time is tracked in `client.lastSendTime`

## Comparison with Python Version

This JavaScript implementation mirrors the Python version's functionality:

| Feature | Python (ec_mqtt.py) | JavaScript (mqtt.js) |
|---------|---------------------|----------------------|
| MQTT Library | paho-mqtt | MQTT.js |
| Topic Declaration | ✓ | ✓ |
| Client Connection | ✓ | ✓ |
| Message Chunking | ✓ | ✓ |
| Event Handlers | ✓ | ✓ |
| Action Validation | ✓ | ✓ |
| QoS Support | ✓ | ✓ |
| JSON Auto-parse | ✓ | ✓ |

### Key Differences

1. **Threading**: Python uses `threading` for background processing; JavaScript uses event-driven callbacks
2. **Byte Encoding**: Python uses UTF-8 bytes directly; JavaScript uses TextEncoder/TextDecoder
3. **MQTT Client**: Python uses `paho.mqtt.client`; JavaScript uses `mqtt.js`

## Example Usage

See [mqtt_example.ecs](mqtt_example.ecs) for a complete working example.

### Basic Publish/Subscribe

```easycoder
script MQTTDemo

topic SensorData
variable Temperature

! Setup topic
init SensorData
    name `home/sensor/temp`
    qos 1

! Connect to broker
mqtt
    id `TempSensor01`
    broker `mqtt.example.com`
    port 1883
    subscribe SensorData

! Handle incoming messages
on mqtt message
    begin
        put the mqtt message into Temperature
        print `Temperature:` Temperature
    end

! Send a reading
put `22.5` into Temperature
send mqtt Temperature to SensorData with qos 1

wait 5
stop
```

### Structured Messages with Validation

```easycoder
script StructuredMQTT

topic Commands
topic Status
variable Command

init Commands name `device/commands` qos 1
init Status name `device/status` qos 1

mqtt
    id `Device001`
    broker `test.mosquitto.org`
    port 1883
    subscribe Commands
    action execute requires sender and message

on mqtt message
    begin
        put the mqtt message into Command
        ! Process command
    end

! Send command with validation
send mqtt to Commands
    action `execute`
    sender Status
    message `reboot`
    qos 2

stop
```

## Testing

To test the plugin:

1. Include the MQTT.js library
2. Include the mqtt.js plugin
3. Run an EasyCoder script using the MQTT commands
4. Use a public MQTT broker like `test.mosquitto.org` for testing

## Architecture

The plugin follows the standard EasyCoder plugin pattern:

```javascript
const EasyCoder_MQTT = {
    name: 'EasyCoder_MQTT',
    
    // Command handlers (Init, MQTT, On, Send, Topic)
    // Each has compile() and run() methods
    
    // Value handler
    value: { compile(), get() },
    
    // Condition handler
    condition: { compile(), test() },
    
    // Dispatcher
    getHandler(name),
    compile(compiler),
    run(program)
};
```

## Related Files

- **Python Implementation**: [easycoder/ec_mqtt.py](easycoder/ec_mqtt.py)
- **Python Test Script**: [tests/mqtt.ecs](tests/mqtt.ecs)
- **JavaScript Example**: [mqtt_example.ecs](mqtt_example.ecs)

## License

Same as EasyCoder-py project (see LICENSE file)

## Support

For issues or questions about this plugin:
1. Check the Python implementation for reference behavior
2. Verify MQTT.js is properly loaded
3. Use browser console/Node.js logs to debug
4. Test with public brokers first before using production brokers
