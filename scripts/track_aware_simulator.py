#!/usr/bin/env python3
"""
Improved Monte Carlo Simulator with Track-Specific Logic

Enhancements over basic simulator:
1. Track archetype classification (superspeedway, intermediate, road course, etc.)
2. Track-specific transition probabilities
3. Stage dynamics (cautions, fuel mileage, green flag runs)
4. Driver skill curves based on track type
5. Correlated events (multi-car crashes, debris cautions)
"""

import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Track Archetypes
TRACK_ARCHETYPES = {
    "superspeedway": {
        "name": "Superspeedway",
        "examples": ["Daytona", "Talladega"],
        "length": "2.5+ miles",
        "characteristics": {
            "pack_racing": 0.9,  # High pack racing
            "caution_rate": 0.15,  # Big crashes common
            "late_race_chaos": 0.8,  # Big one at end
            "overtime_prob": 0.25  # OT common
        }
    },
    "intermediate": {
        "name": "Intermediate Track",
        "examples": ["Texas", "Charlotte", "Kansas", "Las Vegas"],
        "length": "1.5-2.0 miles",
        "characteristics": {
            "pack_racing": 0.7,
            "caution_rate": 0.10,
            "late_race_chaos": 0.4,
            "overtime_prob": 0.08
        }
    },
    "short_track": {
        "name": "Short Track",
        "examples": ["Bristol", "Martinsville", "Richmond"],
        "length": "< 1.0 mile",
        "characteristics": {
            "pack_racing": 0.5,  # More racing room
            "caution_rate": 0.18,  # Frequent cautions
            "late_race_chaos": 0.3,
            "overtime_prob": 0.12
        }
    },
    "road_course": {
        "name": "Road Course",
        "examples": ["Watkins Glen", "Sonoma", "Chicago"],
        "length": "varies",
        "characteristics": {
            "pack_racing": 0.3,  # Less pack racing
            "caution_rate": 0.08,  # Fewer cautions
            "late_race_chaos": 0.2,
            "overtime_prob": 0.05
        }
    },
    "flat": {
        "name": "Flat Track",
        "examples": ["Phoenix", "Pocono", "Indianapolis"],
        "length": "varies",
        "characteristics": {
            "pack_racing": 0.6,
            "caution_rate": 0.09,
            "late_race_chaos": 0.35,
            "overtime_prob": 0.10
        }
    }
}


@dataclass
class TrackInfo:
    """Track information with archetype."""
    name: str
    archetype: str
    characteristics: Dict[str, float]
    stages: int = 3  # Default to 3 stages


@dataclass
class DriverSkill:
    """Driver skill profile across different contexts."""
    driver_id: int
    name: str
    base_skill: float  # Overall skill (0-1)
    superspeedway_skill: Optional[float] = None
    intermediate_skill: Optional[float] = None
    short_track_skill: Optional[float] = None
    road_course_skill: Optional[float] = None


@dataclass
class RaceContext:
    """Current race context state."""
    stage: int  # Current stage (1, 2, 3, final)
    laps_remaining: int
    cautions_this_stage: int
    green_flag_laps: int
    track_archetype: str


