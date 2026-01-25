# EasyCoder MQTT Plugin for JavaScript - Complete Package

## 📦 Package Contents

This is a complete port of the EasyCoder MQTT plugin from Python to JavaScript, providing full MQTT client functionality for EasyCoder scripts running in browser or Node.js environments.

### Core Files

| File | Size | Purpose |
|------|------|---------|
| **mqtt.js** | 720 lines | Main plugin implementation |
| **mqtt_test.html** | 320 lines | Interactive browser test page |
| **mqtt_example.ecs** | 50 lines | Example EasyCoder script |

### Documentation

| File | Size | Purpose |
|------|------|---------|
| **MQTT_PLUGIN_README.md** | 470 lines | Complete API documentation |
| **MQTT_MIGRATION_GUIDE.md** | 590 lines | Python→JavaScript comparison |
| **MQTT_QUICK_REFERENCE.md** | 200 lines | Syntax quick reference |
| **MQTT_PLUGIN_SUMMARY.md** | 250 lines | Project overview |
| **INDEX.md** | This file | Navigation guide |

---

## 🚀 Quick Start

### 1. Installation

```html
<!-- Include dependencies -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
<script src="path/to/easycoder.js"></script>
<script src="mqtt.js"></script>
```

### 2. Basic Usage

```easycoder
topic MyTopic
init MyTopic name `test/topic` qos 1

mqtt id `Client` broker `test.mosquitto.org` port 1883 subscribe MyTopic

on mqtt message
    begin
        put the mqtt message into Data
        print Data
    end

send mqtt `Hello!` to MyTopic
```

### 3. Test It

Open `mqtt_test.html` in your browser for an interactive demo!

---

## 📚 Documentation Guide

### For New Users
**Start Here** → [MQTT_PLUGIN_README.md](MQTT_PLUGIN_README.md)
- Overview of features
- Installation instructions
- API reference with examples
- Troubleshooting guide

### For Developers
**Read Next** → [MQTT_MIGRATION_GUIDE.md](MQTT_MIGRATION_GUIDE.md)
- Architecture comparison: Python vs JavaScript
- Implementation patterns
- Code examples side-by-side
- Common pitfalls and solutions

### For Quick Reference
**Bookmark This** → [MQTT_QUICK_REFERENCE.md](MQTT_QUICK_REFERENCE.md)
- Command syntax cheat sheet
- Common patterns
- Troubleshooting tips
- Testing commands

---

## 🎯 Use Cases

### IoT Applications
```easycoder
! Monitor temperature sensor
topic TempSensor
init TempSensor name `home/sensors/temp` qos 1

mqtt id `HomeController` broker `mqtt.home.local` port 1883 subscribe TempSensor

on mqtt message
    begin
        put the mqtt message into Reading
        if Reading > 25
            begin
                ! Turn on cooling
                send mqtt to ACControl action `set` message `cooling_on`
            end
    end
```

### Real-time Messaging
```easycoder
! Chat application
topic ChatRoom
init ChatRoom name `chat/room1` qos 1

mqtt id `User123` broker `chat.example.com` port 1883 subscribe ChatRoom

on mqtt message
    begin
        put the mqtt message into Message
        display Message in ChatWindow
    end

! Send chat message
send mqtt to ChatRoom action `chat` sender Username message ChatText
```

### Remote Control
```easycoder
! Device control system
topic Commands
topic Status

init Commands name `device/cmd` qos 2
init Status name `device/status` qos 1

mqtt id `Device001` broker `control.example.com` port 1883 
    subscribe Commands

on mqtt message
    begin
        put the mqtt message into Command
        ! Execute command
        gosub to ExecuteCommand
        ! Report status
        send mqtt to Status action `status` message Result
    end
```

---

## 🔍 Feature Highlights

### ✅ Complete MQTT Support
- Connect to any MQTT broker
- Publish and subscribe to topics
- QoS levels 0, 1, 2 supported
- TLS/SSL ready (via MQTT.js)

### ✅ Automatic Message Chunking
- Splits large messages (>1KB) automatically
- Transparent reassembly on receive
- No size limits for messages
- Performance tracking

### ✅ Smart Message Handling
- Automatic JSON parsing
- Nested message parsing
- Fallback to string content
- Type preservation

### ✅ Event-Driven Architecture
- On connect handler
- On message handler
- Async operation support
- Non-blocking execution

### ✅ Developer Friendly
- English-like syntax
- Clear error messages
- Comprehensive documentation
- Working examples included

---

## 📖 API Summary

### Commands

```easycoder
topic Name                          ! Declare topic variable
init Topic name {n} qos {q}        ! Initialize topic
mqtt id {id} broker {b} port {p}   ! Create MQTT client
     subscribe {topic}              ! Subscribe to topic(s)
on mqtt connect                     ! Connection handler
on mqtt message                     ! Message handler
send mqtt {msg} to {topic}         ! Send message
```

### Values

```easycoder
the mqtt message                    ! Last received message
```

---

## 🔧 Project Structure

### Source Code
```
mqtt.js
├── MQTTClient class
│   ├── create()           # Initialize client
│   ├── onConnect()        # Handle connection
│   ├── onMessage()        # Handle messages
│   ├── sendMessage()      # Publish with chunking
│   └── _sendRapidFire()   # Chunk transmission
│
├── ECTopic class          # Topic objects
│
├── Command Handlers
│   ├── Init              # Initialize topics
│   ├── MQTT              # Create client
│   ├── On                # Event handlers
│   ├── Send              # Publish messages
│   └── Topic             # Declare variables
│
├── Value Handler          # Get values
├── Condition Handler      # (Reserved)
└── Dispatcher            # Route commands
```

