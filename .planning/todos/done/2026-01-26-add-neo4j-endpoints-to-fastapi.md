---
created: 2026-01-26T20:34:50
title: Add Neo4j ontology endpoints to FastAPI
area: backend
files:
  - apps/backend/app/main.py:1-256
  - apps/backend/app/ontology.py:1-404
---

## Problem

The FastAPI application has no endpoints for accessing or managing Neo4j ontology data (drivers, tracks, races with metaphysical properties). Users cannot query driver metaphysical properties, update track difficulty, or retrieve race chaos factors through the API.

## Solution

Add REST endpoints for:
- GET /drivers/{driver_id} - Get driver with metaphysical properties
- GET /tracks/{track_id} - Get track with metaphysical properties  
- GET /races/{race_id} - Get race with chaos factor
- POST /drivers - Create/update driver node
- POST /tracks - Create/update track node
- POST /races - Create/update race node
- GET /drivers/{driver_id}/metaphysical - Get metaphysical adjustment factors
