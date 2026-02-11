"""
Kernel logic for enforcing race constraints.
"""
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import logging
import threading

# Initialize logger for module
logger = logging.getLogger(__name__)

# Import conservation utilities
try:
    from packages.axiomatic_sim.src.axiomatic_sim.conservation import (
        validate_laps_led_conservation,
        validate_fastest_laps_conservation,
        validate_position_swaps,
        calculate_max_position_swaps,
        ConservationResult
    )
except ImportError:
    try:
        # Try relative import for package usage
        from axiomatic_sim.conservation import (
            validate_laps_led_conservation,
            validate_fastest_laps_conservation,
            validate_position_swaps,
            calculate_max_position_swaps,
            ConservationResult
        )
    except ImportError:
        # Standalone usage fallback - implement inline
        import numpy as np

        @dataclass
        class ConservationResult:
            """Fallback ConservationResult when conservation module unavailable."""
            laps_led_valid: bool
            fastest_laps_valid: bool
            position_swaps_valid: bool
            veto_reasons: List[str] = field(default_factory=list)
            is_valid: bool = False

            def __post_init__(self):
                self.is_valid = all([
                    self.laps_led_valid,
                    self.fastest_laps_valid,
                    self.position_swaps_valid
                ])

            def add_veto_reason(self, reason: str) -> None:
                if reason and reason not in self.veto_reasons:
                    self.veto_reasons.append(reason)

        def validate_laps_led_conservation(laps_led, race_length):
            total = np.sum(laps_led)
            if total <= race_length:
                return True, ""
            return False, f"Laps led conservation violated: total ({int(total)}) exceeds race length ({race_length})"

        def validate_fastest_laps_conservation(fastest_laps, green_flag_laps):
            total = np.sum(fastest_laps)
            if total <= green_flag_laps:
                return True, ""
            return False, f"Fastest laps conservation violated: total ({int(total)}) exceeds green flag laps ({green_flag_laps})"

        def calculate_max_position_swaps(field_size, green_flag_laps):
            swaps_per_driver_limit = field_size * 2
            track_opportunity_limit = green_flag_laps // 10
            max_swaps = min(swaps_per_driver_limit, track_opportunity_limit)
            return max(max_swaps, field_size)

        def validate_position_swaps(start_positions, finish_positions, max_swaps):
            position_changes = np.abs(finish_positions - start_positions)
            total_swaps = np.sum(position_changes)
            if total_swaps <= max_swaps:
                return True, ""
            return False, f"Position swaps violated: total ({int(total_swaps)}) exceeds max allowed ({max_swaps})"


# Module-level rejection statistics with thread-safe access
_rejection_stats_lock = threading.Lock()
_rejection_stats = {
    "total_validated": 0,
    "total_rejected": 0,
    "veto_reasons": {}
}


def get_rejection_stats() -> Dict[str, Any]:
    """
    Get current rejection statistics from kernel validation.

    Returns a copy of the rejection statistics dict with:
        - total_validated: Total number of scenarios validated
        - total_rejected: Total number of scenarios rejected
        - rejection_rate: Ratio of rejected to validated (0-1)
        - veto_reasons: Dict mapping veto reason to count

    Returns:
        Dictionary with rejection statistics

    Examples:
        >>> stats = get_rejection_stats()
        >>> print(f"Rejection rate: {stats['rejection_rate']:.2%}")
    """
    with _rejection_stats_lock:
        total_validated = _rejection_stats["total_validated"]
        total_rejected = _rejection_stats["total_rejected"]
        veto_reasons = _rejection_stats["veto_reasons"].copy()

    # Compute rejection rate
    rejection_rate = total_rejected / total_validated if total_validated > 0 else 0.0

    return {
        "total_validated": total_validated,
        "total_rejected": total_rejected,
        "rejection_rate": rejection_rate,
        "veto_reasons": veto_reasons,
    }


def reset_rejection_stats() -> None:
    """
    Reset rejection statistics to zero.

    Useful for starting a new batch of validations or testing.

    Examples:
        >>> reset_rejection_stats()
        >>> stats = get_rejection_stats()
        >>> stats["total_validated"]
        0
    """
    with _rejection_stats_lock:
        _rejection_stats["total_validated"] = 0
        _rejection_stats["total_rejected"] = 0
        _rejection_stats["veto_reasons"] = {}

    logger.info("Rejection statistics reset")


