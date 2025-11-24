#!/bin/bash
# ClusterFuzzLite build script
# This script builds fuzz targets for CI fuzzing

# Exit on error
set -e

# Build Python fuzz targets using Atheris
pip install atheris

# Compile the fuzz target
compile_python_fuzzer fuzz/fuzz_input_validation.py
