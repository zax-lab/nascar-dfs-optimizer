---
created: 2026-01-26T20:34:50
title: Align Airflow metaphysical fields with ontology schema
area: data
files:
  - apps/airflow/dags/nascar_etl_dag.py:143-243
  - apps/backend/app/ontology.py:35-169
---

## Problem

The Airflow DAG calculates metaphysical fields (agility, fortune, momentum, resonance, entropy) but the ontology layer expects different properties (skill, psyche_aggression, shadow_risk, realpolitik_pos, difficulty, aggression_factor, chaos_factor). The field names and calculations don't match between the ETL pipeline and the ontology schema.

## Solution

Update the Airflow transform function to calculate the correct metaphysical properties that match the ontology schema. Map the calculated values to DriverNode, TrackNode, and RaceNode properties. Ensure the load_neo4j function uses the correct property names when creating nodes.
