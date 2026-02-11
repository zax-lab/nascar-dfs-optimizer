---
created: 2026-01-26T20:34:50
title: Update FastAPI to use NASCAROptimizer instead of legacy LineupOptimizer
area: backend
files:
  - apps/backend/app/main.py:15-256
  - apps/backend/app/optimizer.py:1096-1310
---

## Problem

The FastAPI main.py endpoint uses the legacy LineupOptimizer class instead of the newer NASCAROptimizer which supports belief systems, epistemic variance, and team stacking. The legacy optimizer doesn't integrate with the epistemic database or support advanced features like risk-adjusted optimization.

## Solution

Refactor the /optimize endpoint to use NASCAROptimizer. Update the request/response models to support the new optimizer's features (beliefs, epistemic variance, team stacking). Ensure backward compatibility or create a migration path for existing clients.
