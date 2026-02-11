---
created: 2026-01-26T20:34:50
title: Add retry logic and dependency management to Docker Compose
area: devops
files:
  - docker-compose.yml:1-168
---

## Problem

Docker Compose health checks exist but services don't retry connections if dependencies aren't ready. The backend depends on Neo4j being healthy, but if Neo4j takes longer than expected to start, the backend may fail to connect and not retry. There's no restart policy or circuit breaker pattern.

## Solution

Add restart policies (unless-stopped) to services. Implement application-level retry logic with exponential backoff for Neo4j connections. Consider using docker-compose wait conditions or init containers to ensure dependencies are truly ready. Add connection retry logic in the application code (already partially addressed in ontology todo).
