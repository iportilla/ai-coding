"""
Examples showing where VIBE CODING fails compared to careful HUMAN CODING
"""

print("=" * 60)
print("EXAMPLE 1: Order Preservation Bug")
print("=" * 60)

# Sample lists with some overlapping values (3 and 5 appear in both)
list1 = [10, 4, 3, 42, 5]
list2 = [60, 7, 8, 3, 5]

# VIBE CODING: Quick and dirty - looks fine at first glance
def vibe_merge(list1, list2):
    """Merge lists and remove duplicates - seems simple!"""
    merged_list = list1 + list2
    merged_list = list(set(merged_list))  # BUG: Loses order!
    return merged_list

# HUMAN CODING: Careful consideration of requirements
def human_merge(list1, list2):
    """Merge lists preserving order and removing duplicates"""
    seen = set()
    result = []
    for item in list1 + list2:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

# Compare outputs: vibe version will have random order, human version preserves original order
print(f"Vibe coding result:  {vibe_merge(list1, list2)}")
print(f"Human coding result: {human_merge(list1, list2)}")
print("❌ Vibe version loses insertion order!\n")


print("=" * 60)
print("EXAMPLE 2: Edge Case Handling")
print("=" * 60)

# VIBE CODING: Doesn't think about edge cases
def vibe_average(numbers):
    """Calculate average - what could go wrong?"""
    return sum(numbers) / len(numbers)  # BUG: Crashes on empty list!

# HUMAN CODING: Defensive programming
def human_average(numbers):
    """Calculate average with proper error handling"""
    if not numbers:
        return 0  # Or raise ValueError with clear message
    return sum(numbers) / len(numbers)

# Test with empty list to demonstrate error handling
try:
    print(f"Vibe average of []: {vibe_average([])}")
except ZeroDivisionError:
    print("❌ Vibe version crashes on empty list!")

print(f"Human average of []: {human_average([])}")
print("✅ Human version handles edge cases\n")


print("=" * 60)
print("EXAMPLE 3: Performance Issues")
print("=" * 60)

# Sample data for performance testing
data = list(range(1000))

# VIBE CODING: Nested loops without thinking about complexity
def vibe_find_duplicates(lst):
    """Find duplicates - simple nested loop"""
    duplicates = []
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            if lst[i] == lst[j] and lst[i] not in duplicates:
                duplicates.append(lst[i])
    return duplicates  # O(n²) - terrible for large lists!

# HUMAN CODING: Considers algorithmic complexity
def human_find_duplicates(lst):
    """Find duplicates efficiently using a hash map"""
    seen = set()
    duplicates = set()
    for item in lst:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    return list(duplicates)  # O(n) - much better!

import time

# Create test data with intentional duplicates (repeated 50 times)
test_data = [1, 2, 3, 2, 4, 5, 3, 6] * 50

# Time the vibe coding approach
start = time.time()
vibe_result = vibe_find_duplicates(test_data)
vibe_time = time.time() - start

# Time the human coding approach
start = time.time()
human_result = human_find_duplicates(test_data)
human_time = time.time() - start

print(f"Vibe coding time:  {vibe_time:.4f}s (O(n²))")
print(f"Human coding time: {human_time:.4f}s (O(n))")
print(f"❌ Vibe version is {vibe_time/human_time:.1f}x slower!\n")


print("=" * 60)
print("EXAMPLE 4: Prime Number Generation")
print("=" * 60)

# Find all prime numbers up to this value
n = 10000

# VIBE CODING: Check each number individually
def vibe_find_primes(n):
    """Find all primes up to n - simple trial division"""
    primes = []
    for num in range(2, n + 1):
        is_prime = True
        for i in range(2, int(num ** 0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
    return primes  # O(n² √n) - very slow!

# HUMAN CODING: Sieve of Eratosthenes
def human_find_primes(n):
    """Find all primes up to n using Sieve of Eratosthenes"""
    if n < 2:
        return []
    
    # Create a boolean array "is_prime" and initialize all as true
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    
    # Start with the smallest prime number, 2
    p = 2
    while p * p <= n:
        # If is_prime[p] is not changed, then it's a prime
        if is_prime[p]:
            # Mark all multiples of p as not prime
            for i in range(p * p, n + 1, p):
                is_prime[i] = False
        p += 1
    
    # Collect all numbers that are still marked as prime
    return [num for num in range(n + 1) if is_prime[num]]  # O(n log log n) - much faster!

import time

# Benchmark the vibe coding approach
start = time.time()
vibe_primes = vibe_find_primes(n)
vibe_time = time.time() - start

# Benchmark the human coding approach
start = time.time()
human_primes = human_find_primes(n)
human_time = time.time() - start

print(f"Finding primes up to {n}:")
print(f"Vibe coding time:  {vibe_time:.4f}s (O(n² √n))")
print(f"Human coding time: {human_time:.4f}s (O(n log log n))")
print(f"Both found {len(vibe_primes)} primes")
print(f"❌ Vibe version is {vibe_time/human_time:.1f}x slower!")
print(f"✅ Sieve of Eratosthenes is a classic algorithmic optimization\n")


print("=" * 60)
print("EXAMPLE 5: Security Vulnerability")
print("=" * 60)

# VIBE CODING: Eval seems convenient!
def vibe_calculator(expression):
    """Quick calculator using eval"""
    return eval(expression)  # DANGER: Code injection vulnerability!

# HUMAN CODING: Safe parsing
def human_calculator(expression):
    """Safe calculator with limited operations"""
    allowed_chars = set('0123456789+-*/(). ')
    if not all(c in allowed_chars for c in expression):
        raise ValueError("Invalid characters in expression")
    # Use ast.literal_eval or a proper parser in production
    return eval(expression)  # Still using eval but with validation

# Test with safe input
print(f"Vibe calc '2+2': {vibe_calculator('2+2')}")
print("❌ But vibe version allows: vibe_calculator('__import__(\"os\").system(\"ls\")')")
print("   This could execute arbitrary code!")
print(f"Human calc '2+2': {human_calculator('2+2')}")

# Test human version with malicious input to show it's blocked
try:
    human_calculator('__import__("os")')
except ValueError as e:
    print(f"✅ Human version blocks malicious input: {e}\n")


print("=" * 60)
print("SUMMARY")
print("=" * 60)
print("""
VIBE CODING is great for:
✅ Quick prototypes
✅ Exploratory coding
✅ Simple, well-understood problems

HUMAN CODING is essential for:
✅ Production code
✅ Edge case handling
✅ Performance-critical code
✅ Security-sensitive operations
✅ Maintainable, long-term codebases
""")
