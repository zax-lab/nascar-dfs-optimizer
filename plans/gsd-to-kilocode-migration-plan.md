# GSD to Kilo Code Migration Plan

## Executive Summary

This document outlines the comprehensive migration plan for porting the GSD (Get Shit Done) system from Claude Code/OpenCode to work natively with Kilo Code. GSD is a sophisticated multi-agent project management and execution framework with 11 specialized agents, 30+ commands, complex orchestration workflows, and extensive template/reference documentation.

**Migration Scope:** Full native port to Kilo Code (not hybrid approach)
**Estimated Effort:** 40-60 hours
**Target Integration:** Global integration into the nascar-model project

---

## 1. Architecture Overview

### 1.1 GSD Architecture (Current)

GSD is built on a multi-agent orchestration model with:

- **11 Specialized Agents:** Each with YAML frontmatter defining role, tools, color, and detailed process instructions
- **30+ Commands:** Orchestrated workflows for project lifecycle management
- **Planning System:** Complex state management with phases, plans, milestones, and verification loops
- **Artifact System:** Living documents (STATE.md, ROADMAP.md, SUMMARY.md, etc.) that track project state
- **Goal-Backward Methodology:** Plans and verifications start from what must be TRUE for goal achievement
- **Checkpoint System:** Three types (human-verify, decision, human-action) for human interaction points
- **Model Profile System:** Quality/balanced/budget profiles controlling which Claude model each agent uses
- **Git Integration:** Atomic commits per task with structured commit messages

### 1.2 Kilo Code Architecture (Target)

Kilo Code provides:

- **Mode-Based System:** orchestrator, code, ask, architect, debug modes with different capabilities
- **Domain-Specific Agents:** 6 specialized agents (backend, data, devops, frontend, ml, test) with COORDINATION.md logs
- **Tool-Based Execution:** Rich set of tools for file operations, command execution, code analysis
- **Context Management:** Workspace-based context with file structure awareness
- **Skill System:** Pluggable skills for specialized workflows

### 1.3 Proposed Merged Architecture

The ported GSD system will leverage Kilo Code's infrastructure while preserving GSD's sophisticated orchestration:

```
.kilocode/
├── skills/
│   └── gsd/                    # GSD as a native Kilo Code skill
│       ├── SKILL.md             # Skill definition
│       ├── agents/              # GSD agents (adapted to Kilo Code format)
│       ├── commands/            # GSD commands (adapted to Kilo Code workflows)
│       ├── workflows/           # GSD orchestration workflows
│       ├── templates/           # GSD template system
│       └── references/         # GSD reference documentation
├── modes/
│   └── gsd-orchestrator/      # New mode for GSD orchestration
│       └── MODE.md
└── config/
    └── gsd.json               # GSD configuration
```

---

## 2. Directory Structure

### 2.1 Current GSD Structure

```
get-shit-done/
├── agents/                    # 11 agent definitions with YAML frontmatter
├── commands/
│   └── gsd/                   # 30+ command definitions
├── get-shit-done/
│   ├── templates/              # Project, state, roadmap, UAT, etc.
│   ├── workflows/              # Orchestration workflows
│   └── references/            # Checkpoints, verification, git, etc.
├── bin/                       # Installation scripts
├── hooks/                     # Git hooks
└── scripts/                   # Build scripts
```

### 2.2 Proposed Kilo Code Structure

```
.kilocode/
├── skills/
│   └── gsd/
│       ├── SKILL.md            # Skill metadata and entry points
│       ├── agents/             # Adapted GSD agents
│       │   ├── gsd-planner.md
│       │   ├── gsd-executor.md
│       │   ├── gsd-verifier.md
│       │   ├── gsd-roadmapper.md
│       │   ├── gsd-phase-researcher.md
│       │   ├── gsd-project-researcher.md
│       │   ├── gsd-research-synthesizer.md
│       │   ├── gsd-plan-checker.md
│       │   ├── gsd-codebase-mapper.md
│       │   ├── gsd-debugger.md
│       │   └── gsd-integration-checker.md
│       ├── commands/           # Command definitions (YAML frontmatter → Kilo Code format)
│       │   ├── new-project.md
│       │   ├── new-milestone.md
│       │   ├── plan-phase.md
│       │   ├── execute-phase.md
│       │   ├── verify-work.md
│       │   └── ... (30+ commands)
│       ├── workflows/          # Orchestration workflows
│       │   ├── execute-phase.md
│       │   ├── execute-plan.md
│       │   ├── verify-work.md
│       │   ├── discovery-phase.md
│       │   ├── map-codebase.md
│       │   ├── diagnose-issues.md
│       │   └── ...
│       ├── templates/          # Template system
│       │   ├── project.md
│       │   ├── state.md
│       │   ├── roadmap.md
│       │   ├── summary.md
│       │   ├── UAT.md
│       │   ├── verification-report.md
│       │   └── codebase/
│       ├── references/         # Reference documentation
│       │   ├── checkpoints.md
│       │   ├── verification-patterns.md
│       │   ├── git-integration.md
│       │   ├── model-profiles.md
│       │   └── ...
│       └── bin/              # Utility scripts
├── modes/
│   └── gsd-orchestrator/
│       └── MODE.md           # GSD orchestration mode definition
├── config/
│   └── gsd.json             # GSD configuration (model profiles, etc.)
└── setup-script             # Updated to include GSD skill installation

.planning/                    # GSD project artifacts (preserved)
├── PROJECT.md
├── STATE.md
├── ROADMAP.md
├── config.json
├── phases/
│   ├── 01-*/
│   │   ├── *-PLAN.md
│   │   ├── *-SUMMARY.md
│   │   ├── *-UAT.md
│   │   └── *-VERIFICATION.md
└── codebase/
    ├── STACK.md
    ├── ARCHITECTURE.md
    └── ...
```

---

## 3. Agent Conversion Plan

### 3.1 Agent Format Comparison

| Aspect | GSD Format | Kilo Code Format | Migration Strategy |
|--------|-----------|-----------------|-------------------|
| **Definition** | YAML frontmatter + markdown | COORDINATION.md (free-form markdown) | Convert YAML frontmatter to SKILL.md metadata + markdown body |
| **Role Definition** | `name`, `description`, `tools`, `color` fields | Free-form role description | Extract to SKILL.md metadata section |
| **Process Instructions** | Detailed sections (role, philosophy, process) | Session summaries, decisions, blockers | Preserve as markdown sections in agent files |
| **Tool Access** | Explicit `tools` list | Implicit via mode capabilities | Map GSD tools to Kilo Code tool equivalents |
| **Model Selection** | Model profile lookup table | Mode-specific model | Implement model profile system in GSD skill |

