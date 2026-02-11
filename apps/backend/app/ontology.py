"""
Ontology layer wrapping Neo4j driver with metaphysical properties.

This module provides a connection-pooled Neo4j driver for managing
Driver, Track, and Race nodes with their metaphysical properties.
"""
import logging
from typing import Dict, List, Optional, Any
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


def validate_range(value: float, name: str, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """
    Validate that a value is in the specified range.

    Args:
        value: Value to validate
        name: Name of the property for error messages
        min_val: Minimum allowed value (default: 0.0)
        max_val: Maximum allowed value (default: 1.0)

    Returns:
        Validated value

    Raises:
        ValueError: If value is out of range
    """
    if not min_val <= value <= max_val:
        raise ValueError(f"{name} must be between {min_val} and {max_val}, got {value}")
    return value


class DriverNode:
    """
    Represents a Driver node in Neo4j with metaphysical properties.
    """
    
    def __init__(
        self,
        driver_id: str,
        name: str,
        skill: float = 0.5,
        psyche_aggression: float = 0.5,
        shadow_risk: float = 0.5,
        realpolitik_pos: float = 0.5
    ) -> None:
        """
        Initialize DriverNode.

        Args:
            driver_id: Unique driver identifier
            name: Driver name
            skill: Driver skill level (0-1)
            psyche_aggression: Aggression level (0-1)
            shadow_risk: Risk of poor performance (0-1)
            realpolitik_pos: Positional advantage (0-1)
        """
        self.driver_id: str = driver_id
        self.name: str = name
        self.skill: float = validate_range(skill, "skill")
        self.psyche_aggression: float = validate_range(
            psyche_aggression, "psyche_aggression"
        )
        self.shadow_risk: float = validate_range(shadow_risk, "shadow_risk")
        self.realpolitik_pos: float = validate_range(
            realpolitik_pos, "realpolitik_pos"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary with driver properties
        """
        return {
            "driver_id": self.driver_id,
            "name": self.name,
            "skill": self.skill,
            "psyche_aggression": self.psyche_aggression,
            "shadow_risk": self.shadow_risk,
            "realpolitik_pos": self.realpolitik_pos,
        }


class TrackNode:
    """
    Represents a Track node in Neo4j with metaphysical properties.
    """
    
    def __init__(
        self,
        track_id: str,
        name: str,
        difficulty: float = 0.5,
        aggression_factor: float = 0.5
    ) -> None:
        """
        Initialize TrackNode.

        Args:
            track_id: Unique track identifier
            name: Track name
            difficulty: Track difficulty (0-1)
            aggression_factor: How much aggression matters (0-1)
        """
        self.track_id: str = track_id
        self.name: str = name
        self.difficulty: float = validate_range(difficulty, "difficulty")
        self.aggression_factor: float = validate_range(
            aggression_factor, "aggression_factor"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary with track properties
        """
        return {
            "track_id": self.track_id,
            "name": self.name,
            "difficulty": self.difficulty,
            "aggression_factor": self.aggression_factor,
        }


class RaceNode:
    """
    Represents a Race node in Neo4j with metaphysical properties.
    """
    
    def __init__(
        self,
        race_id: str,
        name: str,
        track_id: str,
        chaos_factor: float = 0.5
    ) -> None:
        """
        Initialize RaceNode.

        Args:
            race_id: Unique race identifier
            name: Race name
            track_id: Associated track identifier
            chaos_factor: Race unpredictability (0-1)
        """
        self.race_id: str = race_id
        self.name: str = name
        self.track_id: str = track_id
        self.chaos_factor: float = validate_range(chaos_factor, "chaos_factor")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary with race properties
        """
        return {
            "race_id": self.race_id,
            "name": self.name,
            "track_id": self.track_id,
            "chaos_factor": self.chaos_factor,
        }


class OntologyDriver:
    """
    Wrapper for Neo4j driver managing Driver, Track, and Race nodes.

    Provides connection pooling and methods to interact with the ontology layer
    and retrieve metaphysical properties that can influence projections.
    """

    _instance = None
    _driver = None

    def __new__(cls, uri: str = None, user: str = None, password: str = None) -> 'OntologyDriver':
        """
        Singleton pattern for connection pooling.

        Args:
            uri: Neo4j connection URI (only needed on first instantiation)
            user: Neo4j username (only needed on first instantiation)
            password: Neo4j password (only needed on first instantiation)

        Returns:
            OntologyDriver instance
        """
        if cls._instance is None:
            if uri is None or user is None or password is None:
                raise ValueError("uri, user, and password are required for first instantiation")
            cls._instance = super().__new__(cls)
            cls._instance._initialize_driver(uri, user, password)
            logger.info("OntologyDriver initialized with connection pooling")
        return cls._instance

    def _initialize_driver(self, uri: str, user: str, password: str) -> None:
        """
        Initialize Neo4j driver with connection pooling configuration.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
        """
        try:
            self._driver = GraphDatabase.driver(
                uri,
                auth=(user, password),
                max_connection_lifetime=3600,  # 1 hour
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,  # 60 seconds
                connection_timeout=30,  # 30 seconds
                resolver=None,
                encrypted=False,  # Set to True for production with TLS
                trust="TRUST_ALL_CERTIFICATES"  # Configure properly for production
            )
            # Verify connection
            self._driver.verify_connectivity()
            logger.info(f"Neo4j driver connected successfully to {uri}")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {str(e)}")
            raise

    @classmethod
    def get_driver(cls) -> 'OntologyDriver':
        """
        Get the singleton instance.

        Returns:
            OntologyDriver instance

        Raises:
            RuntimeError: If driver has not been initialized
        """
        if cls._instance is None:
            raise RuntimeError("OntologyDriver has not been initialized. Call OntologyDriver(uri, user, password) first.")
        return cls._instance

    def close(self) -> None:
        """
        Close the Neo4j driver connection.
        """
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            OntologyDriver._instance = None
            logger.info("Neo4j driver connection closed")

    def create_driver_node(self, driver_node: DriverNode) -> bool:
        """
        Create or update a Driver node in Neo4j.

        Args:
            driver_node: DriverNode to create

        Returns:
            True if successful, False otherwise
        """
        query = """
        MERGE (d:Driver {driver_id: $driver_id})
        SET d.name = $name,
            d.skill = $skill,
            d.psyche_aggression = $psyche_aggression,
            d.shadow_risk = $shadow_risk,
            d.realpolitik_pos = $realpolitik_pos
        """
        try:
            with self._driver.session() as session:
                session.run(
                    query,
                    driver_node.to_dict()
                )
            logger.info(f"Driver node created/updated: {driver_node.driver_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create driver node {driver_node.driver_id}: {str(e)}")
            return False

    def get_driver_node(self, driver_id: str) -> Optional[DriverNode]:
        """
        Retrieve a Driver node from Neo4j.

        Args:
            driver_id: Driver identifier to retrieve

        Returns:
            DriverNode if found, None otherwise
        """
        query = """
        MATCH (d:Driver {driver_id: $driver_id})
        RETURN d.driver_id as driver_id,
               d.name as name,
               d.skill as skill,
               d.psyche_aggression as psyche_aggression,
               d.shadow_risk as shadow_risk,
               d.realpolitik_pos as realpolitik_pos
        """
        try:
            with self._driver.session() as session:
                result = session.run(query, driver_id=driver_id)
                record = result.single()
                if record:
                    logger.debug(f"Driver node retrieved: {driver_id}")
                    return DriverNode(
                        driver_id=record["driver_id"],
                        name=record["name"],
                        skill=record["skill"],
                        psyche_aggression=record["psyche_aggression"],
                        shadow_risk=record["shadow_risk"],
                        realpolitik_pos=record["realpolitik_pos"],
                    )
        except Exception as e:
            logger.error(f"Failed to retrieve driver node {driver_id}: {str(e)}")
        return None

    def create_track_node(self, track_node: TrackNode) -> bool:
        """
        Create or update a Track node in Neo4j.

        Args:
            track_node: TrackNode to create

        Returns:
            True if successful, False otherwise
        """
        query = """
        MERGE (t:Track {track_id: $track_id})
        SET t.name = $name,
            t.difficulty = $difficulty,
            t.aggression_factor = $aggression_factor
        """
        try:
            with self._driver.session() as session:
                session.run(query, track_node.to_dict())
            logger.info(f"Track node created/updated: {track_node.track_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create track node {track_node.track_id}: {str(e)}")
            return False

    def create_race_node(self, race_node: RaceNode) -> bool:
        """
        Create or update a Race node in Neo4j.

        Args:
            race_node: RaceNode to create

        Returns:
            True if successful, False otherwise
        """
        query = """
        MERGE (r:Race {race_id: $race_id})
        SET r.name = $name,
            r.track_id = $track_id,
            r.chaos_factor = $chaos_factor
        """
        try:
            with self._driver.session() as session:
                session.run(query, race_node.to_dict())
            logger.info(f"Race node created/updated: {race_node.race_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create race node {race_node.race_id}: {str(e)}")
            return False

    def get_driver_metaphysical_adjustment(
        self,
        driver_id: str,
        track_id: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate metaphysical adjustment for a driver's projections.

        Args:
            driver_id: Driver identifier
            track_id: Optional track identifier for context

        Returns:
            Dictionary with adjustment factors
        """
        driver = self.get_driver_node(driver_id)
        if not driver:
            logger.warning(f"Driver not found for metaphysical adjustment: {driver_id}")
            return {"adjustment": 0.0}

        adjustment = driver.skill * (1 - driver.shadow_risk)

        if track_id:
            # Track-specific adjustments could be added here
            logger.debug(f"Calculating adjustment for driver {driver_id} at track {track_id}")

        return {
            "adjustment": adjustment,
            "skill": driver.skill,
            "shadow_risk": driver.shadow_risk,
        }
