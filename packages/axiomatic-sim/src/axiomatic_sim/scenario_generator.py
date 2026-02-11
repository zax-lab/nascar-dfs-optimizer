"""
Skeleton Narrative scenario generator using CBN sampling.

This module provides the core scenario generation engine that produces
mechanically plausible race outcomes by combining:
- Causal Bayesian Networks for driver outcome sampling
- State space simulation for race-flow dynamics
- Feasible-by-design conservation constraints
- Kernel post-validation for final verification

The Skeleton Narrative concept treats races as mostly quiet (coarse granularity)
until something happens (incident/caution triggers fine granularity).
"""
import logging
import uuid
from dataclasses import replace
from typing import Dict, List, Optional, Any
import networkx as nx

# Try to import JAX for performance
try:
    import jax.numpy as jnp
    import jax.random as random
    from jax import vmap, jit
    JAX_AVAILABLE = True
except ImportError:
    # Fallback to numpy
    import numpy as jnp
    import numpy.random as random
    JAX_AVAILABLE = False
    # Dummy vmap and jit for numpy fallback
    def vmap(func):
        def wrapper(*args, **kwargs):
            return [func(*[arg[i] if isinstance(arg, (list, jnp.ndarray)) else arg
                         for i in range(len(args[0]))]) for arg in args]
        return wrapper
    def jit(func):
        return func

# Import from prior plans
from axiomatic_sim.cbn import CausalBayesianNetwork, create_cbn_variables
from axiomatic_sim.ontology_constraints import OntologyConstraints
from axiomatic_sim.state_space import RaceState, RaceSegment, DriverState
from axiomatic_sim.transitions import (
    green_flag_transition,
    caution_transition,
    pit_cycle_transition,
)

# Import narrative types
from axiomatic_sim.narrative import (
    RaceFlowRegime,
    ScenarioComponents,
    DriverOutcome,
    ConservationMetadata,
    PitStrategy,
)

# Import kernel for post-validation
try:
    from apps.backend.app.kernel import KernelLogic
except ImportError:
    try:
        # Try relative import for package usage
        from app.kernel import KernelLogic
    except ImportError:
        KernelLogic = None

# Import ConstraintSpec for compiled constraints
try:
    from apps.backend.app.constraints.models import ConstraintSpec
    ConstraintSpecAvailable = True
except ImportError:
    try:
        from app.constraints.models import ConstraintSpec
        ConstraintSpecAvailable = True
    except ImportError:
        ConstraintSpecAvailable = False
        ConstraintSpec = None

logger = logging.getLogger(__name__)


def create_mock_cbn(
    ontology_constraints: OntologyConstraints,
    driver_ids: List[str]
) -> CausalBayesianNetwork:
    """
    Create mock CBN with fixed priors for scenario generation.

    This function creates a fixed CBN structure with hardcoded edges
    reflecting domain knowledge about causal relationships in NASCAR racing.
    The CBN is parameterized with fixed priors from the ontology constraints.

    Args:
        ontology_constraints: OntologyConstraints instance for driver priors
        driver_ids: List of driver identifiers

    Returns:
        CausalBayesianNetwork instance with fixed structure and priors

    Example:
        >>> ontology = OntologyConstraints()
        >>> driver_ids = ["driver_123", "driver_456"]
        >>> cbn = create_mock_cbn(ontology, driver_ids)
        >>> isinstance(cbn, CausalBayesianNetwork)
        True
    """
    logger.info(f"Creating mock CBN for {len(driver_ids)} drivers")

    # Create fixed CBN structure with hardcoded edges
    structure = nx.DiGraph()

    # Add nodes for each driver
    for driver_id in driver_ids:
        # Latent variables
        structure.add_node(f"{driver_id}_skill")
        structure.add_node(f"{driver_id}_aggression")
        structure.add_node(f"{driver_id}_shadow_risk")

        # Outcome variables
        structure.add_node(f"{driver_id}_laps_led")
        structure.add_node(f"{driver_id}_fastest_laps")
        structure.add_node(f"{driver_id}_finish_position")
        structure.add_node(f"{driver_id}_incident")

        # Add hardcoded causal edges based on domain knowledge
        # skill -> laps_led (skilled drivers lead more laps)
        structure.add_edge(f"{driver_id}_skill", f"{driver_id}_laps_led")

        # skill -> fastest_laps (skilled drivers record more fastest laps)
        structure.add_edge(f"{driver_id}_skill", f"{driver_id}_fastest_laps")

        # aggression -> incidents (aggressive drivers have more incidents)
        structure.add_edge(f"{driver_id}_aggression", f"{driver_id}_incident")

        # shadow_risk -> incident (high shadow risk increases incident probability)
        structure.add_edge(f"{driver_id}_shadow_risk", f"{driver_id}_incident")

        # skill -> finish_position (skilled drivers finish better, inverse relationship)
        structure.add_edge(f"{driver_id}_skill", f"{driver_id}_finish_position")

    # Add global variables
    structure.add_node("track_difficulty")
    structure.add_node("caution_occurred")

    # Connect track_difficulty to all drivers' outcomes
    for driver_id in driver_ids:
        structure.add_edge("track_difficulty", f"{driver_id}_finish_position")
        structure.add_edge("track_difficulty", f"{driver_id}_incident")

    # Connect caution_occurred to all incidents
    for driver_id in driver_ids:
        structure.add_edge("caution_occurred", f"{driver_id}_incident")

    logger.info(
        f"Created fixed CBN structure: {len(structure.nodes)} nodes, "
        f"{len(structure.edges)} edges"
    )

    # Create CBN instance
    cbn = CausalBayesianNetwork(structure, ontology_constraints)

    # Set fixed priors from ontology constraints
    priors = {}
    for driver_id in driver_ids:
        driver_priors = ontology_constraints.get_driver_priors(driver_id)
        priors.update(driver_priors)

    # Note: Parameter learning is skipped for mock CBN
    # In Phase 2, we'll learn CPDs from historical data
    logger.info(f"Mock CBN created with {len(priors)} priors from ontology")

    return cbn


