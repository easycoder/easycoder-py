# Introduction
This is the Python version of EasyCoder, a high-level English-like scripting language suited for prototyping and rapid testing of ideas. It operates on the command line.

The JavaScript version of EasyCoder, which provides a full set of graphical features to run in a browser, is at [https://easycoder.github.io](https://easycoder.github.io)

## Quick Start
1: Install EasyCoder in your Python environment:
```
pip install easycoder
```
2: Write a test script, 'hello.ecs':
```
print `Hello, world!`
```
This is traditionally the first program to be written in virtually any language. To run it under REPL, launch Python and type the following commands:
```
from easycoder import Program
Program(['hello.ecs'])
```
The script is passed in as a list because it could be just one of a number of command-line arguments.

The output will look like this:
```
Compiled <anon>: 1 lines (2 tokens) in 0 ms
Run <anon>
1-> Hello, world!
```
To avoid having to use REPL you can set up a simple executable command such as this Python script. On Linux the first line will ensure it runs as a command if given execute permission. You can name it 'easycoder' - there's no need for a '.py' extension.
```
#!/bin/python3

from sys import argv
from easycoder import Program

if (len(argv) > 1):
    Program(argv[1:])
else:
    print('Syntax: easycoder <scriptname> [plugins]')
```
With this you can run your script with the command `easycoder hello.ecs`. You can place `easycoder` anywhere on your system execution path, such as in a local `bin` directory.

It's conventional to add a program title to a script:
```
!   Test script

    script Test

    print `Hello, world!`
```
The first line here is just a comment and has no effect on the running of the script. The second line gives the script a name, which is useful in debugging as it says which script was running. When run, the output is now
```
Compiled Test: 5 lines (4 tokens) in 0 ms
Run Test
5-> Hello, world!
```
As you can guess from the above, the print command gives the line in the script it was called from. This is very useful in tracking down debugging print commands in large scripts.

In the repository is a folder called `tests` containing a couple of sample scripts. `benchmark.ecs` allows the performance of EasyCoder to be compared to other languages if a similar program is written for each one. `tests.ecs` is a test program containing many of the EasyCoder features.

## The EasyCoder programming language
There are three primary components to the language:
 1 Keywords
 2 Values
 3 Conditions

All program lines start with a keyword - a command to EasyCoder to do something

(Under construction)
