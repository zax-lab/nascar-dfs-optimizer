"""
Causal Bayesian Network with ontology-constrained structure learning.

This module provides a Causal Bayesian Network (CBN) implementation using pgmpy,
constrained by ontology veto rules and priors. The CBN models the causal
relationships between driver skill, track characteristics, and race outcomes.

Key features:
- Structure learning with ontology veto rules
- Hybrid parameterization (ontology priors + data-driven learning)
- Exact inference with VariableElimination
- Conditional outcome sampling
"""
import logging
from typing import Dict, List, Optional, Any
import pandas as pd
import networkx as nx
import numpy as np

# pgmpy imports
from pgmpy.models import BayesianNetwork
from pgmpy.estimators import PC, BayesianEstimator
from pgmpy.inference import VariableElimination

# Local imports
from axiomatic_sim.ontology_constraints import (
    OntologyConstraints,
    apply_veto_rules,
    get_driver_priors,
)

logger = logging.getLogger(__name__)


class CausalBayesianNetwork:
    """
    Causal Bayesian Network wrapper around pgmpy with ontology constraints.

    This class provides:
    1. Structure learning with ontology veto rules
    2. Hybrid parameterization (ontology priors + data-driven CPDs)
    3. Exact inference using VariableElimination
    4. Conditional outcome sampling

    Example:
        >>> from axiomatic_sim.ontology_constraints import OntologyConstraints
        >>> ontology = OntologyConstraints()
        >>> structure = learn_structure(data, ontology)
        >>> cbn = CausalBayesianNetwork(structure, ontology)
        >>> cbn.learn_parameters(data, priors=get_driver_priors(ontology, drivers))
        >>> outcomes = cbn.sample_outcomes(n_samples=100)
    """

    def __init__(
        self,
        structure: nx.DiGraph,
        ontology_constraints: OntologyConstraints
    ):
        """
        Initialize CBN with constrained structure.

        Args:
            structure: CBN structure as NetworkX DiGraph (should be acyclic)
            ontology_constraints: OntologyConstraints instance for priors/veto rules

        Raises:
            ValueError: If structure contains cycles
        """
        self.ontology_constraints = ontology_constraints

        # Validate structure is acyclic
        if not nx.is_directed_acyclic_graph(structure):
            raise ValueError("CBN structure must be a directed acyclic graph (DAG)")

        # Initialize pgmpy BayesianNetwork
        self.model = BayesianNetwork(structure.edges())
        self.structure = structure

        logger.info(f"Initialized CBN with {len(structure.nodes)} nodes, {len(structure.edges)} edges")

    def learn_parameters(
        self,
        data: pd.DataFrame,
        priors: Optional[Dict[str, float]] = None
    ) -> 'CausalBayesianNetwork':
        """
        Learn CBN parameters from data using Bayesian estimation.

        Uses pgmpy's BayesianEstimator which supports prior specification
        as pseudo-counts. If priors are provided (from ontology), they are
        incorporated into the parameter learning.

        Args:
            data: Historical race data with columns matching CBN variables
            priors: Optional dictionary of variable priors from ontology
                   (e.g., {"driver_123_skill": 0.7, "driver_456_skill": 0.6})

        Returns:
            self for method chaining

        Raises:
            ValueError: If data columns don't match CBN structure variables
        """
        # Validate data columns match CBN variables
        model_vars = set(self.structure.nodes())
        data_cols = set(data.columns)

        if not model_vars.issubset(data_cols):
            missing = model_vars - data_cols
            raise ValueError(f"Data missing columns for CBN variables: {missing}")

        # Use BayesianEstimator for parameter learning
        estimator = BayesianEstimator(self.model, data)

        # Learn CPDs for each node
        # If priors provided, use them as pseudo_counts
        prior_counts = {}
        if priors:
            # Convert priors to pseudo-counts format for pgmpy
            # This is a simplified approach - real implementation would
            # need proper Dirichlet prior specification
            for var, prior_val in priors.items():
                if var in self.structure.nodes():
                    # Use prior to weight the likelihood (simplified)
                    prior_counts[var] = prior_val

        # Fit CPDs using Maximum Likelihood Estimation (with priors if provided)
        try:
            # For now, use simple MLE - TODO: implement proper Bayesian estimation with priors
            self.model.fit(
                data,
                estimator=BayesianEstimator,
                prior_type="dirichlet",
                pseudo_counts=[1] * len(data.columns) if not priors else priors
            )
            logger.info(f"Learned CPDs for {len(self.model.get_cpds())} variables")
        except Exception as e:
            logger.error(f"Failed to learn parameters: {e}")
            # Fall back to MLE if Bayesian estimation fails
            logger.warning("Falling back to Maximum Likelihood Estimation")
            self.model.fit(data)

        # Validate CPDs
        if not self.model.check_model():
            raise ValueError("Learned CBN parameters are invalid")

        return self

    def sample_outcomes(
        self,
        n_samples: int,
        evidence: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Sample outcomes from the CBN using exact inference.

        Uses VariableElimination for exact probabilistic inference.
        If evidence is provided (e.g., {"caution": True}), samples are
        conditioned on that evidence.

        Args:
            n_samples: Number of samples to generate
            evidence: Optional dictionary of observed variables

        Returns:
            DataFrame with sampled outcomes, columns depend on CBN variables
            Expected columns include: driver_id, laps_led, fastest_laps,
                                     finish_position, incidents

        Raises:
            ValueError: If parameters not learned or evidence invalid
        """
        if len(self.model.get_cpds()) == 0:
            raise ValueError("CBN parameters not learned. Call learn_parameters() first.")

        # Validate evidence variables exist in CBN
        if evidence:
            evidence_vars = set(evidence.keys())
            model_vars = set(self.structure.nodes())
            if not evidence_vars.issubset(model_vars):
                invalid = evidence_vars - model_vars
                raise ValueError(f"Evidence variables not in CBN: {invalid}")

        # Use VariableElimination for exact inference
        infer = VariableElimination(self.model)

        logger.info(
            f"Sampling {n_samples} outcomes from CBN with "
            f"{len(self.structure.nodes())} variables"
        )
        if evidence:
            logger.info(f"Evidence conditioning: {evidence}")

        # Get topological order for sampling (parents before children)
        variables_sorted = list(nx.topological_sort(self.structure))

        samples = []
        rejected = 0

        for sample_idx in range(n_samples):
            sample = {}

            # Forward sampling: sample variables in topological order
            for var in variables_sorted:
                # If variable is in evidence, use evidence value
                if evidence and var in evidence:
                    sample[var] = evidence[var]
                    continue

                # Get CPD for this variable
                try:
                    cpd = self.model.get_cpds(var)
                except Exception as e:
                    logger.warning(f"No CPD found for {var}, using default value")
                    # Use default based on variable type
                    if "skill" in var or "aggression" in var or "shadow_risk" in var or "_risk" in var:
                        sample[var] = 0.5
                    elif "laps_led" in var or "fastest_laps" in var:
                        sample[var] = 0
                    elif "finish_position" in var:
                        sample[var] = 20
                    elif "incident" in var or "caution" in var:
                        sample[var] = False
                    else:
                        sample[var] = 0
                    continue

                # Build evidence for this variable's parents
                parent_evidence = {}
                if hasattr(cpd, 'variables') and cpd.variables:
                    # Get parent variable names (all variables except the node itself)
                    parents = [v for v in cpd.variables if v != var]
                    for parent in parents:
                        if parent in sample:
                            parent_evidence[parent] = sample[parent]

                # Sample from conditional distribution
                if parent_evidence:
                    # Use VariableElimination to query P(var | parent_evidence)
                    try:
                        result = infer.query(
                            variables=[var],
                            evidence=parent_evidence,
                            show_progress=False
                        )
                        # Sample from the resulting distribution
                        sample[var] = _sample_from_distribution(result, var)
                    except Exception as e:
                        logger.debug(f"Inference failed for {var}, using prior: {e}")
                        sample[var] = _sample_from_cpd(cpd, var, parent_evidence)
                else:
                    # No parents, sample from prior CPD
                    sample[var] = _sample_from_cpd(cpd, var, {})

            samples.append(sample)

        df = pd.DataFrame(samples)

        # Log sampling statistics
        for var in variables_sorted:
            if var in df.columns:
                if df[var].dtype in [float, int]:
                    logger.debug(
                        f"{var}: mean={df[var].mean():.3f}, std={df[var].std():.3f}"
                    )

        logger.info(f"Generated {len(df)} samples from CBN")
        return df

    def get_conditional_probability(
        self,
        target: str,
        evidence: Dict[str, Any]
    ) -> float:
        """
        Query P(target | evidence) using exact inference.

        Args:
            target: Target variable to query
            evidence: Dictionary of observed variables

        Returns:
            Probability value P(target | evidence)

        Raises:
            ValueError: If variables not in CBN or parameters not learned
        """
        if len(self.model.get_cpds()) == 0:
            raise ValueError("CBN parameters not learned. Call learn_parameters() first.")

        # Validate variables exist in CBN
        if target not in self.structure.nodes():
            raise ValueError(f"Target variable {target} not in CBN")

        evidence_vars = set(evidence.keys())
        model_vars = set(self.structure.nodes())
        if not evidence_vars.issubset(model_vars):
            invalid = evidence_vars - model_vars
            raise ValueError(f"Evidence variables not in CBN: {invalid}")

        # Use VariableElimination for exact inference
        infer = VariableElimination(self.model)

        # Query P(target | evidence)
        result = infer.query(
            variables=[target],
            evidence=evidence,
            show_progress=False
        )

        # Return the probability (for binary variables, return P(True))
        # TODO: Handle multi-valued variables properly
        logger.debug(f"P({target} | {evidence}) = {result.values}")

        # For now, return the first value (simplified)
        # Real implementation would handle multi-valued variables
        return float(result.values[0]) if len(result.values) > 0 else 0.0


def _sample_from_distribution(inference_result, var: str) -> Any:
    """
    Sample from a pgmpy inference result distribution.

    Args:
        inference_result: Result from VariableElimination.query()
        var: Variable name being sampled

    Returns:
        Sampled value
    """
    values = inference_result.values
    state_names = inference_result.state_names.get(var, list(range(len(values))))

    # Sample from the probability distribution
    idx = np.random.choice(len(values), p=values)
    return state_names[idx]


def _sample_from_cpd(cpd, var: str, parent_evidence: Dict[str, Any]) -> Any:
    """
    Sample from a CPD given parent evidence.

    Args:
        cpd: pgmpy TabularCPD for the variable
        var: Variable name
        parent_evidence: Dictionary of parent variable values

    Returns:
        Sampled value
    """
    # Get the variable's cardinality (number of states)
    if hasattr(cpd, 'state_names') and var in cpd.state_names:
        states = cpd.state_names[var]
    else:
        # Default: assume integer states 0 to cardinality-1
        cardinality = cpd.variable_card if hasattr(cpd, 'variable_card') else 2
        states = list(range(cardinal))

    # For discrete variables, get conditional probability
    if parent_evidence and hasattr(cpd, 'reduce'):
        # Reduce CPD to the parent evidence state
        try:
            reduced_cpd = cpd.reduce(parent_evidence, inplace=False)
            probs = reduced_cpd.values
            # Ensure probs is 1D
            if len(probs.shape) > 1:
                probs = probs.flatten()
        except Exception:
            # Fallback: use uniform distribution
            probs = np.ones(len(states)) / len(states)
    else:
        # No parent evidence, use the CPD's marginal
        if hasattr(cpd, 'values'):
            probs = cpd.values
            if len(probs.shape) > 1:
                # Use the first row (marginal when no evidence)
                probs = probs.flatten()
        else:
            probs = np.ones(len(states)) / len(states)

    # Normalize probabilities to sum to 1
    probs = probs / np.sum(probs)

    # Sample from the distribution
    idx = np.random.choice(len(states), p=probs)
    return states[idx]


def learn_structure(
    data: pd.DataFrame,
    ontology_constraints: OntologyConstraints
) -> nx.DiGraph:
    """
    Learn CBN structure from data using constraint-based PC algorithm.

    Uses pgmpy's PC estimator for structure learning, then applies
    ontology veto rules to remove forbidden edges.

    Args:
        data: Historical race data with columns for CBN variables
        ontology_constraints: OntologyConstraints instance for veto rules

    Returns:
        Constrained CBN structure as NetworkX DiGraph

    Raises:
        ValueError: If data is insufficient for structure learning

    Example:
        >>> data = pd.DataFrame({
        ...     "driver_123_skill": [0.7, 0.8, 0.6],
        ...     "driver_123_laps_led": [10, 15, 5],
        ...     "track_difficulty": [0.5, 0.6, 0.4]
        ... })
        >>> ontology = OntologyConstraints()
        >>> structure = learn_structure(data, ontology)
        >>> assert nx.is_directed_acyclic_graph(structure)
    """
    # Validate data has enough samples
    if len(data) < 10:
        raise ValueError(f"Need at least 10 samples for structure learning, got {len(data)}")

    # Use PC algorithm for constraint-based structure learning
    logger.info(f"Learning structure from {len(data)} samples with {len(data.columns)} variables")

    try:
        estimator = PC(data=data)
        # Learn DAG using PC algorithm
        # significance level=0.05 for conditional independence tests
        dag = estimator.estimate(
            ci_test="chi_square",
            return_type="dag",
            significance_level=0.05
        )

        logger.info(f"Learned DAG with {len(dag.nodes)} nodes, {len(dag.edges)} edges")

    except Exception as e:
        logger.error(f"PC algorithm failed: {e}")
        # Fall back to empty graph (no edges) if structure learning fails
        # User can then manually specify structure or use domain knowledge
        logger.warning("Falling back to empty graph (no causal edges)")
        dag = nx.DiGraph()
        dag.add_nodes_from(data.columns)

    # Apply ontology veto rules to constrain structure
    veto_rules = ontology_constraints.get_veto_rules()
    constrained_structure = apply_veto_rules(dag, veto_rules)

    logger.info(
        f"Final constrained structure: {len(constrained_structure.nodes)} nodes, "
        f"{len(constrained_structure.edges)} edges"
    )

    return constrained_structure


def create_cbn_variables(driver_ids: List[str]) -> List[str]:
    """
    Create CBN variable names for each driver.

    Generates standardized variable names for CBN nodes based on driver IDs.
    Each driver gets variables for skill (latent), incident probability,
    laps led, fastest laps, and finish position.

    Args:
        driver_ids: List of driver identifiers

    Returns:
        List of CBN variable names

    Example:
        >>> driver_ids = ["driver_123", "driver_456"]
        >>> vars = create_cbn_variables(driver_ids)
        >>> "driver_123_skill" in vars
        True
        >>> "driver_456_finish_position" in vars
        True
    """
    variables = []

    for driver_id in driver_ids:
        # Latent skill variable (from ontology)
        variables.append(f"{driver_id}_skill")

        # Incident probability
        variables.append(f"{driver_id}_incident_prob")

        # Dominator outcomes
        variables.append(f"{driver_id}_laps_led")
        variables.append(f"{driver_id}_fastest_laps")

        # Finishing outcomes
        variables.append(f"{driver_id}_finish_position")

    logger.info(f"Created {len(variables)} CBN variables for {len(driver_ids)} drivers")
    return variables


def get_ontology_priors(
    ontology_constraints: OntologyConstraints,
    driver_ids: List[str]
) -> Dict[str, float]:
    """
    Fetch ontology priors for CBN parameter learning.

    Convenience wrapper around get_driver_priors that formats
    priors for use with BayesianEstimator.

    Args:
        ontology_constraints: OntologyConstraints instance
        driver_ids: List of driver identifiers

    Returns:
        Dictionary mapping CBN variable names to prior values
        Format: {"{driver_id}_skill": skill_value, ...}

    Example:
        >>> ontology = OntologyConstraints()
        >>> priors = get_ontology_priors(ontology, ["driver_123"])
        >>> assert "driver_123_skill" in priors
        >>> assert 0.0 <= priors["driver_123_skill"] <= 1.0
    """
    return get_driver_priors(ontology_constraints, driver_ids)


def apply_ontology_constraints(
    structure: nx.DiGraph,
    ontology_constraints: OntologyConstraints
) -> nx.DiGraph:
    """
    Apply ontology veto rules to CBN structure.

    Convenience function for applying veto rules to a learned structure.

    Args:
        structure: Learned CBN structure
        ontology_constraints: OntologyConstraints instance

    Returns:
        Constrained structure with vetoed edges removed
    """
    veto_rules = ontology_constraints.get_veto_rules()
    return apply_veto_rules(structure, veto_rules)


def sample_conditional_outcomes(
    cbn: CausalBayesianNetwork,
    driver_id: str,
    evidence: Dict[str, Any],
    n_samples: int = 100
) -> pd.DataFrame:
    """
    Sample conditional outcomes for a specific driver given evidence.

    Convenience function for querying driver outcomes under specific
    race conditions (e.g., caution=True, track_difficulty=0.7).

    Args:
        cbn: Trained CausalBayesianNetwork instance
        driver_id: Driver to sample outcomes for
        evidence: Race conditions to condition on
        n_samples: Number of samples to generate

    Returns:
        DataFrame with sampled outcomes for the specified driver

    Example:
        >>> cbn = CausalBayesianNetwork(structure, ontology)
        >>> cbn.learn_parameters(data)
        >>> outcomes = sample_conditional_outcomes(
        ...     cbn,
        ...     driver_id="driver_123",
        ...     evidence={"caution": True},
        ...     n_samples=100
        ... )
        >>> assert "driver_123_laps_led" in outcomes.columns
    """
    # Filter samples to only include the specified driver's variables
    full_samples = cbn.sample_outcomes(n_samples, evidence)

    # Get columns for this driver
    driver_cols = [col for col in full_samples.columns if col.startswith(f"{driver_id}_")]

    if not driver_cols:
        logger.warning(f"No variables found for driver {driver_id} in samples")
        return pd.DataFrame()

    return full_samples[driver_cols]