class SkeletonNarrative:
    """
    Skeleton Narrative scenario generator with CBN-conditioned sampling.

    This class generates race scenarios by:
    1. Sampling race-flow regimes (cautions, pit strategy, fuel risk)
    2. Simulating race using state space transitions
    3. Sampling driver outcomes from CBN conditioned on regime
    4. Applying feasible-by-design conservation (Dirichlet sampling)
    5. Post-validating with kernel conservation validation

    The hybrid granularity approach uses fine granularity for key segments
    (cautions, pit cycles, late race) and coarse granularity for green flag runs.
    """

    def __init__(
        self,
        cbn: CausalBayesianNetwork,
        ontology_constraints: OntologyConstraints,
        track_id: str,
        field_size: int = 40,
        kernel: Optional['KernelLogic'] = None,
        race_length: int = 200,
        constraint_spec: Optional['ConstraintSpec'] = None,
    ):
        """
        Initialize SkeletonNarrative generator.

        Args:
            cbn: Trained CausalBayesianNetwork for outcome sampling
            ontology_constraints: OntologyConstraints for track/driver priors
            track_id: Track identifier for this race
            field_size: Number of drivers in the race (default: 40)
            kernel: Optional KernelLogic for post-validation
            race_length: Total laps in the race (default: 200)
            constraint_spec: Optional compiled ConstraintSpec (replaces live Neo4j queries)
        """
        self.cbn = cbn
        self.ontology_constraints = ontology_constraints
        self.track_id = track_id
        self.field_size = field_size
        self.kernel = kernel
        self.race_length = race_length
        self.constraint_spec = constraint_spec

        # Fetch track difficulty from constraint spec or ontology
        if constraint_spec is not None and track_id in constraint_spec.tracks:
            track_constraints = constraint_spec.tracks[track_id]
            self.track_difficulty = track_constraints.difficulty
            logger.info(f"Using compiled constraint spec for track {track_id} (difficulty={track_constraints.difficulty})")
        else:
            self.track_difficulty = ontology_constraints._track_difficulty_cache.get(
                track_id, 0.5
            )
            if constraint_spec is not None:
                logger.warning(f"Constraint spec provided but track {track_id} not found, using ontology cache")
            else:
                logger.info(f"Using live ontology queries for track {track_id}")

        # Get driver IDs from constraint spec or CBN structure
        self.driver_ids = self._extract_driver_ids()

        # Initialize random seed for reproducibility
        self.random_seed = 42

        # Initialize random key counter for JAX
        self._random_key_counter = 100

        logger.info(
            f"Initialized SkeletonNarrative for track {track_id} "
            f"with {len(self.driver_ids)} drivers"
        )

    def _get_random_key(self):
        """Get a new JAX random key or increment counter for reproducibility."""
        if JAX_AVAILABLE:
            key = random.PRNGKey(self.random_seed + self._random_key_counter)
            self._random_key_counter += 1
            return key
        else:
            return None

    def _random_uniform(self):
        """Generate a random uniform float in [0, 1)."""
        if JAX_AVAILABLE:
            key = self._get_random_key()
            return float(random.uniform(key, (), minval=0.0, maxval=1.0))
        else:
            return float(random.random())

    def _random_randint(self, low, high=None):
        """Generate a random integer in [low, high) or [0, low)."""
        if JAX_AVAILABLE:
            key = self._get_random_key()
            if high is None:
                # JAX randint uses (key, shape, minval, maxval)
                return int(random.randint(key, (), 0, low))
            else:
                # Return integer in [low, high)
                return int(random.randint(key, (), low, high))
        else:
            if high is None:
                return int(random.randint(0, low))
            else:
                return int(random.randint(low, high))

    def _extract_driver_ids(self) -> List[str]:
        """Extract driver IDs from constraint spec or CBN variable names.

        If constraint_spec is provided, extracts driver_ids from spec.drivers.keys().
        Otherwise, handles compound driver IDs like 'driver_1' from variables like
        'driver_1_skill' by removing the suffix.
        """
        # If constraint spec provided, extract from spec
        if self.constraint_spec is not None and len(self.constraint_spec.drivers) > 0:
            driver_ids = list(self.constraint_spec.drivers.keys())
            logger.info(f"Extracted {len(driver_ids)} driver IDs from constraint spec")
            return driver_ids

        # Fallback to CBN structure extraction
        driver_ids = set()
        for var in self.cbn.structure.nodes():
            if "_skill" in var:
                # Remove '_skill' suffix to get driver ID
                driver_id = var.replace("_skill", "")
                driver_ids.add(driver_id)
            elif "_laps_led" in var:
                # Remove '_laps_led' suffix to get driver ID
                driver_id = var.replace("_laps_led", "")
                driver_ids.add(driver_id)

        logger.info(f"Extracted {len(driver_ids)} driver IDs from CBN structure")
        return list(driver_ids)

    def sample_race_flow_regime(self) -> RaceFlowRegime:
        """
        Sample race-flow regime from track-specific distributions.

        Samples the macro-level pattern of how the race unfolds:
        - Number of cautions (Poisson distribution)
        - Pit strategy pattern (categorical distribution)
        - Fuel window risk (Beta distribution)
        - Late race chaos probability (Beta distribution)

        If constraint_spec is provided, uses caution_rate from TrackConstraints.
        Otherwise, uses track_difficulty cache from ontology.

        Returns:
            RaceFlowRegime with sampled parameters
        """
        # Sample n_cautions from Poisson distribution
        # Use constraint_spec caution_rate if available
        if self.constraint_spec is not None and self.track_id in self.constraint_spec.tracks:
            track_constraints = self.constraint_spec.tracks[self.track_id]
            # Use caution_rate from constraint spec (expected cautions per lap)
            # Convert to lambda for Poisson: lambda = caution_rate * race_length
            lambda_cautions = track_constraints.caution_rate * self.race_length
        else:
            # Fallback to track_difficulty-based lambda
            lambda_cautions = 3.0 * self.track_difficulty

        # Sample n_cautions from Poisson distribution
        if JAX_AVAILABLE:
            n_cautions = int(random.poisson(random.PRNGKey(self.random_seed + 10), lambda_cautions))
        else:
            n_cautions = int(random.poisson(lambda_cautions))
        n_cautions = max(0, min(n_cautions, 10))  # Bound to [0, 10]

        # Sample pit_strategy from categorical distribution
        # Track difficulty influences strategy distribution
        if self.track_difficulty > 0.7:
            # High difficulty tracks favor conservative strategy
            pit_strategy_probs = [0.2, 0.5, 0.3]  # [AGGRESSIVE, STANDARD, CONSERVATIVE]
        elif self.track_difficulty < 0.3:
            # Easy tracks allow aggressive strategy
            pit_strategy_probs = [0.4, 0.4, 0.2]
        else:
            # Intermediate tracks have balanced strategy
            pit_strategy_probs = [0.3, 0.5, 0.2]

        # Sample pit_strategy from categorical distribution
        if JAX_AVAILABLE:
            pit_strategy_idx = int(random.choice(random.PRNGKey(self.random_seed + 11), 3, p=jnp.array(pit_strategy_probs)))
        else:
            pit_strategy_idx = int(random.choice(3, p=pit_strategy_probs))
        pit_strategy = [PitStrategy.AGGRESSIVE, PitStrategy.STANDARD, PitStrategy.CONSERVATIVE][pit_strategy_idx]

        # Sample fuel_window_risk from Beta distribution
        # Higher difficulty tracks have higher fuel mileage race risk
        fuel_alpha = 2.0 * self.track_difficulty
        fuel_beta = 5.0
        if JAX_AVAILABLE:
            fuel_window_risk = float(random.beta(random.PRNGKey(self.random_seed + 12), fuel_alpha, fuel_beta))
        else:
            fuel_window_risk = float(random.beta(fuel_alpha, fuel_beta))
        fuel_window_risk = max(0.0, min(fuel_window_risk, 1.0))

        # Sample late_race_chaos from Beta distribution
        chaos_alpha = 3.0
        chaos_beta = 7.0
        if JAX_AVAILABLE:
            late_race_chaos = float(random.beta(random.PRNGKey(self.random_seed + 13), chaos_alpha, chaos_beta))
        else:
            late_race_chaos = float(random.beta(chaos_alpha, chaos_beta))
        late_race_chaos = max(0.0, min(late_race_chaos, 1.0))

        regime = RaceFlowRegime(
            n_cautions=n_cautions,
            pit_strategy=pit_strategy,
            fuel_window_risk=fuel_window_risk,
            late_race_chaos=late_race_chaos,
        )

        logger.debug(
            f"Sampled regime: {n_cautions} cautions, {pit_strategy.value}, "
            f"fuel_risk={fuel_window_risk:.2f}, chaos={late_race_chaos:.2f}"
        )

        return regime

    def _sample_feasible_laps_led(self, n_drivers: int) -> List[int]:
        """
        Sample laps_led using Dirichlet distribution for conservation.

        This feasible-by-design approach ensures sum(laps_led) = race_length
        by sampling from a Dirichlet distribution and scaling.

        Args:
            n_drivers: Number of drivers

        Returns:
            List of laps_led values summing to race_length
        """
        if JAX_AVAILABLE:
            # Use JAX for efficient Dirichlet sampling
            key = random.PRNGKey(self.random_seed)
            alpha = jnp.ones(n_drivers)
            proportions = random.dirichlet(key, alpha)
            laps_led = (proportions * self.race_length).astype(int)

            # Handle rounding error
            remainder = self.race_length - int(jnp.sum(laps_led))
            if remainder > 0:
                # Add remainder to driver with most laps
                max_idx = int(jnp.argmax(laps_led))
                laps_led = laps_led.at[max_idx].add(remainder)
        else:
            # NumPy fallback
            alpha = [1.0] * n_drivers
            proportions = random.dirichlet(alpha)
            laps_led = (proportions * self.race_length).astype(int)

            # Handle rounding error
            remainder = self.race_length - int(jnp.sum(laps_led))
            if remainder > 0:
                max_idx = int(jnp.argmax(laps_led))
                laps_led[max_idx] += remainder

        return laps_led.tolist()

    def _sample_feasible_fastest_laps(self, green_flag_laps: int, n_drivers: int) -> List[int]:
        """
        Sample fastest_laps using Dirichlet distribution for conservation.

        Ensures sum(fastest_laps) ≤ green_flag_laps by sampling proportions
        and scaling. Uses 80% of green flag laps as expected total to allow
        some laps without a clear fastest driver.

        Args:
            green_flag_laps: Total green flag laps in the race
            n_drivers: Number of drivers

        Returns:
            List of fastest_laps values summing to ≤ green_flag_laps
        """
        target_total = int(green_flag_laps * 0.8)

        if JAX_AVAILABLE:
            key = random.PRNGKey(self.random_seed + 1)
            alpha = jnp.ones(n_drivers)
            proportions = random.dirichlet(key, alpha)
            fastest_laps = (proportions * target_total).astype(int)

            remainder = target_total - int(jnp.sum(fastest_laps))
            if remainder > 0:
                max_idx = int(jnp.argmax(fastest_laps))
                fastest_laps = fastest_laps.at[max_idx].add(remainder)
        else:
            alpha = [1.0] * n_drivers
            proportions = random.dirichlet(alpha)
            fastest_laps = (proportions * target_total).astype(int)

            remainder = target_total - int(jnp.sum(fastest_laps))
            if remainder > 0:
                max_idx = int(jnp.argmax(fastest_laps))
                fastest_laps[max_idx] += remainder

        return fastest_laps.tolist()

    def generate_single_scenario(self, scenario_id: str) -> ScenarioComponents:
        """
        Generate a single race scenario with CBN-conditioned outcomes.

        This method:
        1. Samples race-flow regime
        2. Initializes RaceState
        3. Simulates race using transitions (hybrid granularity)
        4. Samples driver outcomes from CBN conditioned on regime
        5. Applies feasible-by-design conservation (Dirichlet sampling)
        6. Returns ScenarioComponents (kernel validation happens post-generation)

        Args:
            scenario_id: Unique identifier for this scenario

        Returns:
            ScenarioComponents with driver outcomes and regime
        """
        # Step 1: Sample race-flow regime
        regime = self.sample_race_flow_regime()

        # Step 2: Initialize RaceState
        # Create initial driver states with starting positions
        initial_drivers = {}
        for i, driver_id in enumerate(self.driver_ids, start=1):
            initial_drivers[driver_id] = DriverState(
                position=i,
                fuel_level=1.0,
                tire_wear=1.0,
                laps_led=0,
                in_pit=False,
                dnf=False,
            )

        initial_state = RaceState(
            lap=1,
            race_length=self.race_length,
            segment=RaceSegment.GREEN_FLAG,
            drivers=initial_drivers,
            active_caution_laps=0,
        )

        # Step 3: Simulate race using state space transitions
        # CBN-conditioned outcome sampling for hybrid granularity simulation

        # Calculate green flag laps from regime
        estimated_caution_laps = regime.n_cautions * 5  # ~5 laps per caution
        green_flag_laps = self.race_length - estimated_caution_laps

        # Step 4: Sample driver outcomes from CBN conditioned on race-flow regime
        # Build evidence dict from race-flow regime
        evidence = {
            "n_cautions": regime.n_cautions,
            "pit_strategy": regime.pit_strategy.value,
            "fuel_window_risk": regime.fuel_window_risk,
            "late_race_chaos": regime.late_race_chaos,
            "track_difficulty": self.track_difficulty,
        }

        # Add driver skill priors to evidence
        for driver_id in self.driver_ids:
            driver_priors = self.ontology_constraints.get_driver_priors(driver_id)
            evidence.update(driver_priors)

        logger.info(
            f"Sampling outcomes for {len(self.driver_ids)} drivers "
            f"with evidence: {evidence}"
        )

        # Try CBN-conditioned outcome sampling
        try:
            if self.cbn is not None and len(self.cbn.model.get_cpds()) > 0:
                # Sample driver outcomes from CBN conditioned on regime
                all_outcomes = self.cbn.sample_outcomes(
                    n_samples=len(self.driver_ids),
                    evidence=evidence
                )
                logger.debug(f"CBN sampled outcomes shape: {all_outcomes.shape}")
                use_cbn = True
            else:
                logger.warning("CBN not initialized or no CPDs, using simplified generation")
                all_outcomes = None
                use_cbn = False
        except Exception as e:
            logger.warning(f"CBN sampling failed: {e}, falling back to simplified generation")
            all_outcomes = None
            use_cbn = False

        # Step 5: Create driver outcomes with feasible-by-design conservation
        if use_cbn and all_outcomes is not None and len(all_outcomes) > 0:
            # Extract driver-specific outcomes from CBN samples
            # Use CBN samples as priors for Dirichlet sampling to maintain conservation
            driver_outcomes = {}

            # First, collect CBN-sampled laps_led as concentration parameters
            cbn_laps_led = []
            for i, driver_id in enumerate(self.driver_ids):
                if i < len(all_outcomes):
                    # Try to get CBN-sampled laps_led for this driver
                    laps_led_col = f"{driver_id}_laps_led"
                    if laps_led_col in all_outcomes.columns:
                        cbn_laps_led.append(all_outcomes[laps_led_col].iloc[i])
                    else:
                        cbn_laps_led.append(1.0)  # Default prior
                else:
                    cbn_laps_led.append(1.0)

            # Use CBN samples as Dirichlet concentration parameters for conservation
            if JAX_AVAILABLE:
                key = random.PRNGKey(self.random_seed + 2)
                alpha = jnp.array(cbn_laps_led) + 1.0  # Add smoothing
                proportions = random.dirichlet(key, alpha)
                laps_led_list = (proportions * self.race_length).astype(int)
                remainder = self.race_length - int(jnp.sum(laps_led_list))
                if remainder > 0:
                    max_idx = int(jnp.argmax(laps_led_list))
                    laps_led_list = laps_led_list.at[max_idx].add(remainder)
            else:
                alpha = [l + 1.0 for l in cbn_laps_led]
                proportions = random.dirichlet(alpha)
                laps_led_list = (proportions * self.race_length).astype(int)
                remainder = self.race_length - int(jnp.sum(laps_led_list))
                if remainder > 0:
                    max_idx = int(jnp.argmax(laps_led_list))
                    laps_led_list[max_idx] += remainder

            fastest_laps_list = self._sample_feasible_fastest_laps(green_flag_laps, len(self.driver_ids))

            # Populate driver outcomes from CBN samples
            for i, driver_id in enumerate(self.driver_ids):
                if i < len(all_outcomes):
                    start_position = initial_drivers[driver_id].position

                    # Extract outcomes from CBN samples
                    incident_col = f"{driver_id}_incident"
                    finish_col = f"{driver_id}_finish_position"

                    incident = all_outcomes[incident_col].iloc[i] if incident_col in all_outcomes.columns else False

                    # Get finish position from CBN or generate
                    if finish_col in all_outcomes.columns:
                        finish_position = all_outcomes[finish_col].iloc[i]
                    else:
                        finish_position = i + 1

                    # Handle DNF
                    dnf_lap = None
                    if incident:
                        if self._random_uniform() < 0.3:
                            dnf_lap = self._random_randint(1, self.race_length + 1)
                        if dnf_lap:
                            finish_position = 40

                    place_differential = finish_position - start_position

                    driver_outcomes[driver_id] = DriverOutcome(
                        driver_id=driver_id,
                        laps_led=int(laps_led_list[i]),
                        fastest_laps=fastest_laps_list[i],
                        finish_position=finish_position,
                        place_differential=place_differential,
                        incident=bool(incident),
                        dnf_lap=dnf_lap,
                    )
                else:
                    # Fallback for missing samples
                    start_position = initial_drivers[driver_id].position
                    finish_position = i + 1
                    place_differential = finish_position - start_position

                    driver_outcomes[driver_id] = DriverOutcome(
                        driver_id=driver_id,
                        laps_led=int(laps_led_list[i]),
                        fastest_laps=fastest_laps_list[i],
                        finish_position=finish_position,
                        place_differential=place_differential,
                        incident=False,
                        dnf_lap=None,
                    )
        else:
            # Fallback to simplified outcome generation
            logger.debug("Using simplified outcome generation")
            laps_led_list = self._sample_feasible_laps_led(len(self.driver_ids))
            fastest_laps_list = self._sample_feasible_fastest_laps(green_flag_laps, len(self.driver_ids))

            # Sample finish positions (permutation with some randomness)
            finish_positions = list(range(1, len(self.driver_ids) + 1))
            # Shuffle based on regime chaos
            if regime.late_race_chaos > 0.5:
                if JAX_AVAILABLE:
                    key = self._get_random_key()
                    finish_positions = jnp.array(finish_positions)
                    finish_positions = random.permutation(key, finish_positions).tolist()
                else:
                    random.shuffle(finish_positions)

            # Create driver outcomes
            driver_outcomes = {}
            for i, driver_id in enumerate(self.driver_ids):
                # Get starting position from initial state
                start_position = initial_drivers[driver_id].position
                finish_position = finish_positions[i]
                place_differential = finish_position - start_position

                # Sample incident from regime chaos
                incident_prob = 0.05 + (regime.late_race_chaos * 0.1)
                incident = self._random_uniform() < incident_prob

                # DNF lap if incident
                dnf_lap = None
                if incident and self._random_uniform() < 0.3:  # 30% of incidents result in DNF
                    dnf_lap = self._random_randint(1, self.race_length + 1)
                    finish_position = 40  # DNF position
                    place_differential = 40 - start_position

                # If finish_position is 40 but no DNF lap, add one
                if finish_position == 40 and dnf_lap is None:
                    dnf_lap = self._random_randint(1, self.race_length + 1)
                    # Update incident to True since DNF implies incident
                    incident = True

                driver_outcomes[driver_id] = DriverOutcome(
                    driver_id=driver_id,
                    laps_led=laps_led_list[i],
                    fastest_laps=fastest_laps_list[i],
                    finish_position=finish_position,
                    place_differential=place_differential,
                    incident=incident,
                    dnf_lap=dnf_lap,
                )

        # Step 5: Create conservation metadata (will be populated by kernel)
        total_laps_led = sum(laps_led_list)
        total_fastest_laps = sum(fastest_laps_list)

        conservation_metadata = ConservationMetadata(
            total_laps_led=total_laps_led,
            total_fastest_laps=total_fastest_laps,
            green_flag_laps=green_flag_laps,
            validation_passed=True,  # Placeholder, kernel will validate
            veto_reasons=[],
        )

        # Step 6: Create scenario
        scenario = ScenarioComponents(
            scenario_id=scenario_id,
            regime=regime,
            driver_outcomes=driver_outcomes,
            conservation_metadata=conservation_metadata,
        )

        logger.debug(f"Generated scenario {scenario_id} with {len(driver_outcomes)} drivers")

        return scenario

    def generate_scenarios(self, n_scenarios: int = 1000) -> List[ScenarioComponents]:
        """
        Generate multiple scenarios with kernel conservation validation.

        This method:
        1. Generates n_scenarios scenarios
        2. Validates each scenario with kernel (if provided)
        3. Filters out scenarios that fail conservation validation
        4. Re-samples until we have n_scenarios valid scenarios

        Args:
            n_scenarios: Number of valid scenarios to generate

        Returns:
            List of valid ScenarioComponents
        """
        logger.info(f"Generating {n_scenarios} scenarios for track {self.track_id}")

        valid_scenarios = []
        max_attempts = n_scenarios * 3  # Allow 3x attempts to account for rejections
        attempt = 0

        while len(valid_scenarios) < n_scenarios and attempt < max_attempts:
            # Generate scenario
            scenario_id = f"scenario_{self.track_id}_{uuid.uuid4().hex[:8]}"
            scenario = self.generate_single_scenario(scenario_id)

            # Kernel post-validation
            if self.kernel is not None:
                # Convert scenario to dict format for kernel
                scenario_dict = self._scenario_to_dict(scenario)

                # Validate with kernel
                validation_result = self.kernel.validate_dominator_conservation(scenario_dict)

                # Populate conservation metadata from validation result
                conservation_metadata = ConservationMetadata(
                    total_laps_led=scenario_dict['total_laps_led'],
                    total_fastest_laps=scenario_dict['total_fastest_laps'],
                    green_flag_laps=scenario_dict['green_flag_laps'],
                    validation_passed=validation_result.is_valid,
                    veto_reasons=validation_result.veto_reasons,
                )

                # Update scenario with validated metadata
                scenario = replace(scenario, conservation_metadata=conservation_metadata)

                # Keep only valid scenarios
                if validation_result.is_valid:
                    valid_scenarios.append(scenario)
                else:
                    logger.debug(
                        f"Scenario {scenario_id} rejected: {validation_result.veto_reasons}"
                    )
            else:
                # No kernel provided, accept all scenarios
                valid_scenarios.append(scenario)

            attempt += 1

            # Log progress every 100 scenarios
            if attempt % 100 == 0:
                logger.info(
                    f"Generated {len(valid_scenarios)}/{n_scenarios} valid scenarios "
                    f"({attempt} attempts)"
                )

        logger.info(
            f"Generated {len(valid_scenarios)} valid scenarios in {attempt} attempts"
        )

        return valid_scenarios[:n_scenarios]

    def _scenario_to_dict(self, scenario: ScenarioComponents) -> Dict[str, Any]:
        """
        Convert ScenarioComponents to dict format for kernel validation.

        Args:
            scenario: ScenarioComponents to convert

        Returns:
            Dictionary with format expected by kernel.validate_dominator_conservation
        """
        laps_led = []
        fastest_laps = []
        start_positions = []
        finish_positions = []

        for driver_id in sorted(scenario.driver_outcomes.keys()):
            outcome = scenario.driver_outcomes[driver_id]
            laps_led.append(outcome.laps_led)
            fastest_laps.append(outcome.fastest_laps)
            # Infer start position from finish position and place differential
            start_position = outcome.finish_position - outcome.place_differential
            start_positions.append(start_position)
            finish_positions.append(outcome.finish_position)

        return {
            'laps_led': laps_led,
            'fastest_laps': fastest_laps,
            'start_positions': start_positions,
            'finish_positions': finish_positions,
            'race_length': self.race_length,
            'green_flag_laps': scenario.conservation_metadata.green_flag_laps,
            'total_laps_led': scenario.conservation_metadata.total_laps_led,
            'total_fastest_laps': scenario.conservation_metadata.total_fastest_laps,
        }


