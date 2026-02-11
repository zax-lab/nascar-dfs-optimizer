---
created: 2026-01-26T20:34:50
title: Improve API rate limiting and add authentication
area: backend
files:
  - apps/backend/app/main.py:26-29
  - apps/backend/app/main.py:131-133
---

## Problem

The API has basic rate limiting (10 requests/minute) but no authentication or authorization. The rate limiting uses slowapi but doesn't differentiate between endpoints or users. There's no API key system or user authentication for production use.

## Solution

Add API key authentication using FastAPI security dependencies. Implement per-user rate limiting instead of global limits. Add different rate limits for different endpoints (optimize should be stricter than health checks). Consider adding request logging and abuse detection. Add CORS configuration for frontend access.
