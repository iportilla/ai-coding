package main

import (
	"fmt"
	"math"
	"strings"
	"time"
)

// VIBE CODING: Quick implementation without optimization
func vibeFindPrimes(n int) []int {
	/*
	   Find all prime numbers up to n - simple but inefficient

	   Args:
	       n: Upper limit to find primes

	   Returns:
	       Slice of prime numbers
	*/
	primes := []int{}

	for num := 2; num <= n; num++ {
		isPrime := true

		// Check if num is divisible by any number from 2 to num-1
		for i := 2; i < num; i++ {
			if num%i == 0 {
				isPrime = false
				break
			}
		}

		if isPrime {
			primes = append(primes, num)
		}
	}

	return primes // O(n²) - very slow for large n!
}

// HUMAN CODING: Optimized implementation with mathematical insights
func humanFindPrimes(n int) []int {
	/*
	   Find all prime numbers up to n using optimized algorithm

	   Uses several optimizations:
	   1. Only check divisibility up to sqrt(num)
	   2. Skip even numbers after 2
	   3. Early exit when divisor found

	   Args:
	       n: Upper limit to find primes

	   Returns:
	       Slice of prime numbers
	*/
	if n < 2 {
		return []int{}
	}

	primes := []int{2} // Start with 2, the only even prime

	// Only check odd numbers
	for num := 3; num <= n; num += 2 {
		isPrime := true
		sqrtNum := int(math.Sqrt(float64(num)))

		// Only need to check up to square root of num
		for i := 3; i <= sqrtNum; i += 2 {
			if num%i == 0 {
				isPrime = false
				break
			}
		}

		if isPrime {
			primes = append(primes, num)
		}
	}

	return primes // Much faster: O(n√n) with constant factor improvements
}

// EXPERT CODING: Sieve of Eratosthenes - the classic algorithm
func expertFindPrimes(n int) []int {
	/*
	   Find all prime numbers up to n using Sieve of Eratosthenes

	   This is the most efficient algorithm for finding all primes up to n

	   Args:
	       n: Upper limit to find primes

	   Returns:
	       Slice of prime numbers
	*/
	if n < 2 {
		return []int{}
	}

	// Create slice of boolean values, initially all true
	isPrime := make([]bool, n+1)
	for i := range isPrime {
		isPrime[i] = true
	}
	isPrime[0] = false
	isPrime[1] = false

	// Sieve algorithm
	for i := 2; i*i <= n; i++ {
		if isPrime[i] {
			// Mark all multiples of i as not prime
			for j := i * i; j <= n; j += i {
				isPrime[j] = false
			}
		}
	}

	// Collect all numbers that are still marked as prime
	primes := []int{}
	for i := 2; i <= n; i++ {
		if isPrime[i] {
			primes = append(primes, i)
		}
	}

	return primes // O(n log log n) - optimal for this problem!
}

// Helper function to convert int slice to comma-separated string
func intsToString(nums []int) string {
	strs := make([]string, len(nums))
	for i, num := range nums {
		strs[i] = fmt.Sprintf("%d", num)
	}
	return strings.Join(strs, ", ")
}

func main() {
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("EXAMPLE: Prime Number Finder")
	fmt.Println(strings.Repeat("=", 60))

	// Test with different values
	testValues := []int{10, 100, 1000}

	for _, n := range testValues {
		fmt.Printf("\nFinding primes up to %d:\n", n)
		fmt.Println(strings.Repeat("-", 60))

		// Vibe coding
		vibeStart := time.Now()
		vibeResult := vibeFindPrimes(n)
		vibeTime := time.Since(vibeStart).Seconds() * 1000 // Convert to ms

		// Human coding
		humanStart := time.Now()
		humanResult := humanFindPrimes(n)
		humanTime := time.Since(humanStart).Seconds() * 1000

		// Expert coding
		expertStart := time.Now()
		expertResult := expertFindPrimes(n)
		expertTime := time.Since(expertStart).Seconds() * 1000

		// Display results
		if n <= 100 {
			fmt.Printf("Primes found: %s\n", intsToString(expertResult))
		} else {
			fmt.Printf("Number of primes found: %d\n", len(expertResult))
			fmt.Printf("First 10 primes: %s\n", intsToString(expertResult[:10]))
			fmt.Printf("Last 10 primes: %s\n", intsToString(expertResult[len(expertResult)-10:]))
		}

		fmt.Println("\nPerformance comparison:")
		fmt.Printf("  Vibe coding:   %.4fms (O(n²))\n", vibeTime)
		fmt.Printf("  Human coding:  %.4fms (O(n√n))\n", humanTime)
		fmt.Printf("  Expert coding: %.4fms (O(n log log n))\n", expertTime)

		if vibeTime > humanTime {
			fmt.Printf("  ❌ Vibe is %.1fx slower than Human\n", vibeTime/humanTime)
		}
		if humanTime > expertTime {
			fmt.Printf("  ✅ Expert is %.1fx faster than Human\n", humanTime/expertTime)
		}

		// Educational note for small n values
		if n <= 10 {
			fmt.Printf("\n  💡 Note: For small n=%d, differences are minimal because:\n", n)
			fmt.Println("     - All algorithms finish in microseconds")
			fmt.Println("     - Function overhead can exceed actual computation time")
			fmt.Println("     - Big O notation matters most as n grows large!")
		}
	}

	// Edge case testing
	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("Edge Case Testing")
	fmt.Println(strings.Repeat("=", 60))

	edgeCases := []struct {
		n    int
		desc string
	}{
		{0, "n = 0 (no primes)"},
		{1, "n = 1 (no primes)"},
		{2, "n = 2 (first prime)"},
		{-5, "n = -5 (negative number)"},
	}

	for _, tc := range edgeCases {
		result := expertFindPrimes(tc.n)
		fmt.Printf("%s: [%s]\n", tc.desc, intsToString(result))
	}

	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("SUMMARY")
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println(`
VIBE CODING (Naive approach):
❌ Simple nested loops
❌ Checks all numbers from 2 to n-1
❌ O(n²) time complexity
✅ Easy to understand

HUMAN CODING (Optimized approach):
✅ Only checks up to √n
✅ Skips even numbers after 2
✅ O(n√n) time complexity
✅ Significant performance improvement

EXPERT CODING (Sieve of Eratosthenes):
✅ Classic algorithm from ancient Greece
✅ Uses memory to trade for speed
✅ O(n log log n) time complexity
✅ Best algorithm for finding all primes up to n
✅ Handles edge cases properly

Key Takeaway:
Choosing the right algorithm matters! For n=1000:
- Vibe coding: ~100x slower
- Human coding: ~10x slower
- Expert coding: Optimal performance
`)
}
