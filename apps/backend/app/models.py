"""
Epistemic Database Schema for NASCAR DFS Optimizer.

This module defines SQLAlchemy ORM models for the axiomatic AI framework,
implementing an epistemic reasoning system for belief management in NASCAR
DFS optimization. The schema supports:

- Agent-based belief tracking across multiple AI components
- Proposition representation for race-related assertions
- World modeling for Monte Carlo simulation scenarios
- Belief states with confidence levels and epistemic variance
- Run tracking for simulation executions
- Update logging for belief revision operations

The epistemic framework enables:
1. Prior belief initialization from historical data
2. Bayesian belief updates from qualifying/practice results
3. AGM contraction/expansion for minimal belief change
4. Confidence tracking across multiple simulation worlds
5. Audit trail of all belief revisions
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    JSON,
    ForeignKey,
    Boolean,
    DateTime,
    Index,
    create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from fastapi import Depends

# Declarative base for all models
Base = declarative_base()


class Agent(Base):
    """
    Represents an AI agent in the epistemic framework.
    
    Agents are autonomous components that form and update beliefs about
    NASCAR race outcomes. Different agent types specialize in different
    aspects of race prediction:
    
    - optimizer: Generates optimal DFS lineups based on current beliefs
    - simulator: Runs Monte Carlo simulations to generate world scenarios
    - projector: Projects driver performance based on historical data
    
    Attributes:
        id: Primary key identifier
        name: Human-readable agent name
        type: Agent type classification
        created_at: Timestamp of agent creation
        active: Whether agent is currently active in the system
    """
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # "optimizer", "simulator", "projector"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    # Relationships
    beliefs = relationship(
        "Belief",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    runs = relationship(
        "Run",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    updates = relationship(
        "Update",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}', type='{self.type}', active={self.active})>"


class Proposition(Base):
    """
    Represents a proposition about a NASCAR race outcome.
    
    Propositions are atomic statements about race events that can be
    believed or disbelieved by agents. They serve as the basic units
    of epistemic reasoning in the system.
    
    Examples:
    - "Larson top-3 at Daytona"
    - "Hamlin wins the race"
    - "Truex finishes in top-10"
    
    Attributes:
        id: Primary key identifier
        content: Natural language proposition statement
        driver_id: Foreign key to driver table
        race_id: Foreign key to race table
        session_type: Type of session (qualifying, practice, race)
        created_at: Timestamp of proposition creation
    """
    __tablename__ = "propositions"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String(500), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False, index=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False, index=True)
    session_type = Column(String(50), nullable=False, index=True)  # "qualifying", "practice", "race"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    beliefs = relationship(
        "Belief",
        back_populates="proposition",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    # Indexes for common queries
    __table_args__ = (
        Index('idx_proposition_driver_race', 'driver_id', 'race_id'),
        Index('idx_proposition_session', 'session_type', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<Proposition(id={self.id}, content='{self.content[:50]}...', session_type='{self.session_type}')>"


class World(Base):
    """
    Represents a possible world in Monte Carlo simulation.
    
    Worlds encapsulate specific race scenarios generated through Monte Carlo
    simulation. Each world represents one possible trajectory of the race,
    including caution laps, tire wear, weather conditions, and other factors.
    
    The probability field indicates the likelihood of this world occurring
    based on the simulation ensemble.
    
    Attributes:
        id: Primary key identifier
        scenario: JSON object containing lap-by-lap scenario details
        mc_path_id: Reference to the Monte Carlo simulation path
        probability: Probability of this world occurring (0-1)
        created_at: Timestamp of world creation
    """
    __tablename__ = "worlds"

    id = Column(Integer, primary_key=True, index=True)
    scenario = Column(JSON, nullable=False)  # {caution_laps, tire_model, weather, ...}
    mc_path_id = Column(String(100), nullable=False, index=True)  # Reference to MC simulation
    probability = Column(Float, nullable=False)  # Probability of this world
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    beliefs = relationship(
        "Belief",
        back_populates="world",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<World(id={self.id}, mc_path_id='{self.mc_path_id}', probability={self.probability})>"


class Belief(Base):
    """
    Represents an agent's belief state about a proposition.
    
    Beliefs are the core epistemic entities, representing what an agent
    believes to be true about race outcomes. Each belief is associated with:
    
    - An agent (who holds the belief)
    - A proposition (what is believed)
    - Optionally, a world (in which context the belief holds)
    
    The confidence field represents the agent's degree of belief (0-1),
    while epistemic_var captures the uncertainty in that belief.
    
    Attributes:
        id: Primary key identifier
        agent_id: Foreign key to agent table
        prop_id: Foreign key to proposition table
        world_id: Foreign key to world table (nullable for general beliefs)
        confidence: Degree of belief (0-1)
        epistemic_var: Epistemic variance/uncertainty
        timestamp: When this belief state was recorded
        source: Source of this belief (prior, mc_sim, qualifying, practice)
    """
    __tablename__ = "beliefs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    prop_id = Column(Integer, ForeignKey("propositions.id"), nullable=False, index=True)
    world_id = Column(Integer, ForeignKey("worlds.id"), nullable=True, index=True)
    confidence = Column(Float, nullable=False)  # 0-1 confidence level
    epistemic_var = Column(Float, nullable=False)  # Epistemic variance
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    source = Column(String(50), nullable=False, index=True)  # "prior", "mc_sim", "qualifying", "practice"

    # Relationships
    agent = relationship("Agent", back_populates="beliefs")
    proposition = relationship("Proposition", back_populates="beliefs")
    world = relationship("World", back_populates="beliefs")
    updates = relationship(
        "Update",
        back_populates="belief",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    # Indexes for common queries
    __table_args__ = (
        Index('idx_belief_agent_prop', 'agent_id', 'prop_id'),
        Index('idx_belief_world', 'world_id', 'confidence'),
        Index('idx_belief_source_time', 'source', 'timestamp'),
    )

    def update_confidence(
        self,
        new_confidence: float,
        evidence: Dict[str, Any],
        update_type: str = "bayesian",
        session: Optional[Session] = None
    ) -> "Update":
        """
        Update belief confidence and create an Update record.
        
        This method implements belief revision by updating the confidence
        level and logging the change for audit purposes. The delta is
        automatically calculated as new_confidence - old_confidence.
        
        Args:
            new_confidence: New confidence value (0-1)
            evidence: JSON object describing what caused the update
            update_type: Type of belief update (bayesian, agm, minimal_change)
            session: SQLAlchemy session (uses current session if None)
            
        Returns:
            Update: The created Update record
            
        Raises:
            ValueError: If new_confidence is not in [0, 1]
        """
        if not 0 <= new_confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        
        old_confidence = self.confidence
        delta = new_confidence - old_confidence
        
        # Create update record
        update = Update(
            agent_id=self.agent_id,
            belief_id=self.id,
            old_confidence=old_confidence,
            new_confidence=new_confidence,
            delta=delta,
            evidence=evidence,
            update_type=update_type
        )
        
        # Update belief
        self.confidence = new_confidence
        self.timestamp = datetime.utcnow()
        
        return update

    def __repr__(self) -> str:
        world_str = f", world_id={self.world_id}" if self.world_id else ""
        return f"<Belief(id={self.id}, agent_id={self.agent_id}, prop_id={self.prop_id}{world_str}, confidence={self.confidence})>"


class Run(Base):
    """
    Represents a complete simulation run by an agent.
    
    Runs track the execution of Monte Carlo simulations or other
    computational processes that generate belief updates. Each run
    captures the initial and final belief states, allowing for
    analysis of how beliefs evolved during the simulation.
    
    The mc_path field contains the detailed trajectory of the simulation,
    including lap-by-lap positions, cautions, and other events.
    
    Attributes:
        id: Primary key identifier
        agent_id: Foreign key to agent table
        mc_path: JSON array of simulation steps
        start_beliefs: JSON object of initial belief states
        end_beliefs: JSON object of final belief states
        created_at: Timestamp of run creation
        status: Run status (running, completed, failed)
    """
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    mc_path = Column(JSON, nullable=False)  # [{lap: 1, pos: 5, ...}, ...]
    start_beliefs = Column(JSON, nullable=False)  # Initial belief states
    end_beliefs = Column(JSON, nullable=False)  # Final belief states
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), nullable=False, index=True)  # "running", "completed", "failed"

    # Relationships
    agent = relationship("Agent", back_populates="runs")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_run_agent_status', 'agent_id', 'status'),
        Index('idx_run_created', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize run to dictionary for JSON responses.
        
        Returns:
            Dict containing all run fields in a serializable format
        """
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "mc_path": self.mc_path,
            "start_beliefs": self.start_beliefs,
            "end_beliefs": self.end_beliefs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status
        }

    def __repr__(self) -> str:
        return f"<Run(id={self.id}, agent_id={self.agent_id}, status='{self.status}')>"


