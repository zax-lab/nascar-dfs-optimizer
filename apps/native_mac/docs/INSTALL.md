# Installation Guide - NASCAR DFS Optimizer

Complete guide to installing and running NASCAR DFS Optimizer on macOS.

## System Requirements

### Hardware
- **Processor:** Apple Silicon (M1/M2/M3) or Intel Mac (x86_64)
- **RAM:** 8 GB minimum, 16 GB recommended
- **Disk Space:** 500 MB free for application, additional space for data exports

### Software
- **macOS:** 12.0 (Monterey) or later
- **Neo4j:** 4.4.0 or later (for constraint ontology)
  - Download: https://neo4j.com/download/
  - Free Community Edition is sufficient

---

## Installation

### Step 1: Install Neo4j Database

1. **Download Neo4j:**
   - Visit https://neo4j.com/download/
   - Select "Neo4j Desktop" or "Neo4j Community Server"
   - Download macOS version

2. **Install Neo4j:**
   - Open downloaded .dmg file
   - Drag Neo4j to Applications folder

3. **Start Neo4j Server:**
   - Launch Neo4j from Applications
   - Wait for "Database started" message
   - Default URL: `http://localhost:7474`
   - Default connection: `bolt://localhost:76874`

4. **Set Initial Password:**
   - On first launch, you'll be prompted to set a password
   - Default username is always `neo4j`
   - Remember this password for app configuration

**Note:** Neo4j must be running when using NASCAR DFS Optimizer. The app stores driver and constraint data in the graph database.

---

### Step 2: Download NASCAR DFS Optimizer

1. **Visit GitHub Releases:**
   - Go to: https://github.com/[your-repo]/releases
   - Find the latest release (e.g., v1.2.0)

2. **Download Application:**
   - Click on `NASCAR-DFS-Optimizer-v1.2.0.zip`
   - Wait for download to complete (typically 100-200 MB)

3. **Verify Download:**
   - Check file size matches release notes
   - Don't use partially downloaded or corrupted files

---

### Step 3: Install Application

1. **Unzip Archive:**
   - Double-click `NASCAR-DFS-Optimizer-v1.2.0.zip`
   - Extract to Downloads folder or desired location

2. **Move to Applications:**
   - Drag `NASCAR-DFS-Optimizer.app` to `/Applications` folder
   - You'll need admin privileges (enter password)

3. **Verify Installation:**
   - Open Finder
   - Navigate to Applications
   - Confirm `NASCAR-DFS-Optimizer.app` is present

---

### Step 4: First Launch

1. **Launch Application:**
   - Double-click `NASCAR-DFS-Optimizer.app` in Applications
   - You may see a Gatekeeper warning

2. **Gatekeeper Workaround (First Launch Only):**

   If you see this warning:
   > "NASCAR DFS Optimizer cannot be opened because the developer cannot be verified"

   **Do this:**
   1. Click "Cancel" in the warning dialog
   2. Control-click (or right-click) the app icon
   3. Choose "Open" from the context menu
   4. Click "Open" in the confirmation dialog

   **Why this happens:**
   - macOS Gatekeeper blocks unsigned apps for security
   - Personal distribution uses ad-hoc signature
   - This is a one-time setup per download
   - The app is safe; Gatekeeper just doesn't recognize the developer

   **Prevention:**
   - For public distribution without warnings, you'd need Apple Developer Program ($99/year)
   - This is not required for personal use

3. **Complete First-Time Setup:**
   - After successful launch, you'll see the main window
   - Navigate to Settings tab
   - Enter Neo4j connection settings:
     - URL: `bolt://localhost:76874`
     - Username: `neo4j`
     - Password: (your Neo4j password)
   - Click "Test Connection" to verify
   - Click "Save" to store settings

---

## Configuration

### Neo4j Connection

**Default Settings:**
- **Bolt URL:** `bolt://localhost:76874`
- **Username:** `neo4j`
- **Password:** (set during Neo4j installation)