### Documentation Structure
```
Documentation/
├── INDEX.md                      # You are here
├── MQTT_PLUGIN_README.md        # Main documentation
├── MQTT_MIGRATION_GUIDE.md      # Implementation guide
├── MQTT_QUICK_REFERENCE.md      # Quick reference
└── MQTT_PLUGIN_SUMMARY.md       # Project summary
```

---

## 🧪 Testing

### Browser Test (Interactive)
```bash
# Open in browser
firefox mqtt_test.html
# or
chromium mqtt_test.html
```

Features:
- Live connection to test.mosquitto.org
- Send and receive messages
- Visual feedback
- Connection status indicator

### Script Test
```html
<!-- In your HTML -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
<script src="easycoder.js"></script>
<script src="mqtt.js"></script>

<pre id="easycoder-script">
    ! Your script here, e.g. mqtt_example.ecs
</pre>
```

### Console Test
```javascript
// Check plugin loaded
console.log(EasyCoder_MQTT);

// Check handlers available
console.log(EasyCoder_MQTT.getHandler('mqtt'));
console.log(EasyCoder_MQTT.getHandler('send'));

// Check domain registered (if EasyCoder loaded)
console.log(EasyCoder.domain.mqtt);
```

---

## 🆚 Comparison with Python Version

### Same Features ✅
- All EasyCoder commands
- Message chunking protocol
- Event handling model
- QoS support
- JSON parsing
- Action validation

### Different Implementation 🔄
- JavaScript vs Python
- MQTT.js vs paho-mqtt
- Event-driven vs threading
- Browser/Node.js vs CLI
- Plugin file vs built-in module

### Script Compatibility 💯
**100% compatible** - Scripts work unchanged in both versions!

See [MQTT_MIGRATION_GUIDE.md](MQTT_MIGRATION_GUIDE.md) for details.

---

## 📦 Dependencies

### Required
- **MQTT.js** - MQTT client library
  - CDN: `https://unpkg.com/mqtt/dist/mqtt.min.js`
  - npm: `mqtt`
  - Version: Latest (4.x or 5.x)

### Optional
- **EasyCoder.js** - Core EasyCoder runtime
  - Required to run EasyCoder scripts
  - Plugin self-registers when loaded

---

## 🔗 Related Files

### In This Package
- `mqtt.js` - Use this in your JavaScript project
- `mqtt_test.html` - Test the plugin standalone
- `mqtt_example.ecs` - Template for your scripts

### Python Reference
- `easycoder/ec_mqtt.py` - Original Python implementation
- `tests/mqtt.ecs` - Python test script (syntax identical)

---

## 📝 Common Tasks

### Copy Plugin to Your Project
```bash
cp mqtt.js /path/to/your/easycoder/plugins/
```

### Include in HTML Page
```html
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
<script src="plugins/mqtt.js"></script>
```

### Create EasyCoder Script
Use `mqtt_example.ecs` as template, or:
```easycoder
script MyApp
topic MyTopic
init MyTopic name `my/topic` qos 1
mqtt id `Client` broker `broker.example.com` port 1883 subscribe MyTopic
! ... your code ...
```

### Test Connection
```easycoder
mqtt id `Test` broker `test.mosquitto.org` port 1883 subscribe Topic
on mqtt connect
    begin
        print `Connected!`
    end
```

---

## 🐛 Troubleshooting

### Plugin not loading?
- ✓ Check MQTT.js is loaded first
- ✓ Check console for errors
- ✓ Verify `EasyCoder_MQTT` exists in console

### Can't connect?
- ✓ Check broker URL and port
- ✓ Try `test.mosquitto.org:1883`
- ✓ Check firewall/network
- ✓ Look at browser console

### Messages not received?
- ✓ Verify topic names match
- ✓ Check subscription succeeded
- ✓ Look for chunking issues
- ✓ Check QoS levels

See [MQTT_PLUGIN_README.md](MQTT_PLUGIN_README.md) § Troubleshooting for more.

---

## 📄 License

Same as EasyCoder-py project.

---

## 🤝 Contributing

This plugin is part of the EasyCoder project. To contribute:
1. Test thoroughly with various brokers
2. Document any issues or enhancements
3. Follow the existing code style
4. Update documentation as needed

---

## 📞 Support

### Documentation
- **Full API**: [MQTT_PLUGIN_README.md](MQTT_PLUGIN_README.md)
- **Migration Guide**: [MQTT_MIGRATION_GUIDE.md](MQTT_MIGRATION_GUIDE.md)
- **Quick Ref**: [MQTT_QUICK_REFERENCE.md](MQTT_QUICK_REFERENCE.md)

### Examples
- **Test Page**: Open `mqtt_test.html`
- **Script Example**: See `mqtt_example.ecs`
- **Python Ref**: Check `tests/mqtt.ecs`

### Resources
- **MQTT.js Docs**: https://github.com/mqttjs/MQTT.js
- **MQTT Spec**: https://mqtt.org/
- **Public Brokers**: https://github.com/mqtt/mqtt.org/wiki/public_brokers

---

## ✨ Credits

**Original Python Implementation**: `easycoder/ec_mqtt.py`  
**JavaScript Port**: Complete feature parity with Python version  
**Based on**: EasyCoder-py MQTT plugin  
**Created**: January 2026  
**Version**: 1.0

---

## 🎉 Ready to Use!

All files are ready to use. Start with:
1. **Read**: [MQTT_PLUGIN_README.md](MQTT_PLUGIN_README.md)
2. **Test**: Open `mqtt_test.html`
3. **Build**: Use `mqtt_example.ecs` as template
4. **Deploy**: Copy `mqtt.js` to your project

Happy coding! 🚀
