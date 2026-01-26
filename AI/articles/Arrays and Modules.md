# Arrays and Modules in EasyCoder

Every programming languge has its own unique features, or combinations of features that are unique. Here are a pair of features in ***EasyCoder***, the combination of which is rarely if ever implemented in any other language. First I'll describe the features, then show an example of how well they work together.

## Arrays
***EasyCoder*** uses plain English words instead of computer code, and the use of symbols is deliberately kept an absolute minimum. (They comprise exclamation marks for comments, colons for labels and backticks to enclose text.) So when it came to implementing arrays, something other than parentheses had to be used. The solution came from SQL, where 'cursors' are used to point to an element of what is essentially an array.

In ***EasyCoder***, every variable is an array. Most only ever have a single element, but they can all have as many as needed for the job at hand. Each variable has an internal 'index' value which specifies which element of the array is currently serving as the value of that variable, and in most cases is zero. Commands exist to change the number of elements and to change the index to point to any element of the array. The array always behaves as if it only has one element - the one currently pointed to by the index.

## Modules
A module is just an ***EasyCoder*** script, the same as any other. It becomes a module when it is run from another script. The identity of the new script is held as a 'module' variable in the parent script. A complete application can be built with any number of modules all working together.

The partnership of a parent script and its child modules offers some unique features, largely based on the ability of the parent to share some of its own variables with the child script. In some ways this is akin to a function subroutine in other languages, but is different in a number of ways. The first is that every time a script is invoked it must be compiled from source. This typically takes a few milliseconds to a few tens of milliseconds, but it's not by any means instant as functions are in Java or Python. So it's not intended for use as a general-purpose function mechanism.

A major difference comes from the way that a child module can run concurrently with its parent. ***EasyCoder** implements cooperative multitasking, which means that threads run until they come to a 'stop' or a 'wait' command, then control is transferred to another thread if there's one waiting to start execution. Obviously it's possible to write a thread that doesn't release in this way, but in the majority of applications targetted by the language this is unlikely to happen or is easy to avoid.

When a module is launched, the parent blocks while the new module runs its initialisation code, whatever that might comprise. This may be all that's wanted, in which case an 'exit' command will close the module and hand control back to the parent. But the other option is to issue a 'release parent' command, which then allows the parent to resume when the child reaches a 'stop' or 'wait' command. So in a real-world control program, modules can individually handle single or multiple hardware devices independently of each other.

There's also an option for a parent to send a message to one of its child modules and for a child to message its parent. This allows two or more modules to run indefintely, passing messages back and forth as if they were independent programs.

## Combining the two
For this I need an application. Let's look at a home heating control system, where each room has its own thermometer and heater that are independent of all the other rooms. In most languages, doing this in a single program can be clumsy and hard to test, involving system-level multithreading, but in ***EasyCoder*** it gets a lot simpler.

We start with a main program, which reads the file(s) comprising a 'map' of the system, identifying the rooms and the devices contained therein. We then write a module that can handle the needs of a single room, and specify a module variable to handle it. The module is given as many array elements as there are rooms, then one by one they are launched, each one being handed the map variable, the name of the room and a status variable, intially empty, that will hold the temperature value read from the thermometer and the on-off state of the heating in the room.

Each of these modules looks in the map for the parameters and rules that apply to the room whose name is given. It then starts managing the room. As it does so it keeps updating the temperature and on-off state in the status variable shared by the main program. Note that because this is cooperative multitasking, two threads cannot modify the same variable at the same time, so there is no need for locks.

It is very easy to substitute a simulation of a room for the real thing. All that matters is that it takes the same inputs and returns the same outputs as the real thing.

While all this is happening, the main program has launched a GUI module. This also uses the map, to create a display of the entire system, and the status variable to provide the values that will be displayed in the appropriate places. When the user interacts with the display, changes result in a message being sent to the main script, which updates the map accordingly. The interconnection of all the modules ensures that the entire system updates itself automatically, each module detecting a change and responding to it.

Other modules can be added, such as one that uses MQTT to communicate with a remote UI, perhaps on a smartphone. Another might handle collection of statistics. The point is that additions are minimally disruptive.

As for testing, it's quite easy to take a module and test it in isolation, by simulating the key aspects of other modules that interact with it. Bugs reveal themselves quickly as it's usually obvious where they originate.
