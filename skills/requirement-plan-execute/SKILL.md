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

**Goal**: Collect enough context to understand what the user wants — quickly and with minimal friction.

### Interaction Principles

1. **Be concise.** Ask short, direct questions. No preambles or lengthy explanations.
2. **Provide selectable options.** Every question should offer 2-5 concrete choices (A/B/C/D) so the user can pick quickly instead of typing long answers. Use the `AskQuestion` tool when available.
3. **Annotate options for clarity.** When an option's meaning isn't self-evident, add a brief parenthetical note explaining its implication — e.g., `(A) SSR (better SEO, slower dev setup)`. This helps the user make informed choices without extra back-and-forth.
4. **Mark recommended options.** When there is a clearly superior or conventional choice given the context, mark it with `⭐` — e.g., `(A) ⭐ React (matches existing codebase)`. Only mark one option per question; omit the marker when no option is clearly better.
5. **Always accept custom answers.** Include an "Other (please specify)" or open-ended escape hatch on every question. The agent must recognize and incorporate free-text answers gracefully.
6. **Auto-decide trivial items.** For decisions that have minimal impact on the overall plan (e.g., folder structure conventions, minor naming choices, standard linting setup), make a reasonable default choice and **do not ask the user**. List these auto-decisions in the Phase 2 summary for transparency.
7. **Batch efficiently.** Group questions into 1-3 batches. Fewer is better — merge questions when possible without sacrificing clarity.

### Question Categories

#### Category A: Background & Goal (ask first)

1. **What** is the end goal? → Offer likely project types as options
2. **Why** is this needed? → Offer common motivations as options
3. **Who** will use it? → Offer audience types as options

#### Category B: Constraints & Boundaries (ask second)

4. **Tech stack** → Detect from codebase when possible; confirm with options
5. **Timeline** → Offer timeframe ranges
6. **Scope limits** → List likely features and ask which are OUT
7. **Dependencies** → Offer common integrations as options

#### Category C: Preferences & Quality (ask last, or merge into B when simple)

8. **Quality priorities** → Offer ranked-choice among: speed-to-ship, performance, maintainability, UX polish
9. **Style preferences** → Only ask when genuinely impactful; otherwise auto-decide
10. **Known risks** → Optional; only ask if the project has obvious risk areas

> **IMPORTANT**: Do NOT ask all questions at once. Use 1-3 batches. Merge Category C into B when the project is straightforward. Skip questions you can infer from context or the codebase.

For domain-specific question templates with options, see [question-bank.md](reference/question-bank.md).

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

### Auto-decided (no user input needed)
- [item]: [chosen default] — [brief reason]
- [item]: [chosen default] — [brief reason]
```

The **Auto-decided** section lists all trivial decisions the agent made without asking. This gives the user visibility and a chance to override if needed.

Ask the user: **"Does this summary accurately capture your requirements? Check the auto-decided items too — override any you disagree with."**

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

**Goal**: Organize tasks into a sequenced, actionable plan that is clear, rigorous, and not overly verbose.

### Step 4.1: Dependency Ordering

Arrange tasks respecting dependencies. Tasks with no dependencies come first. Group into phases where possible.

### Step 4.2: Assemble the Plan

Use the plan template from [plan-template.md](reference/plan-template.md) to produce the final plan.

**Writing guidelines for the plan**:
- **Be precise, not verbose.** Each task description should be 1-2 sentences max. Cut filler words.
- **Every task must be actionable.** A developer should be able to start working from the task card alone.
- **Use tables and lists over paragraphs.** Dense, scannable formats beat prose.
- **Keep the total plan concise.** Aim for a plan that fits in one focused reading session. If the plan exceeds ~40 tasks, group them into sub-plans or milestones.

### Step 4.3: Present and Confirm

Present the complete plan to the user. Ask:
- "Does this plan look reasonable?"
- "Any tasks missing or priorities to adjust?"

### Step 4.4: Offer Agent-Executable Output

After the user confirms the plan, **always** offer:

> "Would you like me to output an **agent-executable version** of this plan? That version is optimized for pasting into a coding agent (e.g., Cursor, Copilot) for direct implementation — with precise instructions, file paths, and acceptance criteria, but no conversational prose."

If the user accepts, re-format the plan using the **Agent-Executable Plan Template** from [plan-template.md](reference/plan-template.md). Key differences from the human-readable version:
- No conversational tone — imperative instructions only
- Include file paths and code-level details where known
- Each task is a self-contained instruction block
- Remove risk register and overview prose — keep only actionable content

The skill's mission is complete after the user confirms the plan (and receives the agent version if requested).

---

## Key Rules for Agents

1. **Never skip questioning.** Even if the request seems clear, confirm at least the goal, constraints, and priorities.
2. **Never plan without confirmation.** Always get user approval on the requirement summary before decomposing.
3. **Keep questions concise and option-driven.** 3-5 questions per batch with selectable choices. Never send a wall of open-ended questions.
4. **Auto-decide what doesn't matter.** Trivial choices should be made by the agent and listed in the summary — not asked to the user.
5. **Be concrete.** Every task in the plan must have a clear deliverable, not just "think about X".
6. **Surface trade-offs.** When you see competing constraints, name them explicitly and ask the user to choose.
7. **Keep plans concise.** Rigorous and complete, but no filler. A good plan is one page you can act on, not ten pages you'll never re-read.
8. **Always offer agent-executable output.** After plan confirmation, prompt the user about the agent-optimized version.

---

## Reference Files

All supplementary material lives under `reference/`:

| File | Purpose |
|------|---------|
| [reference/question-bank.md](reference/question-bank.md) | Domain-specific question templates |
| [reference/plan-template.md](reference/plan-template.md) | Plan output format and task templates |
| [reference/examples.md](reference/examples.md) | Complete worked example of the full workflow |
