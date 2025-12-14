# AI-Assisted Coding Education

> Educational examples demonstrating the differences between quick prototyping ("vibe coding"), thoughtful optimization ("human coding"), and expert-level algorithmic solutions.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📚 Overview

This repository contains educational materials and code examples that illustrate important concepts in software development, particularly focusing on:

- The trade-offs between rapid prototyping and production-ready code
- Algorithm selection and performance optimization
- Edge case handling and defensive programming
- Security considerations in code implementation

## 🗂️ Repository Structure

```
.
├── examples/
│   ├── 01-vibe-vs-human/          # Comparing quick vs thoughtful coding
│   │   ├── example-1.py
│   │   └── README.md
│   └── 02-prime-algorithms/       # Algorithm comparison across languages
│       ├── example-2.py
│       ├── example-2.js
│       ├── example-2.go
│       ├── time_comparison_plot.py
│       └── README.md
├── docs/                          # Analysis documents and presentations
│   ├── code-quality.md
│   └── images/
└── README.md
```

## 🎯 Key Examples

### Example 1: Vibe Coding vs Human Coding
Demonstrates 5 common pitfalls when prioritizing speed over careful implementation:
- Order preservation bugs
- Edge case handling failures
- Performance inefficiencies (O(n²) vs O(n))
- Algorithmic improvements (trial division vs Sieve of Eratosthenes)
- Security vulnerabilities (unsafe `eval()` usage)

**[📖 Read more →](examples/01-vibe-vs-human/README.md)**

### Example 2: Prime Number Algorithms
Compares three approaches to finding prime numbers across Python, JavaScript, and Go:
- **Vibe Coding**: Naive approach - O(n²)
- **Human Coding**: Optimized approach - O(n√n)  
- **Expert Coding**: Sieve of Eratosthenes - O(n log log n)

Includes performance benchmarks and visualization tools.

**[📖 Read more →](examples/02-prime-algorithms/README.md)**

## 🚀 Quick Start

### Prerequisites
- Python 3.x
- Node.js (for JavaScript examples)
- Go 1.x (for Go examples)

### Running Examples

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-coding-education.git
cd ai-coding-education

# Run Example 1 (Python)
python examples/01-vibe-vs-human/example-1.py

# Run Example 2 (multiple languages)
python examples/02-prime-algorithms/example-2.py
node examples/02-prime-algorithms/example-2.js
go run examples/02-prime-algorithms/example-2.go

# Generate performance visualization
python examples/02-prime-algorithms/time_comparison_plot.py
```

## 📊 Key Takeaways

### When to Use Different Approaches

| Approach | Best For | Avoid When |
|----------|----------|------------|
| **Vibe Coding** | Prototypes, exploration, tiny inputs | Production code, large datasets, security-critical |
| **Human Coding** | Production code, moderate inputs, maintainability | Maximum performance needed |
| **Expert Coding** | Performance-critical, large datasets, well-solved problems | Over-optimization of simple problems |

### Performance Matters

Real-world example from the repository:
- Finding primes up to 10,000:
  - Vibe Coding: ~2-5 seconds
  - Human Coding: ~0.5-1 second
  - Expert Coding: ~0.05-0.1 seconds

**That's up to 100x faster!**

## 🎓 Educational Context

These examples are designed for:
- Computer science students learning algorithm analysis
- Developers transitioning from prototyping to production code
- Teams discussing code quality and performance trade-offs
- Understanding Big O notation in practical terms

## 📖 Documentation

- **[Code Quality Analysis](docs/code-quality.md)** - Detailed analysis of coding approaches
- **[Example 1 Details](examples/01-vibe-vs-human/README.md)** - Deep dive into common pitfalls
- **[Example 2 Details](examples/02-prime-algorithms/README.md)** - Algorithm comparison guide

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Add examples in other programming languages
- Improve documentation
- Add more algorithm comparisons
- Fix bugs or improve existing code

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Resources

- [Big O Cheat Sheet](https://www.bigocheatsheet.com/)
- [Sieve of Eratosthenes](https://en.wikipedia.org/wiki/Sieve_of_Eratosthenes)
- [Python Time Complexity](https://wiki.python.org/moin/TimeComplexity)
- [Clean Code Principles](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)

---

**Created for educational purposes** to demonstrate the importance of thoughtful software development and algorithmic thinking.
