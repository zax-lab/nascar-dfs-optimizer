# Troubleshooting - NASCAR DFS Optimizer

Common issues and solutions for NASCAR DFS Optimizer on macOS.

## Viewing Error Logs

macOS applications log errors to **Console.app**. To view logs:

1. Open **Console.app** (Press Command + Space, type "Console")
2. In the sidebar, select your computer name under **Devices**
3. In the search bar, type "NASCAR" to filter logs
4. Look for error messages in red or yellow
5. Copy relevant error text when reporting issues

**Filtering Tips:**
- Search for "error" or "failed" to find critical messages
- Check timestamps to correlate with when issues occurred
- Expand error messages to see full stack traces

---

## Gatekeeper Issues

### "App is damaged and can't be opened"

**Cause:** macOS Gatekeeper blocking unsigned app

**Symptoms:**
- Double-clicking app does nothing
- Error message: "NASCAR DFS Optimizer is damaged and can't be opened"

**Solution:**
1. Control-click (or right-click) the app icon
2. Choose **"Open"** from the context menu
3. Click **"Open"** in the confirmation dialog
4. This only needs to be done once per download

**Why This Happens:**
- macOS Gatekeeper prevents running unsigned apps for security
- Personal distribution uses ad-hoc signature (not from Apple Developer Program)
- Control-click → Open tells macOS you trust this specific download

**Prevention (for public distribution):**
- Sign with Apple Developer ID ($99/year)
- Submit to Apple for notarization
- App then passes Gatekeeper without user interaction

---

## Neo4j Connection Issues

### "Failed to connect to Neo4j database"

**Cause:** Neo4j server not running or unreachable

**Symptoms:**
- App launches but shows connection error
- Settings tab shows "Connection Failed" status
- Can't import or optimize lineups

**Solutions:**

**1. Start Neo4j Server:**
   - Open Neo4j from Applications folder
   - Wait for "Database started" message
   - Verify by visiting http://localhost:7474 in browser
   - Connection URL in app should be: `bolt://localhost:76874`

**2. Check URL in App Settings:**
   - Go to Settings tab
   - Verify URL is `bolt://localhost:76874`
   - Correct if different (e.g., `bolt://localhost:7687`)

**3. Check Firewall:**
   - System Preferences > Security & Privacy > Firewall
   - Ensure port 76874 is not blocked
   - May need to allow `neo4j` or add firewall rule

**4. Restart Neo4j:**
   - If server was running, try restarting it
   - Check Neo4j Console for startup errors

**5. Verify Neo4j Version:**
   - Requires Neo4j 4.4.0 or later
   - Update from: https://neo4j.com/download/

### "Authentication failed for Neo4j"

**Cause:** Incorrect username or password

**Symptoms:**
- Connection error with "Authentication failed" message
- Settings show password field highlighted as invalid

**Solutions:**

**1. Reset Neo4j Password:**
   ```bash
   # In Terminal
   neo4j-admin set-initial-password new-password-here
   ```

**2. Update Password in App:**
   - Go to Settings tab
   - Update password field
   - Click "Test Connection"
   - Click "Save" if test succeeds

**3. Verify Username:**
   - Default username is always `neo4j`
   - Case-sensitive (lowercase)

---

## Import Errors

### "CSV parse error"

**Cause:** Incorrect CSV format or malformed file

**Symptoms:**
- Import dialog shows error
- Console.app logs "CSV parse error" or "Malformed CSV"
- No drivers appear after import

**Solutions:**

**1. Verify CSV Format:**
   CSV must have these DraftKings columns:
   - `Name` (driver name)
   - `Salary` (integer, e.g., 10500)
   - `AvgPoints` (float, e.g., 55.5)
   - `Position` (integer, e.g., 1)

**2. Check File Encoding:**
   - CSV must be UTF-8 encoded
   - Open in text editor, save as UTF-8
   - Avoid special characters in driver names

**3. Check for Corrupt Lines:**
   - Open CSV in text editor (TextEdit, VS Code)
   - Look for:
     - Missing commas between fields
     - Extra quotation marks
     - Empty rows
   - Fix or remove problematic lines

**4. Re-download from Source:**
   - If data looks wrong, re-download from DraftKings
   - Ensure file downloaded completely (check file size)

### "No drivers found in CSV"

**Cause:** Empty CSV or wrong file selected

**Symptoms:**
- Import succeeds but table is empty
- "No drivers available" message shown

**Solutions:**

**1. Check CSV Contents:**
   - Open CSV in text editor
   - Verify there are data rows after header row
   - Should have 40+ driver entries for typical race

**2. Check Selected File:**
   - Ensure correct file was selected in import dialog
   - Look for .bak, .old, or other suffix that might indicate wrong file

**3. Check File Path:**
   - Ensure file path doesn't contain special characters
   - Avoid spaces in file names if possible

---

## Performance Issues

### App is slow or unresponsive

**Cause:** Insufficient RAM or optimization in progress

**Symptoms:**
- UI freezes during optimization
- Beach ball cursor appears
- Window takes long time to respond

**Solutions:**

**1. Close Other Applications:**
   - Quit web browsers, other apps
   - Free up RAM (check Activity Monitor)
   - 8 GB minimum, 16 GB recommended

**2. Check Optimization Status:**
   - Go to Jobs tab
   - See if optimization is running
   - Optimization is CPU-intensive, UI may be slower

**3. Reduce Lineup Count:**
   - Go to Optimization tab
   - Reduce "Number of Lineups" setting
   - Fewer lineups = faster optimization

