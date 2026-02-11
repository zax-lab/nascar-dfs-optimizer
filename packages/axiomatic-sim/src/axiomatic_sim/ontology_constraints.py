"""
Ontology constraint extraction and veto rule enforcement for CBN.

This module provides the interface between the ontology layer (Neo4j) and
the Causal Bayesian Network, extracting driver priors and applying veto rules
to prevent impossible causal relationships.

Key concepts:
- Veto rules: Hard constraints that forbid certain CBN edges (e.g., DNF -> laps_led)
- Driver priors: Ontology-derived skill, aggression, and shadow_risk values
- Track difficulty: Ontology-derived track difficulty for CBN conditioning
"""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import networkx as nx

# Try to import OntologyDriver from backend app
# Use try/except for standalone usage without full backend
try:
    import sys
    from pathlib import Path

    # Add apps/backend to path if available
    backend_path = Path(__file__).parent.parent.parent.parent.parent / "apps" / "backend"
    if backend_path.exists():
        sys.path.insert(0, str(backend_path))
        from app.ontology import OntologyDriver, DriverNode, TrackNode
    else:
        raise ImportError("Backend not found")
except ImportError:
    # Create mock classes for standalone usage
    logging.warning("Could not import OntologyDriver from backend. Using mock classes.")
    OntologyDriver = None  # type: ignore
    DriverNode = None  # type: ignore
    TrackNode = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VetoRule:
    """
    Represents a forbidden causal relationship in the CBN.

    Veto rules enforce physical impossibility constraints from the ontology.
    For example, a DNF driver cannot lead laps after their incident.

    Attributes:
        source: Source variable in CBN (e.g., "DNF", "in_pit")
        target: Target variable in CBN (e.g., "laps_led", "position_changes")
        reason: Human-readable explanation of why this edge is forbidden
    """
    source: str
    target: str
    reason: str

    def __str__(self) -> str:
        return f"{self.source} -> {self.target} (vetoed: {self.reason})"


# Type aliases
CBNStructure = nx.DiGraph
PriorDict = Dict[str, float]


class OntologyConstraints:
    """
    Interface to ontology layer for CBN priors and veto rules.

    This class provides:
    1. Driver priors (skill, aggression, shadow_risk) from ontology
    2. Track difficulty from ontology
    3. Hardcoded veto rules (domain knowledge)
    4. Track-specific veto rules from ontology (if defined)

    Caches driver priors to avoid repeated Neo4j queries.
    """

    def __init__(self, ontology_driver: Optional[Any] = None):
        """
        Initialize ontology constraints.

        Args:
            ontology_driver: OntologyDriver instance (optional, for standalone usage)
        """
        self._ontology_driver = ontology_driver
        self._driver_priors_cache: Dict[str, Dict[str, float]] = {}
        self._track_difficulty_cache: Dict[str, float] = {}

        if ontology_driver is None:
            logger.warning(
                "No OntologyDriver provided. Driver priors and track difficulty "
                "will return default values. Use mock OntologyDriver for testing."
            )

    def get_driver_priors(self, driver_id: str) -> Dict[str, float]:
        """
        Fetch driver priors from ontology.

        Returns driver skill, aggression, and shadow_risk from ontology.
        Results are cached to avoid repeated database queries.

        Args:
            driver_id: Driver identifier (e.g., "driver_123")

        Returns:
            Dictionary with keys:
                - "skill": Driver skill level (0-1, default 0.5 if not found)
                - "aggression": Aggression level (0-1, default 0.5 if not found)
                - "shadow_risk": Risk of poor performance (0-1, default 0.5 if not found)
        """
        # Check cache first
        if driver_id in self._driver_priors_cache:
            logger.debug(f"Returning cached priors for driver {driver_id}")
            return self._driver_priors_cache[driver_id]

        # Fetch from ontology if driver available
        if self._ontology_driver is not None and OntologyDriver is not None:
            try:
                driver_node = self._ontology_driver.get_driver_node(driver_id)
                if driver_node is not None:
                    priors = {
                        "skill": driver_node.skill,
                        "aggression": driver_node.psyche_aggression,
                        "shadow_risk": driver_node.shadow_risk,
                    }
                    self._driver_priors_cache[driver_id] = priors
                    logger.info(f"Fetched priors for driver {driver_id}: {priors}")
                    return priors
            except Exception as e:
                logger.error(f"Failed to fetch driver priors for {driver_id}: {e}")

        # Return default priors if not found or no ontology driver
        priors = {"skill": 0.5, "aggression": 0.5, "shadow_risk": 0.5}
        logger.warning(f"Using default priors for driver {driver_id}: {priors}")
        return priors

    def get_track_difficulty(self, track_id: str) -> float:
        """
        Fetch track difficulty from ontology.

        Args:
            track_id: Track identifier (e.g., "track_daytona")

        Returns:
            Track difficulty (0-1, default 0.5 if not found)
        """
        # Check cache first
        if track_id in self._track_difficulty_cache:
            logger.debug(f"Returning cached difficulty for track {track_id}")
            return self._track_difficulty_cache[track_id]

        # Fetch from ontology if driver available
        if self._ontology_driver is not None and OntologyDriver is not None:
            try:
                # Note: OntologyDriver doesn't have get_track_node method yet
                # This is a placeholder for future implementation
                # For now, return default
                logger.debug(f"Track difficulty fetching not yet implemented, using default")
            except Exception as e:
                logger.error(f"Failed to fetch track difficulty for {track_id}: {e}")

        # Return default difficulty
        difficulty = 0.5
        logger.warning(f"Using default difficulty for track {track_id}: {difficulty}")
        self._track_difficulty_cache[track_id] = difficulty
        return difficulty

    def get_veto_rules(self) -> List[VetoRule]:
        """
        Return veto rules for CBN structure constraints.

        Veto rules are hardcoded domain knowledge that prevents impossible
        causal relationships in the CBN structure.

        Returns:
            List of VetoRule objects representing forbidden edges
        """
        # Hardcoded veto rules from domain knowledge
        # These represent physical impossibilities in NASCAR racing
        veto_rules = [
            VetoRule(
                source="DNF",
                target="laps_led",
                reason="DNF driver cannot lead laps after incident"
            ),
            VetoRule(
                source="DNF",
                target="fastest_laps",
                reason="DNF driver cannot have fastest laps after incident"
            ),
            VetoRule(
                source="in_pit",
                target="position_changes",
                reason="No position changes while pitting"
            ),
            VetoRule(
                source="caution_segment",
                target="position_changes",
                reason="No position changes during caution (field frozen)"
            ),
            VetoRule(
                source="finish_position",
                target="skill",
                reason="Finish position cannot cause driver skill (temporal constraint)"
            ),
            VetoRule(
                source="DNF",
                target="skill",
                reason="DNF status cannot cause driver skill (temporal constraint)"
            ),
        ]

        logger.debug(f"Returning {len(veto_rules)} veto rules")
        return veto_rules

    def clear_cache(self) -> None:
        """
        Clear cached priors and track difficulty.

        Useful for testing or when ontology data is updated.
        """
        self._driver_priors_cache.clear()
        self._track_difficulty_cache.clear()
        logger.info("Cleared ontology constraints cache")


