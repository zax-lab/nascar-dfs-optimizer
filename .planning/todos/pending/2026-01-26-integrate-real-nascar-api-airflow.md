---
created: 2026-01-26T20:34:50
title: Integrate real NASCAR API into Airflow ETL pipeline
area: data
files:
  - apps/airflow/dags/nascar_etl_dag.py:44-106
---

## Problem

The Airflow DAG uses mock data instead of connecting to a real NASCAR API. The scrape_nascar_data function has commented-out code for actual API calls, but production code should fetch real driver statistics, race results, and track information.

## Solution

Implement actual NASCAR API integration. Research available NASCAR APIs (official or third-party), add authentication if needed, implement proper error handling and retries. Update the scrape function to fetch real data and handle API rate limits. Add data validation to ensure scraped data matches expected schema.
