# Introduction
**_EasyCoder_** is a high-level English-like scripting language suited for prototyping and rapid testing of ideas. It operates on the command line and a graphics module is under construction. This version of the language is written in Python and it acts as a fairly thin wrapper around Python functions, giving fast compilation and good runtime performance for general applications.
<hr>

There is also a JavaScript version of **_EasyCoder_**, which provides a full set of graphical features to run in a browser. For this, please visit

Repository: [https://github.com/easycoder/easycoder.github.io](https://github.com/easycoder/easycoder.github.io)  
Website: [https://easycoder.github.io](https://easycoder.github.io)
<hr>

## Quick Start
Install **_EasyCoder_** in your Python environment:
```
pip install easycoder
```
You may also need to install `pytz`, as some commands need it.

Write a test script, 'hello.ecs', containing the following:
```
print `Hello, world!`
```
This is traditionally the first program to be written in virtually any language. To run it, use `easycoder hello.ecs`.

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
**_EasyCoder_** includes a graphical programming environment that is in the early stages of development. A couple of demo scripts are included in the `scripts` directory. To run them, first install the Python `kivy` graphics library if it's not already present on your system. This is done with `pip install kivy`. Then run your **_EasyCoder_** script using `easycoder {scriptname}.ecg`.

Graphical scripts look much like any other script but their file names must use the extension `.ecg` to signal to **_EasyCoder_** that it needs to load the graphics module. Non-graphical applications can use any extension but `.ecs` is recommended. This allows the **_EasyCoder_** application to be used wherever Python is installed, in either a command-line or a graphical environment, but graphics will of course not be available in the former.

Some demo graphical scripts are included in the `scripts` directory:

`graphics-demo.ecg` shows some of the elements that can be created, and demonstrates a variety of the graphical features of the language such as detecting when elements are clicked.

`wave.ecg` is a "Mexican Wave" simulation.

`keyboard.ecg` creates an on-screen keyboard (currently a 4-function calculator keypad) that responds to clicks on its keys. It uses a plugin module (see below) to add extra vocabulary and syntax to the language. This is currently under development so its features are likely to change. The intention is to support a wide range of keyboard styles with the minimum mount of coding. The plugin (`ec_keyword.py`) can be downloaded from the repository.

**_EasyCoder_** graphics are handled by a library module, `ec_renderer` that can be used outside of the **_EasyCoder_** environment, in other Python programs. The renderer works with JSON-formatted specifications of the itens to be displayed.

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
