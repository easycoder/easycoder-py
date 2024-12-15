# Introduction
This is the Python version of **_EasyCoder_**, a high-level English-like scripting language suited for prototyping and rapid testing of ideas. It operates on the command line.

The JavaScript version of **_EasyCoder_**, which provides a full set of graphical features to run in a browser, is at

Repository: [https://github.com/easycoder/easycoder.github.io](https://github.com/easycoder/easycoder.github.io)  
Website: [https://easycoder.github.io](https://easycoder.github.io)

## Quick Start
Install **_EasyCoder_** in your Python environment:
```
pip install easycoder
```
Write a test script, 'hello.ecs', containing the following:
```
print `Hello, world!`
```
This is traditionally the first program to be written in virtually any language. To run it, use `easycoder hello.ecs`.

The output will look like this:

```
EasyCoder version 5
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
The first line here is just a comment and has no effect on the running of the script. The second line gives the script a name, which is useful in debugging as it says which script was running. When run, the output is now

```
EasyCoder version 5
Compiled Test: 5 lines (4 tokens) in 0 ms
Run Test
5-> Hello, world!
```
As you can guess from the above, the print command gives the line in the script it was called from. This is very useful in tracking down debugging print commands in large scripts.

Here in the repository is a folder called `scripts` containing some sample scripts:

`benchmark.ecs` allows the performance of EasyCoder to be compared to other languages if a similar program is written for each one  
`tests.ecs` is a test program containing many of the EasyCoder features  
`fizzbuzz.ecs` is a simple programming challenge often given at job interviews

## Graphical programmming
**_EasyCoder_** is currently being extended to include a graphical programming environment. A single demo script `graphics-demo.ecs` is included in the `scripts` directory. To run it, first install the Python graphics library if it's not already present on your system. On Linux this is done with `sudo apt install python3-tk`. On Windows it's `pip install tk`. Then give the command `easycoder -g scripts/graphics-demo.ecs`.

As development progresses this demo script will be extended to include new features as they are added. **_EasyCoder_** graphics are handled by a library module, `ec_renderer` that can be used outside of the **_EasyCoder_** environment, in other Python programs.

## EasyCoder programming reference

The language comprises a general-purpose core package, which can be enhanced by plugins to provide special features on demand.

[The core package](doc/README.md)

## Extending the language

**_EasyCoder_** can be extended to add new functionality with the use of 'plugins'. These contain compiler and runtime modules for the added language features. **_EasyCoder_** can use the added keywords, values and conditions freely; the effect is completely seamless. There is an outline example in the `plugins` directory called `example.py`, which comprises a module called `Points` with new language syntax to deal with two-valued items such as coordinates. In the `scripts` directory there is `points.ecs`, which exercises the new functionality.

A plugin can act as a wrapper around any Python functionality that has a sensible API, thereby hiding its complexity. The only challenge is to devise an unambiguous syntax that doesn't clash with anything already existing in **_EasyCoder_**.
