---
created: 2026-01-26T20:34:50
title: Implement complete TinyLlama training pipeline with data integration
area: ml
files:
  - packages/axiomatic-kernel/tinyllama_finetune.py:1-402
  - packages/axiomatic-kernel/nascar_dataset.py:1-358
  - apps/airflow/dags/nascar_etl_dag.py:1-381
---

## Problem

The TinyLlama fine-tuning code exists but there's no complete pipeline that connects data ingestion → dataset creation → model training → model deployment. The training code is isolated and doesn't integrate with the Airflow ETL pipeline or the projection model inference.

## Solution

Create an end-to-end training pipeline that:
- Extracts training data from Neo4j/epistemic database
- Formats data into NASCARDataset JSONL format
- Runs TinyLlama fine-tuning with proper hyperparameters
- Validates model performance
- Deploys trained model for inference
- Optionally integrates as an Airflow DAG for scheduled retraining
