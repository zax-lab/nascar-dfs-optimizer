---
created: 2026-01-26T20:34:50
title: Add end-to-end tests for full optimization flow
area: testing
files:
  - tests/integration_test.py
  - tests/E2E_TEST_PLAN.md
---

## Problem

While integration_test.py exists, there may not be comprehensive end-to-end tests that verify the complete flow from data ingestion → ontology storage → projection calculation → optimization → API response. The E2E_TEST_PLAN.md suggests a plan but tests may not be fully implemented.

## Solution

Implement end-to-end tests that:
- Start with mock driver data
- Load data into Neo4j via ontology layer
- Calculate projections using projection model
- Run optimizer with real constraints
- Verify API responses match expected format
- Test error scenarios (missing data, invalid inputs, service failures)
- Use Docker Compose to spin up test environment
