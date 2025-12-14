"""
Prime Number Finder Example
Demonstrates finding prime numbers up to n
"""

import time
import math

print("=" * 60)
print("EXAMPLE: Prime Number Finder")
print("=" * 60)


# VIBE CODING: Quick implementation without optimization
def vibe_find_primes(n):
    """
    Find all prime numbers up to n - simple but inefficient
    
    Args:
        n: Upper limit to find primes
    
    Returns:
        List of prime numbers
    """
    primes = []
    
    for num in range(2, n + 1):
        is_prime = True
        
        # Check if num is divisible by any number from 2 to num-1
        for i in range(2, num):
            if num % i == 0:
                is_prime = False
                break
        
        if is_prime:
            primes.append(num)
    
    return primes  # O(n²) - very slow for large n!


# HUMAN CODING: Optimized implementation with mathematical insights
def human_find_primes(n):
    """
    Find all prime numbers up to n using optimized algorithm
    
    Uses several optimizations:
    1. Only check divisibility up to sqrt(num)
    2. Skip even numbers after 2
    3. Early exit when divisor found
    
    Args:
        n: Upper limit to find primes
    
    Returns:
        List of prime numbers
    """
    if n < 2:
        return []
    
    primes = [2]  # Start with 2, the only even prime
    
    # Only check odd numbers
    for num in range(3, n + 1, 2):
        is_prime = True
        sqrt_num = int(math.sqrt(num))
        
        # Only need to check up to square root of num
        for i in range(3, sqrt_num + 1, 2):
            if num % i == 0:
                is_prime = False
                break
        
        if is_prime:
            primes.append(num)
    
    return primes  # Much faster: O(n√n) with constant factor improvements


# EXPERT CODING: Sieve of Eratosthenes - the classic algorithm
def expert_find_primes(n):
    """
    Find all prime numbers up to n using Sieve of Eratosthenes
    
    This is the most efficient algorithm for finding all primes up to n
    
    Args:
        n: Upper limit to find primes
    
    Returns:
        List of prime numbers
    """
    if n < 2:
        return []
    
    # Create array of boolean values, initially all True
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    
    # Sieve algorithm
    for i in range(2, int(math.sqrt(n)) + 1):
        if is_prime[i]:
            # Mark all multiples of i as not prime
            for j in range(i * i, n + 1, i):
                is_prime[j] = False
    
    # Collect all numbers that are still marked as prime
    primes = [i for i in range(2, n + 1) if is_prime[i]]
    
    return primes  # O(n log log n) - optimal for this problem!


# Test with different values
test_values = [10, 100, 1000]

for n in test_values:
    print(f"\nFinding primes up to {n}:")
    print("-" * 60)
    
    # Vibe coding
    vibe_start = time.perf_counter()
    vibe_result = vibe_find_primes(n)
    vibe_time = (time.perf_counter() - vibe_start) * 1000  # Convert to ms
    
    # Human coding
    human_start = time.perf_counter()
    human_result = human_find_primes(n)
    human_time = (time.perf_counter() - human_start) * 1000
    
    # Expert coding
    expert_start = time.perf_counter()
    expert_result = expert_find_primes(n)
    expert_time = (time.perf_counter() - expert_start) * 1000
    
    # Display results
    if n <= 100:
        print(f"Primes found: {', '.join(map(str, expert_result))}")
    else:
        print(f"Number of primes found: {len(expert_result)}")
        print(f"First 10 primes: {', '.join(map(str, expert_result[:10]))}")
        print(f"Last 10 primes: {', '.join(map(str, expert_result[-10:]))}")
    
    print(f"\nPerformance comparison:")
    print(f"  Vibe coding:   {vibe_time:.4f}ms (O(n²))")
    print(f"  Human coding:  {human_time:.4f}ms (O(n√n))")
    print(f"  Expert coding: {expert_time:.4f}ms (O(n log log n))")
    
    if vibe_time > human_time:
        print(f"  ❌ Vibe is {vibe_time / human_time:.1f}x slower than Human")
    if human_time > expert_time:
        print(f"  ✅ Expert is {human_time / expert_time:.1f}x faster than Human")
    
    # Educational note for small n values
    if n <= 10:
        print(f"\n  💡 Note: For small n={n}, differences are minimal because:")
        print(f"     - All algorithms finish in microseconds")
        print(f"     - Function overhead can exceed actual computation time")
        print(f"     - Big O notation matters most as n grows large!")


# Edge case testing
print("\n" + "=" * 60)
print("Edge Case Testing")
print("=" * 60)

edge_cases = [
    (0, "n = 0 (no primes)"),
    (1, "n = 1 (no primes)"),
    (2, "n = 2 (first prime)"),
    (-5, "n = -5 (negative number)")
]

for n, desc in edge_cases:
    result = expert_find_primes(n)
    print(f"{desc}: {result}")


print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("""
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
""")
