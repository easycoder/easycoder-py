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

## The EasyCoder programming language
There are three primary components to the language:

 - Keywords
 - Values
 - Conditions

The language comprises a general-purpose core package, which can be enhanced by plugins to provide special features on demand.

[The core package](doc/README.md)
