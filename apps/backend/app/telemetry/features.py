"""
Feature availability contract enforcement for telemetry data.

Prevents data leakage by ensuring only features available at prediction time
are used in model training and inference.

Temporal boundaries:
- Historical features: Available (past race data)
- Practice/Qualifying features: Available (pre-race sessions)
- Race telemetry features: NOT available (future information - data leakage)
"""

from typing import List, Set
import logging

logger = logging.getLogger(__name__)


class FeatureAvailabilityContract:
    """
    Enforces temporal boundaries on feature access to prevent data leakage.

    Race telemetry features (laps led, finish position, incidents) constitute
    future information at prediction time and must be blocked.
    """

    # Features available from historical race data
    HISTORICAL_FEATURES: Set[str] = {
        "avg_finish_position",
        "avg_laps_led",
        "win_rate",
        "dnf_rate",
        "recent_form",
    }

    # Features available from practice sessions
    PRACTICE_FEATURES: Set[str] = {
        "practice_lap_time",
        "practice_speed",
        "practice_laps_complete",
    }

    # Features available from qualifying sessions
    QUALIFYING_FEATURES: Set[str] = {
        "qualifying_position",
        "qualifying_speed",
        "qualifying_gap",
    }

    # Features that constitute data leakage (future race information)
    FORBIDDEN_FEATURES: Set[str] = {
        "race_laps_led",
        "race_finish_position",
        "race_incidents",
        "race_dnf_lap",
    }

    @classmethod
    def validate_features(cls, features: List[str]) -> None:
        """
        Validate that requested features don't include forbidden race telemetry.

        Args:
            features: List of feature names to validate

        Raises:
            ValueError: If any forbidden features are requested

        Examples:
            >>> FeatureAvailabilityContract.validate_features(['avg_finish_position'])
            >>> FeatureAvailabilityContract.validate_features(['race_laps_led'])
            ValueError: Requested forbidden features: race_laps_led
        """
        requested_set = set(features)
        forbidden = requested_set & cls.FORBIDDEN_FEATURES

        if forbidden:
            raise ValueError(
                f"Data leakage detected: Requested forbidden features that constitute "
                f"future race information: {sorted(forbidden)}. "
                f"These features are not available at prediction time. "
                f"Use historical, practice, or qualifying features only."
            )

        # Log warning for unknown features
        all_known = cls.HISTORICAL_FEATURES | cls.PRACTICE_FEATURES | cls.QUALIFYING_FEATURES | cls.FORBIDDEN_FEATURES
        unknown = requested_set - all_known
        if unknown:
            logger.warning(
                f"Unknown features requested (not in any known feature list): {sorted(unknown)}. "
                f"These may be custom features - ensure they don't constitute data leakage."
            )

    @classmethod
    def get_allowed_features(cls, available: List[str]) -> List[str]:
        """
        Filter available features to only include non-forbidden ones.

        Args:
            available: List of all available feature names

        Returns:
            Filtered list containing only allowed features

        Examples:
            >>> FeatureAvailabilityContract.get_allowed_features(
            ...     ['avg_finish_position', 'practice_lap_time', 'race_laps_led']
            ... )
            ['avg_finish_position', 'practice_lap_time']
        """
        available_set = set(available)
        allowed = available_set - cls.FORBIDDEN_FEATURES
        return sorted(allowed)

    @classmethod
    def validate_dataframe(cls, columns: List[str]) -> None:
        """
        Validate DataFrame columns don't include forbidden features.

        Args:
            columns: List of DataFrame column names

        Raises:
            ValueError: If any columns are forbidden features

        Examples:
            >>> FeatureAvailabilityContract.validate_dataframe(
            ...     ['lap', 'driver_id', 'avg_finish_position']
            ... )
            >>> FeatureAvailabilityContract.validate_dataframe(
            ...     ['lap', 'driver_id', 'race_laps_led']
            ... )
            ValueError: Data leakage detected in columns: race_laps_led
        """
        requested_set = set(columns)
        forbidden = requested_set & cls.FORBIDDEN_FEATURES

        if forbidden:
            raise ValueError(
                f"Data leakage detected in DataFrame columns: {sorted(forbidden)}. "
                f"These columns contain future race information and cannot be used "
                f"for prediction. Drop forbidden columns before proceeding."
            )

    @classmethod
    def get_metadata_columns(cls) -> Set[str]:
        """
        Get set of metadata columns that are always allowed (non-feature columns).

        Returns:
            Set of metadata column names
        """
        return {
            "lap",
            "driver_id",
            "timestamp",
            "track_id",
            "race_id",
            "session_id",
        }