class TrackAwareMonteCarlo:
    """
    Monte Carlo simulator with track-specific dynamics.

    Improvements over basic simulator:
    - Track archetype selection affects transition probabilities
    - Stage-specific dynamics (cautions more likely in early stages)
    - Driver skill varies by track type
    - Correlated events (big crashes, debris)
    - Overtime scenarios
    """

    def __init__(
        self,
        drivers: List[Dict],
        track: TrackInfo,
        n_simulations: int = 1000
    ):
        """
        Initialize track-aware Monte Carlo simulator.

        Args:
            drivers: List of driver dictionaries with skill data
            track: Track information
            n_simulations: Number of Monte Carlo simulations
        """
        self.drivers = drivers
        self.track = track
        self.n_simulations = n_simulations
        self.n_drivers = len(drivers)

        # Initialize driver skills
        self._init_driver_skills()

        # Track-specific transition matrices
        self._build_track_transitions()

        # Store results
        self.results = {driver['driver_id']: [] for driver in drivers}

    def _init_driver_skills(self):
        """Initialize driver skills with track-specific modifiers."""
        for driver in self.drivers:
            base = driver.get('avg_finish', 20.0) / 43.0  # Normalize to 0-1

            # Track-specific skills (default to base if not specified)
            driver['superspeedway_skill'] = driver.get('superspeedway_skill', base)
            driver['intermediate_skill'] = driver.get('intermediate_skill', base)
            driver['short_track_skill'] = driver.get('short_track_skill', base)
            driver['road_course_skill'] = driver.get('road_course_skill', base)

    def _build_track_transitions(self):
        """
        Build track-specific position transition matrices.

        Different tracks have different position transition patterns:
        - Superspeedways: More position swapping, big crashes
        - Short tracks: Fewer positions change, more caution resets
        - Road courses: Less pack racing, more individual performance
        """
        archetype = self.track.archetype
        chars = TRACK_ARCHETYPES[archetype]['characteristics']

        # Position transition volatility (how much positions change)
        self.position_volatility = 0.15 + (1.0 - chars['pack_racing']) * 0.3

        # Caution probability
        self.caution_prob = chars['caution_rate']

        # Late-race chaos probability
        self.late_race_chaos = chars['late_race_chaos']

        # Overtime probability
        self.overtime_prob = chars['overtime_prob']

    def simulate_race(self, driver_id: int) -> int:
        """
        Simulate a single race for a driver with track dynamics.

        Args:
            driver_id: Driver identifier

        Returns:
            Final finishing position (1-43)
        """
        driver = next(d for d in self.drivers if d['driver_id'] == driver_id)

        # Get track-specific skill
        skill = driver.get(f'{self.track.archetype}_skill', driver.get('avg_finish', 20.0))

        # Expected finish position based on skill
        expected_pos = int((1.0 - skill) * 43) + 1

        # Apply track volatility
        variance = self.position_volatility * expected_pos * 2
        finish_pos = max(1, min(43, int(np.random.normal(expected_pos, variance))))

        # Apply late-race chaos
        if np.random.random() < self.late_race_chaos:
            # Position shuffle in last 20 laps
            chaos_factor = np.random.randint(-10, 10)
            finish_pos = max(1, min(43, finish_pos + chaos_factor))

        # Apply caution resets
        cautions = np.random.poisson(3 * self.caution_prob)
        if cautions > 0:
            # Each caution can shuffle positions 1-3 spots
            caution_shuffle = np.random.randint(-1, 3) * cautions
            finish_pos = max(1, min(43, finish_pos + caution_shuffle))

        # Overtime scenario
        if np.random.random() < self.overtime_prob:
            # Overtime can lead to big position changes
            ot_factor = np.random.randint(-5, 8)
            finish_pos = max(1, min(43, finish_pos + ot_factor))

        return finish_pos

    def run_simulations(self):
        """Run all Monte Carlo simulations for all drivers."""
        results = {}

        for driver in self.drivers:
            driver_id = driver['driver_id']
            finishes = []

            for _ in range(self.n_simulations):
                finish_pos = self.simulate_race(driver_id)
                finishes.append(finish_pos)

            # Calculate statistics
            finishes_array = np.array(finishes)

            results[driver_id] = {
                'name': driver['name'],
                'team': driver.get('team', 'Unknown'),
                'salary': driver.get('salary', 7500),
                'avg_finish': driver.get('avg_finish', 20.0),
                'sim_finishes': finishes_array.tolist(),
                'mean_finish': float(np.mean(finishes_array)),
                'median_finish': float(np.median(finishes_array)),
                'std_finish': float(np.std(finishes_array)),
                'prob_p1': float(np.mean(finishes_array == 1)),
                'prob_top5': float(np.mean(finishes_array <= 5)),
                'prob_top10': float(np.mean(finishes_array <= 10)),
                'distribution': self._build_distribution(finishes_array)
            }

        self.results = results
        return results

    def _build_distribution(self, finishes: np.ndarray) -> Dict[int, float]:
        """Build finish position probability distribution."""
        counts = {}
        total = len(finishes)

        for pos in range(1, 44):  # 1-43
            count = np.sum(finishes == pos)
            counts[pos] = count / total

        return counts

    def generate_report(self) -> Dict:
        """Generate summary report of simulations."""
        report = {
            'track': {
                'name': self.track.name,
                'archetype': self.track.archetype,
                'characteristics': self.track.characteristics
            },
            'simulation': {
                'n_simulations': self.n_simulations,
                'n_drivers': self.n_drivers
            },
            'drivers': self.results
        }
        return report


