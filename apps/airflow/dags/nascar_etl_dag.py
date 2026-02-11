"""Airflow DAG for NASCAR DFS ETL pipeline.

This DAG orchestrates the extraction, transformation, and loading of NASCAR data
into Neo4j with metaphysical fields for the Axiomatic DFS engine.
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator
from neo4j import GraphDatabase

# Environment variables for configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NASCAR_API_URL = os.getenv("NASCAR_API_URL", "https://api.example.com/nascar")

# Default arguments for the DAG
default_args: Dict[str, Any] = {
    "owner": "nascar-dfs",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Create the DAG with daily schedule
dag: DAG = DAG(
    "nascar_etl_dag",
    default_args=default_args,
    description="ETL pipeline for NASCAR DFS data into Neo4j",
    schedule_interval="@daily",
    catchup=False,
    tags=["nascar", "dfs", "etl", "neo4j"],
)


def scrape_nascar_data(**kwargs: Any) -> List[Dict[str, Any]]:
    """Scrape NASCAR data from the API endpoint.

    This function performs a simple HTTP GET request to fetch NASCAR data.
    In production, this would connect to the actual NASCAR data source.

    Args:
        **kwargs: Airflow context variables

    Returns:
        List of dictionaries containing raw NASCAR data
    """
    print(f"Scraping NASCAR data from {NASCAR_API_URL}")

    # Mock data for demonstration - in production, this would be an actual API call
    mock_data: List[Dict[str, Any]] = [
        {
            "driver_id": "driver_001",
            "driver_name": "Kyle Larson",
            "team": "Hendrick Motorsports",
            "car_number": 5,
            "avg_finish": 12.5,
            "wins": 8,
            "top5": 18,
            "top10": 24,
        },
        {
            "driver_id": "driver_002",
            "driver_name": "Denny Hamlin",
            "team": "Joe Gibbs Racing",
            "car_number": 11,
            "avg_finish": 11.2,
            "wins": 5,
            "top5": 15,
            "top10": 22,
        },
        {
            "track_id": "track_001",
            "track_name": "Daytona International Speedway",
            "track_type": "Superspeedway",
            "length": 2.5,
            "turns": 4,
        },
        {
            "track_id": "track_002",
            "track_name": "Bristol Motor Speedway",
            "track_type": "Short Track",
            "length": 0.533,
            "turns": 4,
        },
    ]

    # In production, uncomment the following:
    # try:
    #     response = requests.get(NASCAR_API_URL, timeout=30)
    #     response.raise_for_status()
    #     mock_data = response.json()
    # except requests.RequestException as e:
    #     print(f"Error fetching NASCAR data: {e}")
    #     raise

    print(f"Scraped {len(mock_data)} records")
    return mock_data


def transform_data(**kwargs: Any) -> Dict[str, List[Dict[str, Any]]]:
    """Transform raw NASCAR data into ontology-ready records with metaphysical fields.

    This function maps raw data to driver and track entities, adding metaphysical
    fields for the Axiomatic DFS engine.

    Args:
        **kwargs: Airflow context variables

    Returns:
        Dictionary containing transformed drivers and tracks
    """
    # Pull data from the previous task
    ti = kwargs["ti"]
    raw_data: List[Dict[str, Any]] = ti.xcom_pull(task_ids="scrape")

    print(f"Transforming {len(raw_data)} records")

    drivers: List[Dict[str, Any]] = []
    tracks: List[Dict[str, Any]] = []

    for record in raw_data:
        if "driver_id" in record:
            # Transform driver record with metaphysical fields
            driver: Dict[str, Any] = {
                "driver_id": record["driver_id"],
                "name": record["driver_name"],
                "team": record["team"],
                "car_number": record["car_number"],
                "avg_finish": record["avg_finish"],
                "wins": record["wins"],
                "top5": record["top5"],
                "top10": record["top10"],
                # Metaphysical fields for Axiomatic DFS engine
                "metaphysical_agility": _calculate_agility(record),
                "metaphysical_fortune": _calculate_fortune(record),
                "metaphysical_momentum": _calculate_momentum(record),
                "metaphysical_resonance": _calculate_resonance(record),
                "metaphysical_entropy": _calculate_entropy(record),
            }
            drivers.append(driver)

        elif "track_id" in record:
            # Transform track record with metaphysical fields
            track: Dict[str, Any] = {
                "track_id": record["track_id"],
                "name": record["track_name"],
                "type": record["track_type"],
                "length": record["length"],
                "turns": record["turns"],
                # Metaphysical fields for Axiomatic DFS engine
                "metaphysical_intensity": _calculate_track_intensity(record),
                "metaphysical_chaos": _calculate_track_chaos(record),
                "metaphysical_flow": _calculate_track_flow(record),
            }
            tracks.append(track)

    result: Dict[str, List[Dict[str, Any]]] = {
        "drivers": drivers,
        "tracks": tracks,
    }

    print(f"Transformed {len(drivers)} drivers and {len(tracks)} tracks")
    return result


def _calculate_agility(driver: Dict[str, Any]) -> float:
    """Calculate driver agility metaphysical field.

    Args:
        driver: Driver record

    Returns:
        Agility score between 0 and 1
    """
    # Agility based on top5 percentage and avg_finish
    agility = (1.0 - (driver["avg_finish"] / 43.0)) * 0.6 + (driver["top5"] / 36.0) * 0.4
    return round(min(max(agility, 0.0), 1.0), 4)


def _calculate_fortune(driver: Dict[str, Any]) -> float:
    """Calculate driver fortune metaphysical field.

    Args:
        driver: Driver record

    Returns:
        Fortune score between 0 and 1
    """
    # Fortune based on win rate and recent performance
    fortune = (driver["wins"] / 36.0) * 0.7 + (driver["top10"] / 36.0) * 0.3
    return round(min(max(fortune, 0.0), 1.0), 4)


def _calculate_momentum(driver: Dict[str, Any]) -> float:
    """Calculate driver momentum metaphysical field.

    Args:
        driver: Driver record

    Returns:
        Momentum score between 0 and 1
    """
    # Momentum based on consistency (inverse of avg_finish variance)
    momentum = (1.0 - (driver["avg_finish"] / 43.0)) * (driver["top10"] / 36.0)
    return round(min(max(momentum, 0.0), 1.0), 4)


def _calculate_resonance(driver: Dict[str, Any]) -> float:
    """Calculate driver resonance metaphysical field.

    Args:
        driver: Driver record

    Returns:
        Resonance score between 0 and 1
    """
    # Resonance based on team strength and car number
    resonance = (driver["top5"] / 36.0) * 0.5 + (1.0 - (driver["car_number"] / 99.0)) * 0.5
    return round(min(max(resonance, 0.0), 1.0), 4)


def _calculate_entropy(driver: Dict[str, Any]) -> float:
    """Calculate driver entropy metaphysical field.

    Args:
        driver: Driver record

    Returns:
        Entropy score between 0 and 1
    """
    # Entropy based on unpredictability (inverse of consistency)
    entropy = 1.0 - ((driver["top10"] / 36.0) * 0.7 + (driver["top5"] / 36.0) * 0.3)
    return round(min(max(entropy, 0.0), 1.0), 4)


def _calculate_track_intensity(track: Dict[str, Any]) -> float:
    """Calculate track intensity metaphysical field.

    Args:
        track: Track record

    Returns:
        Intensity score between 0 and 1
    """
    # Intensity based on track type and length
    type_intensity = {
        "Superspeedway": 0.9,
        "Intermediate": 0.6,
        "Short Track": 0.8,
        "Road Course": 0.7,
    }.get(track["track_type"], 0.5)
    return round(type_intensity, 4)


def _calculate_track_chaos(track: Dict[str, Any]) -> float:
    """Calculate track chaos metaphysical field.

    Args:
        track: Track record

    Returns:
        Chaos score between 0 and 1
    """
    # Chaos based on turns and track type
    chaos = (track["turns"] / 14.0) * 0.5 + (1.0 / (track["length"] + 0.1)) * 0.5
    return round(min(max(chaos, 0.0), 1.0), 4)


def _calculate_track_flow(track: Dict[str, Any]) -> float:
    """Calculate track flow metaphysical field.

    Args:
        track: Track record

    Returns:
        Flow score between 0 and 1
    """
    # Flow based on track length and type
    flow = (track["length"] / 3.0) * 0.6 + (1.0 - (track["turns"] / 14.0)) * 0.4
    return round(min(max(flow, 0.0), 1.0), 4)


def load_neo4j(**kwargs: Any) -> None:
    """Load transformed data into Neo4j using Cypher queries.

    This function connects to Neo4j and creates driver and track nodes
    with their metaphysical properties.

    Args:
        **kwargs: Airflow context variables
    """
    # Pull transformed data from the previous task
    ti = kwargs["ti"]
    transformed_data: Dict[str, List[Dict[str, Any]]] = ti.xcom_pull(task_ids="transform")

    drivers: List[Dict[str, Any]] = transformed_data["drivers"]
    tracks: List[Dict[str, Any]] = transformed_data["tracks"]

    print(f"Loading {len(drivers)} drivers and {len(tracks)} tracks into Neo4j")

    # Connect to Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        with driver.session() as session:
            # Create driver nodes
            for driver_record in drivers:
                session.run(
                    """
                    MERGE (d:Driver {driver_id: $driver_id})
                    SET d.name = $name,
                        d.team = $team,
                        d.car_number = $car_number,
                        d.avg_finish = $avg_finish,
                        d.wins = $wins,
                        d.top5 = $top5,
                        d.top10 = $top10,
                        d.metaphysical_agility = $metaphysical_agility,
                        d.metaphysical_fortune = $metaphysical_fortune,
                        d.metaphysical_momentum = $metaphysical_momentum,
                        d.metaphysical_resonance = $metaphysical_resonance,
                        d.metaphysical_entropy = $metaphysical_entropy,
                        d.updated_at = datetime()
                    """,
                    **driver_record,
                )

            # Create track nodes
            for track_record in tracks:
                session.run(
                    """
                    MERGE (t:Track {track_id: $track_id})
                    SET t.name = $name,
                        t.type = $type,
                        t.length = $length,
                        t.turns = $turns,
                        t.metaphysical_intensity = $metaphysical_intensity,
                        t.metaphysical_chaos = $metaphysical_chaos,
                        t.metaphysical_flow = $metaphysical_flow,
                        t.updated_at = datetime()
                    """,
                    **track_record,
                )

            print("Data loaded successfully into Neo4j")

    finally:
        driver.close()


# Define tasks
scrape_task: PythonOperator = PythonOperator(
    task_id="scrape",
    python_callable=scrape_nascar_data,
    dag=dag,
)

transform_task: PythonOperator = PythonOperator(
    task_id="transform",
    python_callable=transform_data,
    dag=dag,
)

load_neo4j_task: PythonOperator = PythonOperator(
    task_id="load_neo4j",
    python_callable=load_neo4j,
    dag=dag,
)

# Set task dependencies
scrape_task >> transform_task >> load_neo4j_task