### 3.2 Agent Mapping Table

| GSD Agent | Purpose | Kilo Code Equivalent | Migration Notes |
|-----------|---------|---------------------|-----------------|
| **gsd-planner** | Creates executable phase plans with task breakdown | architect mode (planning focus) | Preserve goal-backward methodology, adapt to Kilo Code's architect mode |
| **gsd-executor** | Executes PLAN.md files atomically with checkpoint protocols | code mode (execution focus) | Map checkpoint system to Kilo Code's ask_followup_question tool |
| **gsd-verifier** | Verifies phase goal achievement through goal-backward analysis | debug mode (verification focus) | Adapt verification patterns to Kilo Code's capabilities |
| **gsd-roadmapper** | Creates project roadmaps with phase breakdown | architect mode (high-level planning) | Preserve milestone/phase structure |
| **gsd-phase-researcher** | Researches how to implement a phase before planning | ask mode (research focus) | Leverage Kilo Code's search_files and read_file tools |
| **gsd-project-researcher** | Researches domain ecosystem before roadmap creation | ask mode (research focus) | Preserve parallel research pattern |
| **gsd-research-synthesizer** | Synthesizes research outputs from 4 parallel agents | architect mode (synthesis focus) | Implement parallel agent orchestration |
| **gsd-plan-checker** | Verifies plans will achieve phase goal before execution | debug mode (verification focus) | Preserve planner-checker iteration loop |
| **gsd-codebase-mapper** | Explores codebase and writes structured analysis | architect mode (analysis focus) | Map to Kilo Code's list_files and search_files tools |
| **gsd-debugger** | Investigates bugs using scientific method with persistent state | debug mode (native) | Near-direct mapping, preserve debug session format |
| **gsd-integration-checker** | Verifies cross-phase integration and E2E flows | test agent (integration focus) | Map to existing test agent capabilities |

### 3.3 Detailed Agent Conversions

#### 3.3.1 gsd-planner → Kilo Code architect mode

**GSD Capabilities:**
- Creates executable phase plans with task breakdown
- Dependency analysis and wave-based parallelization
- Goal-backward verification methodology
- Deviation rules and checkpoint protocols

**Kilo Code Mapping:**
- Use architect mode's planning capabilities
- Implement wave-based task grouping in workflow
- Preserve goal-backward verification as workflow step
- Map deviation rules to Kilo Code's tool usage patterns

**Conversion Steps:**
1. Extract YAML frontmatter (name, description, tools, color) to SKILL.md metadata
2. Convert process sections to markdown with Kilo Code tool references
3. Adapt checkpoint protocols to use `ask_followup_question` tool
4. Preserve model profile selection logic
5. Implement agent tracking (agent-history.json) using Kilo Code's state management

#### 3.3.2 gsd-executor → Kilo Code code mode

**GSD Capabilities:**
- Executes PLAN.md files atomically
- Checkpoint protocol (human-verify, decision, human-action)
- Atomic commits per task
- Deviation handling

**Kilo Code Mapping:**
- Use code mode's file editing capabilities
- Map checkpoints to `ask_followup_question` tool
- Use execute_command for git operations
- Preserve atomic commit pattern

**Conversion Steps:**
1. Map GSD's task execution to Kilo Code's edit_file/write_to_file tools
2. Convert checkpoint types to ask_followup_question with appropriate follow_up options
3. Implement atomic commit pattern using execute_command
4. Preserve deviation rules as conditional logic in workflow

#### 3.3.3 gsd-verifier → Kilo Code debug mode

**GSD Capabilities:**
- Goal-backward verification
- Must-have vs nice-to-have classification
- Gap identification
- Verification report generation

**Kilo Code Mapping:**
- Use debug mode's analysis capabilities
- Leverage search_files and read_file for verification
- Preserve verification report format

**Conversion Steps:**
1. Implement goal-backward verification algorithm
2. Map verification patterns to Kilo Code tool usage
3. Preserve VERIFICATION.md template structure
4. Adapt model profile selection

#### 3.3.4 gsd-codebase-mapper → Kilo Code architect mode

**GSD Capabilities:**
- Parallel codebase exploration (4 agents)
- Writes 7 structured documents directly
- Fresh context per domain

**Kilo Code Mapping:**
- Use list_files for directory structure
- Use search_files for pattern analysis
- Use read_file for detailed code inspection
- Implement parallel agent spawning via Kilo Code's mode switching

**Conversion Steps:**
1. Map 4 focus areas (tech, arch, quality, concerns) to Kilo Code workflows
2. Adapt document writing to Kilo Code's write_to_file tool
3. Preserve parallel execution pattern
4. Keep template-based document structure

---

## 4. Command Implementation Plan

### 4.1 Command Format Conversion

| GSD Command Format | Kilo Code Equivalent | Migration Strategy |
|------------------|---------------------|-------------------|
| YAML frontmatter (name, description, argument-hint, allowed-tools) | SKILL.md command metadata | Extract to command metadata section |
| Objective section | Command purpose | Preserve as markdown |
| Execution context | Mode/tool requirements | Map to Kilo Code modes and tools |
| Process steps | Workflow steps | Convert to Kilo Code workflow format |
| Offer next | Next command suggestions | Preserve as command routing |

### 4.2 Command Categorization and Mapping

#### 4.2.1 Project Initialization Commands

| GSD Command | Purpose | Kilo Code Implementation |
|-------------|---------|------------------------|
| **new-project** | Initialize new project with deep questioning, research, requirements, roadmap | New command in gsd skill, orchestrates multiple agents |
| **map-codebase** | Analyze codebase with parallel mapper agents | New command, uses list_files/search_files/read_file |
| **set-profile** | Configure workflow toggles and model profile | Configuration command, updates gsd.json |

#### 4.2.2 Planning Commands

| GSD Command | Purpose | Kilo Code Implementation |
|-------------|---------|------------------------|
| **new-milestone** | Start new milestone cycle | New command, updates ROADMAP.md |
| **plan-phase** | Create detailed execution plan for a phase | New command, spawns gsd-planner agent |
| **plan-milestone-gaps** | Create phases to close gaps from audit | New command, gap closure planning |
| **research-phase** | Standalone research for a phase | New command, spawns gsd-phase-researcher |
| **discuss-phase** | Gather phase context through adaptive questioning | New command, uses ask_followup_question |