def apply_veto_rules(structure: nx.DiGraph, veto_rules: List[VetoRule]) -> nx.DiGraph:
    """
    Apply veto rules to CBN structure, removing forbidden edges.

    This function enforces ontology constraints on the learned CBN structure
    by removing edges that violate physical impossibility or temporal ordering.

    Args:
        structure: Learned CBN structure as NetworkX DiGraph
        veto_rules: List of VetoRule objects to enforce

    Returns:
        Constrained structure with vetoed edges removed

    Example:
        >>> import networkx as nx
        >>> structure = nx.DiGraph()
        >>> structure.add_edge("DNF", "laps_led")
        >>> structure.add_edge("skill", "finish_position")
        >>> veto_rules = [VetoRule("DNF", "laps_led", "DNF cannot lead laps")]
        >>> constrained = apply_veto_rules(structure, veto_rules)
        >>> assert ("DNF", "laps_led") not in constrained.edges()
        >>> assert ("skill", "finish_position") in constrained.edges()
    """
    constrained = structure.copy()
    edges_removed = 0

    for rule in veto_rules:
        if constrained.has_edge(rule.source, rule.target):
            constrained.remove_edge(rule.source, rule.target)
            edges_removed += 1
            logger.info(
                f"Applied veto rule: removed edge {rule.source} -> {rule.target}. "
                f"Reason: {rule.reason}"
            )

    logger.info(f"Applied veto rules: removed {edges_removed} edges from CBN structure")
    return constrained


def get_driver_priors(ontology_constraints: OntologyConstraints, driver_ids: List[str]) -> PriorDict:
    """
    Fetch priors for multiple drivers from ontology.

    Convenience function that fetches priors for all drivers and returns
    them formatted for CBN parameter learning.

    Args:
        ontology_constraints: OntologyConstraints instance
        driver_ids: List of driver identifiers

    Returns:
        Dictionary mapping CBN variable names to prior values:
            - "{driver_id}_skill": skill value
            - "{driver_id}_aggression": aggression value
            - "{driver_id}_shadow_risk": shadow_risk value
    """
    priors: PriorDict = {}

    for driver_id in driver_ids:
        driver_priors = ontology_constraints.get_driver_priors(driver_id)
        priors[f"{driver_id}_skill"] = driver_priors["skill"]
        priors[f"{driver_id}_aggression"] = driver_priors["aggression"]
        priors[f"{driver_id}_shadow_risk"] = driver_priors["shadow_risk"]

    logger.info(f"Fetched priors for {len(driver_ids)} drivers, {len(priors)} total priors")
    return priors