**Troubleshooting Connection Issues:**
- **Server not running:** Start Neo4j from Applications
- **Wrong port:** Check Neo4j logs for actual port (default 76874)
- **Firewall:** Ensure port 76874 is not blocked
- **Wrong credentials:** Reset Neo4j password with `neo4j-admin set-initial-password new-password`

### GPU Offload (Optional)

If using GPU acceleration for optimizations:

1. **Install GPU Worker Service:**
   - Follow GPU worker setup documentation
   - Ensure worker is running on accessible host

2. **Configure in App:**
   - Go to Settings tab
   - Enable "Use GPU for Optimization"
   - Enter GPU worker URL (e.g., `http://192.168.1.100:8000`)
   - Set timeout (default 30 seconds)
   - Click "Test Connection" to verify

---

## Importing Data

### DraftKings CSV Format

The app expects DraftKings driver projection CSVs with these columns:

| Column | Description |
|---------|-------------|
| Name | Driver name |
| Salary | Driver salary (integer) |
| AvgPoints | Average projected points (float) |
| Position | Starting position (integer) |
| (Optional) Team | Team name |
| (Optional) Track | Track name |

### Import Steps

1. **Download Projections:**
   - Visit DraftKings or your projection source
   - Download NASCAR driver projections as CSV

2. **Import into App:**
   - Open NASCAR DFS Optimizer
   - Go to File > Import > From Backup
   - Select your CSV file
   - Click "Open"

3. **Verify Import:**
   - Check Lineups tab for driver table
   - Confirm driver data appears correctly
   - Check that projected points and salaries are accurate

---

## Quick Start (First 5 Minutes)

**Minute 1: Launch & Import**
- Launch app and import your first CSV file
- Drivers populate in Lineups tab

**Minute 2-3: Explore & Navigate**
- Click through each tab to familiarize yourself
- Check Settings to confirm Neo4j connection

**Minute 4: Set Constraints**
- Go to Optimization tab
- Adjust salary cap, position requirements
- Select/deselect drivers from table

**Minute 5: Optimize & Export**
- Click "Generate Lineups"
- Wait for optimization to complete (check Jobs tab)
- Export lineups to JSON or CSV

---

## Troubleshooting

### App Won't Open

**Gatekeeper blocks launch:**
- Use Control-click → Open workaround (see Step 4)
- Only required on first launch

**Compatibility check:**
- Verify macOS 12.0 or later (Apple menu > About This Mac)

**Corrupt download:**
- Re-download zip file
- Check file size matches release notes

### Neo4j Connection Fails

**"Failed to connect to Neo4j database"**
- Start Neo4j from Applications
- Visit http://localhost:7474 in browser
- Check firewall settings
- Verify URL in app settings (`bolt://localhost:76874`)

**"Authentication failed"**
- Reset Neo4j password: `neo4j-admin set-initial-password`
- Update password in app Settings

### App Crashes on Launch

**Immediate crash:**
- Check macOS version (requires 12.0+)
- Re-download app bundle
- View Console.app for error details
- Try running from Terminal to see errors

**Insufficient RAM:**
- Close other applications
- Reduce number of lineups in optimization settings

### Performance Issues

**App is slow:**
- Close other apps
- Check if optimization is running in Jobs tab
- Disable GPU offload if worker is unavailable

**Optimization never completes:**
- Review constraints for infeasible settings
- Check Neo4j server is responsive
- Verify GPU worker URL (if using GPU)
- Try with default constraints

---

## Uninstallation

To remove NASCAR DFS Optimizer:

1. **Quit the App** (if running)
2. **Move to Trash:**
   - Open Applications folder
   - Drag `NASCAR-DFS-Optimizer.app` to Trash
3. **Remove App Data (Optional):**
   - Delete `~/Library/Application Support/Zax/NASCAR DFS Optimizer/`
   - This removes all settings, presets, and exported data

---

## Next Steps

After successful installation:

- ✅ Read [README.md](../../README.md) for feature overview
- ✅ Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- ✅ Import your first DraftKings CSV and start optimizing

---

**Last Updated:** 2026-01-30
**App Version:** 1.2.0
**For Support:** Report issues on GitHub with Console.app logs
