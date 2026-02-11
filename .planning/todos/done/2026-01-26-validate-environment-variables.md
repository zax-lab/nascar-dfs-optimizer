---
created: 2026-01-26T20:34:50
title: Add environment variable validation on startup
area: devops
files:
  - apps/backend/app/main.py:1-256
  - apps/backend/app/ontology.py:183-229
  - .env.example:1-16
---

## Problem

The application doesn't validate required environment variables on startup. If NEO4J_PASSWORD or other critical variables are missing or invalid, the application may start but fail silently when trying to use those services. The .env.example shows what's needed but there's no runtime validation.

## Solution

Add startup validation that checks all required environment variables are set and valid (e.g., NEO4J_URI is a valid URL, passwords meet security requirements, API URLs are reachable). Fail fast with clear error messages if validation fails. Consider using pydantic-settings for type-safe configuration management.
