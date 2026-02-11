# Plan: Verify Core Optimization Engine & Ontology Integration

## Phase 1: Environment & Dependency Check [checkpoint: ca30958]
- [x] Task: Verify Neo4j connectivity and schema integrity. 500cb5d
    - [ ] Sub-task: Check Neo4j container status and logs.
    - [ ] Sub-task: Run a query to verify the existence of Driver, Track, and Race nodes.
- [x] Task: Verify JAX/NumPyro installation and hardware acceleration. 8b0b0df
    - [ ] Sub-task: Run a simple JAX matrix multiplication to confirm backend (CPU/MPS).
    - [ ] Sub-task: Verify NumPyro installation and basic sampling capability.

## Phase 2: Core Integration Verification [checkpoint: b05f7cf]
- [x] Task: Verify Ontology Data Ingestion. 31d5ce9
    - [ ] Sub-task: Write a test to fetch metaphysical properties for a specific driver from Neo4j.
    - [ ] Sub-task: Verify that properties (skill, aggression) are correctly typed and bounded (0-1).
- [x] Task: Verify Kernel Logic Constraints. 2576389
    - [ ] Sub-task: Create a test case with an invalid lineup (e.g., salary > cap).
    - [ ] Sub-task: Assert that the Kernel logic correctly rejects this state.
- [ ] Task: Conductor - User Manual Verification 'Core Integration Verification' (Protocol in workflow.md)

## Phase 3: Optimization Engine Stress Test
- [x] Task: Run a deterministic optimization loop. c8bb7b1
    - [ ] Sub-task: Configure a small, fixed race scenario.
    - [ ] Sub-task: Run the optimizer for a limited number of iterations.
    - [ ] Sub-task: specific output consistency check.
- [x] Task: Verify Metaphysical Impact. be6fea1
    - [ ] Sub-task: Run a baseline optimization.
    - [ ] Sub-task: Drastically alter one driver's "skill" in the input data (mocked).
    - [ ] Sub-task: Rerun optimization and assert that the driver's exposure changes significantly.
- [ ] Task: Conductor - User Manual Verification 'Optimization Engine Stress Test' (Protocol in workflow.md)

## Phase 4: Documentation & Reporting
- [ ] Task: Generate Verification Report.
    - [ ] Sub-task: Compile test results and coverage metrics.
    - [ ] Sub-task: Document any discovered bottlenecks or logic gaps.
- [ ] Task: Update ARCHITECTURE.md if discrepancies are found.
    - [ ] Sub-task: Review current architecture docs against findings.
    - [ ] Sub-task: Submit PR for documentation updates.
- [ ] Task: Conductor - User Manual Verification 'Documentation & Reporting' (Protocol in workflow.md)
