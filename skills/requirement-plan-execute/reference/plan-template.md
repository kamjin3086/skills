# Plan Output Templates

> Reference file for the Requirement Elicitation & Plan Assembly skill.
> Read this file when assembling the final plan in Phase 3 and Phase 4 of [SKILL.md](../SKILL.md).

## Table of Contents

- [Requirement Summary Template](#requirement-summary-template)
- [Research Task Template](#research-task-template)
- [Task Card Template](#task-card-template)
- [Full Plan Template](#full-plan-template)
- [Complexity Sizing Guide](#complexity-sizing-guide)

---

## Requirement Summary Template

Use this after Phase 2 to confirm understanding with the user.

```markdown
## Requirement Summary

**Goal**: [What the user wants to achieve, in one sentence]
**Problem**: [What problem this solves or what need it fulfills]
**Users**: [Who will use or benefit from this]
**Tech Stack**: [Languages, frameworks, platforms, databases]
**In Scope**: [Bullet list of what IS included]
**Out of Scope**: [Bullet list of what is NOT included]
**Constraints**:
  - Timeline: [deadline or urgency level]
  - Performance: [latency, throughput, or scale requirements]
  - Other: [any additional constraints]
**Priorities** (ranked):
  1. [Most important quality attribute]
  2. [Second most important]
  3. [Third most important]

### Auto-decided (defaults chosen, override if needed)
- [item]: [default chosen] — [why]
- [item]: [default chosen] — [why]
```

---

## Research Task Template

Use this when a component involves uncertainty or unfamiliar technology.

```markdown
### RESEARCH: [Topic Name]

**Question**: [Specific question to answer]
**Why it matters**: [What decision depends on this answer]
**How to investigate**:
  - [ ] [Action 1, e.g., "Read official docs for X"]
  - [ ] [Action 2, e.g., "Check if library Y supports feature Z"]
  - [ ] [Action 3, e.g., "Test API endpoint with sample data"]
**Expected output**: [What artifact this research produces, e.g., "Decision document", "Proof of concept", "Comparison table"]
**Time estimate**: [e.g., "30 minutes", "2 hours"]
```

---

## Task Card Template

Every task in the plan must follow this format.

```markdown
### Task [ID]: [Task Name]

**Deliverable**: [What concrete artifact is produced]
**Complexity**: [Small / Medium / Large — see sizing guide below]
**Depends on**: [Task IDs that must complete first, or "None"]
**Description**: [1-3 sentences explaining what to do]
**Acceptance criteria**:
  - [ ] [Criterion 1]
  - [ ] [Criterion 2]
```

### Rules for Writing Task Cards

1. **Deliverable is mandatory.** If you cannot name a deliverable, the task is too vague — break it down further.
2. **"Think about X" is not a task.** Rewrite as "Produce a [document/decision/diagram] about X."
3. **Acceptance criteria must be verifiable.** Use binary pass/fail checks, not subjective judgments.
4. **Dependencies must be explicit.** If task B needs task A's output, say so.

---

## Full Plan Template

Use this to assemble the final plan in Phase 4.

```markdown
# Implementation Plan: [Project Name]

## Overview
[2-3 sentences summarizing what will be built and the approach]

## Requirement Summary
[Copy the confirmed requirement summary from Phase 2]

## Research Phase
[List all research tasks. Skip this section if none are needed.]

### RESEARCH: [Topic 1]
[Use Research Task Template]

### RESEARCH: [Topic 2]
[Use Research Task Template]

## Implementation Phases

### Phase 1: [Phase Name, e.g., "Foundation & Setup"]
**Goal**: [What this phase achieves]

#### Task 1.1: [Task Name]
**Deliverable**: [artifact]
**Complexity**: [Small/Medium/Large]
**Depends on**: None
**Description**: [what to do]
**Acceptance criteria**:
  - [ ] [criterion]

#### Task 1.2: [Task Name]
...

### Phase 2: [Phase Name, e.g., "Core Features"]
**Goal**: [What this phase achieves]

#### Task 2.1: [Task Name]
...

### Phase 3: [Phase Name, e.g., "Integration & Polish"]
**Goal**: [What this phase achieves]

#### Task 3.1: [Task Name]
...

## Risk Register
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| [risk 1] | High/Med/Low | High/Med/Low | [mitigation strategy] |
| [risk 2] | ... | ... | ... |

## Summary
- **Total tasks**: [count]
- **Research tasks**: [count]
- **Estimated phases**: [count]
- **Key decision points**: [list any decisions that may change the plan]
```

---

## Agent-Executable Plan Template

Use this when the user requests an agent-optimized version of the plan. This format is designed to be pasted directly into a coding agent (e.g., Cursor Agent, Copilot) for implementation.

**Key differences from the human-readable plan:**
- Imperative tone — direct instructions, no conversational prose
- File paths and code-level hints included where known
- No risk register or overview narrative — only actionable content
- Each task is a self-contained instruction block an agent can execute independently

```markdown
# [Project Name] — Agent Execution Plan

## Context
- Tech stack: [stack]
- Key constraints: [1-2 sentence summary]

## Tasks

### [Phase 1 Name]

#### Task 1.1: [Task Name]
- **Do**: [Imperative instruction: "Create...", "Add...", "Implement..."]
- **Files**: [file paths to create or modify, if known]
- **Depends on**: [Task IDs or "None"]
- **Done when**:
  - [ ] [Verifiable criterion 1]
  - [ ] [Verifiable criterion 2]

#### Task 1.2: [Task Name]
- **Do**: [instruction]
- **Files**: [paths]
- **Depends on**: [IDs]
- **Done when**:
  - [ ] [criterion]

### [Phase 2 Name]

#### Task 2.1: [Task Name]
...

## Notes for Agent
- [Any global instructions: coding style, testing expectations, commit conventions]
- [Anything the agent should NOT do: e.g., "Do not modify auth middleware"]
```

### Rules for Agent-Executable Output

1. **No prose.** Every line must be an instruction, a file path, or a criterion.
2. **Imperative voice.** "Create X" not "We need to create X".
3. **Include file paths** when the codebase structure is known.
4. **Keep each task under 5 lines.** If longer, break into sub-tasks.
5. **Add a "Notes for Agent" section** for cross-cutting concerns (style, testing, etc.).

---

## Complexity Sizing Guide

Use this guide to consistently estimate task complexity.

| Size | Typical Scope | Examples |
|------|---------------|---------|
| **Small** | Single file change, straightforward logic, well-understood pattern | Add a config field, write a utility function, fix a typo |
| **Medium** | Multiple files, some design decisions, moderate logic | Build a new API endpoint, create a UI component with state, write integration tests |
| **Large** | Cross-cutting concern, significant design work, high uncertainty | Design a database schema, implement authentication flow, build a data pipeline |

### Decision Checklist

When unsure about sizing, ask:
- Does this touch more than 3 files? → Likely Medium or Large
- Does this require a design decision? → Likely Medium or Large
- Is there significant uncertainty? → Likely Large
- Could a junior developer do this in under 1 hour? → Likely Small
