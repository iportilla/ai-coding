# Technology Stack & Build System

## Languages & Runtimes
- **Python 3.x**: Primary language for examples and analysis
- **JavaScript (Node.js)**: Cross-platform algorithm demonstrations
- **Go 1.x**: Performance-focused implementations
- **Bash**: Automation and example runner scripts

## Development Tools
- **Git**: Version control
- **VS Code**: Recommended editor (`.vscode` configuration included)

## Dependencies
- **Python**: Standard library only (no external dependencies)
- **Node.js**: Standard library only (no npm packages required)
- **Go**: Standard library only (no external modules)

## Common Commands

### Running Examples
```bash
# Run all examples with dependency checking
./run_examples.sh

# Individual examples
python3 examples/01-vibe-vs-human/example-1.py
python3 examples/02-prime-algorithms/example-2.py
node examples/02-prime-algorithms/example-2.js
go run examples/02-prime-algorithms/example-2.go

# Generate performance visualization
python3 examples/02-prime-algorithms/time_comparison_plot.py
```

### Prerequisites Check
The run script automatically checks for:
- `python3` command availability
- `node` command availability  
- `go` command availability

### Performance Testing
- Use `time.perf_counter()` in Python for microsecond precision
- Use `performance.now()` in JavaScript for high-resolution timing
- Use `time.Now()` and `time.Since()` in Go for nanosecond precision

## Code Standards
- **No external dependencies**: Keep examples self-contained
- **Cross-platform compatibility**: All code should run on Windows, macOS, Linux
- **Educational clarity**: Prioritize readability over micro-optimizations
- **Consistent timing methodology**: Use language-appropriate high-precision timers