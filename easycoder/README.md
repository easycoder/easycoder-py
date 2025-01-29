# EasyCode source code
These are the Python files that comprise **_EasyCoder_**.

**_EasyCoder_** has a small number of third-party dependencies. A minor one is `pytz`, which handles timezones. The biggest one by far is `PySimpleGUI`, a comprehensive Python graphics library.

If an **_EasyCoder_** script filename ends with `.ecs` it's a command-line script. If it ends with `.ecg` it's a script for a graphical application and will cause `PySimpleGUI` to be imported. Obviously this will only work on a GUI-based system, whereas command-line scripts will run anywhere there is Python.
