# Codebase Concerns

**Analysis Date:** 2026-02-11

## Tech Debt

### [Bayesian Estimation Implementation]
- **Issue:** Simplified Maximum Likelihood Estimation (MLE) used instead of proper Bayesian estimation with priors
- **Files:** `packages/axiomatic-sim/src/axiomatic_sim/cbn.py:142`
- **Impact:** Undermines the theoretical foundation of the Bayesian network - lacks proper uncertainty quantification
- **Fix approach:** Implement full Bayesian estimation using priors from historical driver performance data

### [Race Result Import System]
- **Issue:** Race result import functionality is not implemented - hardcoded placeholder comment
- **Files:** `scripts/etl/import_race_data.py:179`
- **Impact:** Cannot import historical race results from external APIs or CSV sources
- **Fix approach:** Implement race result parsing and database ingestion pipeline

### [Multi-valued Variable Handling]
- **Issue:** CBN (Causal Bayesian Network) does not properly handle multi-valued variables
- **Files:** `packages/axiomatic-sim/src/axiomatic_sim/cbn.py:325`
- **Impact:** Limits modeling flexibility for complex driver attributes
- **Fix approach:** Extend CBN to support multi-valued discrete variables with proper conditional probability tables

### [DFS Points Calculation]
- **Issue:** Dynamic Fantasy Sports (DFS) points calculation from ScenarioComponents not implemented
- **Files:** `apps/backend/app/api/optimize_portfolio.py:310`
- **Impact:** Cannot generate optimized DFS lineups with proper scoring
- **Fix approach:** Implement fantasy scoring rules parser and points calculation engine

### [Contest Results Database Query]
- **Issue:** Database query for contest_results table not implemented - placeholder comment
- **Files:** `apps/backend/app/contest/payout_curve.py:575`
- **Impact:** Cannot query historical contest results for performance analysis
- **Fix approach:** Create database schema and query implementation for contest results

## Known Bugs

### [Generic Exception Handler in Simulation Code]
- **Symptoms:** Broad `except:` clause catches all exceptions, masking real errors
- **Files:** `mc_sim.py:186`, `projector.py:138`
- **Trigger:** Any exception in simulation or projection code will silently fail
- **Workaround:** Review logs to identify failures, but no error feedback to user

### [Blocking Sleep Operation in Streamlit UI]
- **Symptoms:** `time.sleep(30)` blocks the entire Streamlit session during auto-refresh
- **Files:** `dashboard.py:893`
- **Trigger:** Enabling "Auto-refresh (30s)" checkbox
- **Workaround:** Disable auto-refresh or use server-side refresh

### [Empty Method Placeholders]
- **Symptoms:** Multiple methods with empty `pass` statements indicate incomplete implementation
- **Files:**
  - `packages/axiomatic-sim/src/axiomatic_sim/cbn.py:24`
  - `packages/axiomatic-sim/src/axiomatic_sim/narrative.py:287, 331`
  - `packages/axiomatic-kernel/tinyllama_finetune.py:367, 383`
  - `apps/native_mac/kernel_logger.py:678, 684`
  - `apps/native_mac/optimization/mcmc_optimizer.py:468`
  - `apps/native_mac/session_restorer.py:78, 101, 171`
  - `apps/native_mac/dock_handler.py:89, 112`
  - `apps/native_mac/undo/undo_manager.py:92, 150`
  - `apps/native_mac/persistence/session_manager.py:115, 125`
  - `apps/native_mac/gui/main_window.py:789, 907`
- **Workaround:** None - features don't work as expected

## Security Considerations

### [Neo4j Database Credentials in Environment File]
- **Risk:** Database credentials stored in plaintext `.env` file, with insecure default value
- **Files:** `.env:4-6`
- **Current mitigation:** Clear comment warning to change password
- **Recommendations:**
  1. Remove hardcoded password from `.env.example`
  2. Use secrets manager (AWS Secrets Manager, HashiCorp Vault) in production
  3. Add credential validation on startup
  4. Implement database connection pooling with credential rotation

