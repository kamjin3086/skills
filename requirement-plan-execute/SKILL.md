---
name: requirement-plan-execute
description: Elicit requirements through structured questioning, then decompose and assemble an actionable plan. Use when the user has a complex or ambiguous task, wants help planning before coding, asks for a plan, or when requirements need clarification before implementation. Trigger on phrases like "plan this", "help me think through", "I need to build", or any multi-step project request.
---

# Requirement Elicitation & Plan Assembly

Turn vague or complex requests into clear, actionable plans through structured questioning and decomposition.

## How This Skill Works

```
Phase 1: ASK     → Gather context via structured questions
Phase 2: VERIFY  → Identify gaps, follow up until clear
Phase 3: DECOMPOSE → Break requirements into tasks + research
Phase 4: PLAN    → Assemble final actionable plan
```

**Mission complete after Phase 4.** Execution is a separate concern.

---

## Phase 1: ASK — Requirement Elicitation

**Goal**: Collect enough context to understand what the user wants.

Ask questions in THREE categories. Use the AskQuestion tool when available; otherwise ask conversationally.

### Category A: Background & Goal

Ask these first:
1. **What** is the end goal? (What does "done" look like?)
2. **Why** is this needed? (What problem does it solve?)
3. **Who** will use it? (Target audience or stakeholders)

### Category B: Constraints & Boundaries

Then ask:
4. **Tech stack**: Any required languages, frameworks, or platforms?
5. **Timeline**: Any deadline or urgency?
6. **Scope limits**: What is explicitly OUT of scope?
7. **Dependencies**: Any existing systems, APIs, or data sources involved?

### Category C: Preferences & Quality

Finally ask:
8. **Quality priorities**: Performance vs. speed-to-ship vs. maintainability?
9. **Style preferences**: Any patterns, conventions, or examples to follow?
10. **Known risks**: Anything the user is worried about?

> **IMPORTANT**: Do NOT ask all 10 questions at once. Group them into 2-3 batches. Start with Category A, then B, then C.

For domain-specific question templates, see [question-bank.md](reference/question-bank.md).

### Phase 1 Completion Checklist

Before moving to Phase 2, confirm you have answers for at least:
- [ ] Clear end goal
- [ ] Core problem / motivation
- [ ] Key constraints (tech, timeline, scope)

---

## Phase 2: VERIFY — Gap Analysis & Follow-up

**Goal**: Ensure no critical information is missing or ambiguous.

### Step 2.1: Review Answers

Re-read all user answers. For each answer, ask yourself:
- Is this specific enough to act on?
- Are there implicit assumptions I need to confirm?
- Does this contradict anything else the user said?

### Step 2.2: Follow-up Questions

For any gaps or ambiguities found, ask follow-up questions. Use this format:

```
I want to clarify a few points before planning:

1. You mentioned [X]. Does that mean [interpretation A] or [interpretation B]?
2. You said [Y] is out of scope, but [Z] seems to depend on it. How should I handle that?
3. For [constraint], what is the acceptable trade-off if we can't fully meet it?
```

### Step 2.3: Summarize Understanding

After all gaps are filled, present a **Requirement Summary** to the user for confirmation:

```markdown
## Requirement Summary

**Goal**: [one sentence]
**Problem**: [one sentence]
**Users**: [who]
**Tech Stack**: [list]
**Scope**: [in-scope items] | **Out of scope**: [excluded items]
**Constraints**: [timeline, performance, etc.]
**Priorities**: [ranked: e.g. correctness > performance > speed-to-ship]
```

Ask the user: **"Does this summary accurately capture your requirements? Anything to add or correct?"**

Do NOT proceed to Phase 3 until the user confirms.

---

## Phase 3: DECOMPOSE — Requirement Breakdown

**Goal**: Break the confirmed requirements into concrete, actionable pieces.

### Step 3.1: Identify Major Components

List the 3-7 major components or feature areas. For each component:
- Name it clearly
- Describe what it does in one sentence
- List its inputs and outputs

### Step 3.2: Research Tasks

For any component that involves unfamiliar technology or uncertainty, create a research task:

```
RESEARCH: [topic]
- Question to answer: [specific question]
- How to investigate: [search docs / read codebase / check API]
- Decision needed: [what choice depends on this research]
```

### Step 3.3: Task Breakdown

For each component, list concrete tasks. Each task must have:
- **Clear deliverable**: What artifact is produced?
- **Estimated complexity**: Small / Medium / Large
- **Dependencies**: Which other tasks must complete first?

For the plan output template, see [plan-template.md](reference/plan-template.md).

---

## Phase 4: PLAN — Assembly

**Goal**: Organize tasks into a sequenced, actionable plan.

### Step 4.1: Dependency Ordering

Arrange tasks respecting dependencies. Tasks with no dependencies come first. Group into phases where possible.

### Step 4.2: Assemble the Plan

Use the plan template from [plan-template.md](reference/plan-template.md) to produce the final plan.

### Step 4.3: Present and Confirm

Present the complete plan to the user. Ask:
- "Does this plan look reasonable?"
- "Any tasks missing or priorities to adjust?"

The skill's mission is complete after the user confirms the plan.

---

## Key Rules for Agents

1. **Never skip questioning.** Even if the request seems clear, confirm at least the goal, constraints, and priorities.
2. **Never plan without confirmation.** Always get user approval on the requirement summary before decomposing.
3. **Keep questions focused.** 3-5 questions per batch, never a wall of 10+ questions.
4. **Be concrete.** Every task in the plan must have a clear deliverable, not just "think about X".
5. **Surface trade-offs.** When you see competing constraints, name them explicitly and ask the user to choose.

---

## Reference Files

All supplementary material lives under `reference/`:

| File | Purpose |
|------|---------|
| [reference/question-bank.md](reference/question-bank.md) | Domain-specific question templates |
| [reference/plan-template.md](reference/plan-template.md) | Plan output format and task templates |
| [reference/examples.md](reference/examples.md) | Complete worked example of the full workflow |