class Update(Base):
    """
    Represents a belief revision operation.
    
    Updates track all changes to belief states, providing a complete
    audit trail of the epistemic reasoning process. Each update
    records:
    
    - The agent performing the update
    - The belief being updated
    - The old and new confidence values
    - The delta (change) in confidence
    - The evidence that caused the update
    - The type of belief revision algorithm used
    
    This enables traceability and debugging of the belief revision
    process, which is critical for understanding and improving the
    system's epistemic reasoning.
    
    Attributes:
        id: Primary key identifier
        agent_id: Foreign key to agent table
        belief_id: Foreign key to belief table
        old_confidence: Confidence before update
        new_confidence: Confidence after update
        delta: Change in confidence (new - old)
        evidence: JSON object describing what caused the update
        update_type: Type of belief update (bayesian, agm, minimal_change)
        timestamp: When the update occurred
    """
    __tablename__ = "updates"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    belief_id = Column(Integer, ForeignKey("beliefs.id"), nullable=False, index=True)
    old_confidence = Column(Float, nullable=False)
    new_confidence = Column(Float, nullable=False)
    delta = Column(Float, nullable=False)  # new_confidence - old_confidence
    evidence = Column(JSON, nullable=False)  # What caused the update
    update_type = Column(String(50), nullable=False, index=True)  # "bayesian", "agm", "minimal_change"
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="updates")
    belief = relationship("Belief", back_populates="updates")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_update_belief_time', 'belief_id', 'timestamp'),
        Index('idx_update_agent_type', 'agent_id', 'update_type'),
    )

    def __repr__(self) -> str:
        return f"<Update(id={self.id}, belief_id={self.belief_id}, delta={self.delta}, type='{self.update_type}')>"


