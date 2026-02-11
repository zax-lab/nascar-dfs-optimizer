"""
Integration Testing and Deployment Verification System for NASCAR DFS Optimizer

This module provides comprehensive integration testing and deployment verification
for the NASCAR DFS optimizer with axiomatic AI framework. It tests all components
individually and together, ensuring the system is production-ready.

Testing Methodology:
- Unit-level integration tests for each component
- End-to-end pipeline tests verifying complete workflow
- Deployment readiness checks for production
- Fast, reliable tests that complete in <5 minutes
- Detailed reporting with timestamps and error messages
"""

import sys
import os
import importlib
import subprocess
import time
import logging
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('integration_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
TEST_TIMEOUT = 300  # 5 minutes in seconds
SAMPLE_RACE_SIZE = 5  # Number of sample races
SAMPLE_DRIVER_SIZE = 10  # Number of sample drivers
SAMPLE_SIMULATION_ITERATIONS = 100  # Reduced for fast testing

# Required dependencies
REQUIRED_DEPENDENCIES = {
    'fastapi': '0.100.0',
    'sqlalchemy': '2.0.0',
    'pulp': '2.7.0',
    'numpy': '1.24.0',
    'pandas': '2.0.0',
    'streamlit': '1.28.0',
    'plotly': '5.18.0',
    'matplotlib': '3.7.0'
}

# Required environment variables (optional for MVP)
REQUIRED_ENV_VARS = {
    'DATABASE_URL': False,  # Optional, defaults to SQLite
    'SPORTSDATAIO_API_KEY': False,  # Optional for MVP
    'NEO4J_URI': False,  # Optional for MVP
    'NEO4J_USER': False,  # Optional for MVP
    'NEO4J_PASSWORD': False  # Optional for MVP
}


class IntegrationTestSuite:
    """
    Comprehensive integration test suite for NASCAR DFS optimizer components.
    
    Tests all P0 components individually and together:
    - Models (database schema and ORM)
    - Monte Carlo Simulator
    - Belief Projector
    - Optimizer
    - Dashboard
    - Backtest
    - End-to-end pipeline
    """
    
    def __init__(self):
        """Initialize the integration test suite."""
        self.test_results = []
        self.start_time = None
        self.test_data = {}
        logger.info("IntegrationTestSuite initialized")
    
    def test_database_connection(self) -> bool:
        """
        Test database connection and schema verification.
        
        Returns:
            bool: True if database connection and schema are valid
        """
        test_name = "Database Connection"
        start_time = time.time()
        
        try:
            logger.info(f"Testing {test_name}...")
            
            # Try to import database models
            sys.path.insert(0, os.path.join(os.getcwd(), 'apps', 'backend'))
            from app.models import Base, engine, SessionLocal
            
            # Test database connection
            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
            
            # Test schema by checking tables exist
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            if len(tables) > 0:
                duration = time.time() - start_time
                self.log_test_result(test_name, True, f"Connected successfully. Tables: {tables}", duration)
                return True
            else:
                duration = time.time() - start_time
                self.log_test_result(test_name, False, "No tables found in database", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Database connection failed: {str(e)}"
            logger.error(error_msg)
            self.log_test_result(test_name, False, error_msg, duration)
            return False
    
    def test_models_creation(self) -> bool:
        """
        Test all models can be created and instantiated.
        
        Returns:
            bool: True if all models can be created successfully
        """
        test_name = "Models Creation"
        start_time = time.time()
        
        try:
            logger.info(f"Testing {test_name}...")
            
            # Import models
            sys.path.insert(0, os.path.join(os.getcwd(), 'apps', 'backend'))
            from app.models import Race, Driver, SimulationResult, Projection, Lineup
            
            # Test model instantiation
            test_race = Race(
                track_name="Daytona",
                race_date=datetime.now(),
                race_id="test_race_001"
            )
            
            test_driver = Driver(
                driver_name="Test Driver",
                driver_id="test_driver_001",
                team="Test Team",
                average_finish_position=10.5,
                win_rate=0.15
            )
            
            test_simulation = SimulationResult(
                race_id="test_race_001",
                driver_id="test_driver_001",
                simulation_id="test_sim_001",
                finish_position=5,
                points=150
            )
            
            test_projection = Projection(
                race_id="test_race_001",
                driver_id="test_driver_001",
                projected_points=45.5,
                projected_finish_position=8,
                confidence=0.85
            )
            
            test_lineup = Lineup(
                lineup_id="test_lineup_001",
                race_id="test_race_001",
                lineup_data={"drivers": ["d1", "d2", "d3", "d4", "d5", "d6"]},
                total_projected_points=250.5,
                salary=50000
            )
            
            duration = time.time() - start_time
            self.log_test_result(test_name, True, "All models created successfully", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Models creation failed: {str(e)}"
            logger.error(error_msg)
            self.log_test_result(test_name, False, error_msg, duration)
            return False
    
    def test_mc_simulator(self) -> bool:
        """
        Test Monte Carlo simulator with sample data.
        
        Returns:
            bool: True if MC simulator runs successfully
        """
        test_name = "Monte Carlo Simulator"
        start_time = time.time()
        
        try:
            logger.info(f"Testing {test_name}...")
            
            # Import MC simulator
            sys.path.insert(0, os.getcwd())
            import mc_sim
            
            # Create sample data
            sample_drivers = self.create_sample_driver_data()
            
            # Run a small simulation
            results = mc_sim.run_simulation(
                drivers=sample_drivers,
                num_iterations=SAMPLE_SIMULATION_ITERATIONS,
                race_id="test_race_001"
            )
            
            # Verify results
            if results and len(results) > 0:
                duration = time.time() - start_time
                self.log_test_result(test_name, True, f"Simulation completed with {len(results)} results", duration)
                self.test_data['simulation_results'] = results
                return True
            else:
                duration = time.time() - start_time
                self.log_test_result(test_name, False, "Simulation returned no results", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"MC simulator failed: {str(e)}"
            logger.error(error_msg)
            self.log_test_result(test_name, False, error_msg, duration)
            return False
    
    def test_belief_projector(self) -> bool:
        """
        Test belief projection with sample data.
        
        Returns:
            bool: True if belief projector runs successfully
        """
        test_name = "Belief Projector"
        start_time = time.time()
        
        try:
            logger.info(f"Testing {test_name}...")
            
            # Import projector
            sys.path.insert(0, os.getcwd())
            import projector
            
            # Create sample belief data
            sample_beliefs = self.create_sample_belief_data()
            
            # Run projection
            projections = projector.project_beliefs(
                beliefs=sample_beliefs,
                race_id="test_race_001"
            )
            
            # Verify projections
            if projections and len(projections) > 0:
                duration = time.time() - start_time
                self.log_test_result(test_name, True, f"Projection completed with {len(projections)} projections", duration)
                self.test_data['projections'] = projections
                return True
            else:
                duration = time.time() - start_time
                self.log_test_result(test_name, False, "Projection returned no results", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Belief projector failed: {str(e)}"
            logger.error(error_msg)
            self.log_test_result(test_name, False, error_msg, duration)
            return False
    
    def test_optimizer(self) -> bool:
        """
        Test optimizer with sample data.
        
        Returns:
            bool: True if optimizer runs successfully
        """
        test_name = "Optimizer"
        start_time = time.time()
        
        try:
            logger.info(f"Testing {test_name}...")
            
            # Import optimizer
            sys.path.insert(0, os.path.join(os.getcwd(), 'apps', 'backend'))
            from app.optimizer import Optimizer
            
            # Create sample projections
            sample_projections = self.create_sample_driver_data()
            
            # Initialize and run optimizer
            optimizer = Optimizer()
            lineups = optimizer.optimize(
                projections=sample_projections,
                salary_cap=50000,
                num_lineups=3
            )
            
            # Verify lineups
            if lineups and len(lineups) > 0:
                duration = time.time() - start_time
                self.log_test_result(test_name, True, f"Optimization completed with {len(lineups)} lineups", duration)
                self.test_data['lineups'] = lineups
                return True
            else:
                duration = time.time() - start_time
                self.log_test_result(test_name, False, "Optimization returned no lineups", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Optimizer failed: {str(e)}"
            logger.error(error_msg)
            self.log_test_result(test_name, False, error_msg, duration)
            return False
    
    def test_dashboard_imports(self) -> bool:
        """
        Test dashboard can import all components.
        
        Returns:
            bool: True if dashboard imports are successful
        """
        test_name = "Dashboard Imports"
        start_time = time.time()
        
        try:
            logger.info(f"Testing {test_name}...")
            
            # Try to import dashboard
            sys.path.insert(0, os.getcwd())
            import dashboard
            
            # Check if dashboard has required components
            required_components = ['main', 'display_lineups', 'display_projections']
            has_components = all(hasattr(dashboard, comp) for comp in required_components)
            
            if has_components:
                duration = time.time() - start_time
                self.log_test_result(test_name, True, "Dashboard imports successful", duration)
                return True
            else:
                duration = time.time() - start_time
                missing = [comp for comp in required_components if not hasattr(dashboard, comp)]
                self.log_test_result(test_name, False, f"Missing components: {missing}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Dashboard imports failed: {str(e)}"
            logger.error(error_msg)
            self.log_test_result(test_name, False, error_msg, duration)
            return False
    
    def test_backtest(self) -> bool:
        """
        Test backtest with sample data.
        
        Returns:
            bool: True if backtest runs successfully
        """
        test_name = "Backtest"
        start_time = time.time()
        
        try:
            logger.info(f"Testing {test_name}...")
            
            # Import backtest
            sys.path.insert(0, os.getcwd())
            import backtest
            
            # Create sample data
            sample_races = self.create_sample_race_data()
            sample_lineups = self.test_data.get('lineups', [])
            
            if not sample_lineups:
                # Create dummy lineups if not available
                sample_lineups = [
                    {
                        'lineup_id': f'lineup_{i}',
                        'drivers': [f'driver_{j}' for j in range(6)],
                        'total_projected_points': 200 + i * 10
                    }
                    for i in range(3)
                ]
            
            # Run backtest
            results = backtest.run_backtest(
                races=sample_races,
                lineups=sample_lineups
            )
            
            # Verify results
            if results:
                duration = time.time() - start_time
                self.log_test_result(test_name, True, f"Backtest completed successfully", duration)
                return True
            else:
                duration = time.time() - start_time
                self.log_test_result(test_name, False, "Backtest returned no results", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Backtest failed: {str(e)}"
            logger.error(error_msg)
            self.log_test_result(test_name, False, error_msg, duration)
            return False
    
    def test_end_to_end_pipeline(self) -> bool:
        """
        Test complete pipeline from data to lineup.
        
        Pipeline Steps:
        1. Initialize database
        2. Load sample race data
        3. Run MC simulation
        4. Project beliefs from simulation
        5. Generate optimal lineups
        6. Export lineups to CSV
        7. Verify CSV format
        8. Cleanup test data
        
        Returns:
            bool: True if complete pipeline executes successfully
        """
        test_name = "End-to-End Pipeline"
        pipeline_start_time = time.time()
        pipeline_steps = []
        
        try:
            logger.info(f"Testing {test_name}...")
            
            # Step 1: Initialize database
            step_start = time.time()
            sys.path.insert(0, os.path.join(os.getcwd(), 'apps', 'backend'))
            from app.models import Base, engine, SessionLocal
            Base.metadata.create_all(bind=engine)
            step_duration = time.time() - step_start
            pipeline_steps.append(("Initialize Database", True, step_duration))
            logger.info(f"Step 1: Database initialized in {step_duration:.2f}s")
            
            # Step 2: Load sample race data
            step_start = time.time()
            sample_races = self.create_sample_race_data()
            sample_drivers = self.create_sample_driver_data()
            db = SessionLocal()
            for race in sample_races:
                db.add(race)
            for driver in sample_drivers:
                db.add(driver)
            db.commit()
            db.close()
            step_duration = time.time() - step_start
            pipeline_steps.append(("Load Sample Data", True, step_duration))
            logger.info(f"Step 2: Sample data loaded in {step_duration:.2f}s")
            
            # Step 3: Run MC simulation
            step_start = time.time()
            import mc_sim
            sim_results = mc_sim.run_simulation(
                drivers=sample_drivers,
                num_iterations=SAMPLE_SIMULATION_ITERATIONS,
                race_id="test_race_001"
            )
            step_duration = time.time() - step_start
            if sim_results and len(sim_results) > 0:
                pipeline_steps.append(("Run MC Simulation", True, step_duration))
                logger.info(f"Step 3: MC simulation completed in {step_duration:.2f}s")
            else:
                raise Exception("MC simulation returned no results")
            
            # Step 4: Project beliefs from simulation
            step_start = time.time()
            import projector
            beliefs = self.create_sample_belief_data()
            projections = projector.project_beliefs(
                beliefs=beliefs,
                race_id="test_race_001"
            )
            step_duration = time.time() - step_start
            if projections and len(projections) > 0:
                pipeline_steps.append(("Project Beliefs", True, step_duration))
                logger.info(f"Step 4: Belief projection completed in {step_duration:.2f}s")
            else:
                raise Exception("Belief projection returned no results")
            
            # Step 5: Generate optimal lineups
            step_start = time.time()
            from app.optimizer import Optimizer
            optimizer = Optimizer()
            lineups = optimizer.optimize(
                projections=projections,
                salary_cap=50000,
                num_lineups=3
            )
            step_duration = time.time() - step_start
            if lineups and len(lineups) > 0:
                pipeline_steps.append(("Generate Lineups", True, step_duration))
                logger.info(f"Step 5: Lineups generated in {step_duration:.2f}s")
            else:
                raise Exception("Optimizer returned no lineups")
            
            # Step 6: Export lineups to CSV
            step_start = time.time()
            import pandas as pd
            csv_path = "test_lineups.csv"
            df = pd.DataFrame(lineups)
            df.to_csv(csv_path, index=False)
            step_duration = time.time() - step_start
            pipeline_steps.append(("Export to CSV", True, step_duration))
            logger.info(f"Step 6: Lineups exported to CSV in {step_duration:.2f}s")
            
            # Step 7: Verify CSV format
            step_start = time.time()
            if os.path.exists(csv_path):
                df_verify = pd.read_csv(csv_path)
                if len(df_verify) == len(lineups):
                    pipeline_steps.append(("Verify CSV Format", True, step_duration))
                    logger.info(f"Step 7: CSV format verified in {step_duration:.2f}s")
                else:
                    raise Exception("CSV row count mismatch")
            else:
                raise Exception("CSV file not created")
            
            # Step 8: Cleanup test data
            step_start = time.time()
            self.cleanup_test_data()
            if os.path.exists(csv_path):
                os.remove(csv_path)
            step_duration = time.time() - step_start
            pipeline_steps.append(("Cleanup Test Data", True, step_duration))
            logger.info(f"Step 8: Test data cleaned up in {step_duration:.2f}s")
            
            # Calculate total duration
            total_duration = time.time() - pipeline_start_time
            
            # Log pipeline results
            step_summary = "\n".join([
                f"  - {step[0]}: {'✓' if step[1] else '✗'} ({step[2]:.2f}s)"
                for step in pipeline_steps
            ])
            
            self.log_test_result(
                test_name,
                True,
                f"Pipeline completed successfully\n{step_summary}",
                total_duration
            )
            
            return True
            
        except Exception as e:
            total_duration = time.time() - pipeline_start_time
            error_msg = f"Pipeline failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            # Cleanup on failure
            self.cleanup_test_data()
            
            self.log_test_result(test_name, False, error_msg, total_duration)
            return False
    
    def run_all_tests(self, stop_on_failure: bool = False) -> Dict:
        """
        Run all tests and generate report.
        
        Args:
            stop_on_failure: If True, stop testing on first failure
            
        Returns:
            Dict: Test results summary
        """
        self.start_time = time.time()
        logger.info("=" * 80)
        logger.info("Starting Integration Test Suite")
        logger.info("=" * 80)
        
        # Define all tests
        tests = [
            ("Database Connection", self.test_database_connection),
            ("Models Creation", self.test_models_creation),
            ("MC Simulator", self.test_mc_simulator),
            ("Belief Projector", self.test_belief_projector),
            ("Optimizer", self.test_optimizer),
            ("Dashboard Imports", self.test_dashboard_imports),
            ("Backtest", self.test_backtest),
            ("End-to-End Pipeline", self.test_end_to_end_pipeline)
        ]
        
        # Run tests
        for test_name, test_func in tests:
            try:
                passed = test_func()
                if not passed and stop_on_failure:
                    logger.error(f"Stopping tests due to failure in {test_name}")
                    break
            except Exception as e:
                logger.error(f"Unexpected error in {test_name}: {str(e)}")
                if stop_on_failure:
                    break
        
        # Generate summary
        total_duration = time.time() - self.start_time
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['passed'])
        failed_tests = total_tests - passed_tests
        
        summary = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%",
            'total_duration': f"{total_duration:.2f}s",
            'results': self.test_results
        }
        
        # Print summary
        self.print_summary(summary)
        
        # Save report to file
        self.save_report(summary)
        
        return summary
    
    def log_test_result(self, test_name: str, passed: bool, message: str, duration: float):
        """
        Log test result with timestamp.
        
        Args:
            test_name: Name of the test
            passed: Whether the test passed
            message: Test result message
            duration: Test duration in seconds
        """
        result = {
            'test_name': test_name,
            'passed': passed,
            'message': message,
            'duration': f"{duration:.2f}s",
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status} - {test_name} ({duration:.2f}s): {message}")
    
    def print_summary(self, summary: Dict):
        """
        Print test summary to console.
        
        Args:
            summary: Test results summary
        """
        logger.info("=" * 80)
        logger.info("Integration Test Summary")
        logger.info("=" * 80)
        logger.info(f"Total Tests: {summary['total_tests']}")
        logger.info(f"Passed: {summary['passed_tests']}")
        logger.info(f"Failed: {summary['failed_tests']}")
        logger.info(f"Success Rate: {summary['success_rate']}")
        logger.info(f"Total Duration: {summary['total_duration']}")
        logger.info("=" * 80)
        
        if summary['failed_tests'] > 0:
            logger.info("Failed Tests:")
            for result in summary['results']:
                if not result['passed']:
                    logger.info(f"  - {result['test_name']}: {result['message']}")
    
    def save_report(self, summary: Dict):
        """
        Save test report to file.
        
        Args:
            summary: Test results summary
        """
        report_path = f"integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Test report saved to {report_path}")
    
    # Helper methods for test data creation
    def create_sample_race_data(self) -> List:
        """
        Create sample race data for testing.
        
        Returns:
            List: Sample race objects
        """
        races = []
        for i in range(SAMPLE_RACE_SIZE):
            race = {
                'race_id': f'test_race_{i:03d}',
                'track_name': f'Track {i+1}',
                'race_date': datetime.now(),
                'laps': 200 + i * 50
            }
            races.append(race)
        return races
    
    def create_sample_driver_data(self) -> List:
        """
        Create sample driver data for testing.
        
        Returns:
            List: Sample driver objects
        """
        drivers = []
        for i in range(SAMPLE_DRIVER_SIZE):
            driver = {
                'driver_id': f'driver_{i:03d}',
                'driver_name': f'Driver {i+1}',
                'team': f'Team {(i % 3) + 1}',
                'average_finish_position': 5 + i,
                'win_rate': 0.05 + (i * 0.01),
                'salary': 5000 + i * 500,
                'projected_points': 30 + i * 5
            }
            drivers.append(driver)
        return drivers
    
    def create_sample_belief_data(self) -> List:
        """
        Create sample belief data for testing.
        
        Returns:
            List: Sample belief objects
        """
        beliefs = []
        for i in range(SAMPLE_DRIVER_SIZE):
            belief = {
                'driver_id': f'driver_{i:03d}',
                'belief_mean': 30 + i * 5,
                'belief_std': 10 + i,
                'confidence': 0.7 + (i * 0.02)
            }
            beliefs.append(belief)
        return beliefs
    
    def cleanup_test_data(self):
        """
        Clean up test data after tests.
        """
        try:
            sys.path.insert(0, os.path.join(os.getcwd(), 'apps', 'backend'))
            from app.models import Base, engine, SessionLocal
            
            # Drop all tables
            Base.metadata.drop_all(bind=engine)
            
            logger.info("Test data cleaned up successfully")
        except Exception as e:
            logger.warning(f"Cleanup failed (non-critical): {str(e)}")


class DeploymentVerifier:
    """
    Deployment verification system for NASCAR DFS optimizer.
    
    Verifies all components are ready for production deployment:
    - Dependencies and versions
    - Environment variables
    - Database schema
    - API endpoints
    - Airflow DAG
    - Dashboard
    - File permissions
    """
    
    def __init__(self):
        """Initialize the deployment verifier."""
        self.verification_results = []
        self.start_time = None
        logger.info("DeploymentVerifier initialized")
    
    def check_dependencies(self) -> bool:
        """
        Check all required dependencies are installed.
        
        Returns:
            bool: True if all dependencies are satisfied
        """
        check_name = "Dependencies Check"
        start_time = time.time()
        
        try:
            logger.info(f"Checking {check_name}...")
            
            # Check Python version
            python_version = sys.version_info
            if python_version >= (3, 9):
                logger.info(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro} ✓")
            else:
                raise Exception(f"Python version {python_version.major}.{python_version.minor} is too old. Required: >= 3.9")
            
            # Check each dependency
            missing_deps = []
            version_issues = []
            
            for package, min_version in REQUIRED_DEPENDENCIES.items():
                try:
                    module = importlib.import_module(package)
                    version = getattr(module, '__version__', 'unknown')
                    
                    # Parse version and compare
                    min_ver_parts = [int(x) for x in min_version.split('.')]
                    if version != 'unknown':
                        ver_parts = [int(x) for x in version.split('.')[:len(min_ver_parts)]]
                        if ver_parts < min_ver_parts:
                            version_issues.append(f"{package} ({version} < {min_version})")
                        else:
                            logger.info(f"{package}: {version} ✓")
                    else:
                        logger.warning(f"{package}: version unknown (assuming OK)")
                        
                except ImportError:
                    missing_deps.append(package)
            
            if missing_deps:
                raise Exception(f"Missing dependencies: {', '.join(missing_deps)}")
            
            if version_issues:
                raise Exception(f"Version issues: {', '.join(version_issues)}")
            
            duration = time.time() - start_time
            self.log_verification_result(check_name, True, "All dependencies satisfied", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Dependencies check failed: {str(e)}"
            logger.error(error_msg)
            self.log_verification_result(check_name, False, error_msg, duration)
            return False
    
    def check_environment_variables(self) -> bool:
        """
        Check all required environment variables.
        
        Returns:
            bool: True if all required environment variables are set
        """
        check_name = "Environment Variables Check"
        start_time = time.time()
        
        try:
            logger.info(f"Checking {check_name}...")
            
            missing_vars = []
            for var, required in REQUIRED_ENV_VARS.items():
                value = os.getenv(var)
                if required and not value:
                    missing_vars.append(var)
                else:
                    status = "✓" if value else "(optional)"
                    logger.info(f"{var}: {value or 'not set'} {status}")
            
            if missing_vars:
                raise Exception(f"Missing required environment variables: {', '.join(missing_vars)}")
            
            duration = time.time() - start_time
            self.log_verification_result(check_name, True, "Environment variables OK", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Environment variables check failed: {str(e)}"
            logger.error(error_msg)
            self.log_verification_result(check_name, False, error_msg, duration)
            return False
    
    def check_database_schema(self) -> bool:
        """
        Verify database schema is correct.
        
        Returns:
            bool: True if database schema is valid
        """
        check_name = "Database Schema Check"
        start_time = time.time()
        
        try:
            logger.info(f"Checking {check_name}...")
            
            sys.path.insert(0, os.path.join(os.getcwd(), 'apps', 'backend'))
            from app.models import Base, engine
            from sqlalchemy import inspect
            
            # Check connection
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            # Expected tables
            expected_tables = ['races', 'drivers', 'simulation_results', 'projections', 'lineups']
            
            missing_tables = [t for t in expected_tables if t not in tables]
            if missing_tables:
                raise Exception(f"Missing tables: {', '.join(missing_tables)}")
            
            logger.info(f"Database schema verified. Tables: {', '.join(tables)}")
            
            duration = time.time() - start_time
            self.log_verification_result(check_name, True, f"Schema valid with {len(tables)} tables", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Database schema check failed: {str(e)}"
            logger.error(error_msg)
            self.log_verification_result(check_name, False, error_msg, duration)
            return False
    
    def check_api_endpoints(self) -> bool:
        """
        Verify FastAPI endpoints are accessible.
        
        Returns:
            bool: True if API endpoints are accessible
        """
        check_name = "API Endpoints Check"
        start_time = time.time()
        
        try:
            logger.info(f"Checking {check_name}...")
            
            # Check if main.py exists
            main_path = os.path.join('apps', 'backend', 'app', 'main.py')
            if not os.path.exists(main_path):
                raise Exception("FastAPI main.py not found")
            
            # Try to import and check routes
            sys.path.insert(0, os.path.join(os.getcwd(), 'apps', 'backend'))
            from app.main import app
            
            routes = [route.path for route in app.routes]
            
            if len(routes) > 0:
                logger.info(f"API endpoints found: {len(routes)} routes")
                for route in routes[:5]:  # Show first 5
                    logger.info(f"  - {route}")
            else:
                raise Exception("No API routes defined")
            
            duration = time.time() - start_time
            self.log_verification_result(check_name, True, f"API has {len(routes)} endpoints", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"API endpoints check failed: {str(e)}"
            logger.error(error_msg)
            self.log_verification_result(check_name, False, error_msg, duration)
            return False
    
    def check_airflow_dag(self) -> bool:
        """
        Verify Airflow DAG is valid.
        
        Returns:
            bool: True if Airflow DAG is valid
        """
        check_name = "Airflow DAG Check"
        start_time = time.time()
        
        try:
            logger.info(f"Checking {check_name}...")
            
            # Check if DAG file exists
            dag_path = os.path.join('apps', 'airflow', 'dags', 'nascar_etl_dag.py')
            if not os.path.exists(dag_path):
                raise Exception("Airflow DAG file not found")
            
            # Try to import DAG
            sys.path.insert(0, os.path.join(os.getcwd(), 'apps', 'airflow'))
            from dags.nascar_etl_dag import dag
            
            # Check DAG properties
            if not hasattr(dag, 'dag_id'):
                raise Exception("DAG missing dag_id")
            
            logger.info(f"Airflow DAG verified: {dag.dag_id}")
            
            duration = time.time() - start_time
            self.log_verification_result(check_name, True, f"DAG {dag.dag_id} is valid", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Airflow DAG check failed: {str(e)}"
            logger.error(error_msg)
            self.log_verification_result(check_name, False, error_msg, duration)
            return False
    
    def check_dashboard(self) -> bool:
        """
        Verify dashboard can start.
        
        Returns:
            bool: True if dashboard can start
        """
        check_name = "Dashboard Check"
        start_time = time.time()
        
        try:
            logger.info(f"Checking {check_name}...")
            
            # Check if dashboard.py exists
            dashboard_path = 'dashboard.py'
            if not os.path.exists(dashboard_path):
                raise Exception("dashboard.py not found")
            
            # Try to import dashboard
            sys.path.insert(0, os.getcwd())
            import dashboard
            
            logger.info("Dashboard module imported successfully")
            
            duration = time.time() - start_time
            self.log_verification_result(check_name, True, "Dashboard can be imported", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Dashboard check failed: {str(e)}"
            logger.error(error_msg)
            self.log_verification_result(check_name, False, error_msg, duration)
            return False
    
    def check_file_permissions(self) -> bool:
        """
        Verify file permissions are correct.
        
        Returns:
            bool: True if file permissions are correct
        """
        check_name = "File Permissions Check"
        start_time = time.time()
        
        try:
            logger.info(f"Checking {check_name}...")
            
            # Check critical files
            critical_files = [
                'dashboard.py',
                'backtest.py',
                'mc_sim.py',
                'projector.py',
                os.path.join('apps', 'backend', 'app', 'main.py'),
                os.path.join('apps', 'airflow', 'dags', 'nascar_etl_dag.py')
            ]
            
            permission_issues = []
            for filepath in critical_files:
                if not os.path.exists(filepath):
                    permission_issues.append(f"{filepath} not found")
                    continue
                
                if not os.access(filepath, os.R_OK):
                    permission_issues.append(f"{filepath} not readable")
                
                # Check if directory is writable
                dir_path = os.path.dirname(filepath)
                if not os.access(dir_path, os.W_OK):
                    permission_issues.append(f"{dir_path} not writable")
            
            if permission_issues:
                raise Exception(f"Permission issues: {', '.join(permission_issues)}")
            
            logger.info("All file permissions are correct")
            
            duration = time.time() - start_time
            self.log_verification_result(check_name, True, "File permissions OK", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"File permissions check failed: {str(e)}"
            logger.error(error_msg)
            self.log_verification_result(check_name, False, error_msg, duration)
            return False
    
    def generate_deployment_report(self) -> Dict:
        """
        Generate deployment readiness report.
        
        Returns:
            Dict: Deployment readiness report
        """
        self.start_time = time.time()
        logger.info("=" * 80)
        logger.info("Starting Deployment Verification")
        logger.info("=" * 80)
        
        # Run all checks
        checks = [
            ("Dependencies", self.check_dependencies),
            ("Environment Variables", self.check_environment_variables),
            ("Database Schema", self.check_database_schema),
            ("API Endpoints", self.check_api_endpoints),
            ("Airflow DAG", self.check_airflow_dag),
            ("Dashboard", self.check_dashboard),
            ("File Permissions", self.check_file_permissions)
        ]
        
        for check_name, check_func in checks:
            try:
                check_func()
            except Exception as e:
                logger.error(f"Error in {check_name}: {str(e)}")
        
        # Generate summary
        total_duration = time.time() - self.start_time
        total_checks = len(self.verification_results)
        passed_checks = sum(1 for r in self.verification_results if r['passed'])
        failed_checks = total_checks - passed_checks
        
        # Determine deployment readiness
        is_ready = failed_checks == 0
        readiness_status = "READY" if is_ready else "NOT READY"
        
        report = {
            'deployment_status': readiness_status,
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'success_rate': f"{(passed_checks/total_checks*100):.1f}%" if total_checks > 0 else "0%",
            'total_duration': f"{total_duration:.2f}s",
            'checks': self.verification_results,
            'recommendations': self._generate_recommendations()
        }
        
        # Print summary
        self.print_deployment_summary(report)
        
        # Save report to file
        self.save_deployment_report(report)
        
        return report
    
    def log_verification_result(self, check_name: str, passed: bool, message: str, duration: float):
        """
        Log verification result with timestamp.
        
        Args:
            check_name: Name of the check
            passed: Whether the check passed
            message: Check result message
            duration: Check duration in seconds
        """
        result = {
            'check_name': check_name,
            'passed': passed,
            'message': message,
            'duration': f"{duration:.2f}s",
            'timestamp': datetime.now().isoformat()
        }
        self.verification_results.append(result)
        
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status} - {check_name} ({duration:.2f}s): {message}")
    
    def print_deployment_summary(self, report: Dict):
        """
        Print deployment summary to console.
        
        Args:
            report: Deployment verification report
        """
        logger.info("=" * 80)
        logger.info("Deployment Verification Summary")
        logger.info("=" * 80)
        logger.info(f"Deployment Status: {report['deployment_status']}")
        logger.info(f"Total Checks: {report['total_checks']}")
        logger.info(f"Passed: {report['passed_checks']}")
        logger.info(f"Failed: {report['failed_checks']}")
        logger.info(f"Success Rate: {report['success_rate']}")
        logger.info(f"Total Duration: {report['total_duration']}")
        logger.info("=" * 80)
        
        if report['failed_checks'] > 0:
            logger.info("Failed Checks:")
            for check in report['checks']:
                if not check['passed']:
                    logger.info(f"  - {check['check_name']}: {check['message']}")
        
        if report['recommendations']:
            logger.info("\nRecommendations:")
            for rec in report['recommendations']:
                logger.info(f"  - {rec}")
    
    def save_deployment_report(self, report: Dict):
        """
        Save deployment report to file.
        
        Args:
            report: Deployment verification report
        """
        report_path = f"deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Deployment report saved to {report_path}")
    
    def _generate_recommendations(self) -> List[str]:
        """
        Generate recommendations based on verification results.
        
        Returns:
            List: List of recommendations
        """
        recommendations = []
        
        for check in self.verification_results:
            if not check['passed']:
                check_name = check['check_name']
                
                if 'Dependencies' in check_name:
                    recommendations.append(
                        "Install missing dependencies: pip install -r requirements.txt"
                    )
                elif 'Environment Variables' in check_name:
                    recommendations.append(
                        "Set required environment variables in .env file"
                    )
                elif 'Database Schema' in check_name:
                    recommendations.append(
                        "Run database migrations: alembic upgrade head"
                    )
                elif 'API Endpoints' in check_name:
                    recommendations.append(
                        "Verify FastAPI application configuration"
                    )
                elif 'Airflow DAG' in check_name:
                    recommendations.append(
                        "Check Airflow DAG syntax and dependencies"
                    )
                elif 'Dashboard' in check_name:
                    recommendations.append(
                        "Verify Streamlit dashboard configuration"
                    )
                elif 'File Permissions' in check_name:
                    recommendations.append(
                        "Fix file permissions: chmod +rwx <files>"
                    )
        
        return recommendations


# Helper functions for deployment verification

def check_python_version() -> bool:
    """
    Check Python version is compatible.
    
    Returns:
        bool: True if Python version is >= 3.9
    """
    version = sys.version_info
    return version >= (3, 9)


def check_package_version(package: str, min_version: str) -> bool:
    """
    Check package version meets minimum requirement.
    
    Args:
        package: Package name
        min_version: Minimum required version
        
    Returns:
        bool: True if package version meets requirement
    """
    try:
        module = importlib.import_module(package)
        version = getattr(module, '__version__', '0.0.0')
        
        min_ver_parts = [int(x) for x in min_version.split('.')]
        ver_parts = [int(x) for x in version.split('.')[:len(min_ver_parts)]]
        
        return ver_parts >= min_ver_parts
    except ImportError:
        return False


def check_file_exists(filepath: str) -> bool:
    """
    Check file exists.
    
    Args:
        filepath: Path to file
        
    Returns:
        bool: True if file exists
    """
    return os.path.exists(filepath)


def check_file_readable(filepath: str) -> bool:
    """
    Check file is readable.
    
    Args:
        filepath: Path to file
        
    Returns:
        bool: True if file is readable
    """
    return os.path.exists(filepath) and os.access(filepath, os.R_OK)


def check_file_writable(filepath: str) -> bool:
    """
    Check file is writable.
    
    Args:
        filepath: Path to file
        
    Returns:
        bool: True if file is writable
    """
    if os.path.exists(filepath):
        return os.access(filepath, os.W_OK)
    else:
        # Check if directory is writable
        dir_path = os.path.dirname(filepath) or '.'
        return os.access(dir_path, os.W_OK)


def check_port_available(port: int) -> bool:
    """
    Check port is available.
    
    Args:
        port: Port number to check
        
    Returns:
        bool: True if port is available
    """
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return True
    except OSError:
        return False


# Main execution function

def main():
    """
    Main execution function for integration testing and deployment verification.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='NASCAR DFS Optimizer - Integration Testing and Deployment Verification'
    )
    parser.add_argument(
        '--mode',
        choices=['integration', 'deployment', 'all'],
        default='all',
        help='Execution mode: integration tests, deployment verification, or both'
    )
    parser.add_argument(
        '--stop-on-failure',
        action='store_true',
        help='Stop testing on first failure'
    )
    
    args = parser.parse_args()
    
    # Run integration tests
    if args.mode in ['integration', 'all']:
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING INTEGRATION TESTS")
        logger.info("=" * 80 + "\n")
        
        test_suite = IntegrationTestSuite()
        test_results = test_suite.run_all_tests(stop_on_failure=args.stop_on_failure)
    
    # Run deployment verification
    if args.mode in ['deployment', 'all']:
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING DEPLOYMENT VERIFICATION")
        logger.info("=" * 80 + "\n")
        
        verifier = DeploymentVerifier()
        deployment_report = verifier.generate_deployment_report()
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("EXECUTION COMPLETE")
    logger.info("=" * 80)
    logger.info("Check the generated reports for detailed results:")
    logger.info("  - integration_test_report_*.json")
    logger.info("  - deployment_report_*.json")
    logger.info("  - integration_test.log")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
