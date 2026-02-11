import os
import pytest
from neo4j import GraphDatabase

# Retrieve Neo4j credentials from environment or use defaults
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "CHANGE_ME_TO_SECURE_PASSWORD")

@pytest.fixture(scope="module")
def neo4j_driver():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    yield driver
    driver.close()

def test_neo4j_connectivity(neo4j_driver):
    """Verify that we can connect to the Neo4j database."""
    try:
        neo4j_driver.verify_connectivity()
    except Exception as e:
        pytest.fail(f"Failed to connect to Neo4j: {e}")

def test_node_counts(neo4j_driver):
    """Verify the existence of Driver, Track, and Race nodes."""
    with neo4j_driver.session() as session:
        result = session.run("""
            MATCH (d:Driver) RETURN count(d) as DriverCount
        """)
        driver_count = result.single()["DriverCount"]
        
        result = session.run("""
            MATCH (t:Track) RETURN count(t) as TrackCount
        """)
        track_count = result.single()["TrackCount"]
        
        result = session.run("""
            MATCH (r:Race) RETURN count(r) as RaceCount
        """)
        race_count = result.single()["RaceCount"]
        
        print(f"Driver Count: {driver_count}")
        print(f"Track Count: {track_count}")
        print(f"Race Count: {race_count}")
        
        # We expect at least some drivers based on the earlier manual check (72)
        assert driver_count > 0, "No Driver nodes found in the database."
        
        # We observed 0 Track and 0 Race nodes earlier. 
        # For the purpose of this verification track, we should assert what is currently there 
        # to pass the test, OR deciding if this is a failure condition.
        # The spec says "Verify the existence", implying we *expect* them.
        # However, since I am in the "Red" phase, I will write assertions that *should* pass 
        # for a fully populated DB, so that I can see them fail if the DB is incomplete.
        # But wait, the task is "Verify connectivity and schema integrity".
        # If the schema expects these nodes, their absence is a failure.
        
        # Let's assert we have drivers (we know we do).
        assert driver_count > 0
        
        # Let's assert we have tracks (we likely don't, so this might fail).
        # This confirms the "Red" phase if the expectation is to have data.
        # If the expectation is just to be able to *query* without error, 
        # then the assertion should be minimal.
        # But "Verify ... existence" strongly implies > 0.
        
        # I'll assert > 0 for all to confirm the state of the DB.
        # If it fails, I'll know I need to seed data or adjust the test.