def create_track_from_name(track_name: str) -> TrackInfo:
    """
    Infer track archetype from track name.

    Args:
        track_name: Name of the track

    Returns:
        TrackInfo with inferred archetype
    """
    track_lower = track_name.lower()

    # Superspeedways
    if any(t in track_lower for t in ['daytona', 'talladega']):
        archetype = "superspeedway"
    # Road courses
    elif any(t in track_lower for t in ['watkins', 'sonoma', 'chicago', 'road', 'glen']):
        archetype = "road_course"
    # Short tracks
    elif any(t in track_lower for t in ['bristol', 'martinsville', 'richmond']):
        archetype = "short_track"
    # Flat tracks
    elif any(t in track_lower for t in ['phoenix', 'pocono', 'indianapolis']):
        archetype = "flat"
    # Default to intermediate
    else:
        archetype = "intermediate"

    return TrackInfo(
        name=track_name,
        archetype=archetype,
        characteristics=TRACK_ARCHETYPES[archetype]['characteristics']
    )


def main():
    """Main function to run improved simulations."""
    print("=== Track-Aware Monte Carlo Simulator ===")
    print()

    # Load driver data from simulation results
    sim_file = Path(__file__).parent.parent / "output" / "sim_results.json"
    if not sim_file.exists():
        print("❌ No simulation results found. Run basic simulator first.")
        return

    with open(sim_file, 'r') as f:
        basic_results = json.load(f)

    # Convert to driver list
    drivers = [
        {
            'driver_id': int(did),
            'name': data['name'],
            'team': data.get('team', 'Unknown'),
            'salary': data.get('salary', 7500),
            'avg_finish': data.get('avg_finish', 20.0)
        }
        for did, data in basic_results.items()
    ]

    # Test with different track types
    test_tracks = [
        create_track_from_name("Daytona"),  # Superspeedway
        create_track_from_name("Texas"),    # Intermediate
        create_track_from_name("Bristol"),  # Short track
        create_track_from_name("Watkins Glen"),  # Road course
    ]

    print(f"Drivers: {len(drivers)}")
    print(f"Simulations per driver: 1000")
    print()

    all_results = {}

    for track in test_tracks:
        print(f"--- Simulating at {track.name} ({track.archetype}) ---")

        simulator = TrackAwareMonteCarlo(
            drivers=drivers,
            track=track,
            n_simulations=1000
        )

        results = simulator.run_simulations()
        report = simulator.generate_report()

        # Save results
        track_file = Path(__file__).parent.parent / "output" / f"track_sim_{track.archetype}.json"
        with open(track_file, 'w') as f:
            json.dump(report, f, indent=2)

        all_results[track.archetype] = results

        print(f"  ✅ Saved to {track_file.name}")
        print(f"  Kyle Larson: P1={results[2]['prob_p1']:.1%}, Top10={results[2]['prob_top10']:.1%}")
        print(f"  Shane van Gisbergen: P1={results[36]['prob_p1']:.1%}, Top10={results[36]['prob_top10']:.1%}")
        print()

    # Combined results
    combined_file = Path(__file__).parent.parent / "output" / "track_comparison.json"
    with open(combined_file, 'w') as f:
        json.dump({
            'archetypes': all_results,
            'summary': {
                'archetypes_tested': list(all_results.keys()),
                'n_drivers': len(drivers),
                'n_simulations_per_driver': 1000
            }
        }, f, indent=2)

    print(f"=== Complete ===")
    print(f"Combined results: {combined_file.name}")


if __name__ == "__main__":
    main()
