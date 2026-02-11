# 🚀 NASCAR DFS Optimizer - Quick Start Guide

## Launching the App

**Method 1: Double-click (EASIEST)**
```bash
# Just double-click this file:
"Launch App.command"
```

**Method 2: From command line**
```bash
cd "/path/to/nascar-model copy 2"
source .venv/bin/activate
PYTHONPATH=. python apps/native_mac/main.py
```

**Method 3: Run from project directory**
```bash
cd apps/native_mac
../../.venv/bin/python main.py
```

---

## 🏁 Sourcing Data for Tomorrow's Race

### Option 1: Import CSV File (RECOMMENDED)

1. **Click "New Race"** or press `Cmd+N`
2. Select your driver data CSV file (from DraftKings or other source)
3. App will import and display driver data

### Option 2: Use Previous Race Data

If you have previously imported data, it will be saved in the database.

---

## 🎯 Using the App (Basic Workflow)

1. **Race Data Tab** - Import/verify driver data
2. **Optimization Tab** - Set constraints and run optimization
3. **Lineups Tab** - View and save generated lineups
4. **Presets Tab** - Save/load constraint presets for quick reuse
5. **Settings Tab** - Configure preferences
6. **Jobs Tab** - Monitor optimization jobs

---

## ⚡ Quick Keyboard Shortcuts

| Action | Shortcut |
|---------|----------|
| New Race | Cmd+N |
| Open Data | Cmd+O |
| Save Lineups | Cmd+S |
| Undo | Cmd+Z |
| Redo | Cmd+Shift+Z |
| Run Optimization | Ctrl+Return |
| Cancel | Cmd+. |
| Switch to Lineups | Ctrl+L |
| Switch to Jobs | Ctrl+J |
| Find | Cmd+F |
| Quit | Cmd+Q |

---

## 📁 Importing Race Data

### Required Data Format

Your CSV file should have these columns:

| Column | Description | Example |
|---------|-------------|---------|
| Name | Driver name | Kyle Larson |
| Position | Starting position (1-43) | 1 |
| Team | Team name | Hendrick Motorsports |
| Salary | Player salary | 9800 |
| Points | Driver points | 32.5 |
| Avg Finish | Average finish position | 12.4 |
| Owns the Race | Win indicator | 1 |
| Track Record | Track performance score | 75.0 |

### Where to Get Race Data

**DraftKings.com** (RECOMMENDED)
1. Go to [DraftKings.com](https://www.draftkings.com)
2. Select tomorrow's NASCAR race
3. Click "Export CSV"
4. Download the CSV file
5. Import into this app

**Other Sources**
- NASCAR.com
- DriverAverages.com
- Your own historical data (must match format above)

### Import Steps

1. Click **"New Race"** (Cmd+N) OR **"Open Data"** (Cmd+O)
2. Select your CSV file
3. Review imported data in **Race Data** tab
4. Verify all columns are correct
5. Proceed to **Optimization** tab

---

## 🔧 Setting Up Constraints

### Salary Cap
- Default: $50,000
- Range: $40,000 - $60,000
- Adjust based on your site salary cap

### Driver Constraints
- **Salary Range**: Min/Max salary per driver
- **Ownership Limits**: Min/Max total drivers per team/owner
- **Stacking Rules**: Drivers from same team (adjust for qualifying vs main event)

### Common Settings

**Max Drivers per Team**: 
- 3-4 for qualifying
- 4-5 for main race

**Min/Max Salary**: 
- Usually $4,600 - $10,000 per driver

**Ownership Exposure**: 
- Track your exposure to individual drivers
- Avoid overconcentration in 50-100 lineups

---

## 🎲 Running Optimization

1. **Go to Optimization tab** (or Ctrl+2)
2. **Set constraints** (salary cap, stacking rules, etc.)
3. **Set number of lineups**: How many optimal lineups to generate
4. **Click "Run Optimization"** (Ctrl+Return)
5. **Monitor progress** in Jobs tab (Ctrl+J)

### Optimization Tips

- Start with fewer lineups (10-20) to test quickly
- Adjust constraints based on results
- Check veto logs for rejected lineups
- Save good constraint sets as presets

---

## 📊 Viewing & Saving Lineups

### Viewing Results

1. Go to **Lineups Tab** (Ctrl+L)
2. Browse generated lineups
3. Check lineup stats (salary, projected points, etc.)
4. Double-click lineup to view full details

### Saving Lineups

**Export to CSV:**
1. In Lineups tab, click lineups to export
2. Click **"Export to DraftKings"** (Ctrl+E)
3. Save file for uploading to DraftKings

**Save in App:**
1. Click **"Save Lineups"** (Cmd+S)
2. Lineups are saved to app database
3. Can be reloaded later

---

## ⚙️ Common Issues

### App Won't Launch
- Make sure Python 3.12.7 is installed
- Delete `.venv` folder and re-run `Launch App.command`
- Check Console.app for error messages

### Data Import Issues
- Ensure CSV has all required columns
- Check for special characters in data
- Verify salary format (numbers, not currency symbols)

### Optimization Not Running
- Check Jobs tab (Ctrl+J) for job status
- Verify constraints are set correctly
- Try fewer lineups first

---

## 💾 Backing Up Your Work

### Quick Backup
```bash
# Double-click "Backup App.command"
```

### Manual Backup
```bash
zip -r NASCAR-backup-$(date +%Y%m%d-%H%M).zip \
    .venv/ \
    apps/native_mac/ \
    packages/ \
    "Launch App.command" \
    "Backup App.command"
```

---

## 🆘 Troubleshooting

### App Crashes Immediately
**Solution**: Check Console.app
1. Open Console.app (Cmd+Space, type "Console")
2. Select your app on the left
3. Look for error messages

### Can't Import CSV
**Solution**: Check file format
- Ensure headers match expected columns
- No trailing commas in data
- Check encoding (UTF-8)

### Optimization Takes Too Long
**Solution**: Reduce lineup count
- Start with 10 lineups to test
- Increase count once working
- Check Jobs tab for progress

---

## 📱 Need Help?

Check these files:
- `LAUNCH_SCRIPT_README.md` - More technical details
- `apps/native_mac/docs/INSTALL.md` - Installation guide
- `apps/native_mac/docs/TROUBLESHOOTING.md` - Common issues

---

## 🏎️ Race Day Checklist

- [ ] Import driver CSV (from DraftKings or other source)
- [ ] Verify all data columns are correct
- [ ] Set salary cap for race
- [ ] Configure stacking rules for race type
- [ ] Set lineup count (start with 10-20)
- [ ] Run test optimization
- [ ] Review results and adjust constraints
- [ ] Generate full set of lineups (50-150)
- [ ] Export lineups to CSV for DraftKings
- [ ] Save work in app
- [ ] Create backup for future reference

**Good luck with tomorrow's race! 🏁**