**4. Disable GPU Offload:**
   - If GPU worker is slow or unreachable
   - Go to Settings tab
   - Uncheck "Use GPU for Optimization"
   - Restart app to apply

### Optimization never completes

**Cause:** Infeasible constraints or network issues

**Symptoms:**
- Jobs tab shows "Running" indefinitely
- Progress bar stuck at same percentage
- No lineups generated after 10+ minutes

**Solutions:**

**1. Review Constraints:**
   - Go to Optimization tab
   - Check constraint panel settings:
     - Salary cap too low? (e.g., < $50,000)
     - Too many position locks?
     - Impossible driver combinations?
   - Try with default constraints

**2. Check Neo4j Server:**
   - Ensure Neo4j is still running
   - Visit http://localhost:7474 to verify
   - Restart Neo4j if needed

**3. Verify GPU Worker (if using):**
   - Go to Settings tab
   - Click "Test Connection" for GPU worker
   - Check GPU worker URL is correct
   - Ensure worker machine is on and accessible

**4. Check Console Logs:**
   - Open Console.app
   - Search for "optimization" or "error"
   - Look for constraint violations or solver errors

---

## UI Issues

### Window doesn't appear after launch

**Cause:** App launched in background or display issue

**Symptoms:**
- Dock icon shows app is running
- No window visible on screen

**Solutions:**

**1. Bring to Front:**
   - Click app icon in Dock
   - Check multiple desktop spaces (Control + Arrow keys)
   - Press F11 to minimize all, then click Dock icon

**2. Check for Windows Off-Screen:**
   - System Preferences > Displays > Arrangement
   - Ensure monitors are arranged correctly
   - Try disconnecting external monitor

**3. Quit and Relaunch:**
   - Right-click Dock icon > Quit
   - Double-click app to relaunch

### Dark mode not working

**Cause:** macOS appearance setting overrides app

**Symptoms:**
- App always appears in light mode
- System is in dark mode

**Solutions:**

**1. Force Dark Mode in macOS:**
   - System Preferences > General > Appearance
   - Select **"Dark"** (not "Auto")
   - Relaunch app

**2. Check App Version:**
   - Help > About
   - Ensure version 1.2.0 or later
   - Dark mode support added in v1.2.0

---

## Crash on Launch

### Immediate crash on double-click

**Causes:**
- Corrupt app bundle
- Missing system dependencies
- Incompatible macOS version

**Symptoms:**
- Dock icon briefly bounces, then disappears
- "Unexpectedly quit" error message
- Console shows crash logs

**Solutions:**

**1. Check macOS Version:**
   - Apple menu > About This Mac
   - Requires macOS 12.0 (Monterey) or later
   - Update macOS if version < 12.0

**2. Re-download App Bundle:**
   - Delete existing app from Applications
   - Empty Trash
   - Re-download zip from GitHub Releases
   - Verify file size matches release notes

**3. Check Console Logs:**
   - Open Console.app
   - Search for crash reports
   - Look for "Exception", "Error", or stack traces
   - Copy logs when reporting issue

**4. Run from Terminal (for debugging):**
   ```bash
   cd /Applications
   ./NASCAR\ DFS\ Optimizer.app/Contents/MacOS/NASCAR-DFS-Optimizer
   ```
   - Look for error output in Terminal
   - Note any ImportError or missing modules

---

## File System Issues

### "Permission denied" when saving exports

**Cause:** Read-only file system or permission issues

**Solutions:**

**1. Save to Different Location:**
   - Choose Desktop or Downloads instead of system folders
   - Try external drive if available

**2. Check File Permissions:**
   - Right-click folder > Get Info
   - Check "Sharing & Permissions"
   - Ensure user has "Read & Write" access

**3. Check Disk Space:**
   - Open Finder
   - Select drive and press Command + I
   - Ensure sufficient space available

---

## Network Issues (GPU Offload)

### "GPU worker connection timeout"

**Cause:** Worker machine offline or network blocked

**Solutions:**

**1. Verify Worker URL:**
   - Go to Settings tab
   - Check GPU worker URL is correct (e.g., `http://192.168.1.100:8000`)
   - Try `http://localhost:8000` if worker on same machine

**2. Check Worker Status:**
   - Verify worker machine is powered on
   - Try opening worker URL in web browser
   - Check worker logs for errors

**3. Check Network:**
   - Ensure both machines on same network
   - Check firewall settings (port 8000)
   - Try local network instead of VPN

---

## Reporting Issues

When reporting issues, provide:

**System Information:**
- macOS version (Apple menu > About This Mac)
- App version (Help > About)
- Architecture (Intel or Apple Silicon)

**Steps to Reproduce:**
1. What you did (step-by-step)
2. What you expected to happen
3. What actually happened
4. Frequency (always, sometimes, once)

**Logs and Screenshots:**
- Console.app error logs (filter for "NASCAR" or "error")
- Screenshots of error messages
- Screenshots of UI state when issue occurred

**Where to Report:**
- GitHub Issues: https://github.com/[your-repo]/issues
- Include detailed information for faster resolution

---

## Glossary

- **Gatekeeper:** macOS security feature that blocks unsigned apps
- **Ad-hoc signature:** Code signature without developer certificate
- **Control-click → Open:** Workaround to bypass Gatekeeper for unsigned apps
- **Console.app:** macOS application for viewing system and app logs
- **Neo4j:** Graph database used for constraint ontology
- **GPU offload:** Running optimization on GPU worker instead of CPU

---

**Last Updated:** 2026-01-30
**App Version:** 1.2.0
