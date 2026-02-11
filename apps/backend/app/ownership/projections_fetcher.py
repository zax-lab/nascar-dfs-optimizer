"""
Projections fetcher for external projection sources.

This module provides ProjectionsFetcher for integrating with external
projection sources (FantasyPros, DraftKings, FanDuel) or for manual
projection input via API.

Key features:
- Manual mode: projections provided via API input
- Placeholder structure for future API integrations
- Projections validation (positive, reasonable range)

Usage:
    fetcher = ProjectionsFetcher(projection_source='manual')
    projections = fetcher.fetch_projections([1, 2, 3], race_id=100)
    is_valid = fetcher.validate_projections(projections)
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ProjectionsFetcher:
    """
    Fetch driver projections from external sources.

    Supports multiple projection sources:
    - 'manual': Projections provided via API input (default)
    - 'fantasypros': Placeholder for future FantasyPros API integration
    - 'dfs_sites': Placeholder for future DraftKings/FanDuel integration

    For manual mode, fetch_projections returns an empty dict, indicating
    that projections should be provided externally (e.g., via API request).

    Attributes:
        projection_source: Source type ('manual', 'fantasypros', 'dfs_sites')

    Example:
        >>> fetcher = ProjectionsFetcher(projection_source='manual')
        >>> projections = fetcher.fetch_projections([1, 2, 3], race_id=100)
        >>> # In manual mode, projections = {}
        >>> # Projections should be provided via API input
        >>> is_valid = fetcher.validate_projections({1: 50.0, 2: 45.0})
    """

    VALID_SOURCES = ['manual', 'fantasypros', 'dfs_sites']

    def __init__(self, projection_source: str = 'manual'):
        """
        Initialize ProjectionsFetcher.

        Args:
            projection_source: Source type ('manual', 'fantasypros', 'dfs_sites')

        Raises:
            ValueError: If projection_source is not valid
        """
        if projection_source not in self.VALID_SOURCES:
            raise ValueError(
                f"Invalid projection_source: {projection_source}. "
                f"Must be one of {self.VALID_SOURCES}"
            )

        self.projection_source = projection_source

        logger.info(
            f"Initialized ProjectionsFetcher with source: {projection_source}"
        )

    def fetch_projections(
        self,
        driver_ids: List[int],
        race_id: int
    ) -> Dict[int, float]:
        """
        Fetch driver projections from the configured source.

        For 'manual' mode, returns an empty dict indicating that projections
        should be provided externally (e.g., via API request).

        For API sources ('fantasypros', 'dfs_sites'), logs a warning that
        API integration is not yet implemented and returns empty dict.

        Args:
            driver_ids: List of driver IDs to fetch projections for
            race_id: Race identifier

        Returns:
            Dictionary mapping driver_id -> projected_points
            (Empty dict for manual mode or unimplemented APIs)
        """
        if self.projection_source == 'manual':
            # Manual mode: projections provided via API input
            logger.debug(
                f"Manual projection mode: returning empty dict for "
                f"{len(driver_ids)} drivers in race {race_id}"
            )
            return {}

        elif self.projection_source == 'fantasypros':
            # Placeholder for future FantasyPros API integration
            logger.warning(
                "FantasyPros API integration not yet implemented. "
                "Use manual mode and provide projections via API input."
            )
            return {}

        elif self.projection_source == 'dfs_sites':
            # Placeholder for future DraftKings/FanDuel integration
            logger.warning(
                "DFS sites API integration not yet implemented. "
                "Use manual mode and provide projections via API input."
            )
            return {}

        else:
            # Should not reach here due to __init__ validation
            logger.error(f"Unknown projection source: {self.projection_source}")
            return {}

    def validate_projections(
        self,
        projections: Dict[int, float]
    ) -> bool:
        """
        Validate that projections are reasonable.

        Checks:
        - All projections are positive (> 0)
        - Projections are in reasonable range (0-100 DFS points)

        Args:
            projections: Dictionary mapping driver_id -> projected_points

        Returns:
            True if projections are valid, False otherwise

        Raises:
            ValueError: If projections is not a dict
        """
        if not isinstance(projections, dict):
            raise ValueError("Projections must be a dictionary")

        if not projections:
            logger.debug("Empty projections dict, nothing to validate")
            return True

        # Check all projections are positive
        for driver_id, proj_points in projections.items():
            if proj_points <= 0:
                logger.warning(
                    f"Invalid projection for driver {driver_id}: "
                    f"{proj_points} <= 0"
                )
                return False

            # Check projections are in reasonable range (0-100)
            # Most NASCAR DFS scores are 20-60 range, but can go higher
            if proj_points > 100:
                logger.warning(
                    f"Suspicious projection for driver {driver_id}: "
                    f"{proj_points} > 100 (unusually high)"
                )
                # Don't return False, just warn

        logger.debug(
            f"Validated {len(projections)} projections: all positive"
        )
        return True

    def fetch_and_validate(
        self,
        driver_ids: List[int],
        race_id: int
    ) -> Dict[int, float]:
        """
        Fetch projections and validate them.

        Convenience method that combines fetch_projections and validate_projections.

        Args:
            driver_ids: List of driver IDs to fetch projections for
            race_id: Race identifier

        Returns:
            Dictionary mapping driver_id -> projected_points (empty if invalid)

        Raises:
            ValueError: If projections fail validation
        """
        projections = self.fetch_projections(driver_ids, race_id)

        if projections and not self.validate_projections(projections):
            raise ValueError(
                f"Invalid projections for race {race_id}. "
                "See logs for details."
            )

        return projections
