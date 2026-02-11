# Troubleshooting Guide - NASCAR DFS Optimizer v1.2.0

Common issues and solutions for the macOS app.

## Installation Issues

### "App is damaged and can't be opened"

**Cause:** macOS Gatekeeper blocks unsigned or ad-hoc signed apps.

**Solution:**
1. Right-click (Control-click) on the app
2. Select "Open"
3. Click "Open" in the dialog
4. This is only required on first launch

**Alternative:** Temporarily disable Gatekeeper (not recommended):
```bash
sudo spctl --master-disable
# Launch the app
sudo spctl --master-enable
```

### "Bad CPU type in executable" Error

**Cause:** Architecture mismatch (app built for wrong CPU type).

**Solution:** Download the correct build:
- Apple Silicon (M1/M2/M3): Use universal2 build (included)
- Intel Mac: Use universal2 build (included)

If the issue persists, rebuild from source on your machine.

### App crashes on launch

**Cause:** Missing dependencies or incompatible macOS version.

**Solution:**
1. Verify macOS version: 12.0 (Monterey) or later required
2. Check Console.app for crash logs: Applications → Utilities → Console
3. Look for "ImportError" or "ModuleNotFoundError" in the logs
4. Report issues with crash logs on GitHub

## Neo4j Connection Issues

### "Connection refused" when connecting to Neo4j

**Cause:** Neo4j server not running or wrong port.

**Solution:**
1. Verify Neo4j is running:
   ```bash
   docker ps | grep neo4j
   # or check the Neo4j Desktop app
   ```
2. Check port 7687 is accessible:
   ```bash
   lsof -i :7687
   ```
3. If using Docker, restart the container:
   ```bash
   docker restart neo4j
   ```

### "Authentication failed" when connecting to Neo4j

**Cause:** Incorrect username or password.

**Solution:**
1. Verify credentials in Settings → Neo4j Connection
2. Default Neo4j credentials: `neo4j` / `neo4j` (first login requires password change)
3. If using Docker, check the `-e NEO4J_AUTH` variable

### Neo4j constraint ontology not loading

**Cause:** Database schema not initialized or incompatible Neo4j version.

**Solution:**
1. Verify Neo4j version: 4.x or 5.x required
2. Open Neo4j Browser at http://localhost:7474
3. Run schema verification:
   ```cypher
   CALL db.schema() YIELD nodes, relationships
   RETURN nodes, relationships
   ```
4. If no schema exists, the app will auto-create it on first run

## API Authentication Issues

### "401 Unauthorized" from API

**Cause:** Missing or invalid API key for non-health endpoints.

**Solution:**
1. Set `API_KEYS` in the backend `.env` (comma-separated).
2. Send `X-API-Key` on all non-health requests.
3. If using the frontend, set `NEXT_PUBLIC_API_KEY` to the same value.

## App Performance Issues

### Optimization is slow (30+ seconds)

**Cause:** Running optimization on local CPU (normal for MCMC sampling).

**Solution:**
1. Use GPU offload for faster optimization:
   - Settings → GPU Offload
   - Enter Windows GPU worker URL
   - Test connection
2. Reduce iterations in Optimization tab (default 1000, try 500)
3. Reduce lineup count (default 10, try 5)

### App freezes during optimization

**Cause:** Long-running MCMC job blocking UI thread.

**Solution:**
1. Optimization runs in background thread by design
2. If UI freezes, wait for job to complete (monitor in Jobs tab)
3. Force-quit app if frozen for >2 minutes and try again with fewer iterations

## Data Import/Export Issues

### CSV import fails with parsing errors

**Cause:** Malformed CSV or incorrect column headers.

**Solution:**
1. Verify CSV format matches expected schema:
   - Required columns: Driver, Salary, Team, Position
   - Encoding: UTF-8 or UTF-8 with BOM
2. Open CSV in text editor to check for special characters
3. Use Excel "Save as CSV UTF-8" if export from Excel

### Lineup export fails with "invalid format"

**Cause:** Lineup data contains invalid characters or missing fields.

**Solution:**
1. Verify lineups have 6 drivers each
2. Check total salary <= $50,000
3. Export to JSON for debugging, inspect for invalid data

## GUI Issues

### Dark mode not working correctly

**Cause:** App not following system appearance or macOS version < 10.14.

**Solution:**
1. Verify macOS version: 10.14 (Mojave) or later required
2. App should auto-detect system dark mode
3. If still broken, restart app after changing system appearance

### Keyboard shortcuts not working

**Cause:** Shortcut conflicts or custom shortcuts disabled.

**Solution:**
1. Check Settings → Keyboard Shortcuts for custom bindings
2. Verify no app conflicts (check macOS System Settings → Keyboard → Shortcuts)
3. Reset to factory defaults in Settings → Keyboard Shortcuts → Reset

### Window geometry not saving

**Cause:** App data directory permissions or corrupted state.

**Solution:**
1. Reset app data (WARNING: clears all settings):
   ```bash
   rm -rf ~/Library/Application Support/com.zax.nascar-dfs
   ```
2. Relaunch the app

## Still Having Issues?

1. Check Console.app for error logs (filter by "NASCAR DFS Optimizer")
2. Search [GitHub Issues](https://github.com/your-repo/issues) for similar problems
3. Create a new issue with:
   - macOS version
   - App version
   - Steps to reproduce
   - Console logs (if applicable)
