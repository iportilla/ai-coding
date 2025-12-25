# Project Structure & Organization

## Directory Layout

```
.
├── examples/                    # Educational code examples
│   ├── 01-vibe-vs-human/       # Comparing coding approaches
│   │   ├── README.md           # Detailed explanation
│   │   └── example-1.py        # Python implementation
│   └── 02-prime-algorithms/    # Algorithm performance comparison
│       ├── README.md           # Algorithm analysis
│       ├── example-2.py        # Python implementation
│       ├── example-2.js        # JavaScript implementation
│       ├── example-2.go        # Go implementation
│       └── time_comparison_plot.py  # Visualization tool
├── docs/                       # Analysis and presentations
│   ├── README.md              # Documentation index
│   ├── code-quality.md        # Quality analysis
│   ├── ai-coding-why.pdf      # Educational materials
│   └── images/                # Charts and visualizations
├── .kiro/                     # Kiro AI assistant configuration
│   └── steering/              # AI guidance rules
├── README.md                  # Main project documentation
├── CONTRIBUTING.md            # Contribution guidelines
├── LICENSE                    # MIT license
└── run_examples.sh           # Automated example runner
```

## File Naming Conventions

### Examples
- **Pattern**: `example-N.{py,js,go}` where N is the example number
- **README**: Each example directory must have a `README.md` with detailed analysis
- **Consistency**: Same algorithm implemented across multiple languages for comparison

### Documentation
- **README.md**: Required in root and each major directory
- **Markdown**: All documentation in Markdown format
- **Images**: Store visualizations in `docs/images/`

## Code Organization Patterns

### Example Structure
Each example should demonstrate:
1. **Vibe Coding**: Quick, naive implementation
2. **Human Coding**: Optimized, production-ready approach  
3. **Expert Coding**: Algorithmic best practices

### Function Naming
- `vibe_*()`: Naive implementations
- `human_*()`: Optimized implementations
- `expert_*()`: Expert-level algorithms

### Documentation Requirements
- **Docstrings**: All functions must have clear docstrings
- **Big O notation**: Include time complexity comments
- **Educational comments**: Explain the "why" not just the "what"
- **Performance notes**: Document expected performance characteristics

## Adding New Examples

### Directory Structure
```
examples/XX-example-name/
├── README.md              # Problem description and analysis
├── example-X.py          # Python implementation (required)
├── example-X.js          # JavaScript implementation (optional)
├── example-X.go          # Go implementation (optional)
└── visualization.py      # Performance plotting (if applicable)
```

### Content Requirements
- Clear problem statement
- Multiple solution approaches (vibe/human/expert)
- Performance comparison with timing
- Edge case handling demonstration
- Educational takeaways section