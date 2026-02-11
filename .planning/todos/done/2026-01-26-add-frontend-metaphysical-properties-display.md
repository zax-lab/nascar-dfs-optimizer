---
created: 2026-01-26T20:34:50
title: Add metaphysical properties display to frontend
area: frontend
files:
  - apps/frontend/src/components/ProjectionTable.tsx:1-85
  - apps/frontend/src/components/OptimizerPanel.tsx:1-115
---

## Problem

The frontend displays basic driver information (name, salary, projected points) but doesn't show metaphysical properties (skill, psyche_aggression, shadow_risk, realpolitik_pos) that influence projections. Users can't see why certain drivers are projected higher or understand the "axiomatic" factors affecting lineups.

## Solution

Add columns or tooltips to ProjectionTable showing metaphysical properties. Create a detailed driver view that displays all metaphysical factors. Add visualizations (progress bars, color coding) to make these abstract properties more understandable. Consider adding filters/sorting by metaphysical properties.
