# Installation Guide - NASCAR DFS Optimizer v1.2.0

This guide walks you through installing NASCAR DFS Optimizer on macOS.

## Requirements

- macOS 12.0 (Monterey) or later
- Apple Silicon (M1/M2/M3) or Intel Mac
- 4GB RAM minimum, 8GB recommended
- 500MB free disk space for app bundle
- Neo4j 5.x or 4.x database server (for constraint ontology)

## Installation

### Step 1: Download the App

1. Visit [GitHub Releases](https://github.com/your-repo/releases) page
2. Download the latest version: `NASCAR-DFS-Optimizer-1.2.0.zip`
3. Extract the zip file to get `NASCAR DFS Optimizer.app`

### Step 2: Install the App

1. Drag `NASCAR DFS Optimizer.app` to your `/Applications` folder
2. Launch the app by double-clicking in `/Applications`

### Step 3: Gatekeeper (First Launch Only)

On first launch, macOS may show a security warning:
> "NASCAR DFS Optimizer.app is damaged and can't be opened"

**Solution:**
1. Right-click (Control-click) on the app
2. Select "Open" from the context menu
3. Click "Open" in the confirmation dialog

You only need to do this once. The app will launch normally afterward.

## Neo4j Setup

The app requires Neo4j database for constraint ontology.

### Option A: Docker (Recommended)

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/yourpassword \
  neo4j:5.15
```

### Option B: Native Installation

Download Neo4j from [neo4j.com](https://neo4j.com/download/) and follow the macOS installation guide.

### Configure the App

1. Launch NASCAR DFS Optimizer
2. Go to Settings → Neo4j Connection
3. Enter connection details:
   - URI: `bolt://localhost:7687`
   - Username: `neo4j`
   - Password: (your password from Docker or setup)

## Backend API Key (If Using the API Directly)

If you run the backend API separately (for example, with the Next.js frontend),
configure API key authentication:

1. Set `API_KEYS` in your backend `.env` (comma-separated).
2. Set `NEXT_PUBLIC_API_KEY` in your frontend `.env` to the same value.
3. Clients must send `X-API-Key` on all non-health API requests.

## Verification

After installation, verify the app works:

1. Launch the app
2. Go to File → Open and import a sample CSV file
3. Set constraints and click "Run Optimization"
4. Verify lineups are generated in the Lineups tab

## Uninstalling

To remove the app:
1. Quit NASCAR DFS Optimizer
2. Delete `NASCAR DFS Optimizer.app` from `/Applications`
3. (Optional) Delete `~/Library/Application Support/com.zax.nascar-dfs` to remove app data

## Next Steps

See README.md for a quick start guide and TROUBLESHOOTING.md for common issues.
