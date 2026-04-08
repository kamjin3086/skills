# Question Bank — Domain-Specific Templates

> Reference file for the Requirement Elicitation & Plan Assembly skill.
> Read this file when you need domain-specific questions beyond the core 10 in [SKILL.md](../SKILL.md).

## Interaction Style Guide

**All questions should follow the option-driven format:**

```
[Short question]
  (A) ⭐ [Option 1] ([brief note on why recommended])
  (B) [Option 2] ([brief note on implication/trade-off])
  (C) [Option 3] ([brief note on implication/trade-off])
  (D) Other — please specify
```

**Option formatting rules:**
- Add a parenthetical note when the option's meaning or trade-off isn't obvious — e.g., `(B) GraphQL (flexible queries, steeper learning curve)`.
- Mark one recommended option with `⭐` when there is a clearly better choice given the project context. Omit the marker when no option is clearly superior.
- Keep notes short — ideally under 8 words per note.

When using the `AskQuestion` tool, map each option to a selectable choice. Always include an open-ended escape hatch.

**When to auto-decide instead of asking:**
- The choice has no meaningful impact on architecture or scope (e.g., lint config, file naming convention)
- There is an obvious industry default (e.g., UTF-8 encoding, .gitignore inclusion)
- The codebase already implies the answer (e.g., existing package.json reveals the framework)

## Table of Contents

- [Web Application Projects](#web-application-projects)
- [API / Backend Projects](#api--backend-projects)
- [Data Pipeline / ETL Projects](#data-pipeline--etl-projects)
- [CLI Tool Projects](#cli-tool-projects)
- [Refactoring / Migration Projects](#refactoring--migration-projects)
- [AI / ML Projects](#ai--ml-projects)
- [General Clarification Patterns](#general-clarification-patterns)

---

## Web Application Projects

### Background & Goal
- Is this a new app or adding features to an existing app?
- What are the 3 most important pages or user flows?
- Is there a design mockup, wireframe, or reference site?

### Constraints
- Does it need to support mobile, desktop, or both?
- Are there specific browsers that must be supported?
- Is SSR (server-side rendering) required, or is CSR acceptable?
- What authentication method is needed? (OAuth, email/password, SSO, none)

### Preferences
- Any UI library preference? (e.g., Tailwind, Material UI, Ant Design)
- Do you have an existing design system or component library?
- What level of accessibility (a11y) compliance is required?

---

## API / Backend Projects

### Background & Goal
- Is this a new API or extending an existing one?
- What are the primary consumers of this API? (frontend, mobile, third-party)
- What data entities are involved?

### Constraints
- Expected request volume? (rough order of magnitude)
- Latency requirements? (real-time vs. eventual consistency)
- Authentication and authorization model?
- Any rate limiting or throttling needs?

### Preferences
- REST vs. GraphQL vs. gRPC?
- Database preference? (SQL, NoSQL, existing DB)
- Any API documentation standard? (OpenAPI, etc.)

---

## Data Pipeline / ETL Projects

### Background & Goal
- What data sources are involved? (databases, APIs, files)
- What is the destination or output format?
- What transformations are needed?

### Constraints
- How frequently does the pipeline run? (real-time, hourly, daily)
- What is the expected data volume per run?
- Are there data quality or validation requirements?
- How should errors and failed records be handled?

### Preferences
- Batch vs. streaming processing?
- Any orchestration tool preference? (Airflow, Prefect, cron)
- Where should intermediate data be stored?

---

## CLI Tool Projects

### Background & Goal
- What problem does this tool solve?
- Who are the target users? (developers, ops, end users)
- What is the primary input and output?

### Constraints
- Which operating systems must be supported?
- Any installation method preference? (pip, npm, binary, etc.)
- Does it need to work offline?

### Preferences
- Interactive or non-interactive (scriptable)?
- Any argument parsing convention? (POSIX, GNU-style)
- Should it produce structured output? (JSON, table, plain text)

---

## Refactoring / Migration Projects

### Background & Goal
- What is being migrated? (language, framework, database, architecture)
- What is the current state and desired end state?
- Why is this migration needed? (performance, maintainability, EOL)

### Constraints
- Can the migration happen incrementally or must it be all-at-once?
- Is there a rollback plan needed?
- What is the acceptable downtime window?
- Are there tests covering the current behavior?

### Preferences
- Should the new code maintain backward compatibility?
- Is this an opportunity to also clean up tech debt, or strictly 1:1 migration?
- How should the team coordinate during the migration?

---

## AI / ML Projects

### Background & Goal
- What is the prediction/generation task?
- What data is available for training or inference?
- What does a successful output look like? (accuracy, quality, latency)

### Constraints
- Inference latency budget? (real-time vs. batch)
- Hardware constraints? (GPU available? Cloud or local?)
- Privacy / data sensitivity concerns?
- Budget for API calls or compute?

### Preferences
- Pre-trained model vs. fine-tuned vs. trained from scratch?
- Any framework preference? (PyTorch, TensorFlow, HuggingFace)
- How should model performance be evaluated?

---

## General Clarification Patterns

Use these option-driven templates when a user's answer is too vague:

### Vague Goal
```
User said: "I want to improve the system."

Follow-up: "What does 'improved' mean here?
  (A) Faster response times (reduce latency / throughput)
  (B) Fewer bugs or errors (stability focus)
  (C) Better user experience (UI/UX polish)
  (D) Easier to maintain (refactor / simplify code)
  (E) Other — please specify"
```

### Vague Scope
```
User said: "Build a dashboard."

Follow-up: "What kind of dashboard?
  (A) Analytics (charts, metrics, trends)
  (B) Admin panel (manage data/users)
  (C) Monitoring (real-time system health)
  (D) Other — please specify

Who uses it?
  (A) Internal team (devs/ops)
  (B) Customers (external-facing)
  (C) Executives (high-level KPIs)
  (D) Other"
```

### Vague Constraint
```
User said: "It should be fast."

Follow-up: "How fast?
  (A) < 100ms (real-time feel, needs optimization)
  (B) ⭐ < 1s (responsive, standard target)
  (C) < 10s (batch/report, relaxed)
  (D) Not sure — what's current performance?"
```

### Contradictory Requirements
```
Detected: User wants [A] but also [B], which conflicts.

Follow-up: "These two seem to conflict:
  - [A] vs. [B] — because [reason]

  Which wins?
  (A) Prioritize [A] ([trade-off note])
  (B) Prioritize [B] ([trade-off note])
  (C) Find a middle ground — I'll suggest one"
```
