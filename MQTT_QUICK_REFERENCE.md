# MQTT Plugin Quick Reference

## Installation

```html
<!-- Include MQTT.js -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>

<!-- Include the plugin -->
<script src="mqtt.js"></script>
```

## Syntax Reference

### Topic Declaration
```easycoder
topic MyTopic
init MyTopic name `device/sensor` qos 1
```

### Client Connection
```easycoder
mqtt
    id `ClientID`
    broker `test.mosquitto.org`
    port 1883
    subscribe Topic1 and Topic2
```

### Event Handlers
```easycoder
on mqtt connect
    begin
        print `Connected!`
    end

on mqtt message
    begin
        put the mqtt message into Data
        print Data
    end
```

### Sending Messages

**Simple:**
```easycoder
send mqtt `Hello` to MyTopic
```

**With options:**
```easycoder
send mqtt Message to MyTopic with qos 2
```

**Structured:**
```easycoder
send mqtt to MyTopic
    action `query`
    sender ResponseTopic
    message Data
    qos 1
```

### Values
```easycoder
put the mqtt message into Variable
```

## Command Reference

| Command | Purpose | Parameters |
|---------|---------|------------|
| `topic Name` | Declare topic variable | Name of topic variable |
| `init Topic name {n} qos {q}` | Initialize topic | Topic name string, QoS level (0-2) |
| `mqtt id {id} broker {b} port {p} subscribe {t}` | Create MQTT client | Client ID, broker host, port, topics |
| `on mqtt (connect\|message)` | Define event handler | Event type and action block |
| `send mqtt {msg} to {topic}` | Send message | Message content, destination topic |

## Message Format

### Outgoing (Auto-generated)
```json
{
    "action": "query",
    "sender": "device/response",
    "topics": "sensor/temp",
    "message": "get_reading"
}
```

### Chunked Messages
- Automatically chunks messages > 1KB
- Format: `!part!N TOTAL data` (intermediate chunks)
- Format: `!last!TOTAL data` (final chunk)
- Transparent reassembly on receive

## Complete Example

```easycoder
script MQTTExample

topic Commands
topic Status
variable Message

! Setup
init Commands name `device/cmd` qos 1
init Status name `device/status` qos 1

! Connect
mqtt
    id `Device001`
    broker `test.mosquitto.org`
    port 1883
    subscribe Commands

! Handlers
on mqtt connect
    begin
        print `Ready`
        send mqtt to Status
            action `status`
            message `online`
    end

on mqtt message
    begin
        put the mqtt message into Message
        print `Received:` Message
    end

! Wait
wait 10
stop
```

## Troubleshooting

### Not connecting?
- Check broker URL and port
- Verify MQTT.js is loaded
- Check browser console for errors
- Try public broker: `test.mosquitto.org:1883`

### Messages not received?
- Ensure topic names match exactly
- Check QoS levels
- Verify subscription succeeded
- Look for chunking issues (check console)

### Plugin not found?
- Load MQTT.js before plugin
- Load plugin before EasyCoder scripts
- Check `EasyCoder.domain.mqtt` exists in console

## Testing Commands

```javascript
// Check plugin loaded
console.log(EasyCoder_MQTT);

// Check MQTT.js loaded  
console.log(mqtt);

// Check domain registered
console.log(EasyCoder.domain.mqtt);
```

## Files

- **Plugin**: `mqtt.js`
- **Test Page**: `mqtt_test.html`
- **Example Script**: `mqtt_example.ecs`
- **Documentation**: `MQTT_PLUGIN_README.md`
- **Migration Guide**: `MQTT_MIGRATION_GUIDE.md`

## Resources

- **MQTT.js**: https://github.com/mqttjs/MQTT.js
- **Public Brokers**: https://github.com/mqtt/mqtt.org/wiki/public_brokers
- **MQTT Spec**: https://mqtt.org/

## QoS Levels

| Level | Guarantee | Use Case |
|-------|-----------|----------|
| 0 | At most once | Fire and forget |
| 1 | At least once | Default, reliable |
| 2 | Exactly once | Critical data |

---

**Version**: 1.0  
**Based on**: ec_mqtt.py (Python implementation)  
**License**: Same as EasyCoder-py