### [API Keys Exposed in Error Messages]
- **Risk:** API keys partially exposed in error message truncation
- **Files:** `scripts/etl/download_with_brave.py:137`, `scripts/etl/brave_download.py:126`
- **Current mitigation:** Only shows first 20 characters plus "..."
- **Recommendations:**
  1. Never include API keys in logs or error messages
  2. Implement key masking in logging middleware
  3. Validate API keys at service boundary

### [Input Validation Gaps in API Endpoints]
- **Risk:** Potential for injection attacks if user input not properly validated
- **Files:** API endpoints in `apps/backend/app/api/` directory
- **Current mitigation:** Minimal validation present
- **Recommendations:**
  1. Implement request body schema validation (Pydantic models)
  2. Add rate limiting to prevent abuse
  3. Validate all user-provided parameters for type, range, and format
  4. Implement CORS configuration for production

### [Environment Variable Configuration]
- **Risk:** API URLs hardcoded for local development but may be used in production
- **Files:** `.env:20-21`, `apps/frontend/src/lib/api-client.ts:14`
- **Current mitigation:** Uses environment variables
- **Recommendations:**
  1. Add environment validation on application startup
  2. Document required environment variables
  3. Use different configuration files for dev/staging/prod

## Performance Bottlenecks

### [Blocking I/O in Streamlit Auto-Refresh]
- **Problem:** `time.sleep(30)` blocks the entire Streamlit session
- **Files:** `dashboard.py:893`
- **Cause:** Synchronous blocking call in event loop
- **Improvement path:** Use server-side refresh or async polling mechanism

### [Large File Processing in Backtest Module]
- **Problem:** `backtest.py` is 1713 lines with complex logic that may be hard to optimize
- **Files:** `backtest.py`
- **Cause:** Monolithic file with mixed responsibilities
- **Improvement path:** Refactor into smaller, focused modules:
  - Backtest engine
  - Performance metrics calculator
  - Visualization renderer

### [Database Session Management]
- **Problem:** Potential for unbounded session creation without proper cleanup
- **Files:** Multiple files using SQLAlchemy sessions
- **Cause:** Inconsistent session management patterns
- **Improvement path:**
  1. Implement session context manager pattern
  2. Add connection pooling configuration
  3. Implement session timeout and cleanup

### [Pandas Operations on Large DataFrames]
- **Problem:** Large CSV files (race-logs.csv is 3.6MB) processed without memory optimization
- **Files:** Data processing scripts in `scripts/etl/` directory
- **Cause:** Loading entire CSV into memory before processing
- **Improvement path:**
  1. Use chunked reading for large files
  2. Implement lazy evaluation where possible
  3. Consider Parquet/Feather formats for better compression

## Fragile Areas

### [Monolithic Configuration Files]
- **Files:** `config.yaml` (2480 bytes)
- **Why fragile:** Single source of truth for configuration, changes can affect multiple components
- **Safe modification:** Test changes in isolated environment first, use environment variables for overrides
- **Test coverage:** Configuration validation tests needed

### [Database Schema Dependencies]
- **Files:** `apps/backend/app/models.py` (20292 bytes)
- **Why fragile:** Database models tightly coupled to business logic; schema changes require careful migration planning
- **Safe modification:** Use SQLAlchemy migrations, test against sample data
- **Test coverage:** Schema integrity tests and constraint validation tests

### [Embedded API Keys in Source Code]
- **Files:** Various ETL scripts
- **Why fragile:** Hardcoded or default API keys can lead to credential exposure
- **Safe modification:** Move all API keys to environment variables or secrets manager
- **Test coverage:** Security audit of all credential usage

### [Native Mac Application Bundle Dependencies]
- **Files:** `apps/native_mac/` directory with py2app-generated files
- **Why fragile:** Build artifacts in source directory can cause version confusion
- **Safe modification:** Exclude build artifacts from version control (already in .gitignore)
- **Test coverage:** Testing against clean build needed

## Scaling Limits

