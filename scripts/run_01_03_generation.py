#!/usr/bin/env python3
"""
Generate 1,000+ race scenarios for the Daytona 500 using calibrated priors.
This script executes Phase 01 Plan 03 objective.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Fix paths for imports
# Assuming running from project root
project_root = Path.cwd()
packages_path = project_root / "packages" / "axiomatic-sim" / "src"
backend_path = project_root / "apps" / "backend"

# Add paths to sys.path
sys.path.insert(0, str(packages_path))
sys.path.insert(0, str(backend_path))

# Configure logging to be more descriptive
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("01-03-Execution")

try:
    from app.ontology import OntologyDriver
    from app.config import get_settings
    from app.models import SessionLocal, Race, Driver
    from axiomatic_sim.ontology_constraints import OntologyConstraints
    from axiomatic_sim.scenario_generator import create_mock_cbn, SkeletonNarrative
    from axiomatic_sim.narrative import serialize_scenarios_to_parquet
    from app.kernel import KernelLogic
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

def run_generation():
    settings = get_settings()
    
    # 1. Initialize Ontology Connection
    logger.info("Initializing Neo4j Ontology connection...")
    ontology = OntologyDriver(
        uri=str(settings.NEO4J_URI),
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )
    
    # 2. Get target race (Daytona 500 ID 9)
    db = SessionLocal()
    try:
        # Find Daytona 500
        race = db.query(Race).filter(Race.name == "Daytona 500", Race.status == "scheduled").first()
        if not race:
            logger.error("Daytona 500 (scheduled) not found in database.")
            # Fallback to any scheduled race
            race = db.query(Race).filter(Race.status == "scheduled").first()
            if not race:
                logger.error("No scheduled races found. Seeding might be incomplete.")
                return
            
        logger.info(f"Targeting Race: {race.name} at {race.track} (Laps: {race.laps})")
        
        # 3. Setup Constraints and CBN
        # Use live ontology driver for constraints to get calibrated skill priors
        ontology_constraints = OntologyConstraints(ontology_driver=ontology)
        
        # Get all drivers to participate in the race
        drivers = db.query(Driver).all()
        driver_ids = [str(d.id) for d in drivers]
        logger.info(f"Loaded {len(driver_ids)} drivers for simulation")
        
        # Create mock CBN (placeholder for structural learning in Phase 2)
        # It uses the ontology_constraints to set driver-specific priors
        logger.info("Initializing Causal Bayesian Network (CBN) with calibrated priors...")
        cbn = create_mock_cbn(ontology_constraints, driver_ids)
        
        # 4. Initialize Generator
        logger.info("Initializing Skeleton Narrative Generator...")
        kernel = KernelLogic(field_size=len(driver_ids))
        
        generator = SkeletonNarrative(
            cbn=cbn,
            ontology_constraints=ontology_constraints,
            track_id=race.track,
            field_size=len(driver_ids),
            kernel=kernel,
            race_length=race.laps
        )
        
        # 5. Generate 1,000 Scenarios
        n_scenarios = 1000
        logger.info(f"Generating {n_scenarios} scenarios. This may take a moment...")
        start_time = datetime.now()
        scenarios = generator.generate_scenarios(n_scenarios=n_scenarios)
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Successfully generated {len(scenarios)} valid scenarios in {duration:.2f}s.")
        
        # 6. Save to Parquet for downstream use (Optimizer/Analytics)
        output_dir = project_root / "data" / "scenarios"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"race_{race.id}_scenarios.parquet"
        
        logger.info(f"Serializing {len(scenarios)} scenarios to {output_path}...")
        serialize_scenarios_to_parquet(scenarios, str(output_path))
        logger.info("Generation and serialization complete.")
        
        # 7. Print summary of one scenario for verification
        if scenarios:
            s_obj = scenarios[0]
            logger.info("--- Sample Scenario Summary ---")
            logger.info(f"ID: {s_obj.scenario_id}")
            logger.info(f"Regime: {s_obj.regime.n_cautions} cautions, Strategy: {s_obj.regime.pit_strategy.value}")
            logger.info(f"Conservation: Laps Led={s_obj.conservation_metadata.total_laps_led}/{race.laps}")
            
    except Exception as e:
        logger.exception(f"An error occurred during generation: {e}")
    finally:
        db.close()
        ontology.close()

if __name__ == "__main__":
    run_generation()