#### 4.2.3 Execution Commands

| GSD Command | Purpose | Kilo Code Implementation |
|-------------|---------|------------------------|
| **execute-phase** | Execute all plans in a phase with wave-based parallelization | New command, orchestrates gsd-executor agents |
| **execute-plan** | Execute a single PLAN.md file | New command, spawns gsd-executor agent |
| **quick** | Execute quick tasks skipping optional agents | New command, simplified execution path |
| **debug** | Systematic debugging with persistent state | New command, uses debug mode |

#### 4.2.4 Verification Commands

| GSD Command | Purpose | Kilo Code Implementation |
|-------------|---------|------------------------|
| **verify-work** | Validate built features through conversational UAT | New command, orchestrates UAT workflow |
| **audit-milestone** | Audit milestone completion against original intent | New command, verification workflow |
| **complete-milestone** | Archive completed milestone | New command, updates ROADMAP.md and creates archive |

#### 4.2.5 State Management Commands

| GSD Command | Purpose | Kilo Code Implementation |
|-------------|---------|------------------------|
| **progress** | Check project progress and route to next action | New command, reads STATE.md and ROADMAP.md |
| **pause-work** | Create context handoff when pausing | New command, writes continue-here.md |
| **resume-work** | Resume work from previous session | New command, reads continue-here.md |
| **check-todos** | List pending todos | New command, reads STATE.md todos section |

#### 4.2.6 Project Management Commands

| GSD Command | Purpose | Kilo Code Implementation |
|-------------|---------|------------------------|
| **add-phase** | Add phase to end of current milestone | New command, updates ROADMAP.md |
| **insert-phase** | Insert urgent work as decimal phase | New command, updates ROADMAP.md |
| **remove-phase** | Remove future phase and renumber | New command, updates ROADMAP.md |
| **add-todo** | Capture idea/task as todo | New command, updates STATE.md |
| **list-phase-assumptions** | Surface Claude's assumptions about a phase | New command, analysis workflow |

#### 4.2.7 System Commands

| GSD Command | Purpose | Kilo Code Implementation |
|-------------|---------|------------------------|
| **settings** | Configure workflow toggles and model profile | Configuration command, updates gsd.json |
| **update** | Update GSD to latest version | System command (may not be needed in Kilo Code) |
| **help** | Show available GSD commands and usage guide | Help command, reads command metadata |
| **join-discord** | Join GSD Discord community | External link (preserve) |

### 4.3 Command Implementation Strategy

Each GSD command will be converted to a Kilo Code workflow:

1. **Extract command metadata** from YAML frontmatter to SKILL.md
2. **Convert process steps** to Kilo Code workflow format using available tools
3. **Map tool references** to Kilo Code tool equivalents
4. **Preserve checkpoint protocols** using `ask_followup_question`
5. **Implement model profile selection** in command workflow
6. **Add command routing** to offer next command suggestions

---

## 5. Workflow Adaptation Plan

### 5.1 Workflow Conversion Strategy

GSD workflows define orchestration patterns for complex operations. These will be adapted to Kilo Code's workflow system:

| GSD Workflow | Purpose | Kilo Code Adaptation |
|--------------|---------|---------------------|
| **execute-phase** | Execute all plans in a phase with wave-based parallelization | New workflow, orchestrates parallel agent spawning |
| **execute-plan** | Execute a single PLAN.md file | New workflow, single agent execution with checkpoint handling |
| **verify-work** | Conversational UAT with persistent state | New workflow, uses ask_followup_question for testing |
| **discovery-phase** | Execute discovery at appropriate depth level | New workflow, uses search_files and read_file |
| **map-codebase** | Orchestrate parallel codebase mapper agents | New workflow, parallel agent spawning |
| **diagnose-issues** | Orchestrate parallel debug agents for UAT gaps | New workflow, parallel debug mode usage |
| **complete-milestone** | Archive completed milestone | New workflow, file operations and git commits |
| **transition** | Handoff between sessions | New workflow, state preservation |
| **verify-phase** | Verify phase goal achievement | New workflow, verification patterns |
| **list-phase-assumptions** | Surface Claude's assumptions | New workflow, analysis and reporting |

### 5.2 Key Workflow Adaptations

#### 5.2.1 execute-phase Workflow

**GSD Pattern:**
1. Load project state (STATE.md)
2. Validate phase exists
3. Discover plans and extract metadata
4. Group by wave (pre-computed)
5. Execute waves sequentially with parallel agents within waves
6. Handle checkpoints (human-verify, decision, human-action)
7. Aggregate results
8. Spawn verifier
9. Update ROADMAP.md

**Kilo Code Adaptation:**
1. Use `read_file` to load STATE.md and ROADMAP.md
2. Use `list_files` to discover plan files
3. Parse frontmatter using regex or simple string parsing
4. Implement wave grouping logic
5. Use `switch_mode` to spawn parallel agents (or implement within same mode if supported)
6. Use `ask_followup_question` for checkpoints
7. Use `write_to_file` to update STATE.md and ROADMAP.md
8. Use `execute_command` for git operations

**Challenges:**
- Parallel agent spawning may need custom implementation
- Agent tracking (agent-history.json) needs Kilo Code state management
- Model profile selection needs to be implemented

#### 5.2.2 verify-work Workflow

**GSD Pattern:**
1. Check for active UAT sessions
2. Find summaries and extract tests
3. Create UAT file with all tests
4. Present tests one at a time
5. Process user responses (pass/skip/issue)
6. If issues found, diagnose with parallel debug agents
7. Plan gap closure
8. Verify gap plans
9. Complete session

**Kilo Code Adaptation:**
1. Use `list_files` to find UAT files
2. Use `read_file` to extract tests
3. Use `write_to_file` to create UAT.md
4. Use `ask_followup_question` for each test
5. Parse responses and update UAT.md
6. Use `switch_mode` to debug mode for diagnosis
7. Use architect mode for gap planning
8. Use debug mode for plan verification
9. Complete and commit

**Challenges:**
- Conversational testing pattern needs careful implementation
- Parallel debug agent spawning
- Gap closure planning iteration loop

#### 5.2.3 map-codebase Workflow

**GSD Pattern:**
1. Check existing codebase map
2. Create .planning/codebase/ directory
3. Spawn 4 parallel mapper agents (tech, arch, quality, concerns)
4. Each agent writes documents directly
5. Collect confirmations
6. Verify output
7. Commit codebase map

