---
created: 2026-01-26T20:34:50
title: Add integration tests for Neo4j ontology layer
area: testing
files:
  - apps/backend/app/ontology.py:1-404
  - apps/backend/tests/
---

## Problem

There are no integration tests for the ontology layer. The OntologyDriver, DriverNode, TrackNode, and RaceNode classes need tests that verify they can actually connect to Neo4j, create nodes, retrieve nodes, and handle errors properly. Current tests only cover kernel and optimizer logic.

## Solution

Create test_ontology.py with integration tests that:
- Test Neo4j connection establishment and failure handling
- Test DriverNode/TrackNode/RaceNode creation and retrieval
- Test get_driver_metaphysical_adjustment calculations
- Test connection pooling and singleton pattern
- Use a test Neo4j instance or mock Neo4j driver for CI/CD
