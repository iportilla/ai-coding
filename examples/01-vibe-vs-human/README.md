# Example 1: Vibe Coding vs Human Coding

This script demonstrates common pitfalls when using "vibe coding" (quick, intuitive solutions) compared to careful "human coding" (thoughtful, robust solutions).

## Overview

The script contains 5 examples that highlight where fast, intuitive coding fails and why careful consideration is important for production code.

```mermaid
graph TD
    A[Coding Approach] --> B{Vibe Coding}
    A --> C{Human Coding}
    B --> D[Quick & Intuitive]
    B --> E[Potential Issues]
    E --> F[❌ Order Loss]
    E --> G[❌ Edge Cases]
    E --> H[❌ Performance]
    E --> I[❌ Security]
    C --> J[Thoughtful & Robust]
    C --> K[Production Ready]
    K --> L[✅ Order Preserved]
    K --> M[✅ Edge Cases Handled]
    K --> N[✅ Optimized Performance]
    K --> O[✅ Secure Implementation]
```

## Examples

### Example 1: Order Preservation Bug
- **Problem**: Merging two lists and removing duplicates
- **Vibe Coding Flaw**: Using `set()` loses insertion order
- **Human Solution**: Manual iteration with a set to track seen items while preserving order

### Example 2: Edge Case Handling
- **Problem**: Calculating the average of a list of numbers
- **Vibe Coding Flaw**: Crashes with `ZeroDivisionError` on empty lists
- **Human Solution**: Defensive programming with proper edge case handling

### Example 3: Performance Issues
- **Problem**: Finding duplicate items in a list
- **Vibe Coding Flaw**: O(n²) nested loops - slow for large datasets
- **Human Solution**: O(n) hash map approach for efficient duplicate detection
- **Performance**: Human version is significantly faster on large datasets

```mermaid
graph LR
    A["Input: 400 items"] --> B["Vibe Coding O(n²)"]
    A --> C["Human Coding O(n)"]
    B --> D["160,000 operations"]
    C --> E["400 operations"]
    D --> F["❌ Slow"]
    E --> G["✅ Fast"]
    style D fill:#ffcccc
    style E fill:#ccffcc
```

### Example 4: Prime Number Generation
- **Problem**: Finding all prime numbers up to n
- **Vibe Coding Flaw**: O(n² √n) trial division for each number
- **Human Solution**: O(n log log n) Sieve of Eratosthenes algorithm
- **Performance**: Human version is dramatically faster (orders of magnitude)

```mermaid
graph TD
    A["Find Primes up to 10000"] --> B["Vibe: Trial Division"]
    A --> C["Human: Sieve of Eratosthenes"]
    B --> D["Check each number<br/>individually"]
    B --> E["O(n² √n)"]
    C --> F["Mark multiples<br/>as composite"]
    C --> G["O(n log log n)"]
    E --> H["⏱️ Seconds"]
    G --> I["⚡ Milliseconds"]
    style H fill:#ffcccc
    style I fill:#ccffcc
```

### Example 5: Security Vulnerability
- **Problem**: Building a simple calculator
- **Vibe Coding Flaw**: Using `eval()` without validation allows code injection attacks
- **Human Solution**: Input validation to block malicious code execution

```mermaid
sequenceDiagram
    participant U as User Input
    participant V as Vibe Calc
    participant H as Human Calc
    participant S as System
    
    U->>V: "2+2"
    V->>V: eval("2+2")
    V-->>U: 4 ✅
    
    U->>V: "__import__('os').system('rm -rf /')"
    V->>S: Execute malicious code ⚠️
    S-->>V: System compromised ❌
    
    U->>H: "2+2"
    H->>H: Validate + eval("2+2")
    H-->>U: 4 ✅
    
    U->>H: "__import__('os')"
    H->>H: Validate input
    H-->>U: ValueError: Invalid characters ✅
```

## Running the Script

```bash
# From repository root
python examples/01-vibe-vs-human/example-1.py

# Or from this directory
cd examples/01-vibe-vs-human
python example-1.py
```

## Key Takeaways

**Vibe Coding is great for:**
- Quick prototypes
- Exploratory coding
- Simple, well-understood problems

**Human Coding is essential for:**
- Production code
- Edge case handling
- Performance-critical code
- Security-sensitive operations
- Maintainable, long-term codebases

## Requirements

- Python 3.x
- No external dependencies required (uses only standard library)
