---
created: 2026-01-26T20:34:50
title: Add tests for projection model inference
area: testing
files:
  - packages/axiomatic-kernel/projection_model.py:1-372
  - packages/axiomatic-kernel/tests/test_projection_model.py
---

## Problem

The projection model has basic structure but lacks comprehensive tests for inference. The test_projection_model.py file exists but may not cover edge cases like invalid inputs, model loading failures, device selection, or batch prediction.

## Solution

Expand test_projection_model.py to include:
- Model loading and initialization tests
- Single prediction tests with various input formats
- Batch prediction tests
- Error handling for invalid inputs
- Device selection (CPU/CUDA/MPS) tests
- Model caching tests
- Integration tests with actual model checkpoints (if available)
