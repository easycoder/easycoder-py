# Print the first 50 prime numbers #

## The algorithm ##

Start by setting the number of primes to print to 50 and initialise an array of primes to have 50 elements. Then preload it with the obvious 3, 5 and 7 and set an index to 3 to point to the next free element. Then start testing from 9.

The main loop runs until 50 primes have been discovered. Every odd number is tested by checking the remainder when it is divided by each of the known primes so far. If there is a remainder on all of them, the candidate is a prime. It is added to the array and the index moved on. In all cases, the candidate is increased by 2 and the tests start again.

Because EasyCoder only supports integer arithmetic, the candidate and each of the existing primes are multiplied by 10 before calling the modulo function.
