"""SWE-CLI - AI-powered command-line tool for accelerated development workflows."""

import warnings

# Suppress transformers warning about missing ML frameworks
# SWE-CLI uses LLM APIs directly and doesn't need local models
warnings.filterwarnings("ignore", message=".*None of PyTorch, TensorFlow.*found.*")

__version__ = "0.1.0"