### [Neo4j Graph Database Performance]
- **Current capacity:** Limited by Neo4j instance configuration in `.env`
- **Limit:** Unbounded queries without indexing or query optimization
- **Scaling path:**
  1. Implement query optimization and caching
  2. Add proper indexes on frequently queried fields
  3. Consider read replicas for scaling reads
  4. Implement pagination for large result sets

### [API Rate Limits and Concurrency**
- **Current capacity:** No visible rate limiting or request throttling
- **Limit:** Unbounded concurrent requests can overwhelm backend
- **Scaling path:**
  1. Implement Redis-based rate limiting
  2. Add connection pool sizing based on backend capacity
  3. Implement request queuing for heavy operations
  4. Add circuit breakers for failing external APIs

### [File System Storage for Large Datasets**
- **Current capacity:** CSV files stored in project root (race-logs.csv is 3.6MB)
- **Limit:** Project root directory approaching size limit
- **Scaling path:**
  1. Move data files to dedicated data directory
  2. Implement data archiving for old race logs
  3. Use database instead of CSV for large datasets

## Dependencies at Risk

### [jailbreak/extract artifact generation]
- **Risk:** Large generated build artifacts in `apps/native_mac/build/` directory
- **Impact:** Bloated repository, potential for confusion between source and build artifacts
- **Migration plan:** Use py2app build system properly - build artifacts should be in separate build directory or generated on demand

### [Bundled Python Dependencies]
- **Risk:** `.eggs` directory contains 300+ dependencies bundled in application bundle
- **Impact:** Large disk usage, potential security vulnerabilities in bundled dependencies
- **Migration plan:**
  1. Review and update bundled dependencies
  2. Consider using system Python with proper dependency management
  3. Use containerized deployment to avoid bundling issues

## Missing Critical Features

### [Real-time Data Streaming]
- **Problem:** No WebSocket or SSE implementation for real-time data updates
- **Blocks:** Live race updates, real-time lineup adjustments
- **Recommended approach:** Add WebSocket endpoint to backend for real-time updates

### [Data Versioning and Rollback]
- **Problem:** No mechanism to track data changes or rollback to previous versions
- **Blocks:** Auditing data sources, reproducing historical results
- **Recommended approach:** Implement data versioning with migration tracking

### [User Authentication and Authorization**
- **Problem:** No user authentication or authorization system
- **Blocks:** Multi-user deployment, shared configurations
- **Recommended approach:** Implement OAuth2 or JWT-based authentication

### [Comprehensive Logging and Monitoring**
- **Problem:** Logging is basic with limited structured logging
- **Blocks:** Production debugging, performance monitoring, error tracking
- **Recommended approach:** Implement structured logging (JSON format), centralized logging, and error tracking (Sentry/LogRocket)

## Test Coverage Gaps

### [Frontend Components Without Tests**
- **What's not tested:** UI components in `apps/frontend/src/components/` directory
- **Files:** Multiple components lack unit tests
- **Risk:** UI bugs may not be caught until production, regression testing is manual
- **Priority:** High - UI is critical user entry point

### [Backend Integration Tests**
- **What's not tested:** End-to-end API integration with external services (Neo4j, NASCAR API, etc.)
- **Files:** Most integration tests in `tests/integration/` directory exist, but coverage is incomplete
- **Risk:** Broken integrations may not be caught until runtime
- **Priority:** Medium - Many tests exist, but need expansion

### [Database Migration Tests**
- **What's not tested:** Database schema changes and data migrations
- **Files:** No dedicated migration test files
- **Risk:** Schema changes can break existing deployments
- **Priority:** High - Database integrity is critical

### [Error Path Tests**
- **What's not tested:** Error conditions, exception handling, edge cases
- **Files:** Limited test coverage for negative cases
- **Risk:** Errors in production may not be caught in testing
- **Priority:** Medium - Error handling is important but not as critical as core functionality

### [Performance and Load Tests**
- **What's not tested:** Application behavior under load, database performance
- **Files:** No load testing infrastructure
- **Risk:** System may degrade under real-world usage patterns
- **Priority:** Low - Nice to have but not critical for current scale

---

*Concerns audit: 2026-02-11*
