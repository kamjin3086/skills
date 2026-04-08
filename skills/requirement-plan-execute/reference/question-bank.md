# Question Bank — Domain-Specific Templates

> Reference file for the Requirement Elicitation & Plan Assembly skill.
> Read this file when you need domain-specific questions beyond the core 10 in [SKILL.md](../SKILL.md).

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

Use these templates when a user's answer is too vague:

### Vague Goal
```
User said: "I want to improve the system."

Follow-up: "Can you describe what 'improved' looks like?
For example:
  (A) Faster response times
  (B) Fewer bugs or errors
  (C) Better user experience
  (D) Easier to maintain
  (E) Something else — please describe"
```

### Vague Scope
```
User said: "Build a dashboard."

Follow-up: "To scope this properly, I need to understand:
  1. What data should the dashboard display?
  2. How many distinct views or pages?
  3. Does it need real-time updates or is periodic refresh OK?
  4. Who will use this dashboard? (internal team, customers, executives)"
```

### Vague Constraint
```
User said: "It should be fast."

Follow-up: "Can you quantify 'fast'?
  (A) Under 100ms response time (real-time feel)
  (B) Under 1 second (responsive)
  (C) Under 10 seconds (acceptable for batch/report)
  (D) Not sure — what is the current performance?"
```

### Contradictory Requirements
```
Detected: User wants [A] but also [B], which conflicts.

Follow-up: "I noticed a potential conflict:
  - You mentioned wanting [A]
  - But you also said [B]
  - These may conflict because [reason]

  Which should take priority? Or is there a middle ground you'd accept?"
```
