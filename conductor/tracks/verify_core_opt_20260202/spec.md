# Specification: Verify Core Optimization Engine & Ontology Integration

## Goal
To verify that the JAX/NumPyro optimization engine correctly interfaces with the Neo4j ontology, respecting all "metaphysical" driver properties (skill, aggression, shadow_risk) and axiomatic constraints during lineup generation.

## Scope
- **Integration Tests:** Verify the data flow from Neo4j -> Backend -> Optimization Engine.
- **Constraint Validation:** Ensure that hard axiomatic constraints (e.g., salary cap, uniqueness) are never violated.
- **Metaphysical Influence:** Confirm that changes in Neo4j properties (e.g., increasing a driver's aggression) produce statistically significant changes in the optimizer's output.
- **Documentation:** Document the current state of these integrations for future reference.

## Success Criteria
- [ ] Integration test suite passes with >80% code coverage on relevant modules.
- [ ] MCMC sampling converges within acceptable timeframes (<10s for verification runs).
- [ ] "Impossible states" are correctly identified and rejected by the Kernel.
- [ ] A verification report is generated summarizing the findings.
