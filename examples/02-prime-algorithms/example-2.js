/**
 * Prime Number Finder Example
 * Demonstrates finding prime numbers up to n
 */

console.log("=".repeat(60));
console.log("EXAMPLE: Prime Number Finder");
console.log("=".repeat(60));

// VIBE CODING: Quick implementation without optimization
function vibeFindPrimes(n) {
    /**
     * Find all prime numbers up to n - simple but inefficient
     * @param {number} n - Upper limit to find primes
     * @returns {number[]} Array of prime numbers
     */
    const primes = [];

    for (let num = 2; num <= n; num++) {
        let isPrime = true;

        // Check if num is divisible by any number from 2 to num-1
        for (let i = 2; i < num; i++) {
            if (num % i === 0) {
                isPrime = false;
                break;
            }
        }

        if (isPrime) {
            primes.push(num);
        }
    }

    return primes;  // O(n²) - very slow for large n!
}

// HUMAN CODING: Optimized implementation with mathematical insights
function humanFindPrimes(n) {
    /**
     * Find all prime numbers up to n using optimized algorithm
     * Uses several optimizations:
     * 1. Only check divisibility up to sqrt(num)
     * 2. Skip even numbers after 2
     * 3. Early exit when divisor found
     * @param {number} n - Upper limit to find primes
     * @returns {number[]} Array of prime numbers
     */
    if (n < 2) return [];

    const primes = [2];  // Start with 2, the only even prime

    // Only check odd numbers
    for (let num = 3; num <= n; num += 2) {
        let isPrime = true;
        const sqrtNum = Math.sqrt(num);

        // Only need to check up to square root of num
        for (let i = 3; i <= sqrtNum; i += 2) {
            if (num % i === 0) {
                isPrime = false;
                break;
            }
        }

        if (isPrime) {
            primes.push(num);
        }
    }

    return primes;  // Much faster: O(n√n) with constant factor improvements
}

// EXPERT CODING: Sieve of Eratosthenes - the classic algorithm
function expertFindPrimes(n) {
    /**
     * Find all prime numbers up to n using Sieve of Eratosthenes
     * This is the most efficient algorithm for finding all primes up to n
     * @param {number} n - Upper limit to find primes
     * @returns {number[]} Array of prime numbers
     */
    if (n < 2) return [];

    // Create array of boolean values, initially all true
    const isPrime = new Array(n + 1).fill(true);
    isPrime[0] = isPrime[1] = false;

    // Sieve algorithm
    for (let i = 2; i * i <= n; i++) {
        if (isPrime[i]) {
            // Mark all multiples of i as not prime
            for (let j = i * i; j <= n; j += i) {
                isPrime[j] = false;
            }
        }
    }

    // Collect all numbers that are still marked as prime
    const primes = [];
    for (let i = 2; i <= n; i++) {
        if (isPrime[i]) {
            primes.push(i);
        }
    }

    return primes;  // O(n log log n) - optimal for this problem!
}

// Test with different values
const testValues = [10, 100, 1000];

testValues.forEach(n => {
    console.log(`\nFinding primes up to ${n}:`);
    console.log("-".repeat(60));

    // Vibe coding
    const vibeStart = performance.now();
    const vibeResult = vibeFindPrimes(n);
    const vibeTime = performance.now() - vibeStart;

    // Human coding
    const humanStart = performance.now();
    const humanResult = humanFindPrimes(n);
    const humanTime = performance.now() - humanStart;

    // Expert coding
    const expertStart = performance.now();
    const expertResult = expertFindPrimes(n);
    const expertTime = performance.now() - expertStart;

    // Display results
    if (n <= 100) {
        console.log(`Primes found: ${expertResult.join(", ")}`);
    } else {
        console.log(`Number of primes found: ${expertResult.length}`);
        console.log(`First 10 primes: ${expertResult.slice(0, 10).join(", ")}`);
        console.log(`Last 10 primes: ${expertResult.slice(-10).join(", ")}`);
    }

    console.log(`\nPerformance comparison:`);
    console.log(`  Vibe coding:   ${vibeTime.toFixed(4)}ms (O(n²))`);
    console.log(`  Human coding:  ${humanTime.toFixed(4)}ms (O(n√n))`);
    console.log(`  Expert coding: ${expertTime.toFixed(4)}ms (O(n log log n))`);

    if (vibeTime > humanTime) {
        console.log(`  ❌ Vibe is ${(vibeTime / humanTime).toFixed(1)}x slower than Human`);
    }
    if (humanTime > expertTime) {
        console.log(`  ✅ Expert is ${(humanTime / expertTime).toFixed(1)}x faster than Human`);
    }

    // Educational note for small n values
    if (n <= 10) {
        console.log(`\n  💡 Note: For small n=${n}, differences are minimal because:`);
        console.log(`     - All algorithms finish in microseconds`);
        console.log(`     - Function overhead can exceed actual computation time`);
        console.log(`     - Big O notation matters most as n grows large!`);
    }
});

// Edge case testing
console.log("\n" + "=".repeat(60));
console.log("Edge Case Testing");
console.log("=".repeat(60));

const edgeCases = [
    { n: 0, desc: "n = 0 (no primes)" },
    { n: 1, desc: "n = 1 (no primes)" },
    { n: 2, desc: "n = 2 (first prime)" },
    { n: -5, desc: "n = -5 (negative number)" }
];

edgeCases.forEach(({ n, desc }) => {
    const result = expertFindPrimes(n);
    console.log(`${desc}: [${result.join(", ")}]`);
});

console.log("\n" + "=".repeat(60));
console.log("SUMMARY");
console.log("=".repeat(60));
console.log(`
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
`);
