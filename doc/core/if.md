## Syntax:
`if {condition} {true-outcome} [else {false-outcome}]`
## Examples:
`if Value1 is greater than Value2 put true into Result`  
`if Remaining is 0 stop else go to Repeat`
## Description:
`if` tests the condition that follows. If the result is `true` then control resumes at the named label; otherwise if there's an `else` section this is executed, then the program resumes at the next instruction after the `if`. (Unless a [goto](go.md) or [stop](stop.md) was encountered as in the second example). See also [while](while.md).

Next: [increment](increment.md)  
Prev: [gosub](gosub.md)

[Back to keywords](../keywords.md)
