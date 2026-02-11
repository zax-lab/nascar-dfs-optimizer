"""
NASCAR DFS Optimizer Dashboard - Axiomatic AI Engine

Streamlit dashboard for the NASCAR DFS optimizer with epistemic-Markov Bayesian optimization.
Features:
- NASCAR red/black theme
- Race selection and data loading
- Optimizer controls for lineup generation
- Lineup display with tabs
- Belief visualization
- Monte Carlo simulation results
- CSV export for DraftKings upload
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io
from typing import List, Dict, Optional, Any
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Database imports
try:
    from apps.backend.app.models import (
        Driver, Race, Belief, Proposition, Agent, SessionLocal
    )
    from apps.backend.app.lineup_optimizer import NASCAROptimizer, create_optimizer
    from projector import EpistemicProjector, create_projector
    from mc_sim import NASCARSimulator, run_simulation
    DB_AVAILABLE = True
except ImportError as e:
    st.error(f"Database module import error: {e}")
    DB_AVAILABLE = False

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== THEME CONFIGURATION ====================
NASCAR_COLORS = {
    'primary': '#E31837',      # NASCAR Red
    'secondary': '#000000',    # Black
    'background': '#1A1A1A',   # Dark Gray
    'text': '#FFFFFF',          # White
    'accent': '#FFD700',        # Yellow
    'success': '#00C851',       # Green
    'warning': '#FFAB00',       # Orange
    'error': '#FF3D00',        # Red
    'info': '#2962FF',         # Blue
}

# ==================== PAGE CONFIGURATION ====================
st.set_page_config(
    page_title="NASCAR DFS Optimizer",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS ====================
def apply_nascar_theme():
    """Apply NASCAR red/black theme to Streamlit app."""
    st.markdown(f"""
    <style>
    /* Main theme colors */
    .stApp {{
        background-color: {NASCAR_COLORS['background']};
    }}
    
    /* Header styling */
    .main-header {{
        background: linear-gradient(135deg, {NASCAR_COLORS['primary']} 0%, {NASCAR_COLORS['secondary']} 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    
    .main-title {{
        color: {NASCAR_COLORS['text']};
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }}
    
    .main-subtitle {{
        color: {NASCAR_COLORS['accent']};
        font-size: 1.2rem;
        margin-top: 0.5rem;
        font-weight: 500;
    }}
    
    /* Sidebar styling */
    .css-1d391kg {{
        background-color: {NASCAR_COLORS['secondary']};
    }}
    
    /* Metric cards */
    .metric-card {{
        background-color: {NASCAR_COLORS['background']};
        border: 2px solid {NASCAR_COLORS['primary']};
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }}
    
    /* Status indicators */
    .status-running {{
        color: {NASCAR_COLORS['accent']};
        font-weight: bold;
    }}
    
    .status-completed {{
        color: {NASCAR_COLORS['success']};
        font-weight: bold;
    }}
    
    .status-failed {{
        color: {NASCAR_COLORS['error']};
        font-weight: bold;
    }}
    
    /* Dataframe styling */
    .stDataFrame {{
        background-color: {NASCAR_COLORS['background']};
        color: {NASCAR_COLORS['text']};
    }}
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 2rem;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background-color: {NASCAR_COLORS['secondary']};
        color: {NASCAR_COLORS['text']};
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1rem;
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: {NASCAR_COLORS['primary']};
        color: {NASCAR_COLORS['text']};
    }}
    
    /* Button styling */
    .stButton>button {{
        background-color: {NASCAR_COLORS['primary']};
        color: {NASCAR_COLORS['text']};
        border: none;
        border-radius: 8px;
        font-weight: bold;
        padding: 0.5rem 1rem;
        transition: all 0.3s;
    }}
    
    .stButton>button:hover {{
        background-color: {NASCAR_COLORS['accent']};
        color: {NASCAR_COLORS['secondary']};
        transform: scale(1.05);
    }}
    
    /* Slider styling */
    .stSlider [data-baseweb="slider"] {{
        color: {NASCAR_COLORS['primary']};
    }}
    
    /* Select box styling */
    .stSelectbox [data-baseweb="selectbox"] {{
        background-color: {NASCAR_COLORS['background']};
        color: {NASCAR_COLORS['text']};
        border: 1px solid {NASCAR_COLORS['primary']};
    }}
    </style>
    """, unsafe_allow_html=True)


# ==================== DATABASE HELPERS ====================
def get_db_session():
    """Get database session with error handling."""
    if not DB_AVAILABLE:
        return None
    try:
        return SessionLocal()
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None


def load_races() -> List[Dict[str, Any]]:
    """
    Load available races from database.
    
    Returns:
        List of race dictionaries with id, name, track, date, status
    """
    if not DB_AVAILABLE:
        # Return sample races for demo
        return [
            {'id': 1, 'name': 'Daytona 500', 'track': 'Daytona International Speedway', 'date': '2024-02-18', 'status': 'scheduled'},
            {'id': 2, 'name': 'Atlanta 500', 'track': 'Atlanta Motor Speedway', 'date': '2024-02-25', 'status': 'scheduled'},
            {'id': 3, 'name': 'Las Vegas 400', 'track': 'Las Vegas Motor Speedway', 'date': '2024-03-03', 'status': 'scheduled'},
        ]
    
    db = get_db_session()
    if not db:
        return []
    
    try:
        races = db.query(Race).order_by(Race.date.desc()).all()
        return [
            {
                'id': r.id,
                'name': r.name,
                'track': r.track,
                'date': r.date.strftime('%Y-%m-%d') if r.date else 'N/A',
                'status': r.status,
                'laps': r.laps
            }
            for r in races
        ]
    except Exception as e:
        st.error(f"Error loading races: {e}")
        return []
    finally:
        db.close()


def load_drivers(race_id: int) -> List[Dict[str, Any]]:
    """
    Load driver data for selected race.
    
    Args:
        race_id: Race identifier
    
    Returns:
        List of driver dictionaries
    """
    if not DB_AVAILABLE:
        # Return sample drivers for demo
        return [
            {'id': 1, 'name': 'Kyle Larson', 'team': 'Hendrick Motorsports', 'car_number': 5, 'salary': 12000, 'avg_finish': 8.5, 'wins': 25, 'top5': 120, 'top10': 180},
            {'id': 2, 'name': 'Denny Hamlin', 'team': 'Joe Gibbs Racing', 'car_number': 11, 'salary': 11500, 'avg_finish': 10.2, 'wins': 50, 'top5': 150, 'top10': 250},
            {'id': 3, 'name': 'Martin Truex Jr.', 'team': 'Joe Gibbs Racing', 'car_number': 19, 'salary': 11000, 'avg_finish': 9.8, 'wins': 35, 'top5': 130, 'top10': 200},
            {'id': 4, 'name': 'Chase Elliott', 'team': 'Hendrick Motorsports', 'car_number': 9, 'salary': 10800, 'avg_finish': 12.1, 'wins': 18, 'top5': 85, 'top10': 140},
            {'id': 5, 'name': 'Ryan Blaney', 'team': 'Team Penske', 'car_number': 12, 'salary': 10500, 'avg_finish': 11.5, 'wins': 15, 'top5': 75, 'top10': 130},
            {'id': 6, 'name': 'Joey Logano', 'team': 'Team Penske', 'car_number': 22, 'salary': 10200, 'avg_finish': 13.2, 'wins': 32, 'top5': 95, 'top10': 160},
        ]
    
    db = get_db_session()
    if not db:
        return []
    
    try:
        drivers = db.query(Driver).all()
        return [
            {
                'id': d.id,
                'name': d.name,
                'team': d.team,
                'car_number': d.car_number,
                'salary': float(d.salary),
                'avg_finish': d.avg_finish,
                'wins': d.wins,
                'top5': d.top5,
                'top10': d.top10
            }
            for d in drivers
        ]
    except Exception as e:
        st.error(f"Error loading drivers: {e}")
        return []
    finally:
        db.close()


def load_beliefs(race_id: int, driver_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Load belief data for visualization.
    
    Args:
        race_id: Race identifier
        driver_id: Optional driver filter
    
    Returns:
        List of belief dictionaries
    """
    if not DB_AVAILABLE:
        # Return sample beliefs for demo
        return [
            {'id': 1, 'driver_id': 1, 'driver_name': 'Kyle Larson', 'confidence': 0.85, 'epistemic_var': 0.12, 'source': 'mc_sim', 'timestamp': '2024-01-26 10:00:00'},
            {'id': 2, 'driver_id': 2, 'driver_name': 'Denny Hamlin', 'confidence': 0.78, 'epistemic_var': 0.15, 'source': 'qualifying', 'timestamp': '2024-01-26 10:30:00'},
            {'id': 3, 'driver_id': 3, 'driver_name': 'Martin Truex Jr.', 'confidence': 0.72, 'epistemic_var': 0.18, 'source': 'practice', 'timestamp': '2024-01-26 11:00:00'},
        ]
    
    db = get_db_session()
    if not db:
        return []
    
    try:
        query = db.query(Belief, Proposition, Driver).join(
            Proposition, Belief.prop_id == Proposition.id
        ).join(
            Driver, Proposition.driver_id == Driver.id
        ).filter(Proposition.race_id == race_id)
        
        if driver_id:
            query = query.filter(Proposition.driver_id == driver_id)
        
        results = query.all()
        return [
            {
                'id': b.id,
                'driver_id': d.id,
                'driver_name': d.name,
                'confidence': b.confidence,
                'epistemic_var': b.epistemic_var,
                'source': b.source,
                'timestamp': b.timestamp.strftime('%Y-%m-%d %H:%M:%S') if b.timestamp else 'N/A'
            }
            for b, p, d in results
        ]
    except Exception as e:
        st.error(f"Error loading beliefs: {e}")
        return []
    finally:
        db.close()


# ==================== OPTIMIZER HELPERS ====================
def generate_lineups(config: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Generate lineups using optimizer.
    
    Args:
        config: Configuration dictionary with race_id, n_lineups, salary_cap, etc.
    
    Returns:
        List of lineup dictionaries or None if error
    """
    if not DB_AVAILABLE:
        # Generate mock lineups for demo
        drivers = load_drivers(config['race_id'])
        lineups = []
        for i in range(config['n_lineups']):
            selected_drivers = np.random.choice(drivers, 6, replace=False).tolist()
            total_salary = sum(d['salary'] for d in selected_drivers)
            total_points = sum(25 + np.random.randint(-5, 15) for _ in range(6))
            lineups.append({
                'lineup_id': i + 1,
                'drivers': selected_drivers,
                'total_salary': total_salary,
                'total_projected_points': total_points,
                'total_value': total_points / total_salary * 1000 if total_salary > 0 else 0,
                'risk_score': np.random.uniform(5, 25)
            })
        return lineups
    
    db = get_db_session()
    if not db:
        return None
    
    try:
        optimizer = create_optimizer(
            db_session=db,
            salary_cap=config['salary_cap'],
            n_drivers=6,
            min_stack=config.get('min_stack', 2),
            max_stack=config.get('max_stack', 3)
        )
        
        lineups = optimizer.optimize_lineup(
            race_id=config['race_id'],
            n_lineups=config['n_lineups'],
            objective=config.get('objective', 'maximize_points')
        )
        
        # Add lineup_id to each lineup
        for idx, lineup in enumerate(lineups, 1):
            lineup['lineup_id'] = idx
        
        return lineups
    except Exception as e:
        st.error(f"Error generating lineups: {e}")
        return None
    finally:
        db.close()


def display_lineup(lineup: Dict[str, Any]) -> None:
    """
    Display single lineup in table format.
    
    Args:
        lineup: Lineup dictionary
    """
    drivers = lineup['drivers']
    
    # Create driver data for table
    driver_data = []
    for driver in drivers:
        # Calculate value score
        expected_points = driver.get('expected_points', 25.0)
        salary = driver.get('salary', 10000)
        value_score = (expected_points / salary * 1000) if salary > 0 else 0
        
        # Get confidence from beliefs if available
        confidence = driver.get('confidence', 0.7)
        epistemic_var = driver.get('epistemic_var', 0.1)
        
        driver_data.append({
            'Name': driver['name'],
            'Team': driver['team'],
            'Car #': driver['car_number'],
            'Salary': f"${salary:,.0f}",
            'Proj. Points': f"{expected_points:.1f}",
            'Value': f"{value_score:.2f}",
            'Confidence': f"{confidence:.2f}",
            'Epistemic Var': f"{epistemic_var:.3f}"
        })
    
    df = pd.DataFrame(driver_data)
    
    # Display driver table
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=300
    )
    
    # Display totals
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Total Salary",
            f"${lineup['total_salary']:,.0f}",
            delta=f"${lineup['total_salary'] - 50000:,.0f}" if lineup['total_salary'] != 50000 else None,
            delta_color="normal" if lineup['total_salary'] <= 50000 else "inverse"
        )
    with col2:
        st.metric(
            "Total Projected Points",
            f"{lineup['total_projected_points']:.1f}"
        )
    with col3:
        st.metric(
            "Value Score",
            f"{lineup['total_value']:.2f}",
            delta=f"Risk: {lineup['risk_score']:.1f}"
        )


def display_beliefs(driver_id: int, race_id: int) -> None:
    """
    Display belief visualization for a driver.
    
    Args:
        driver_id: Driver identifier
        race_id: Race identifier
    """
    beliefs = load_beliefs(race_id, driver_id)
    
    if not beliefs:
        st.info("No belief data available for this driver.")
        return
    
    # Create confidence heatmap
    st.subheader("🎯 Driver Confidence Heat Map")
    
    df_beliefs = pd.DataFrame(beliefs)
    
    # Confidence vs Epistemic Variance scatter
    fig = px.scatter(
        df_beliefs,
        x='confidence',
        y='epistemic_var',
        color='source',
        size='confidence',
        hover_data=['driver_name', 'timestamp'],
        title="Confidence vs Epistemic Variance",
        labels={
            'confidence': 'Confidence',
            'epistemic_var': 'Epistemic Variance',
            'source': 'Source'
        },
        color_discrete_map={
            'mc_sim': NASCAR_COLORS['primary'],
            'qualifying': NASCAR_COLORS['accent'],
            'practice': NASCAR_COLORS['info'],
            'race': NASCAR_COLORS['success']
        }
    )
    
    fig.update_layout(
        plot_bgcolor=NASCAR_COLORS['background'],
        paper_bgcolor=NASCAR_COLORS['background'],
        font=dict(color=NASCAR_COLORS['text']),
        xaxis=dict(gridcolor=NASCAR_COLORS['secondary']),
        yaxis=dict(gridcolor=NASCAR_COLORS['secondary'])
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Belief delta history
    st.subheader("📈 Belief Delta History")
    
    df_beliefs['timestamp'] = pd.to_datetime(df_beliefs['timestamp'])
    df_beliefs = df_beliefs.sort_values('timestamp')
    
    fig_delta = go.Figure()
    
    for source in df_beliefs['source'].unique():
        source_data = df_beliefs[df_beliefs['source'] == source]
        fig_delta.add_trace(go.Scatter(
            x=source_data['timestamp'],
            y=source_data['confidence'],
            mode='lines+markers',
            name=source.upper(),
            line=dict(color=NASCAR_COLORS.get(source, NASCAR_COLORS['primary'])),
            marker=dict(size=8)
        ))
    
    fig_delta.update_layout(
        title="Confidence Timeline",
        xaxis_title="Time",
        yaxis_title="Confidence",
        plot_bgcolor=NASCAR_COLORS['background'],
        paper_bgcolor=NASCAR_COLORS['background'],
        font=dict(color=NASCAR_COLORS['text']),
        xaxis=dict(gridcolor=NASCAR_COLORS['secondary']),
        yaxis=dict(gridcolor=NASCAR_COLORS['secondary']),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_delta, use_container_width=True)
    
    # Epistemic variance bar chart
    st.subheader("⚠️ Epistemic Variance by Source")
    
    fig_var = px.bar(
        df_beliefs,
        x='source',
        y='epistemic_var',
        color='source',
        title="Epistemic Variance by Source",
        labels={
            'source': 'Source',
            'epistemic_var': 'Epistemic Variance'
        }
    )
    
    fig_var.update_layout(
        plot_bgcolor=NASCAR_COLORS['background'],
        paper_bgcolor=NASCAR_COLORS['background'],
        font=dict(color=NASCAR_COLORS['text']),
        xaxis=dict(gridcolor=NASCAR_COLORS['secondary']),
        yaxis=dict(gridcolor=NASCAR_COLORS['secondary'])
    )
    
    st.plotly_chart(fig_var, use_container_width=True)


def display_simulation(driver_id: int, race_id: int) -> None:
    """
    Display Monte Carlo simulation results.
    
    Args:
        driver_id: Driver identifier
        race_id: Race identifier
    """
    st.subheader("🏎️ Monte Carlo Simulation Results")
    
    if not DB_AVAILABLE:
        # Display sample simulation results
        st.info("Sample simulation data (database not connected)")
        
        # Finish position distribution
        finish_dist = {
            'Winner (1st)': 0.15,
            'Top-3': 0.28,
            'Top-5': 0.42,
            'Top-10': 0.65,
            'Top-15': 0.78,
            'Top-20': 0.88,
            'Top-25': 0.94,
            'Top-30': 0.97,
            'Running >30': 0.99,
            'DNF': 0.01
        }
        
        fig_finish = px.bar(
            x=list(finish_dist.keys()),
            y=list(finish_dist.values()),
            title="Finish Position Distribution (10,000 simulations)",
            labels={'x': 'Finish Position', 'y': 'Probability'}
        )
        
        fig_finish.update_layout(
            plot_bgcolor=NASCAR_COLORS['background'],
            paper_bgcolor=NASCAR_COLORS['background'],
            font=dict(color=NASCAR_COLORS['text']),
            xaxis=dict(gridcolor=NASCAR_COLORS['secondary']),
            yaxis=dict(gridcolor=NASCAR_COLORS['secondary'])
        )
        
        st.plotly_chart(fig_finish, use_container_width=True)
        
        # Lap-by-lap position chart
        laps = list(range(1, 201))
        positions = [5 + np.random.randint(-2, 3) for _ in range(200)]
        
        fig_laps = go.Figure()
        fig_laps.add_trace(go.Scatter(
            x=laps,
            y=positions,
            mode='lines',
            name='Position',
            line=dict(color=NASCAR_COLORS['primary'], width=2)
        ))
        
        fig_laps.update_layout(
            title="Lap-by-Lap Position (Sample Path)",
            xaxis_title="Lap",
            yaxis_title="Position State",
            plot_bgcolor=NASCAR_COLORS['background'],
            paper_bgcolor=NASCAR_COLORS['background'],
            font=dict(color=NASCAR_COLORS['text']),
            xaxis=dict(gridcolor=NASCAR_COLORS['secondary']),
            yaxis=dict(gridcolor=NASCAR_COLORS['secondary'])
        )
        
        st.plotly_chart(fig_laps, use_container_width=True)
        
        # Simulation statistics
        st.subheader("📊 Simulation Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Simulations", "10,000")
        with col2:
            st.metric("Avg Finish Position", "8.5")
        with col3:
            st.metric("Top-10 Probability", "65%")
        
        # World probability distribution
        st.subheader("🌍 World Probability Distribution")
        
        world_probs = {
            'World 1': 0.25,
            'World 2': 0.30,
            'World 3': 0.20,
            'World 4': 0.15,
            'World 5': 0.10
        }
        
        fig_worlds = px.pie(
            values=list(world_probs.values()),
            names=list(world_probs.keys()),
            title="World Probability Distribution",
            hole=0.3
        )
        
        fig_worlds.update_traces(
            marker=dict(colors=[
                NASCAR_COLORS['primary'],
                NASCAR_COLORS['accent'],
                NASCAR_COLORS['info'],
                NASCAR_COLORS['success'],
                NASCAR_COLORS['warning']
            ])
        )
        
        fig_worlds.update_layout(
            plot_bgcolor=NASCAR_COLORS['background'],
            paper_bgcolor=NASCAR_COLORS['background'],
            font=dict(color=NASCAR_COLORS['text'])
        )
        
        st.plotly_chart(fig_worlds, use_container_width=True)
        return
    
    db = get_db_session()
    if not db:
        st.error("Cannot connect to database for simulation data.")
        return
    
    try:
        # Load simulation data from database
        # This would query World and Run tables
        st.info("Simulation data loading from database...")
        
    except Exception as e:
        st.error(f"Error loading simulation data: {e}")
    finally:
        db.close()


def export_csv(lineup: Dict[str, Any]) -> str:
    """
    Export lineup to CSV format for DraftKings upload.
    
    Args:
        lineup: Lineup dictionary
    
    Returns:
        CSV string
    """
    drivers = lineup['drivers']
    
    csv_data = []
    for driver in drivers:
        csv_data.append({
            'DriverID': driver['id'],
            'Name': driver['name'],
            'Team': driver['team'],
            'CarNumber': driver['car_number'],
            'Salary': driver['salary'],
            'ProjectedPoints': driver.get('expected_points', 25.0)
        })
    
    df = pd.DataFrame(csv_data)
    return df.to_csv(index=False)


def export_multiple_lineups_csv(lineups: List[Dict[str, Any]]) -> str:
    """
    Export multiple lineups to CSV format.
    
    Args:
        lineups: List of lineup dictionaries
    
    Returns:
        CSV string
    """
    csv_data = []
    
    for lineup in lineups:
        for driver in lineup['drivers']:
            csv_data.append({
                'Lineup': lineup['lineup_id'],
                'DriverID': driver['id'],
                'Name': driver['name'],
                'Team': driver['team'],
                'CarNumber': driver['car_number'],
                'Salary': driver['salary'],
                'ProjectedPoints': driver.get('expected_points', 25.0)
            })
    
    df = pd.DataFrame(csv_data)
    return df.to_csv(index=False)


# ==================== MAIN DASHBOARD ====================
def main():
    """Main Streamlit application."""
    
    # Apply NASCAR theme
    apply_nascar_theme()
    
    # Initialize session state
    if 'selected_race' not in st.session_state:
        st.session_state.selected_race = None
    if 'generated_lineups' not in st.session_state:
        st.session_state.generated_lineups = []
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()
    
    # ==================== HEADER SECTION ====================
    st.markdown(f"""
    <div class="main-header">
        <h1 class="main-title">🏁 NASCAR DFS Optimizer - Axiomatic AI Engine</h1>
        <p class="main-subtitle">Epistemic-Markov Bayesian Optimization</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Last updated timestamp
    st.caption(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ==================== SIDEBAR CONTROLS ====================
    with st.sidebar:
        st.header("⚙️ Controls")
        
        # Race selection
        st.subheader("🏁 Race Selection")
        races = load_races()
        
        if races:
            race_options = {f"{r['name']} ({r['date']})": r for r in races}
            selected_race_name = st.selectbox(
                "Select Race",
                options=list(race_options.keys()),
                index=0 if not st.session_state.selected_race else None
            )
            
            if selected_race_name:
                st.session_state.selected_race = race_options[selected_race_name]
                race = st.session_state.selected_race
                
                # Display race info
                st.info(f"""
                **Track:** {race['track']}  
                **Date:** {race['date']}  
                **Laps:** {race.get('laps', 'N/A')}  
                **Status:** {race['status']}
                """)
        else:
            st.warning("No races available in database.")
            st.session_state.selected_race = None
        
        st.divider()
        
        # Optimizer controls
        st.subheader("🎯 Optimizer Settings")
        
        salary_cap = st.slider(
            "Salary Cap",
            min_value=40000,
            max_value=60000,
            value=50000,
            step=1000,
            format="$%d"
        )
        
        n_lineups = st.slider(
            "Number of Lineups",
            min_value=1,
            max_value=20,
            value=5,
            step=1
        )
        
        stacking_strategy = st.selectbox(
            "Stacking Strategy",
            options=['none', 'min2', 'max3', 'custom'],
            index=0
        )
        
        objective = st.selectbox(
            "Optimization Objective",
            options=['max_points', 'max_value', 'min_risk'],
            format_func=lambda x: {
                'max_points': 'Maximize Points',
                'max_value': 'Maximize Value',
                'min_risk': 'Minimize Risk'
            }.get(x, x)
        )
        
        st.divider()
        
        # Action buttons
        st.subheader("🚀 Actions")
        
        col1, col2 = st.columns(2)
        with col1:
            generate_btn = st.button("Generate Lineups", type="primary", use_container_width=True)
        with col2:
            refresh_btn = st.button("🔄 Refresh Data", use_container_width=True)
        
        if refresh_btn:
            st.session_state.last_update = datetime.now()
            st.rerun()
        
        st.divider()
        
        # Data pipeline status
        st.subheader("📊 Pipeline Status")
        
        status_col1, status_col2 = st.columns(2)
        with status_col1:
            etl_status = st.selectbox("ETL Status", ['running', 'completed', 'failed'], index=1)
            mc_status = st.selectbox("MC Sim Status", ['running', 'completed', 'failed'], index=1)
        with status_col2:
            belief_status = st.selectbox("Belief Projection", ['running', 'completed', 'failed'], index=1)
            db_status = st.selectbox("Database", ['connected', 'disconnected'], index=0 if DB_AVAILABLE else 1)
        
        # Auto-refresh setting
        st.divider()
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
        
        if auto_refresh:
            import time
            time.sleep(30)
            st.rerun()
    
    # ==================== MAIN CONTENT AREA ====================
    if not st.session_state.selected_race:
        st.info("👆 Please select a race from the sidebar to begin.")
        return
    
    race_id = st.session_state.selected_race['id']
    
    # Generate lineups button handler
    if generate_btn:
        with st.spinner("Generating optimal lineups..."):
            config = {
                'race_id': race_id,
                'n_lineups': n_lineups,
                'salary_cap': salary_cap,
                'stacking_strategy': stacking_strategy,
                'objective': objective,
                'min_stack': 2 if stacking_strategy != 'none' else 1,
                'max_stack': 3 if stacking_strategy != 'none' else 6
            }
            
            lineups = generate_lineups(config)
            
            if lineups:
                st.session_state.generated_lineups = lineups
                st.success(f"✅ Generated {len(lineups)} optimal lineups!")
            else:
                st.error("❌ Failed to generate lineups. Please check configuration.")
    
    # ==================== LINEUP DISPLAY ====================
    if st.session_state.generated_lineups:
        st.header("🏆 Generated Lineups")
        
        lineups = st.session_state.generated_lineups
        
        # Create tabs for multiple lineups
        tab_names = [f"Lineup {l['lineup_id']}" for l in lineups]
        tabs = st.tabs(tab_names)
        
        for tab, lineup in zip(tabs, lineups):
            with tab:
                display_lineup(lineup)
                
                # Export button for single lineup
                csv_data = export_csv(lineup)
                st.download_button(
                    label="📥 Export Lineup to CSV",
                    data=csv_data,
                    file_name=f"lineup_{lineup['lineup_id']}_race_{race_id}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        # Export all lineups button
        st.divider()
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            all_csv_data = export_multiple_lineups_csv(lineups)
            st.download_button(
                label="📥 Export All Lineups to CSV",
                data=all_csv_data,
                file_name=f"all_lineups_race_{race_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # Team distribution chart
        st.subheader("📊 Team Distribution")
        
        # Aggregate team counts across all lineups
        team_counts = {}
        for lineup in lineups:
            for driver in lineup['drivers']:
                team = driver['team']
                team_counts[team] = team_counts.get(team, 0) + 1
        
        fig_teams = px.bar(
            x=list(team_counts.keys()),
            y=list(team_counts.values()),
            title="Team Distribution Across All Lineups",
            labels={'x': 'Team', 'y': 'Count'}
        )
        
        fig_teams.update_layout(
            plot_bgcolor=NASCAR_COLORS['background'],
            paper_bgcolor=NASCAR_COLORS['background'],
            font=dict(color=NASCAR_COLORS['text']),
            xaxis=dict(gridcolor=NASCAR_COLORS['secondary']),
            yaxis=dict(gridcolor=NASCAR_COLORS['secondary'])
        )
        
        st.plotly_chart(fig_teams, use_container_width=True)
        
        # Risk metrics
        st.subheader("⚠️ Risk Metrics")
        
        risk_data = []
        for lineup in lineups:
            risk_data.append({
                'Lineup': f"Lineup {lineup['lineup_id']}",
                'Risk Score': lineup['risk_score'],
                'Total Salary': lineup['total_salary'],
                'Projected Points': lineup['total_projected_points']
            })
        
        df_risk = pd.DataFrame(risk_data)
        st.dataframe(df_risk, use_container_width=True, hide_index=True)
    
    # ==================== BELIEF VISUALIZATION ====================
    st.header("🎯 Belief Visualization")
    
    # Driver selector for beliefs
    drivers = load_drivers(race_id)
    if drivers:
        driver_options = {f"{d['name']} (#{d['car_number']})": d['id'] for d in drivers}
        selected_driver_name = st.selectbox(
            "Select Driver for Belief Analysis",
            options=list(driver_options.keys()),
            index=0
        )
        
        if selected_driver_name:
            selected_driver_id = driver_options[selected_driver_name]
            display_beliefs(selected_driver_id, race_id)
    
    # ==================== MC SIMULATION RESULTS ====================
    st.header("🏎️ Monte Carlo Simulation Results")
    
    # Driver selector for simulation
    if drivers:
        selected_sim_driver_name = st.selectbox(
            "Select Driver for Simulation Analysis",
            options=list(driver_options.keys()),
            index=0,
            key="sim_driver_selector"
        )
        
        if selected_sim_driver_name:
            selected_sim_driver_id = driver_options[selected_sim_driver_name]
            display_simulation(selected_sim_driver_id, race_id)
    
    # ==================== FOOTER ====================
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p>🏁 NASCAR DFS Optimizer - Axiomatic AI Engine</p>
        <p>Epistemic-Markov Bayesian Optimization for DraftKings DFS</p>
        <p style='font-size: 0.8rem;'>© 2024 NASCAR DFS Optimizer. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
