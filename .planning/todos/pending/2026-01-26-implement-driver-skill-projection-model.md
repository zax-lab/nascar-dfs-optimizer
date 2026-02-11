---
created: 2026-01-26T20:34:50
title: Implement driver skill projection model
area: ml
files:
  - packages/axiomatic-kernel/projection_model.py:1-372
  - packages/axiomatic-kernel/nascar_dataset.py:1-358
---

## Problem

The ProjectionModel exists but doesn't integrate driver skill projections from the ontology layer. The model should use metaphysical properties (skill, psyche_aggression, shadow_risk, realpolitik_pos) from Neo4j to enhance projections, but currently these properties are not being passed to the model's predict method. The ontology phase features should include driver skill metrics.

## Solution

Integrate ontology metaphysical properties into the projection model's ontology_phase input. Create a service layer that fetches driver metaphysical properties from Neo4j and includes them in the projection calculation. Update the projection model to weight these metaphysical factors appropriately in the prediction.