class KernelLogic:
    """
    Core logic class enforcing race constraints.

    Ensures positions are within valid range and prevents impossible states.
    The kernel provides the foundational logic that cannot be overridden by
    metaphysical factors from the ontology.

    Version 1.1.0: Extended with dominator conservation validation.
    """

    VERSION = "1.1.0"

    def __init__(self, field_size: int = 40) -> None:
        """
        Initialize KernelLogic with field size.
        
        Args:
            field_size: Total number of drivers in the race (default 40)
        """
        self.field_size: int = field_size
    
    def validate_position(self, position: int) -> bool:
        """
        Validate that a position is within the valid range.
        
        Args:
            position: Starting position to validate
            
        Returns:
            True if position is valid, False otherwise
        """
        return 1 <= position <= self.field_size
    
    def validate_lineup_positions(
        self,
        positions: List[int]
    ) -> bool:
        """
        Validate that all positions in a lineup are valid.
        
        Args:
            positions: List of positions to validate
            
        Returns:
            True if all positions are valid, False otherwise
        """
        return all(self.validate_position(pos) for pos in positions)
    
    def validate_unique_positions(
        self,
        positions: List[int]
    ) -> bool:
        """
        Validate that all positions in a lineup are unique.
        
        Args:
            positions: List of positions to validate
            
        Returns:
            True if all positions are unique, False otherwise
        """
        return len(positions) == len(set(positions))
    
    def validate_lineup_size(
        self,
        lineup_size: int,
        required_size: int = 6
    ) -> bool:
        """
        Validate that lineup size matches required size.
        
        Args:
            lineup_size: Actual lineup size
            required_size: Required lineup size (default 6 for DK NASCAR)
            
        Returns:
            True if lineup size is valid, False otherwise
        """
        return lineup_size == required_size
    
    def is_impossible_state(
        self,
        positions: List[int],
        salaries: Optional[List[int]] = None,
        salary_cap: Optional[int] = None
    ) -> bool:
        """
        Check if the current state represents an impossible configuration.
        
        Args:
            positions: List of driver positions
            salaries: Optional list of driver salaries
            salary_cap: Optional salary cap to validate against
            
        Returns:
            True if state is impossible, False otherwise
        """
        # Check for invalid positions
        if not self.validate_lineup_positions(positions):
            return True
        
        # Check for duplicate positions
        if not self.validate_unique_positions(positions):
            return True
        
        # Check salary constraints if provided
        if salaries is not None and salary_cap is not None:
            total_salary = sum(salaries)
            if total_salary > salary_cap:
                return True
        
        return False

    def validate_dominator_conservation(
        self,
        scenario_data: Dict[str, any]
    ) -> ConservationResult:
        """
        Validate dominator conservation constraints for a scenario.

        This method enforces conservation principles that prevent impossible
        scenarios from propagating to optimization. Dominator conservation
        ensures that:
        - Total laps led ≤ race length (only one driver can lead per lap)
        - Total fastest laps ≤ green flag laps (one fastest lap per green flag lap)
        - Position swaps ≤ physical opportunities (bounded by track geometry)

        Args:
            scenario_data: Dictionary containing:
                - laps_led: Dict[str, int] or List[int] (driver_id -> laps led)
                - fastest_laps: Dict[str, int] or List[int] (driver_id -> fastest laps)
                - start_positions: Dict[str, int] or List[int] (driver_id -> starting position)
                - finish_positions: Dict[str, int] or List[int] (driver_id -> finish position)
                - race_length: int (total laps in race)
                - green_flag_laps: int (total green flag laps)

        Returns:
            ConservationResult with validation status and veto reasons

        Examples:
            >>> kernel = KernelLogic(field_size=40)
            >>> scenario = {
            ...     'laps_led': [100, 50, 30, 20] + [0] * 36,
            ...     'fastest_laps': [10, 8, 5, 3] + [0] * 36,
            ...     'start_positions': list(range(1, 41)),
            ...     'finish_positions': list(range(1, 41)),
            ...     'race_length': 200,
            ...     'green_flag_laps': 180
            ... }
            >>> result = kernel.validate_dominator_conservation(scenario)
            >>> result.is_valid
            True
        """

        # Extract data from scenario_data
        laps_led_input = scenario_data.get('laps_led', [])
        fastest_laps_input = scenario_data.get('fastest_laps', [])
        start_positions_input = scenario_data.get('start_positions', [])
        finish_positions_input = scenario_data.get('finish_positions', [])
        race_length = scenario_data.get('race_length', 0)
        green_flag_laps = scenario_data.get('green_flag_laps', 0)

        # Convert dicts to lists if needed
        if isinstance(laps_led_input, dict):
            laps_led_list = list(laps_led_input.values())
        else:
            laps_led_list = laps_led_input

        if isinstance(fastest_laps_input, dict):
            fastest_laps_list = list(fastest_laps_input.values())
        else:
            fastest_laps_list = fastest_laps_input

        if isinstance(start_positions_input, dict):
            start_positions_list = list(start_positions_input.values())
        else:
            start_positions_list = start_positions_input

        if isinstance(finish_positions_input, dict):
            finish_positions_list = list(finish_positions_input.values())
        else:
            finish_positions_list = finish_positions_input

        # Convert to numpy arrays (JAX arrays if available)
        try:
            import numpy as np
            laps_led = np.array(laps_led_list, dtype=np.int32)
            fastest_laps = np.array(fastest_laps_list, dtype=np.int32)
            start_positions = np.array(start_positions_list, dtype=np.int32)
            finish_positions = np.array(finish_positions_list, dtype=np.int32)
        except Exception as e:
            logger.error(f"Failed to convert scenario data to arrays: {e}")
            return ConservationResult(
                laps_led_valid=False,
                fastest_laps_valid=False,
                position_swaps_valid=False,
                veto_reasons=[f"Invalid scenario data format: {e}"]
            )

        # Validate laps led conservation
        laps_led_valid, laps_led_reason = validate_laps_led_conservation(
            laps_led, race_length
        )

        # Validate fastest laps conservation
        fastest_laps_valid, fastest_laps_reason = validate_fastest_laps_conservation(
            fastest_laps, green_flag_laps
        )

        # Calculate max position swaps
        max_swaps = calculate_max_position_swaps(self.field_size, green_flag_laps)

        # Validate position swaps
        position_swaps_valid, position_swaps_reason = validate_position_swaps(
            start_positions, finish_positions, max_swaps
        )

        # Build result
        result = ConservationResult(
            laps_led_valid=bool(laps_led_valid),
            fastest_laps_valid=bool(fastest_laps_valid),
            position_swaps_valid=bool(position_swaps_valid)
        )

        # Add veto reasons and log failures
        if not laps_led_valid:
            result.add_veto_reason(laps_led_reason)
            logger.warning(
                f"Conservation violation: {laps_led_reason} "
                f"(scenario has {int(sum(laps_led))} laps led, race length is {race_length})"
            )

        if not fastest_laps_valid:
            result.add_veto_reason(fastest_laps_reason)
            logger.warning(
                f"Conservation violation: {fastest_laps_reason} "
                f"(scenario has {int(sum(fastest_laps))} fastest laps, green flag laps is {green_flag_laps})"
            )

        if not position_swaps_valid:
            result.add_veto_reason(position_swaps_reason)
            logger.warning(
                f"Conservation violation: {position_swaps_reason} "
                f"(max allowed: {max_swaps})"
            )

        # Instrumentation: Track rejection statistics
        with _rejection_stats_lock:
            _rejection_stats["total_validated"] += 1

            if not result.is_valid:
                _rejection_stats["total_rejected"] += 1

                # Track veto reasons
                for veto_reason in result.veto_reasons:
                    if veto_reason not in _rejection_stats["veto_reasons"]:
                        _rejection_stats["veto_reasons"][veto_reason] = 0
                    _rejection_stats["veto_reasons"][veto_reason] += 1

        # Log validation result with structured data
        total_validated = _rejection_stats["total_validated"]
        total_rejected = _rejection_stats["total_rejected"]

        if result.is_valid:
            logger.debug(
                f"Validation passed (scenario_id: N/A, total_validated: {total_validated})"
            )
        else:
            logger.warning(
                f"Validation failed (scenario_id: N/A, is_valid: {result.is_valid}, "
                f"veto_reasons: {result.veto_reasons}, "
                f"total_validated: {total_validated}, total_rejected: {total_rejected})"
            )

        # Log rejection rate every 100 validations
        if total_validated % 100 == 0:
            rejection_rate = total_rejected / total_validated if total_validated > 0 else 0.0
            logger.info(
                f"Rejection statistics: total_validated={total_validated}, "
                f"total_rejected={total_rejected}, rejection_rate={rejection_rate:.2%}"
            )

        return result

    def validate_position_swaps(
        self,
        start_positions: List[int],
        finish_positions: List[int],
        green_flag_laps: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Validate that position swaps are within physical limits.

        This is a convenience wrapper around the validate_position_swaps utility
        that automatically calculates max_swaps based on field size.

        Args:
            start_positions: List of starting positions
            finish_positions: List of finishing positions
            green_flag_laps: Total green flag laps (defaults to 180 if not provided)

        Returns:
            Tuple of (is_valid, veto_reason)

        Examples:
            >>> kernel = KernelLogic(field_size=40)
            >>> kernel.validate_position_swaps(
            ...     list(range(1, 41)),
            ...     list(range(1, 41)),
            ...     180
            ... )
            (True, "")
        """
        if green_flag_laps is None:
            green_flag_laps = 180

        max_swaps = calculate_max_position_swaps(self.field_size, green_flag_laps)

        try:
            import numpy as np
            start_array = np.array(start_positions, dtype=np.int32)
            finish_array = np.array(finish_positions, dtype=np.int32)
        except Exception as e:
            return False, f"Invalid position data: {e}"

        return validate_position_swaps(start_array, finish_array, max_swaps)

    def batch_validate_scenarios(
        self,
        scenarios: List[Dict[str, any]]
    ) -> Tuple[List[ConservationResult], Dict[str, Any]]:
        """
        Validate conservation constraints across a batch of scenarios.

        This method processes multiple scenarios efficiently, using JAX
        vectorization when available for parallel validation. Returns
        both validation results and batch-level statistics.

        Args:
            scenarios: List of scenario dictionaries, each containing:
                - laps_led: List[int] (laps led per driver)
                - fastest_laps: List[int] (fastest laps per driver)
                - race_length: int
                - green_flag_laps: int

        Returns:
            Tuple of:
                - List of ConservationResult objects (one per scenario)
                - Batch summary dict with total_validated, total_rejected, rejection_rate

        Examples:
            >>> kernel = KernelLogic(field_size=40)
            >>> scenarios = [
            ...     {
            ...         'laps_led': [100, 50] + [0] * 38,
            ...         'fastest_laps': [10, 8] + [0] * 38,
            ...         'race_length': 200,
            ...         'green_flag_laps': 180
            ...     },
            ...     {
            ...         'laps_led': [150, 70] + [0] * 38,  # Violates conservation
            ...         'fastest_laps': [15, 12] + [0] * 38,
            ...         'race_length': 200,
            ...         'green_flag_laps': 180
            ...     }
            ... ]
            >>> results, summary = kernel.batch_validate_scenarios(scenarios)
            >>> len(results)
            2
            >>> summary['rejection_rate']
            0.5
        """
        logger = logging.getLogger(__name__)

        # Capture stats before batch
        stats_before = get_rejection_stats()

        logger.info(f"Starting batch validation of {len(scenarios)} scenarios")

        results = []
        for scenario in scenarios:
            result = self.validate_dominator_conservation(scenario)
            results.append(result)

        # Capture stats after batch
        stats_after = get_rejection_stats()

        # Compute batch-level statistics
        batch_validated = stats_after["total_validated"] - stats_before["total_validated"]
        batch_rejected = stats_after["total_rejected"] - stats_before["total_rejected"]
        batch_rejection_rate = batch_rejected / batch_validated if batch_validated > 0 else 0.0

        batch_summary = {
            "batch_size": len(scenarios),
            "batch_validated": batch_validated,
            "batch_rejected": batch_rejected,
            "batch_rejection_rate": batch_rejection_rate,
            "batch_valid": sum(1 for r in results if r.is_valid),
        }

        logger.info(
            f"Batch validation complete: {batch_summary['batch_valid']}/{len(scenarios)} valid, "
            f"rejection_rate={batch_rejection_rate:.2%}"
        )

        return results, batch_summary

    @classmethod
    def get_rejection_summary(cls) -> Dict[str, Any]:
        """
        Get rejection summary with top veto reasons.

        Returns a summary of rejection statistics including:
        - Total validated and rejected counts
        - Overall rejection rate
        - Top 5 veto reasons by count

        Returns:
            Dictionary with rejection summary

        Examples:
            >>> summary = KernelLogic.get_rejection_summary()
            >>> print(f"Rejection rate: {summary['rejection_rate']:.2%}")
            >>> print(f"Top veto reason: {summary['top_veto_reasons'][0]}")
        """
        stats = get_rejection_stats()

        # Get top 5 veto reasons by count
        veto_reasons = stats["veto_reasons"]
        top_veto_reasons = sorted(
            veto_reasons.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            "total_validated": stats["total_validated"],
            "total_rejected": stats["total_rejected"],
            "rejection_rate": stats["rejection_rate"],
            "top_veto_reasons": [
                {"reason": reason, "count": count}
                for reason, count in top_veto_reasons
            ],
        }

    def get_version(self) -> str:
        """
        Get the kernel version.

        Returns:
            Version string (e.g., "1.1.0")
        """
        return self.VERSION

    def get_field_size(self) -> int:
        """
        Get the current field size.
        
        Returns:
            Field size
        """
        return self.field_size
    
    def set_field_size(self, field_size: int) -> None:
        """
        Update the field size.
        
        Args:
            field_size: New field size
        """
        if field_size < 1:
            raise ValueError("Field size must be at least 1")
        self.field_size = field_size
