import os
import pytest
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "CHANGE_ME_TO_SECURE_PASSWORD")

@pytest.fixture(scope="module")
def neo4j_driver():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    yield driver
    driver.close()

def test_fetch_metaphysical_properties(neo4j_driver):
    """Fetch metaphysical properties for a specific driver and verify types/bounds."""
    driver_id = "1" # Ryan Blaney
    with neo4j_driver.session() as session:
        result = session.run("""
            MATCH (d:Driver {driver_id: $driver_id})
            RETURN d.name as name, d.skill as skill, d.psyche_aggression as aggression, d.shadow_risk as risk
        """, driver_id=driver_id)
        
        record = result.single()
        assert record is not None, f"Driver with driver_id {driver_id} not found."
        
        print(f"Driver: {record['name']}")
        print(f"Skill: {record['skill']} (Type: {type(record['skill'])})")
        print(f"Aggression: {record['aggression']} (Type: {type(record['aggression'])})")
        print(f"Risk: {record['risk']} (Type: {type(record['risk'])})")
        
        # Verify types (should be float or int that can be cast to float)
        assert isinstance(record['skill'], (int, float))
        assert isinstance(record['aggression'], (int, float))
        assert isinstance(record['risk'], (int, float))
        
        # Verify bounds (0-1)
        assert 0 <= record['skill'] <= 1
        assert 0 <= record['aggression'] <= 1
        assert 0 <= record['risk'] <= 1
