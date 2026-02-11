---
created: 2026-01-26T20:34:50
title: Connect frontend to real backend API instead of mock data
area: frontend
files:
  - apps/frontend/src/app/page.tsx
  - apps/frontend/src/components/OptimizerPanel.tsx
  - apps/frontend/src/components/ProjectionTable.tsx
---

## Problem

The frontend currently uses mock data and doesn't make actual API calls to the FastAPI backend. The OptimizerPanel and ProjectionTable components need to fetch real driver data and submit optimization requests to the /optimize endpoint.

## Solution

Create API client utilities to call the FastAPI backend. Replace mock data with fetch calls to /optimize and /health endpoints. Add proper error handling, loading states, and retry logic. Ensure the frontend handles API errors gracefully and displays appropriate user feedback.
