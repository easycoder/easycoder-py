# Introduction
**_EasyCoder_** is a high-level English-like scripting language suited for prototyping and rapid testing of ideas. It operates on the command line and a graphics module is under construction. The language is written in Python and it acts as a fairly thin wrapper around standard Python functions, giving fast compilation and good runtime performance for general applications.
<hr>

There is also a JavaScript version of **_EasyCoder_**, which provides a full set of graphical features to run in a browser. For this, please visit

Repository: [https://github.com/easycoder/easycoder.github.io](https://github.com/easycoder/easycoder.github.io)  
Website: [https://easycoder.github.io](https://easycoder.github.io)
<hr>

## Quick Start
Install **_EasyCoder_** in your Python environment:
```
pip install requests pytz easycoder
```

Test the install by typing the command `easycoder`.
<hr>
On Linux, this will probably fail as the installer places the executable file in the `$HOME/.local/bin` directory. So give the command
```
    export PATH=$HOME/.local/bin:$PATH
```

To make this change permanent, edit your `.profile` file, adding the following:
```
# set PATH so it includes user's private .local/bin if it exists
if [ -d "$HOME/.local/bin" ] ; then
    PATH="$HOME/.local/bin:$PATH"
fi
```
<hr>

Now write a test script, 'hello.ecs', containing the following:
```
print `Hello, world!`
```
(Note the backticks.) This is traditionally the first program to be written in virtually any language. To run it, use `easycoder hello.ecs`.

The output will look like this (the version number will differ):
```
EasyCoder version 250101.1
Compiled <anon>: 1 lines (2 tokens) in 0 ms
Run <anon>
1-> Hello, world!
```

It's conventional to add a program title to a script:
```
!   Test script
    script Test
    print `Hello, world!`
```
The first line here is just a comment and has no effect on the running of the script.   The second line gives the script a name, which is useful in debugging as it says which script was running. When run, the output is now
```
EasyCoder version 250101.1
Compiled Test: 3 lines (4 tokens) in 0 ms
Run Test
3-> Hello, world!
```

As you might guess from the above, the print command shows the line in the script it was called from. This is very useful in tracking down debugging print commands in large scripts.

Here in the repository is a folder called `scripts` containing some sample scripts:

`fizzbuzz.ecs` is a simple programming challenge often given at job interviews  
`tests.ecs` is a test program containing many of the **_EasyCoder_** features  
`benchmark.ecs` allows the performance of **_EasyCoder_** to be compared to other languages if a similar script is written for each one.

## Graphical programmming
**_EasyCoder_** includes a graphical programming environment that is in the early stages of development. Some demo scripts will be included in the `scripts` directory; these can be recognised by the extension`.ecg`. To run them, first install `tkinter`. On Linux this is done with
```
    sudo apt install python3-tk
```

Next, install the Python `pySimpleGUI` graphics library; this is done with `pip install pysimplegui`. Then run your **_EasyCoder_** script using `easycoder {scriptname}.ecg`.

Graphical scripts look much like any other script but their file names must use the extension `.ecg` to signal to **_EasyCoder_** that it needs to load the graphics module. Non-graphical applications can use any extension but `.ecs` is recommended. This allows the **_EasyCoder_** application to be used wherever Python is installed, in either a command-line or a graphical environment, but graphics will of course not be available in the former.

Some demo graphical scripts will included in the `scripts` directory as development proceeds.

`gtest.ecg` contains sample code to demonstrate and test basic features.

## Significant features

 - English-like syntax based on vocabulary rather than structure. Scripts can be read as English
 - Comprehensive feature set
 - Runs directly from source scripts. A fast compiler creates efficient intermediate code that runs immediately after compilation
 - Low memory requirements
 - Minimim dependency on other 3rd-party packages
 - Built-in co-operative multitasking
 - Dynamic loading of scripts on demand
 - The language can be extended seamlessly using plugin function modules
 - Plays well with any Python code
 - Fully Open Source

## Programming reference

**_EasyCoder_** comprises a set of modules to handle tokenisation, compilation and runtime control. Syntax and grammar are defined by [packages](doc/README.md), of which there are currently two; the [core](doc/core/README.md) package, which implements a comprehensive set of command-line programming features, and and the [graphics](doc/graphics/README.md) package, which adds graphical features in a windowing environment.

## Extending the language

**_EasyCoder_** can be extended to add new functionality with the use of 'plugins'. These contain compiler and runtime modules for the added language features. **_EasyCoder_** can use the added keywords, values and conditions freely; the effect is completely seamless. There is an outline example in the `plugins` directory called `example.py`, which comprises a module called `Points` with new language syntax to deal with two-valued items such as coordinates. In the `scripts` directory there is `points.ecs`, which exercises the new functionality.

A plugin can act as a wrapper around any Python functionality that has a sensible API, thereby hiding its complexity. The only challenge is to devise an unambiguous syntax that doesn't clash with anything already existing in **_EasyCoder_**.
