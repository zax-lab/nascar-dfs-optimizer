"""
Neo4j batch query compiler for constraint specifications.

This module provides the ConstraintCompiler that batch-queries Neo4j to compile
immutable constraint specifications, eliminating live database queries in
simulation/optimization loops.

Key concepts:
- Batch queries minimize database round trips (<100ms per slate)
- RoutingControl.READ for efficient read operations
- Validation after compilation ensures data integrity
"""
from neo4j import GraphDatabase, RoutingControl
from datetime import datetime
from typing import List, Dict, Optional
import logging
import time

from app.constraints.models import ConstraintSpec, DriverConstraints, TrackConstraints
from app.ontology import OntologyDriver

logger = logging.getLogger(__name__)


class ConstraintCompiler:
    """
    Compiles constraint specifications from Neo4j using batch queries.

    This class replaces live Neo4j queries in hot loops with pre-compiled
    immutable constraint specifications, ensuring deterministic execution.

    Attributes:
        ontology_driver: OntologyDriver instance for Neo4j connection
    """

    def __init__(self, ontology_driver: OntologyDriver):
        """
        Initialize constraint compiler.

        Args:
            ontology_driver: OntologyDriver instance with active Neo4j connection
        """
        self._ontology_driver = ontology_driver
        logger.info("ConstraintCompiler initialized")

    def compile_driver_constraints(self, driver_ids: List[str]) -> Dict[str, DriverConstraints]:
        """
        Compile driver constraints using a single batch query.

        Fetches all drivers in one query using IN clause for efficiency.

        Args:
            driver_ids: List of driver identifiers to compile

        Returns:
            Dictionary mapping driver_id to DriverConstraints

        Raises:
            ValueError: If any driver is not found in Neo4j
        """
        start_time = time.time()

        if not driver_ids:
            logger.warning("No driver IDs provided, returning empty dict")
            return {}

        # Batch query for all drivers
        query = """
        MATCH (d:Driver)
        WHERE d.driver_id IN $driver_ids
        OPTIONAL MATCH (d)-[:HAS_VETO_RULE]->(v:VetoRule)
        RETURN d.driver_id as driver_id,
               d.skill as skill,
               d.psyche_aggression as aggression,
               d.shadow_risk as shadow_risk,
               COLLECT(v.rule_id) as veto_rules
        """

        try:
            result = self._ontology_driver._driver.execute_query(
                query,
                {"driver_ids": driver_ids},
                routing_=RoutingControl.READ
            )

            # Build dict from results
            drivers = {}
            found_ids = set()

            for record in result.records:
                driver_id = record["driver_id"]
                found_ids.add(driver_id)

                # Create DriverConstraints with derived fields
                drivers[driver_id] = DriverConstraints(
                    driver_id=driver_id,
                    skill=float(record["skill"] or 0.5),
                    aggression=float(record["aggression"] or 0.5),
                    shadow_risk=float(record["shadow_risk"] or 0.5),
                    min_laps_led=0,  # Derived from track length
                    max_laps_led=100,  # Placeholder for track-specific max
                    veto_rules=[v for v in record["veto_rules"] if v is not None] or []
                )

            # Validate all requested drivers were found
            missing_ids = set(driver_ids) - found_ids
            if missing_ids:
                raise ValueError(f"Drivers not found in Neo4j: {missing_ids}")

            duration = time.time() - start_time
            logger.info(
                f"Compiled {len(drivers)} driver constraints in {duration*1000:.2f}ms "
                f"({duration/len(drivers)*1000:.2f}ms per driver)"
            )

            return drivers

        except Exception as e:
            logger.error(f"Failed to compile driver constraints: {e}")
            raise

    def compile_track_constraints(self, track_ids: List[str]) -> Dict[str, TrackConstraints]:
        """
        Compile track constraints using a single batch query.

        Fetches all tracks in one query using IN clause for efficiency.

        Args:
            track_ids: List of track identifiers to compile

        Returns:
            Dictionary mapping track_id to TrackConstraints

        Raises:
            ValueError: If any track is not found in Neo4j
        """
        start_time = time.time()

        if not track_ids:
            logger.warning("No track IDs provided, returning empty dict")
            return {}

        # Batch query for all tracks
        query = """
        MATCH (t:Track)
        WHERE t.track_id IN $track_ids
        RETURN t.track_id as track_id,
               t.difficulty as difficulty,
               t.aggression_factor as aggression_factor
        """

        try:
            result = self._ontology_driver._driver.execute_query(
                query,
                {"track_ids": track_ids},
                routing_=RoutingControl.READ
            )

            # Build dict from results
            tracks = {}
            found_ids = set()

            for record in result.records:
                track_id = record["track_id"]
                found_ids.add(track_id)

                # Create TrackConstraints with standard values
                tracks[track_id] = TrackConstraints(
                    track_id=track_id,
                    difficulty=float(record["difficulty"] or 0.5),
                    aggression_factor=float(record["aggression_factor"] or 0.5),
                    caution_rate=0.05,  # Standard caution rate
                    pit_window_laps=[35, 70, 105, 140, 175]  # Standard pit windows
                )

            # Validate all requested tracks were found
            missing_ids = set(track_ids) - found_ids
            if missing_ids:
                raise ValueError(f"Tracks not found in Neo4j: {missing_ids}")

            duration = time.time() - start_time
            logger.info(
                f"Compiled {len(tracks)} track constraints in {duration*1000:.2f}ms "
                f"({duration/len(tracks)*1000:.2f}ms per track)"
            )

            return tracks

        except Exception as e:
            logger.error(f"Failed to compile track constraints: {e}")
            raise

    def compile_spec(
        self,
        slate_id: str,
        driver_ids: List[str],
        track_ids: List[str]
    ) -> ConstraintSpec:
        """
        Compile complete constraint specification for a slate.

        Performs batch queries for drivers and tracks, then creates
        an immutable ConstraintSpec with computed version hash.

        Args:
            slate_id: Unique slate identifier
            driver_ids: List of driver identifiers in the slate
            track_ids: List of track identifiers in the slate

        Returns:
            Frozen ConstraintSpec with all constraints

        Raises:
            ValueError: If compilation fails or drivers/tracks not found
        """
        start_time = time.time()
        logger.info(f"Compiling constraint spec for slate {slate_id}")

        # Compile drivers and tracks
        drivers = self.compile_driver_constraints(driver_ids)
        tracks = self.compile_track_constraints(track_ids)

        # Create constraint spec (hash is auto-computed in __post_init__)
        spec = ConstraintSpec(
            slate_id=slate_id,
            compiled_at=datetime.utcnow().isoformat() + "Z",
            drivers=drivers,
            tracks=tracks,
            version="1.0"  # Version incremented on schema changes
        )

        duration = time.time() - start_time
        logger.info(
            f"Compiled constraint spec for slate {slate_id} in {duration*1000:.2f}ms "
            f"({len(drivers)} drivers, {len(tracks)} tracks, hash={spec.hash[:16]}...)"
        )

        return spec


def compile_constraints_from_neo4j(
    slate_id: str,
    driver_ids: List[str],
    track_ids: List[str],
    ontology_driver: Optional[OntologyDriver] = None
) -> ConstraintSpec:
    """
    Convenience function to compile constraints from Neo4j.

    Args:
        slate_id: Unique slate identifier
        driver_ids: List of driver identifiers in the slate
        track_ids: List of track identifiers in the slate
        ontology_driver: OntologyDriver instance (uses singleton if not provided)

    Returns:
        Frozen ConstraintSpec with all constraints

    Example:
        >>> spec = compile_constraints_from_neo4j(
        ...     "slate_20240127",
        ...     ["driver_1", "driver_2"],
        ...     ["track_daytona"]
        ... )
        >>> print(spec.hash)
    """
    if ontology_driver is None:
        ontology_driver = OntologyDriver.get_driver()

    compiler = ConstraintCompiler(ontology_driver)
    return compiler.compile_spec(slate_id, driver_ids, track_ids)