def generate_scenarios_with_constraints(
    constraint_spec: 'ConstraintSpec',
    track_id: str,
    n_scenarios: int = 1000,
    kernel: Optional['KernelLogic'] = None,
    random_seed: int = 42,
) -> List[ScenarioComponents]:
    """
    Generate scenarios using compiled ConstraintSpec.

    This function creates a SkeletonNarrative with the provided constraint_spec
    and generates scenarios. Returns scenarios along with rejection statistics
    from kernel validation.

    Args:
        constraint_spec: Compiled ConstraintSpec with driver and track constraints
        track_id: Track identifier for the race
        n_scenarios: Number of scenarios to generate (default: 1000)
        kernel: Optional KernelLogic for post-validation
        random_seed: Random seed for reproducibility (default: 42)

    Returns:
        List of ScenarioComponents (valid scenarios only)

    Example:
        >>> from app.constraints.models import ConstraintSpec, DriverConstraints, TrackConstraints
        >>> spec = ConstraintSpec(...)
        >>> scenarios = generate_scenarios_with_constraints(
        ...     constraint_spec=spec,
        ...     track_id="daytona",
        ...     n_scenarios=100,
        ...     kernel=KernelLogic(field_size=40)
        ... )
        >>> len(scenarios)
        100
    """
    logger.info(f"Generating {n_scenarios} scenarios with compiled constraints for track {track_id}")

    # Create ontology constraints (will use constraint_spec internally)
    ontology_constraints = OntologyConstraints(None)

    # Extract driver IDs from constraint spec
    driver_ids = list(constraint_spec.drivers.keys())

    # Create mock CBN
    cbn = create_mock_cbn(ontology_constraints, driver_ids)

    # Instantiate SkeletonNarrative with constraint_spec
    generator = SkeletonNarrative(
        cbn=cbn,
        ontology_constraints=ontology_constraints,
        track_id=track_id,
        field_size=len(driver_ids),
        kernel=kernel,
        constraint_spec=constraint_spec,
    )

    # Generate scenarios
    scenarios = generator.generate_scenarios(n_scenarios)

    logger.info(f"Generated {len(scenarios)} scenarios with compiled constraints")

    return scenarios


