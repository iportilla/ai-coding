#!/bin/bash

# Quick Start Script for AI-Assisted Coding Education Examples
# This script runs all examples and shows their output

echo "=================================="
echo "AI-Assisted Coding Education"
echo "Running All Examples"
echo "=================================="
echo ""

# Check for required tools
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Skipping Python examples."; SKIP_PYTHON=1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed. Skipping JavaScript examples."; SKIP_NODE=1; }
command -v go >/dev/null 2>&1 || { echo "Go is required but not installed. Skipping Go examples."; SKIP_GO=1; }

echo ""
echo "=================================="
echo "Example 1: Vibe vs Human Coding"
echo "=================================="
echo ""

if [ -z "$SKIP_PYTHON" ]; then
    python3 examples/01-vibe-vs-human/example-1.py
else
    echo "Skipped (Python not available)"
fi

echo ""
echo "=================================="
echo "Example 2: Prime Algorithms (Python)"
echo "=================================="
echo ""

if [ -z "$SKIP_PYTHON" ]; then
    python3 examples/02-prime-algorithms/example-2.py
else
    echo "Skipped (Python not available)"
fi

echo ""
echo "=================================="
echo "Example 2: Prime Algorithms (JavaScript)"
echo "=================================="
echo ""

if [ -z "$SKIP_NODE" ]; then
    node examples/02-prime-algorithms/example-2.js
else
    echo "Skipped (Node.js not available)"
fi

echo ""
echo "=================================="
echo "Example 2: Prime Algorithms (Go)"
echo "=================================="
echo ""

if [ -z "$SKIP_GO" ]; then
    go run examples/02-prime-algorithms/example-2.go
else
    echo "Skipped (Go not available)"
fi

echo ""
echo "=================================="
echo "All examples completed!"
echo "=================================="
echo ""
echo "To generate visualization:"
echo "  python3 examples/02-prime-algorithms/time_comparison_plot.py"
echo ""
