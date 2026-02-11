---
created: 2026-01-26T20:34:50
title: Fix Neo4j connection timeout in ontology layer
area: ontology
files:
  - apps/backend/app/ontology.py:203-229
---

## Problem

The OntologyDriver class initializes Neo4j connections but lacks proper timeout handling, retry logic, and connection health checks. The current implementation has connection_timeout=30 seconds but no retry mechanism if the connection fails. In production, Neo4j may be temporarily unavailable, and the system should gracefully handle connection failures with exponential backoff retries.

## Solution

Add connection retry logic with exponential backoff, implement connection health checks, and add proper error handling for connection failures. Consider implementing a connection pool monitor that can detect stale connections and recreate them automatically.