**Kilo Code Adaptation:**
1. Use `list_files` to check existing
2. Use `write_to_file` to create files
3. Implement parallel agent spawning (may need custom implementation)
4. Each agent uses `list_files`, `search_files`, `read_file` for exploration
5. Use `write_to_file` to create documents
6. Use `execute_command` for git operations

**Challenges:**
- Parallel agent execution is the main challenge
- May need to implement sequential execution if parallel not supported

---

## 6. Template and Reference Updates

### 6.1 Template System Preservation

GSD's template system is critical and must be preserved:

| Template | Purpose | Kilo Code Adaptation |
|----------|---------|---------------------|
| **project.md** | Living project context with vision, requirements, decisions | Preserve in .kilocode/skills/gsd/templates/ |
| **state.md** | Project memory with current position, decisions, blockers | Preserve, update tool references |
| **roadmap.md** | Phase structure with goals and success criteria | Preserve, adapt formatting |
| **summary.md** | Phase completion documentation | Preserve, update commit format references |
| **UAT.md** | User acceptance testing framework | Preserve, adapt checkpoint references |
| **verification-report.md** | Verification results | Preserve, update tool references |
| **milestone-archive.md** | Milestone completion archive | Preserve |
| **continue-here.md** | Session continuation context | Preserve |
| **context.md** | Phase context for implementation decisions | Preserve |
| **requirements.md** | Project requirements | Preserve |
| **discovery.md** | Discovery research output | Preserve |
| **research.md** | Research output | Preserve |
| **codebase/** | Codebase mapping templates | Preserve all 7 templates |

### 6.2 Reference Documentation Updates

GSD references need to be updated for Kilo Code:

| Reference | Purpose | Kilo Code Updates |
|-----------|---------|------------------|
| **checkpoints.md** | Checkpoint types and protocols | Update tool references (e.g., replace Task tool with Kilo Code tools) |
| **verification-patterns.md** | How to verify artifacts | Update grep/bash commands to use Kilo Code tools |
| **git-integration.md** | Git commit formats and strategy | Preserve (git operations via execute_command) |
| **model-profiles.md** | Model profile definitions | Preserve (implement profile selection in GSD skill) |
| **planning-config.md** | Configuration options | Preserve (adapt to gsd.json) |
| **questioning.md** | Adaptive questioning patterns | Preserve |
| **tdd.md** | Test-driven development patterns | Preserve |
| **ui-brand.md** | UI branding guidelines | Preserve |
| **continuation-format.md** | Session continuation format | Preserve |

---

## 7. Configuration Changes Required

### 7.1 New Configuration Files

#### 7.1.1 .kilocode/config/gsd.json

```json
{
  "version": "1.0.0",
  "model_profile": "balanced",
  "planning": {
    "commit_docs": true,
    "search_gitignored": false
  },
  "model_profiles": {
    "quality": {
      "gsd-planner": "opus",
      "gsd-executor": "opus",
      "gsd-verifier": "sonnet",
      "gsd-roadmapper": "opus",
      "gsd-phase-researcher": "opus",
      "gsd-project-researcher": "opus",
      "gsd-research-synthesizer": "sonnet",
      "gsd-plan-checker": "sonnet",
      "gsd-codebase-mapper": "sonnet",
      "gsd-debugger": "opus",
      "gsd-integration-checker": "sonnet"
    },
    "balanced": {
      "gsd-planner": "opus",
      "gsd-executor": "sonnet",
      "gsd-verifier": "sonnet",
      "gsd-roadmapper": "sonnet",
      "gsd-phase-researcher": "sonnet",
      "gsd-project-researcher": "sonnet",
      "gsd-research-synthesizer": "sonnet",
      "gsd-plan-checker": "sonnet",
      "gsd-codebase-mapper": "haiku",
      "gsd-debugger": "sonnet",
      "gsd-integration-checker": "sonnet"
    },
    "budget": {
      "gsd-planner": "sonnet",
      "gsd-executor": "sonnet",
      "gsd-verifier": "haiku",
      "gsd-roadmapper": "sonnet",
      "gsd-phase-researcher": "haiku",
      "gsd-project-researcher": "haiku",
      "gsd-research-synthesizer": "haiku",
      "gsd-plan-checker": "haiku",
      "gsd-codebase-mapper": "haiku",
      "gsd-debugger": "sonnet",
      "gsd-integration-checker": "haiku"
    }
  },
  "workflow_toggles": {
    "auto_discovery": true,
    "auto_verification": true,
    "auto_diagnosis": true,
    "auto_gap_planning": true
  }
}
```

#### 7.1.2 .kilocode/modes/gsd-orchestrator/MODE.md

```markdown
# GSD Orchestrator Mode

## Purpose
Orchestrate GSD workflows for project management and execution.

## Capabilities
- Execute GSD commands
- Spawn and coordinate GSD agents
- Manage project state (STATE.md, ROADMAP.md)
- Handle checkpoints and user interactions
- Coordinate parallel agent execution

## Tool Access
- All Kilo Code tools (read_file, write_to_file, list_files, search_files, execute_command, etc.)
- ask_followup_question for checkpoints
- switch_mode for agent spawning

## When to Use
- Running GSD commands (/gsd:*)
- Coordinating multi-agent workflows
- Managing project state and artifacts
```

### 7.2 Existing Configuration Updates

#### 7.2.1 .kilocode/setup-script

Update to include GSD skill installation:

```bash
# Add GSD skill installation
echo "Installing GSD skill..."
mkdir -p .kilocode/skills/gsd
cp -r get-shit-done/agents .kilocode/skills/gsd/
cp -r get-shit-done/commands .kilocode/skills/gsd/
cp -r get-shit-done/get-shit-done/templates .kilocode/skills/gsd/
cp -r get-shit-done/get-shit-done/workflows .kilocode/skills/gsd/
cp -r get-shit-done/get-shit-done/references .kilocode/skills/gsd/

# Create GSD config
mkdir -p .kilocode/config
cat > .kilocode/config/gsd.json << 'EOF'
{
  "version": "1.0.0",
  "model_profile": "balanced",
  "planning": {
    "commit_docs": true,
    "search_gitignored": false
  }
}
EOF

echo "GSD skill installed successfully"
```

---

## 8. Testing Strategy

### 8.1 Unit Testing

#### 8.1.1 Agent Conversion Tests

For each of 11 agents:
- [ ] YAML frontmatter correctly extracted to metadata
- [ ] Process sections preserved as markdown
- [ ] Tool references mapped to Kilo Code equivalents
- [ ] Model profile selection logic works
- [ ] Checkpoint protocols use ask_followup_question correctly

#### 8.1.2 Command Conversion Tests

For each of 30+ commands:
- [ ] Frontmatter correctly extracted
- [ ] Process steps convert to Kilo Code workflow format
- [ ] Tool references updated
- [ ] Next command suggestions work

#### 8.1.3 Workflow Tests

For each workflow:
- [ ] Orchestration logic preserved
- [ ] Parallel agent spawning works (or sequential fallback)
- [ ] State management works
- [ ] Checkpoint handling works
- [ ] Error handling preserved

### 8.2 Integration Testing

#### 8.2.1 End-to-End Workflow Tests

Test complete GSD workflows in Kilo Code:

1. **New Project Flow:**
   - [ ] `/gsd:new-project` creates project artifacts
   - [ ] Research agents spawn and complete
   - [ ] Roadmap created with phases
   - [ ] STATE.md initialized

2. **Plan and Execute Flow:**
   - [ ] `/gsd:plan-phase` creates PLAN.md
   - [ ] `/gsd:execute-phase` executes plans
   - [ ] Checkpoints handled correctly
   - [ ] Atomic commits created
   - [ ] SUMMARY.md created
   - [ ] STATE.md updated

3. **Verification Flow:**
   - [ ] `/gsd:verify-work` creates UAT.md
   - [ ] Tests presented one at a time
   - [ ] Issues diagnosed with parallel agents
   - [ ] Gap plans created and executed
   - [ ] VERIFICATION.md created

4. **Codebase Mapping Flow:**
   - [ ] `/gsd:map-codebase` spawns parallel agents
   - [ ] 7 documents created
   - [ ] Documents have correct structure
   - [ ] Codebase map committed

### 8.3 Regression Testing

Ensure existing Kilo Code functionality is not broken:

- [ ] Existing modes (orchestrator, code, ask, architect, debug) work
- [ ] Existing agents (backend, data, devops, frontend, ml, test) work
- [ ] Existing tools work
- [ ] No conflicts with GSD skill

### 8.4 Performance Testing

- [ ] Parallel agent execution performance
- [ ] Large project handling (many phases/plans)
- [ ] State file parsing performance
- [ ] Git operation performance

---

## 9. Risk Assessment and Mitigation

### 9.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Parallel agent spawning not supported** | High | Medium | Implement sequential fallback; document limitation |
| **Model profile system incompatibility** | High | Low | Implement custom model selection in GSD skill |
| **Tool capability gaps** | Medium | Medium | Map GSD tools to closest Kilo Code equivalents; document gaps |
| **State management differences** | Medium | Low | Implement GSD state system on top of Kilo Code |
| **Git integration differences** | Low | Low | Use execute_command for git operations; preserve GSD commit format |

### 9.2 Process Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Incomplete agent conversion** | High | Medium | Systematic testing of each agent; user feedback loop |
| **Workflow logic errors** | High | Medium | Thorough workflow testing; preserve GSD logic |
| **Template/reference inconsistencies** | Medium | Low | Audit all templates and references for tool references |
| **Configuration complexity** | Medium | Low | Simplify configuration; provide sensible defaults |

### 9.3 User Experience Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Learning curve for Kilo Code users** | Medium | Medium | Comprehensive documentation; migration guide |
| **GSD power users frustrated by changes** | Medium | Low | Preserve GSD command interface; minimize changes |
| **Performance degradation** | Medium | Low | Performance testing; optimize critical paths |
| **Feature parity gaps** | High | Low | Document gaps; plan future enhancements |

### 9.4 Migration Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Time estimate exceeded** | Medium | Medium | Phased migration; prioritize core features |
| **Integration conflicts with existing Kilo Code** | High | Low | Isolate GSD as skill; test integration early |
| **Data loss during migration** | High | Low | Backup existing GSD projects; preserve .planning/ |
| **Rollback complexity** | Medium | Low | Version control; clear rollback plan |

---

## 10. Implementation Phases

### Phase 1: Foundation (10-15 hours)

**Goal:** Set up basic GSD skill structure in Kilo Code

**Tasks:**
1. Create .kilocode/skills/gsd/ directory structure
2. Create SKILL.md with skill metadata
3. Set up .kilocode/config/gsd.json
4. Create gsd-orchestrator mode
5. Migrate core templates (project.md, state.md, roadmap.md)
6. Migrate core references (checkpoints.md, git-integration.md)

**Deliverables:**
- GSD skill skeleton
- Configuration files
- Core templates and references

**Success Criteria:**
- Skill loads without errors
- Configuration works
- Templates can be read

### Phase 2: Agent Migration (15-20 hours)

**Goal:** Convert all 11 GSD agents to Kilo Code format

**Tasks:**
1. Convert gsd-planner
2. Convert gsd-executor
3. Convert gsd-verifier
4. Convert gsd-roadmapper
5. Convert gsd-phase-researcher
6. Convert gsd-project-researcher
7. Convert gsd-research-synthesizer
8. Convert gsd-plan-checker
9. Convert gsd-codebase-mapper
10. Convert gsd-debugger
11. Convert gsd-integration-checker

**Deliverables:**
- 11 converted agent files
- Agent metadata in SKILL.md
- Model profile system working

**Success Criteria:**
- All agents load
- Model profile selection works
- Tool references correct

### Phase 3: Command Migration (10-15 hours)

**Goal:** Convert all 30+ GSD commands to Kilo Code workflows

**Tasks:**
1. Migrate project initialization commands (new-project, map-codebase, set-profile)
2. Migrate planning commands (new-milestone, plan-phase, plan-milestone-gaps, research-phase, discuss-phase)
3. Migrate execution commands (execute-phase, execute-plan, quick, debug)
4. Migrate verification commands (verify-work, audit-milestone, complete-milestone)
5. Migrate state management commands (progress, pause-work, resume-work, check-todos)
6. Migrate project management commands (add-phase, insert-phase, remove-phase, add-todo, list-phase-assumptions)
7. Migrate system commands (settings, update, help, join-discord)

**Deliverables:**
- 30+ converted command workflows
- Command metadata in SKILL.md
- Command routing working

**Success Criteria:**
- All commands execute
- Command routing works
- Next command suggestions work

### Phase 4: Workflow Migration (5-10 hours)

**Goal:** Convert all GSD orchestration workflows

**Tasks:**
1. Convert execute-phase workflow
2. Convert execute-plan workflow
3. Convert verify-work workflow
4. Convert discovery-phase workflow
5. Convert map-codebase workflow
6. Convert diagnose-issues workflow
7. Convert complete-milestone workflow
8. Convert transition workflow
9. Convert verify-phase workflow
10. Convert list-phase-assumptions workflow

**Deliverables:**
- 10 converted workflow files
- Workflow orchestration working

**Success Criteria:**
- All workflows execute
- Parallel agent spawning works (or sequential fallback)
- State management works

### Phase 5: Testing and Refinement (10-15 hours)

**Goal:** Comprehensive testing and bug fixes

**Tasks:**
1. Unit testing (agents, commands, workflows)
2. Integration testing (end-to-end workflows)
3. Regression testing (existing Kilo Code functionality)
4. Performance testing
5. Bug fixes and refinements
6. Documentation updates

**Deliverables:**
- Test results
- Bug fixes
- Updated documentation

**Success Criteria:**
- All tests pass
- No regressions
- Performance acceptable

### Phase 6: Documentation and Deployment (5-10 hours)

**Goal:** Complete documentation and deploy

**Tasks:**
1. Write migration guide for GSD users
2. Write Kilo Code user guide for GSD
3. Write troubleshooting guide
4. Update README.md
5. Create example projects
6. Deploy to nascar-model project

**Deliverables:**
- Complete documentation
- Deployment complete

**Success Criteria:**
- Documentation complete
- Deployment successful
- Users can use GSD in Kilo Code

---

## 11. Key Architectural Decisions

### 11.1 Skill-Based Architecture

**Decision:** Implement GSD as a Kilo Code skill rather than modifying core Kilo Code.

**Rationale:**
- Preserves separation of concerns
- Allows GSD to be optional
- Easier to maintain and update
- Follows Kilo Code's plugin architecture

**Tradeoffs:**
- Some GSD features may need custom implementation
- May have performance overhead
- Requires skill loading mechanism

### 11.2 New GSD Orchestrator Mode

**Decision:** Create a new gsd-orchestrator mode for GSD-specific orchestration.

**Rationale:**
- GSD has unique orchestration requirements
- Preserves GSD's command interface
- Allows GSD to leverage Kilo Code tools
- Keeps GSD logic isolated

**Tradeoffs:**
- Adds complexity to mode system
- May duplicate some orchestrator functionality

### 11.3 Preserve GSD State System

**Decision:** Preserve GSD's STATE.md, ROADMAP.md, and artifact system.

**Rationale:**
- GSD's state management is sophisticated and battle-tested
- Preserves existing GSD projects
- Minimizes migration effort
- Maintains GSD's unique capabilities

**Tradeoffs:**
- Adds complexity (dual state systems)
- May confuse Kilo Code users

### 11.4 Sequential Fallback for Parallel Execution

**Decision:** Implement parallel agent spawning if supported, with sequential fallback.

**Rationale:**
- GSD heavily relies on parallel execution
- Kilo Code may not support parallel mode switching
- Sequential fallback ensures functionality

**Tradeoffs:**
- Performance degradation if parallel not supported
- More complex implementation

### 11.5 Preserve Model Profile System

**Decision:** Preserve GSD's model profile system (quality/balanced/budget).

**Rationale:**
- Critical for cost control
- Well-designed allocation strategy
- Preserves GSD's flexibility

**Tradeoffs:**
- Requires custom implementation
- May conflict with Kilo Code's model selection

---

## 12. GSD Component to Kilo Code Mapping

### 12.1 Agent Mapping Summary

| GSD Agent | Kilo Code Mode | Primary Tools | Notes |
|-----------|---------------|---------------|-------|
| gsd-planner | architect | read_file, write_to_file, list_files, search_files | Goal-backward methodology |
| gsd-executor | code | edit_file, write_to_file, execute_command | Checkpoint protocols |
| gsd-verifier | debug | read_file, search_files, list_files | Verification patterns |
| gsd-roadmapper | architect | write_to_file, read_file | Milestone/phase structure |
| gsd-phase-researcher | ask | search_files, read_file | Research patterns |
| gsd-project-researcher | ask | search_files, read_file | Parallel research |
| gsd-research-synthesizer | architect | read_file, write_to_file | Synthesis logic |
| gsd-plan-checker | debug | read_file, search_files | Iteration loop |
| gsd-codebase-mapper | architect | list_files, search_files, read_file | Parallel mapping |
| gsd-debugger | debug | read_file, search_files, execute_command | Debug sessions |
| gsd-integration-checker | test | read_file, search_files, execute_command | Integration testing |

### 12.2 Command Mapping Summary

| Category | Commands | Kilo Code Implementation |
|----------|-----------|------------------------|
| Project Init | new-project, map-codebase, set-profile | New commands in gsd skill |
| Planning | new-milestone, plan-phase, plan-milestone-gaps, research-phase, discuss-phase | New commands |
| Execution | execute-phase, execute-plan, quick, debug | New commands |
| Verification | verify-work, audit-milestone, complete-milestone | New commands |
| State Mgmt | progress, pause-work, resume-work, check-todos | New commands |
| Project Mgmt | add-phase, insert-phase, remove-phase, add-todo, list-phase-assumptions | New commands |
| System | settings, update, help, join-discord | New commands |

### 12.3 Tool Mapping Summary

| GSD Tool | Kilo Code Tool | Notes |
|-----------|---------------|-------|
| Bash tool | execute_command | Direct mapping |
| Write tool | write_to_file | Direct mapping |
| Read tool | read_file | Direct mapping |
| Explore tool | list_files + search_files | Combination |
| Task tool | switch_mode | Mode switching for agents |
| AskUserQuestion | ask_followup_question | Direct mapping |
| Git operations | execute_command | Via bash commands |

### 12.4 Template Mapping Summary

| GSD Template | Kilo Code Location | Notes |
|-------------|-------------------|-------|
| project.md | .kilocode/skills/gsd/templates/ | Preserve |
| state.md | .kilocode/skills/gsd/templates/ | Preserve |
| roadmap.md | .kilocode/skills/gsd/templates/ | Preserve |
| summary.md | .kilocode/skills/gsd/templates/ | Preserve |
| UAT.md | .kilocode/skills/gsd/templates/ | Preserve |
| verification-report.md | .kilocode/skills/gsd/templates/ | Preserve |
| codebase/* | .kilocode/skills/gsd/templates/codebase/ | Preserve all 7 |

### 12.5 Reference Mapping Summary

| GSD Reference | Kilo Code Location | Notes |
|---------------|-------------------|-------|
| checkpoints.md | .kilocode/skills/gsd/references/ | Update tool references |
| verification-patterns.md | .kilocode/skills/gsd/references/ | Update grep/bash commands |
| git-integration.md | .kilocode/skills/gsd/references/ | Preserve |
| model-profiles.md | .kilocode/skills/gsd/references/ | Preserve |
| planning-config.md | .kilocode/skills/gsd/references/ | Adapt to gsd.json |
| questioning.md | .kilocode/skills/gsd/references/ | Preserve |
| tdd.md | .kilocode/skills/gsd/references/ | Preserve |
| ui-brand.md | .kilocode/skills/gsd/references/ | Preserve |
| continuation-format.md | .kilocode/skills/gsd/references/ | Preserve |

---

## 13. Blockers and Concerns

### 13.1 Technical Blockers

1. **Parallel Agent Spawning**
   - **Issue:** GSD relies heavily on parallel agent execution (e.g., 4 mapper agents, parallel debug agents)
   - **Concern:** Kilo Code may not support spawning multiple agents in parallel
   - **Mitigation:** Implement sequential fallback; document performance impact
   - **Status:** Needs investigation

2. **Model Profile System**
   - **Issue:** GSD has sophisticated model profile system (quality/balanced/budget)
   - **Concern:** Kilo Code may not support per-agent model selection
   - **Mitigation:** Implement custom model selection in GSD skill
   - **Status:** Needs implementation

3. **Agent Tracking and Resume**
   - **Issue:** GSD tracks spawned agents (agent-history.json, current-agent-id.txt) for resume capability
   - **Concern:** Kilo Code may not provide agent tracking
   - **Mitigation:** Implement custom tracking in GSD skill
   - **Status:** Needs implementation

4. **Context Transfer Between Agents**
   - **Issue:** GSD orchestrator stays lean by having agents write documents directly
   - **Concern:** Kilo Code mode switching may not preserve this pattern
   - **Mitigation:** Adapt to Kilo Code's context management
   - **Status:** Needs investigation

### 13.2 Process Concerns

1. **Conversion Complexity**
   - **Issue:** 11 agents, 30+ commands, 10 workflows, 15+ templates, 9+ references
   - **Concern:** High conversion effort may exceed estimate
   - **Mitigation:** Phased approach; prioritize core features
   - **Status:** Managed

2. **Testing Coverage**
   - **Issue:** Comprehensive testing of all converted components
   - **Concern:** Time-consuming; may miss edge cases
   - **Mitigation:** Focus on critical paths; user feedback loop
   - **Status:** Planned

3. **Documentation Gap**
   - **Issue:** Need documentation for both GSD users and Kilo Code users
   - **Concern:** Significant documentation effort
   - **Mitigation:** Start with migration guide; expand based on feedback
   - **Status:** Planned

### 13.3 User Experience Concerns

1. **Learning Curve**
   - **Issue:** GSD users need to learn Kilo Code interface
   - **Concern:** May reduce adoption
   - **Mitigation:** Preserve GSD command interface; comprehensive docs
   - **Status:** Addressed in plan

2. **Feature Parity**
   - **Issue:** Some GSD features may not map perfectly to Kilo Code
   - **Concern:** Reduced functionality
   - **Mitigation:** Document gaps; plan future enhancements
   - **Status:** Ongoing assessment

3. **Performance**
   - **Issue:** Sequential fallback for parallel execution may be slower
   - **Concern:** User frustration
   - **Mitigation:** Optimize critical paths; document expectations
   - **Status:** Needs testing

---

## 14. Success Criteria

### 14.1 Technical Success Criteria

- [ ] All 11 GSD agents converted and functional
- [ ] All 30+ GSD commands converted and functional
- [ ] All 10 GSD workflows converted and functional
- [ ] All templates and references migrated
- [ ] Model profile system working
- [ ] State management working (STATE.md, ROADMAP.md)
- [ ] Checkpoint system working (human-verify, decision, human-action)
- [ ] Git integration working (atomic commits)
- [ ] No regressions in existing Kilo Code functionality

### 14.2 User Experience Success Criteria

- [ ] GSD users can use familiar commands in Kilo Code
- [ ] Kilo Code users can discover and use GSD features
- [ ] Documentation is comprehensive and clear
- [ ] Performance is acceptable (within 20% of GSD native)
- [ ] Error messages are helpful
- [ ] Learning curve is manageable

### 14.3 Project Success Criteria

- [ ] Migration completed within estimated time (40-60 hours)
- [ ] Budget not exceeded significantly
- [ ] Integration into nascar-model successful
- [ ] User feedback positive
- [ ] Maintenance burden manageable

---

## 15. Conclusion

This migration plan provides a comprehensive roadmap for porting GSD from Claude Code/OpenCode to work natively with Kilo Code. The key challenges are:

1. **Parallel agent execution** - May need sequential fallback
2. **Model profile system** - Requires custom implementation
3. **Agent tracking and resume** - Needs custom implementation
4. **Conversion complexity** - 11 agents, 30+ commands, 10 workflows

The proposed architecture implements GSD as a Kilo Code skill with a new gsd-orchestrator mode, preserving GSD's sophisticated orchestration while leveraging Kilo Code's infrastructure.

The phased approach (6 phases, 40-60 hours) allows for iterative development, testing, and refinement. Risk mitigation strategies address the main technical and process concerns.

If executed according to this plan, the result will be a fully functional GSD system integrated into Kilo Code, providing users with GSD's powerful project management and execution capabilities within Kilo Code's environment.

---

## Appendix A: File Inventory

### A.1 GSD Files to Migrate

**Agents (11 files):**
- get-shit-done/agents/gsd-codebase-mapper.md
- get-shit-done/agents/gsd-debugger.md
- get-shit-done/agents/gsd-executor.md
- get-shit-done/agents/gsd-integration-checker.md
- get-shit-done/agents/gsd-phase-researcher.md
- get-shit-done/agents/gsd-plan-checker.md
- get-shit-done/agents/gsd-planner.md
- get-shit-done/agents/gsd-project-researcher.md
- get-shit-done/agents/gsd-research-synthesizer.md
- get-shit-done/agents/gsd-roadmapper.md
- get-shit-done/agents/gsd-verifier.md

**Commands (30+ files):**
- get-shit-done/commands/gsd/add-phase.md
- get-shit-done/commands/gsd/add-todo.md
- get-shit-done/commands/gsd/audit-milestone.md
- get-shit-done/commands/gsd/check-todos.md
- get-shit-done/commands/gsd/complete-milestone.md
- get-shit-done/commands/gsd/debug.md
- get-shit-done/commands/gsd/discuss-phase.md
- get-shit-done/commands/gsd/execute-phase.md
- get-shit-done/commands/gsd/execute-plan.md
- get-shit-done/commands/gsd/help.md
- get-shit-done/commands/gsd/insert-phase.md
- get-shit-done/commands/gsd/join-discord.md
- get-shit-done/commands/gsd/list-phase-assumptions.md
- get-shit-done/commands/gsd/map-codebase.md
- get-shit-done/commands/gsd/new-milestone.md
- get-shit-done/commands/gsd/new-project.md
- get-shit-done/commands/gsd/pause-work.md
- get-shit-done/commands/gsd/plan-milestone-gaps.md
- get-shit-done/commands/gsd/plan-phase.md
- get-shit-done/commands/gsd/progress.md
- get-shit-done/commands/gsd/quick.md
- get-shit-done/commands/gsd/remove-phase.md
- get-shit-done/commands/gsd/research-phase.md
- get-shit-done/commands/gsd/resume-work.md
- get-shit-done/commands/gsd/set-profile.md
- get-shit-done/commands/gsd/settings.md
- get-shit-done/commands/gsd/update.md
- get-shit-done/commands/gsd/verify-work.md

**Workflows (10 files):**
- get-shit-done/get-shit-done/workflows/complete-milestone.md
- get-shit-done/get-shit-done/workflows/diagnose-issues.md
- get-shit-done/get-shit-done/workflows/discovery-phase.md
- get-shit-done/get-shit-done/workflows/discuss-phase.md
- get-shit-done/get-shit-done/workflows/execute-phase.md
- get-shit-done/get-shit-done/workflows/execute-plan.md
- get-shit-done/get-shit-done/workflows/list-phase-assumptions.md
- get-shit-done/get-shit-done/workflows/map-codebase.md
- get-shit-done/get-shit-done/workflows/resume-project.md
- get-shit-done/get-shit-done/workflows/transition.md
- get-shit-done/get-shit-done/workflows/verify-phase.md
- get-shit-done/get-shit-done/workflows/verify-work.md

**Templates (20+ files):**
- get-shit-done/get-shit-done/templates/config.json
- get-shit-done/get-shit-done/templates/context.md
- get-shit-done/get-shit-done/templates/continue-here.md
- get-shit-done/get-shit-done/templates/debug-subagent-prompt.md
- get-shit-done/get-shit-done/templates/DEBUG.md
- get-shit-done/get-shit-done/templates/discovery.md
- get-shit-done/get-shit-done/templates/milestone-archive.md
- get-shit-done/get-shit-done/templates/milestone.md
- get-shit-done/get-shit-done/templates/phase-prompt.md
- get-shit-done/get-shit-done/templates/planner-subagent-prompt.md
- get-shit-done/get-shit-done/templates/project.md
- get-shit-done/get-shit-done/templates/requirements.md
- get-shit-done/get-shit-done/templates/research.md
- get-shit-done/get-shit-done/templates/roadmap.md
- get-shit-done/get-shit-done/templates/state.md
- get-shit-done/get-shit-done/templates/summary.md
- get-shit-done/get-shit-done/templates/UAT.md
- get-shit-done/get-shit-done/templates/user-setup.md
- get-shit-done/get-shit-done/templates/verification-report.md
- get-shit-done/get-shit-done/templates/codebase/architecture.md
- get-shit-done/get-shit-done/templates/codebase/concerns.md
- get-shit-done/get-shit-done/templates/codebase/conventions.md
- get-shit-done/get-shit-done/templates/codebase/integrations.md
- get-shit-done/get-shit-done/templates/codebase/stack.md
- get-shit-done/get-shit-done/templates/codebase/structure.md
- get-shit-done/get-shit-done/templates/codebase/testing.md

**References (9 files):**
- get-shit-done/get-shit-done/references/checkpoints.md
- get-shit-done/get-shit-done/references/continuation-format.md
- get-shit-done/get-shit-done/references/git-integration.md
- get-shit-done/get-shit-done/references/model-profiles.md
- get-shit-done/get-shit-done/references/planning-config.md
- get-shit-done/get-shit-done/references/questioning.md
- get-shit-done/get-shit-done/references/tdd.md
- get-shit-done/get-shit-done/references/ui-brand.md
- get-shit-done/get-shit-done/references/verification-patterns.md

**Total Files to Migrate:** ~80 files

### A.2 New Kilo Code Files to Create

**Skill Structure:**
- .kilocode/skills/gsd/SKILL.md
- .kilocode/modes/gsd-orchestrator/MODE.md
- .kilocode/config/gsd.json

**Migrated Files:** ~80 files (see above)

**Total New Files:** ~83 files

---

## Appendix B: Glossary

| Term | Definition |
|-------|------------|
| **GSD** | Get Shit Done - A sophisticated multi-agent project management and execution framework for Claude Code/OpenCode |
| **Kilo Code** | The target AI coding assistant with mode-based system (orchestrator, code, ask, architect, debug) |
| **Agent** | Specialized AI entity with specific role, tools, and process instructions |
| **Command** | User-invocable workflow that orchestrates agents and operations |
| **Workflow** | Orchestration pattern for complex multi-step operations |
| **Checkpoint** | Human interaction point in automated execution (human-verify, decision, human-action) |
| **Model Profile** | Configuration controlling which Claude model each agent uses (quality/balanced/budget) |
| **Goal-Backward Methodology** | Planning approach that starts from what must be TRUE for goal achievement |
| **Atomic Commit** | Git commit for each individual task with structured message format |
| **Skill** | Kilo Code's plugin system for extending functionality |
| **Mode** | Kilo Code's execution context with different capabilities (orchestrator, code, ask, architect, debug) |
| **STATE.md** | GSD's living project memory with current position, decisions, blockers |
| **ROADMAP.md** | GSD's phase structure with goals and success criteria |
| **PLAN.md** | GSD's executable plan with tasks, checkpoints, and deviation rules |
| **SUMMARY.md** | GSD's phase completion documentation |
| **UAT.md** | GSD's user acceptance testing framework |
| **VERIFICATION.md** | GSD's verification results document |
| **Wave-Based Parallelization** | GSD's execution strategy where independent plans execute in parallel waves |

---

**Document Version:** 1.0
**Last Updated:** 2025-01-25
**Author:** Kilo Code Architect Mode
**Status:** Draft - Ready for Review
