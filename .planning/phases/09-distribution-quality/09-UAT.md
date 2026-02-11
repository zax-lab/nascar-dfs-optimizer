# User Acceptance Testing (UAT) Checklist - NASCAR DFS Optimizer v1.2.0

**Purpose:** Verify app works correctly on a clean macOS installation without development tools.

**Prerequisites:**
- Clean macOS machine (no Python, no Xcode, no dev tools)
- macOS 12.0 (Monterey) or later
- 4GB+ RAM
- Internet connection (for Neo4j Docker pull)

**Test Data:**
Create a sample CSV file with the following columns: `Driver`, `Salary`, `Team`, `Position`

```csv
Driver,Salary,Team,Position
Kyle Larson,12000,Hendrick,1
Chase Elliott,11000,Hendrick,2
Denny Hamlin,10500,Joe Gibbs,3
...
```

---

## Test 1: Installation & First Launch

**Setup:**
1. [ ] Download `NASCAR-DFS-Optimizer-1.2.0.zip` from GitHub Releases
2. [ ] Extract zip file to get `NASCAR DFS Optimizer.app`
3. [ ] Drag app to `/Applications` folder

**First Launch - Gatekeeper:**
4. [ ] Double-click app to launch
5. [ ] **Expected:** Gatekeeper warning appears: "app is damaged and can't be opened"
6. [ ] Right-click (Control-click) app → Select "Open"
7. [ ] Click "Open" in the confirmation dialog
8. [ ] **Expected:** App launches successfully (main window appears)

**Pass Criteria:** App launches without crash after Gatekeeper workaround

---

## Test 2: Neo4j Connection

**Setup Neo4j (Docker):**
1. [ ] Open Terminal
2. [ ] Run: `docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/testpass neo4j:5.15`
3. [ ] Verify Neo4j is running: `docker ps | grep neo4j`

**Configure App:**
4. [ ] In app, go to Settings tab → Neo4j Connection
5. [ ] Enter credentials:
   - URI: `bolt://localhost:7687`
   - Username: `neo4j`
   - Password: `testpass`
6. [ ] Click "Test Connection"
7. [ ] **Expected:** "Connection successful" message

**Error Handling Test:**
8. [ ] Stop Neo4j: `docker stop neo4j`
9. [ ] Click "Test Connection" again
10. [ ] **Expected:** Clear error message "Connection refused: Is Neo4j running?"
11. [ ] Restart Neo4j: `docker start neo4j`

**Pass Criteria:** Connection test succeeds when Neo4j is running, fails gracefully when stopped

---

## Test 3: CSV Import

1. [ ] Go to File → Open (or press CMD+O)
2. [ ] Select sample CSV file with driver data
3. [ ] **Expected:** CSV loads into Race Data table
4. [ ] **Expected:** Driver count displays correctly (e.g., "40 drivers loaded")
5. [ ] **Expected:** Salary summary shows min/max/average

**Pass Criteria:** CSV imports without errors, data displays correctly

---

## Test 4: Optimization Workflow

1. [ ] Switch to Optimization tab
2. [ ] Verify race data is available (drivers loaded from Test 3)
3. [ ] Set constraints:
   - [ ] Salary cap: $50,000
   - [ ] Lineups: 10
   - [ ] Iterations: 1000
4. [ ] Click "Run Optimization"
5. [ ] **Expected:** Progress dialog appears with progress bar
6. [ ] **Expected:** Progress updates every 1-2 seconds
7. [ ] **Expected:** Completes in 30-90 seconds (depending on hardware)
8. [ ] **Expected:** Results automatically appear in Lineups tab

**Pass Criteria:** Optimization completes, results displayed, no crashes or hangs

---

## Test 5: Lineup Export

1. [ ] Switch to Lineups tab
2. [ ] Verify lineups are displayed with:
   - [ ] Driver names
   - [ ] Total salary
   - [ ] Projected points
3. [ ] Click "Export to DraftKings"
4. [ ] Save CSV file to Desktop
5. [ ] Open CSV in Excel or text editor
6. [ ] **Expected:** CSV has columns: Entry ID, Driver 1, Driver 2, Driver 3, Driver 4, Driver 5, Driver 6
7. [ ] **Expected:** 10 rows (one per lineup)
8. [ ] **Expected:** UTF-8 encoding (no garbled characters)

**Pass Criteria:** CSV exports correctly, opens in Excel, format matches DraftKings requirements

---

## Test 6: Settings Persistence

1. [ ] Resize window to different dimensions
2. [ ] Move window to different position
3. [ ] Change a setting (e.g., default lineup count)
4. [ ] Quit app: CMD+Q
5. [ ] Relaunch app
6. [ ] **Expected:** Window size and position restored
7. [ ] **Expected:** Changed setting persists

**Pass Criteria:** All settings persist across app restarts

---

## Test 7: Keyboard Shortcuts

1. [ ] Press CMD+O → **Expected:** File Open dialog appears
2. [ ] Press CMD+W → **Expected:** Active tab closes (or window if single tab)
3. [ ] Press CMD+Z → **Expected:** Last action undone (if applicable)
4. [ ] Press CMD+Shift+Z → **Expected:** Redo action

**Pass Criteria:** All shortcuts work as documented

---

## Test 8: Dock & Notifications

1. [ ] Start an optimization job
2. [ ] Switch to another app (keep NASCAR DFS Optimizer in background)
3. [ ] Wait for optimization to complete
4. [ ] **Expected:** Dock icon bounces when optimization completes
5. [ ] **Expected:** macOS notification appears with "View Lineups" button
6. [ ] Click "View Lineups" in notification
7. [ ] **Expected:** App switches to Lineups tab

**Pass Criteria:** Dock bounce and notifications work correctly

---

## Test 9: Dark Mode

1. [ ] Open System Settings → Appearance
2. [ ] Switch to Dark mode
3. [ ] Return to NASCAR DFS Optimizer
4. [ ] **Expected:** App interface switches to dark theme
5. [ ] Switch back to Light mode
6. [ ] **Expected:** App interface switches to light theme

**Pass Criteria:** App follows system appearance setting

---

## Test 10: Uninstallation

1. [ ] Quit app: CMD+Q
2. [ ] Delete app: Drag `NASCAR DFS Optimizer.app` from `/Applications` to Trash
3. [ ] (Optional) Delete app data:
   ```bash
   rm -rf ~/Library/Application Support/com.zax.nascar-dfs
   ```

**Pass Criteria:** App removes cleanly without system errors

---

## Summary

| Test | Status | Notes |
|------|--------|-------|
| 1. Installation & First Launch | ⬜ | |
| 2. Neo4j Connection | ⬜ | |
| 3. CSV Import | ⬜ | |
| 4. Optimization Workflow | ⬜ | |
| 5. Lineup Export | ⬜ | |
| 6. Settings Persistence | ⬜ | |
| 7. Keyboard Shortcuts | ⬜ | |
| 8. Dock & Notifications | ⬜ | |
| 9. Dark Mode | ⬜ | |
| 10. Uninstallation | ⬜ | |

**Overall Result:** ⬜ PASS / ⬜ FAIL

**Tester:** _______________  
**Date:** _______________  
**macOS Version:** _______________  
**Hardware:** _______________

**Issues Found:**
1. 
2. 
3. 

**Recommendations:**

---

*UAT Checklist Version: 1.0*  
*For: NASCAR DFS Optimizer v1.2.0*
