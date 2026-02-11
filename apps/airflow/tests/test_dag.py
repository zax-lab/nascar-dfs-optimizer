"""Tests for the NASCAR ETL Airflow DAG.

This module contains tests to verify the DAG loads correctly and has
the expected structure and task dependencies.
"""

import os
import sys
from typing import Any

import pytest

# Add the dags directory to the path to import the DAG module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dags"))


class TestNascarEtlDag:
    """Test suite for the NASCAR ETL DAG."""

    def test_dag_imports_without_errors(self) -> None:
        """Test that the DAG module can be imported without errors."""
        try:
            import nascar_etl_dag  # noqa: F401
        except ImportError as e:
            pytest.fail(f"Failed to import nascar_etl_dag: {e}")

    def test_dag_exists(self) -> None:
        """Test that the DAG object exists and has the expected ID."""
        import nascar_etl_dag

        assert hasattr(nascar_etl_dag, "dag"), "DAG object not found in module"
        assert nascar_etl_dag.dag.dag_id == "nascar_etl_dag", "DAG ID mismatch"

    def test_dag_has_three_tasks(self) -> None:
        """Test that the DAG has exactly three tasks."""
        import nascar_etl_dag

        dag = nascar_etl_dag.dag
        tasks = dag.tasks

        assert len(tasks) == 3, f"Expected 3 tasks, found {len(tasks)}"

        # Verify task IDs
        task_ids = {task.task_id for task in tasks}
        expected_task_ids = {"scrape", "transform", "load_neo4j"}
        assert task_ids == expected_task_ids, f"Task IDs mismatch: {task_ids} != {expected_task_ids}"

    def test_task_dependencies(self) -> None:
        """Test that the tasks have the correct dependencies."""
        import nascar_etl_dag

        dag = nascar_etl_dag.dag
        scrape_task = dag.get_task("scrape")
        transform_task = dag.get_task("transform")
        load_neo4j_task = dag.get_task("load_neo4j")

        # Verify scrape -> transform dependency
        assert scrape_task in transform_task.upstream_list, "scrape should be upstream of transform"
        assert transform_task in scrape_task.downstream_list, "transform should be downstream of scrape"

        # Verify transform -> load_neo4j dependency
        assert transform_task in load_neo4j_task.upstream_list, "transform should be upstream of load_neo4j"
        assert load_neo4j_task in transform_task.downstream_list, "load_neo4j should be downstream of transform"

        # Verify no other dependencies
        assert len(scrape_task.upstream_list) == 0, "scrape should have no upstream tasks"
        assert len(load_neo4j_task.downstream_list) == 0, "load_neo4j should have no downstream tasks"

    def test_dag_has_correct_schedule(self) -> None:
        """Test that the DAG has the correct schedule interval."""
        import nascar_etl_dag

        dag = nascar_etl_dag.dag
        assert dag.schedule_interval == "@daily", f"Expected daily schedule, got {dag.schedule_interval}"

    def test_dag_has_correct_tags(self) -> None:
        """Test that the DAG has the expected tags."""
        import nascar_etl_dag

        dag = nascar_etl_dag.dag
        expected_tags = {"nascar", "dfs", "etl", "neo4j"}
        assert set(dag.tags) == expected_tags, f"Tags mismatch: {set(dag.tags)} != {expected_tags}"

    def test_dag_catchup_is_disabled(self) -> None:
        """Test that catchup is disabled for the DAG."""
        import nascar_etl_dag

        dag = nascar_etl_dag.dag
        assert dag.catchup is False, "Catchup should be disabled"

    def test_scrape_task_is_python_operator(self) -> None:
        """Test that the scrape task is a PythonOperator."""
        import nascar_etl_dag
        from airflow.operators.python import PythonOperator

        dag = nascar_etl_dag.dag
        scrape_task = dag.get_task("scrape")

        assert isinstance(scrape_task, PythonOperator), "scrape task should be a PythonOperator"

    def test_transform_task_is_python_operator(self) -> None:
        """Test that the transform task is a PythonOperator."""
        import nascar_etl_dag
        from airflow.operators.python import PythonOperator

        dag = nascar_etl_dag.dag
        transform_task = dag.get_task("transform")

        assert isinstance(transform_task, PythonOperator), "transform task should be a PythonOperator"

    def test_load_neo4j_task_is_python_operator(self) -> None:
        """Test that the load_neo4j task is a PythonOperator."""
        import nascar_etl_dag
        from airflow.operators.python import PythonOperator

        dag = nascar_etl_dag.dag
        load_neo4j_task = dag.get_task("load_neo4j")

        assert isinstance(load_neo4j_task, PythonOperator), "load_neo4j task should be a PythonOperator"

    def test_environment_variables_are_used(self) -> None:
        """Test that the DAG uses environment variables for configuration."""
        import nascar_etl_dag

        # Verify that the module has the expected environment variable references
        assert hasattr(nascar_etl_dag, "NEO4J_URI"), "NEO4J_URI not defined"
        assert hasattr(nascar_etl_dag, "NEO4J_USER"), "NEO4J_USER not defined"
        assert hasattr(nascar_etl_dag, "NEO4J_PASSWORD"), "NEO4J_PASSWORD not defined"
        assert hasattr(nascar_etl_dag, "NASCAR_API_URL"), "NASCAR_API_URL not defined"

    def test_dag_has_default_args(self) -> None:
        """Test that the DAG has the expected default arguments."""
        import nascar_etl_dag

        dag = nascar_etl_dag.dag
        default_args = dag.default_args

        assert default_args["owner"] == "nascar-dfs", f"Owner mismatch: {default_args['owner']}"
        assert default_args["depends_on_past"] is False, "depends_on_past should be False"
        assert default_args["retries"] == 1, f"Retries mismatch: {default_args['retries']}"

    def test_metaphysical_field_calculators_exist(self) -> None:
        """Test that the metaphysical field calculation functions exist."""
        import nascar_etl_dag

        # Driver metaphysical fields
        assert hasattr(nascar_etl_dag, "_calculate_agility"), "_calculate_agility not found"
        assert hasattr(nascar_etl_dag, "_calculate_fortune"), "_calculate_fortune not found"
        assert hasattr(nascar_etl_dag, "_calculate_momentum"), "_calculate_momentum not found"
        assert hasattr(nascar_etl_dag, "_calculate_resonance"), "_calculate_resonance not found"
        assert hasattr(nascar_etl_dag, "_calculate_entropy"), "_calculate_entropy not found"

        # Track metaphysical fields
        assert hasattr(nascar_etl_dag, "_calculate_track_intensity"), "_calculate_track_intensity not found"
        assert hasattr(nascar_etl_dag, "_calculate_track_chaos"), "_calculate_track_chaos not found"
        assert hasattr(nascar_etl_dag, "_calculate_track_flow"), "_calculate_track_flow not found"

    def test_transform_data_returns_correct_structure(self) -> None:
        """Test that transform_data returns the expected structure."""
        import nascar_etl_dag

        # Create mock input data
        mock_input = [
            {
                "driver_id": "test_driver_001",
                "driver_name": "Test Driver",
                "team": "Test Team",
                "car_number": 1,
                "avg_finish": 10.0,
                "wins": 2,
                "top5": 10,
                "top10": 20,
            },
            {
                "track_id": "test_track_001",
                "track_name": "Test Track",
                "track_type": "Superspeedway",
                "length": 2.5,
                "turns": 4,
            },
        ]

        # Call transform_data with mock data
        result = nascar_etl_dag.transform_data(ti=None, **{"ti": type("MockTI", (), {"xcom_pull": lambda task_id: mock_input})()})

        # Verify structure
        assert "drivers" in result, "Result should contain 'drivers' key"
        assert "tracks" in result, "Result should contain 'tracks' key"
        assert len(result["drivers"]) == 1, f"Expected 1 driver, got {len(result['drivers'])}"
        assert len(result["tracks"]) == 1, f"Expected 1 track, got {len(result['tracks'])}"

        # Verify driver has metaphysical fields
        driver = result["drivers"][0]
        assert "metaphysical_agility" in driver, "Driver should have metaphysical_agility"
        assert "metaphysical_fortune" in driver, "Driver should have metaphysical_fortune"
        assert "metaphysical_momentum" in driver, "Driver should have metaphysical_momentum"
        assert "metaphysical_resonance" in driver, "Driver should have metaphysical_resonance"
        assert "metaphysical_entropy" in driver, "Driver should have metaphysical_entropy"

        # Verify track has metaphysical fields
        track = result["tracks"][0]
        assert "metaphysical_intensity" in track, "Track should have metaphysical_intensity"
        assert "metaphysical_chaos" in track, "Track should have metaphysical_chaos"
        assert "metaphysical_flow" in track, "Track should have metaphysical_flow"

    def test_metaphysical_values_are_in_range(self) -> None:
        """Test that metaphysical field values are between 0 and 1."""
        import nascar_etl_dag

        # Test driver metaphysical fields
        driver_data = {
            "driver_id": "test",
            "driver_name": "Test",
            "team": "Test",
            "car_number": 5,
            "avg_finish": 12.5,
            "wins": 3,
            "top5": 10,
            "top10": 20,
        }

        agility = nascar_etl_dag._calculate_agility(driver_data)
        fortune = nascar_etl_dag._calculate_fortune(driver_data)
        momentum = nascar_etl_dag._calculate_momentum(driver_data)
        resonance = nascar_etl_dag._calculate_resonance(driver_data)
        entropy = nascar_etl_dag._calculate_entropy(driver_data)

        assert 0.0 <= agility <= 1.0, f"Agility out of range: {agility}"
        assert 0.0 <= fortune <= 1.0, f"Fortune out of range: {fortune}"
        assert 0.0 <= momentum <= 1.0, f"Momentum out of range: {momentum}"
        assert 0.0 <= resonance <= 1.0, f"Resonance out of range: {resonance}"
        assert 0.0 <= entropy <= 1.0, f"Entropy out of range: {entropy}"

        # Test track metaphysical fields
        track_data = {
            "track_id": "test",
            "track_name": "Test",
            "track_type": "Superspeedway",
            "length": 2.5,
            "turns": 4,
        }

        intensity = nascar_etl_dag._calculate_track_intensity(track_data)
        chaos = nascar_etl_dag._calculate_track_chaos(track_data)
        flow = nascar_etl_dag._calculate_track_flow(track_data)

        assert 0.0 <= intensity <= 1.0, f"Intensity out of range: {intensity}"
        assert 0.0 <= chaos <= 1.0, f"Chaos out of range: {chaos}"
        assert 0.0 <= flow <= 1.0, f"Flow out of range: {flow}"
