#!/bin/bash

# Wrapper script for transcribe.py that handles RTX 5090 CUDA compatibility
# Checks GPU compatibility first, then runs with appropriate settings

# Check GPU compatibility
if python check_gpu.py 2>/dev/null; then
    echo "GPU is compatible, running with GPU acceleration..."
    python transcribe.py "$@"
else
    echo "GPU incompatible or not available, running on CPU..."
    CUDA_VISIBLE_DEVICES="" python transcribe.py "$@"
fi
