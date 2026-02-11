---
created: 2026-01-26T20:34:50
title: Integrate ontology layer with lineup optimizer
area: backend
files:
  - apps/backend/app/optimizer.py:1-1366
  - apps/backend/app/ontology.py:1-404
  - apps/backend/app/main.py:1-256
---

## Problem

The NASCAROptimizer uses SQLAlchemy models (Driver, Race, Belief) from the epistemic database, but the ontology layer (Neo4j) with metaphysical properties is not integrated. The optimizer should use driver metaphysical properties (skill, psyche_aggression, shadow_risk, realpolitik_pos) from Neo4j to adjust projections, but currently these two systems operate independently.

## Solution

Create an integration layer that fetches metaphysical properties from Neo4j and incorporates them into the optimizer's expected points calculation. Update calculate_expected_points to use get_driver_metaphysical_adjustment from OntologyDriver. Ensure the optimizer can work with both SQLAlchemy (for beliefs) and Neo4j (for metaphysical properties).