def generate_scenarios(
    track_id: str,
    n_scenarios: int = 1000,
    ontology_driver: Optional[Any] = None,
    kernel: Optional['KernelLogic'] = None,
    driver_ids: Optional[List[str]] = None,
    constraint_spec: Optional['ConstraintSpec'] = None,
) -> List[ScenarioComponents]:
    """
    Standalone function to generate race scenarios.

    This is a convenience function that creates all necessary components
    and generates scenarios. Useful for quick scenario generation without
    manually setting up the SkeletonNarrative class.

    Args:
        track_id: Track identifier for the race
        n_scenarios: Number of scenarios to generate (default: 1000)
        ontology_driver: Optional OntologyDriver instance
        kernel: Optional KernelLogic for post-validation
        driver_ids: Optional list of driver IDs (defaults to 40 mock drivers)
        constraint_spec: Optional compiled ConstraintSpec (replaces live Neo4j queries)

    Returns:
        List of ScenarioComponents

    Example:
        >>> scenarios = generate_scenarios(
        ...     track_id="daytona",
        ...     n_scenarios=100,
        ...     kernel=KernelLogic(field_size=40)
        ... )
        >>> len(scenarios)
        100
    """
    logger.info(f"Generating {n_scenarios} scenarios for track {track_id}")

    # Create ontology constraints
    ontology_constraints = OntologyConstraints(ontology_driver)

    # Use mock driver IDs if not provided
    if driver_ids is None:
        if constraint_spec is not None and len(constraint_spec.drivers) > 0:
            driver_ids = list(constraint_spec.drivers.keys())
        else:
            driver_ids = [f"driver_{i}" for i in range(1, 41)]

    # Create mock CBN
    cbn = create_mock_cbn(ontology_constraints, driver_ids)

    # Instantiate SkeletonNarrative
    generator = SkeletonNarrative(
        cbn=cbn,
        ontology_constraints=ontology_constraints,
        track_id=track_id,
        field_size=len(driver_ids),
        kernel=kernel,
        constraint_spec=constraint_spec,
    )

    # Generate scenarios
    scenarios = generator.generate_scenarios(n_scenarios)

    logger.info(f"Generated {len(scenarios)} scenarios")

    return scenarios