class Driver(Base):
    """
    Represents a NASCAR driver.
    
    This model stores driver information used for DFS optimization
    and belief formation. Drivers are referenced by propositions
    and serve as the primary entities about which beliefs are formed.
    
    Attributes:
        id: Primary key identifier
        name: Driver's full name
        team: Driver's team name
        car_number: Car number (1-99)
        salary: DraftKings salary for DFS
        avg_finish: Average finishing position
        wins: Number of career wins
        top5: Number of top-5 finishes
        top10: Number of top-10 finishes
    """
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    team = Column(String(100), nullable=False)
    car_number = Column(Integer, nullable=False)
    salary = Column(Float, nullable=False)  # DraftKings salary
    avg_finish = Column(Float, nullable=True)
    wins = Column(Integer, default=0, nullable=False)
    top5 = Column(Integer, default=0, nullable=False)
    top10 = Column(Integer, default=0, nullable=False)

    # Relationships (propositions reference drivers)
    propositions = relationship(
        "Proposition",
        back_populates="driver",
        lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Driver(id={self.id}, name='{self.name}', car_number={self.car_number}, salary={self.salary})>"


class Race(Base):
    """
    Represents a NASCAR race event.
    
    This model stores race information used for DFS optimization
    and belief formation. Races are referenced by propositions
    and provide the context for belief formation.
    
    Attributes:
        id: Primary key identifier
        name: Race name (e.g., "Daytona 500")
        track: Track name (e.g., "Daytona International Speedway")
        date: Scheduled race date
        laps: Total number of laps in the race
        status: Race status (scheduled, in_progress, completed)
    """
    __tablename__ = "races"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    track = Column(String(200), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    laps = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, index=True)  # "scheduled", "in_progress", "completed"

    # Relationships (propositions reference races)
    propositions = relationship(
        "Proposition",
        back_populates="race",
        lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Race(id={self.id}, name='{self.name}', track='{self.track}', status='{self.status}')>"


# Database configuration
DATABASE_URL = "sqlite:///./epistemic.db"  # Default to SQLite, can be overridden

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False  # Set to True for SQL query logging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_all_tables() -> None:
    """
    Create all database tables.
    
    This function creates all tables defined in the schema if they
    don't already exist. It's safe to call multiple times as it uses
    SQLAlchemy's create_all which only creates missing tables.
    
    Note: This should be called during application initialization,
    typically in a startup event or migration script.
    """
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """
    FastAPI dependency for getting database sessions.
    
    This function provides a database session to FastAPI route handlers.
    The session is automatically closed after the request is processed.
    
    Usage:
        @app.get("/beliefs")
        def get_beliefs(db: Session = Depends(get_db)):
            beliefs = db.query(Belief).all()
            return beliefs
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database with default data.
    
    This function creates tables and optionally seeds the database
    with initial data such as default agents, sample drivers,
    and reference races. This is useful for development and testing.
    
    Note: This is a convenience function and should be customized
    based on application requirements.
    """
    # Create all tables
    create_all_tables()
    
    # Create default agents if they don't exist
    db = SessionLocal()
    try:
        if db.query(Agent).count() == 0:
            default_agents = [
                Agent(name="Optimizer Agent", type="optimizer", active=True),
                Agent(name="Simulator Agent", type="simulator", active=True),
                Agent(name="Projector Agent", type="projector", active=True),
            ]
            db.add_all(default_agents)
            db.commit()
    finally:
        db.close()
