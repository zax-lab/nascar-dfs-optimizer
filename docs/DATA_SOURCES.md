# NASCAR DFS Data Sources

**Last Updated:** February 2, 2026

This document catalogs real data sources for the NASCAR DFS Optimizer, organized by data type and access method.

---

## ⭐ Recommended: Lap Raptor

**URL:** [lapraptor.com](https://lapraptor.com)

Lap Raptor is an excellent choice for NASCAR analytics and loop data. Key features:

### What Lap Raptor Offers

| Data Type | Description | URL |
|-----------|-------------|-----|
| **Loop Data Index** | Complete NASCAR loop data with search, filter, and CSV download | [lapraptor.com/drivers/race-log-index](https://lapraptor.com/drivers/race-log-index) |
| **Pass Matrix** | Visual analysis of passing patterns | [lapraptor.com/matrix/pass/](https://lapraptor.com/matrix/pass/) |
| **Stats by Track** | Track-specific driver performance | [lapraptor.com/indexes/nascar/stats-by-track](https://lapraptor.com/indexes/nascar/stats-by-track) |
| **Driver Profiles** | Detailed driver statistics | [lapraptor.com/drivers/](https://lapraptor.com/drivers/) |
| **Race Results** | Historical race data with lap-by-lap analysis | [lapraptor.com/races/](https://lapraptor.com/races/) |
| **Stat Pack Recaps** | Pre-race analysis articles | [blog.lapraptor.com](https://blog.lapraptor.com) |

### Loop Data Metrics Available

- Average Running Position
- Driver Rating
- Fastest Laps Run
- Green Flag Passes
- Laps in Top 15
- Quality Passes
- Laps Led

### How to Get Data

1. Navigate to [Loop Data Index](https://lapraptor.com/drivers/race-log-index)
2. Use filters to select series, drivers, tracks, or date range
3. Click **"Download CSV (all rows)"** for complete dataset

---

## API-Based Data Sources

### 1. Sportradar (Official NASCAR Partner)

**URL:** [sportradar.com/sports/nascar](https://sportradar.com/sports/nascar)

| Feature | Description |
|---------|-------------|
| **Coverage** | Cup, Xfinity, Truck Series |
| **Real-time Data** | Live race leaderboards, lap times, positions |
| **Static Data** | Entry lists, practice/qualifying results, seasonal stats |
| **Source** | Direct from NASCAR's Fuel API |
| **Access** | Free trial key via Developer Portal |

**Best for:** Live race tracking, official data verification

---

### 2. SportsDataIO (Fantasy-Focused)

**URL:** [sportsdata.io/nascar](https://sportsdata.io/developers/data-coverage/nascar)

| Feature | Description |
|---------|-------------|
| **Fantasy Projections** | DraftKings and FanDuel scoring formats |
| **DFS Salaries** | DraftKings salary data |
| **Historical Stats** | Driver averages, track performance |
| **Free Tier** | Last season's data via Discovery Lab |
| **Format** | JSON / XML |

**Best for:** DFS projections, salary integration

---

### 3. OddsMatrix

**URL:** [oddsmatrix.com/nascar](https://oddsmatrix.com)

| Feature | Description |
|---------|-------------|
| **Betting Odds** | Pre-race and live odds |
| **Lap-by-lap Data** | Real-time position updates |
| **Pit Stop Analytics** | Duration, strategy analysis |
| **Format** | JSON / XML |

**Best for:** Betting odds integration, live analytics

---

## Free Historical Data Sources

### 4. nascaR.data (R Package)

**GitHub:** [github.com/kyleGrealis/nascaR.data](https://github.com/kyleGrealis/nascaR.data)

| Feature | Description |
|---------|-------------|
| **Coverage** | Cup (1949-2024), Xfinity (1982-2024), Trucks (1995-2024) |
| **Data Source** | DriverAverages.com (with permission) |
| **Updates** | Weekly during race season |
| **Format** | R data frames (exportable to CSV) |

**Best for:** Historical analysis, model training data

**How to Use:**

```R
# Install
install.packages("nascaR.data")

# Load data
library(nascaR.data)
data(cup_race_results)
```

---

### 5. Kaggle NASCAR Datasets

**URL:** [kaggle.com/datasets?search=nascar](https://kaggle.com/datasets?search=nascar)

| Dataset | Description |
|---------|-------------|
| **NASCAR Season History (1949-Present)** | Champions, manufacturers, wins by season |
| **Race Results** | Various contributor datasets |

**Best for:** Quick historical snapshots, learning/prototyping

---

### 6. Racing-Reference.info

**URL:** [racing-reference.info](https://racing-reference.info)

| Feature | Description |
|---------|-------------|
| **Coverage** | Complete NASCAR history |
| **Driver Stats** | Career statistics, head-to-head |
| **Track Stats** | Historical track performance |
| **Access** | Manual (no API, scraping restricted) |

**Best for:** Reference, verification, manual lookup

⚠️ **Note:** Automated scraping is prohibited by their ToS. Use for reference only.

---

### 7. DriverAverages.com

**URL:** [driveraverages.com](https://driveraverages.com)

| Feature | Description |
|---------|-------------|
| **Track Averages** | Driver average finishes by track |
| **Track Type Averages** | Performance by track type (superspeedway, short track, etc.) |
| **Car Number History** | Historical car ownership |

**Best for:** Track-type analysis, baseline projections

---

## DFS-Specific Sources

### 8. FRCS.pro

**URL:** [frcs.pro](https://frcs.pro)

| Feature | Description |
|---------|-------------|
| **Interactive Loop Data** | Cup, Xfinity, Truck Series |
| **Salary Tier Analysis** | Dynamic salary categorization |
| **DFS Tools** | Lineup optimization support |

**Best for:** DFS research, salary tier analysis

---

### 9. Fantasy Alarm

**URL:** [fantasyalarm.com/nascar](https://fantasyalarm.com/nascar)

| Feature | Description |
|---------|-------------|
| **Projections** | DraftKings and FanDuel |
| **Value Scores** | Salary vs. upside analysis |
| **Ownership Projections** | Expected roster percentages |

**Best for:** Ownership leverage, GPP strategies

---

### 10. WIN THE RACE

**URL:** [wintherace.info](https://wintherace.info)

| Feature | Description |
|---------|-------------|
| **Free Loop Data Archives** | Historical loop data |
| **Driver Ratings** | Performance metrics |

**Best for:** Free historical loop data access

---

## Data Integration Priority

For your NASCAR DFS Optimizer, I recommend integrating data sources in this order:

### Phase 1: Core Historical Data

1. **Lap Raptor** - Loop data CSV downloads → `/data/historical/`
2. **nascaR.data** - R package for 75+ years of results
3. **Kaggle** - Supplementary historical datasets

### Phase 2: Real-Time & Projections

4. **SportsDataIO** - Fantasy projections and DFS salaries
2. **Sportradar** - Live race data (if needed)

### Phase 3: Advanced Analytics

6. **FRCS.pro** - Interactive loop data tools
2. **OddsMatrix** - Betting odds for implied probability

---

## Current Data Status

| Directory | Status | Source |
|-----------|--------|--------|
| `data/historical/2024/` | Empty | Needs: Lap Raptor CSVs |
| `data/historical/2025/` | Empty | Needs: Lap Raptor CSVs |
| `data/imports/` | Unknown | Check for existing imports |
| `data/telemetry/` | Unknown | Check for live data |

---

## Next Steps

1. **Download Lap Raptor Loop Data:**
   - Visit [lapraptor.com/drivers/race-log-index](https://lapraptor.com/drivers/race-log-index)
   - Filter by series (Cup) and year (2024, 2025)
   - Download CSV files to `data/historical/`

2. **Set up nascaR.data for training data:**
   - Install R package for historical baseline

3. **Consider SportsDataIO for DFS salaries:**
   - Enables salary-aware optimization
