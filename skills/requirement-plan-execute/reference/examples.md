# Worked Example — Full Workflow

> Reference file for the Requirement Elicitation & Plan Assembly skill.
> Read this file to see a complete example of all 4 phases in [SKILL.md](../SKILL.md) applied to a real-world scenario.

## Table of Contents

- [Scenario: Team Task Management App](#scenario-team-task-management-app)
  - [Phase 1: ASK](#phase-1-ask)
  - [Phase 2: VERIFY](#phase-2-verify)
  - [Phase 3: DECOMPOSE](#phase-3-decompose)
  - [Phase 4: PLAN](#phase-4-plan)

---

## Scenario: Team Task Management App

**User's initial request**: "I want to build a task management tool for my team."

This is a typical vague request. Below is how the agent handles it through all 4 phases.

---

### Phase 1: ASK

#### Batch 1 — Background & Goal

**Agent asks:**

> To help you plan this effectively, I need to understand the big picture first:
>
> 1. What does "done" look like for this project? Is it a web app, mobile app, CLI tool, or something else?
> 2. What problem are you solving? Is your team currently using another tool that doesn't work well, or is there no tool at all?
> 3. How many people will use this? Just your immediate team, or the whole company?

**User responds:**

> It's a web app. We're using spreadsheets right now and it's a mess — tasks get lost, no one knows what's assigned to whom. It's a team of about 15 people, all developers.

#### Batch 2 — Constraints & Boundaries

**Agent asks:**

> Got it. Now some practical constraints:
>
> 4. Do you have a preferred tech stack? (e.g., React, Vue, Node.js, Python, etc.)
> 5. Is there a deadline or timeline? When would you like this to be usable?
> 6. What is explicitly out of scope? For example: time tracking, calendar integration, file attachments?
> 7. Any existing systems this needs to connect to? (e.g., Slack, GitHub, email)

**User responds:**

> We use React and Node.js. I'd like a working version in 4 weeks. Out of scope: time tracking, calendar integration. It should integrate with our GitHub repos for linking PRs to tasks.

#### Batch 3 — Preferences & Quality

**Agent asks:**

> Almost done with questions:
>
> 8. What matters most: polished UI, fast performance, or getting it shipped quickly?
> 9. Any existing task management tools you like the UX of? (for reference)
> 10. Any concerns or risks you're already thinking about?

**User responds:**

> Ship quickly first, polish later. I like Linear's simplicity. My concern is that team adoption might be low if it's clunky.

---

### Phase 2: VERIFY

#### Step 2.1 — Gap Analysis

The agent reviews the answers and identifies:
- **Gap**: No mention of authentication. Does the team need login?
- **Gap**: No mention of data storage. What database?
- **Ambiguity**: "Integrate with GitHub" — does this mean show PR status on tasks, or create tasks from GitHub issues?

#### Step 2.2 — Follow-up

**Agent asks:**

> I want to clarify a few points before planning:
>
> 1. Does this need user authentication? (e.g., each person logs in with their account)
> 2. Do you have a database preference? (PostgreSQL, MongoDB, SQLite, etc.)
> 3. For the GitHub integration — should it:
>    (A) Let users link PRs to tasks and show PR status
>    (B) Automatically create tasks from GitHub issues
>    (C) Both
>    (D) Something else

**User responds:**

> Yes, simple login with email. PostgreSQL — we already have a server. For GitHub, option A — just link PRs and show their status.

#### Step 2.3 — Summary

**Agent presents:**

> ## Requirement Summary
>
> **Goal**: Build a web-based task management app to replace spreadsheets for a 15-person dev team
> **Problem**: Tasks get lost in spreadsheets; no clear ownership or status visibility
> **Users**: 15 developers on one team
> **Tech Stack**: React (frontend), Node.js (backend), PostgreSQL (database)
> **In Scope**:
> - Task CRUD (create, read, update, delete)
> - Task assignment to team members
> - Task status tracking (e.g., To Do, In Progress, Done)
> - Simple email-based authentication
> - GitHub PR linking with status display
>
> **Out of Scope**:
> - Time tracking
> - Calendar integration
> - File attachments
> - GitHub issue sync
>
> **Constraints**:
> - Timeline: 4 weeks to working version
> - UX: Simple and clean (Linear as reference)
> - Adoption risk: Must not feel clunky
>
> **Priorities** (ranked):
> 1. Ship quickly (working MVP)
> 2. Usability (low friction for adoption)
> 3. Polish (can come later)
>
> **Does this summary accurately capture your requirements? Anything to add or correct?**

**User responds**: "Looks good. Let's go."

---

### Phase 3: DECOMPOSE

#### Step 3.1 — Major Components

| # | Component | Description | Inputs | Outputs |
|---|-----------|-------------|--------|---------|
| 1 | Auth System | Email-based login and session management | Email + password | JWT token, session |
| 2 | Task Engine | Core CRUD and assignment logic | User actions | Task data |
| 3 | Board UI | Kanban-style board for viewing and managing tasks | Task data | Visual board |
| 4 | GitHub Integration | Link PRs to tasks, display PR status | GitHub API | PR status on task cards |
| 5 | Database Layer | Schema design and data access | App queries | Stored data |
| 6 | Deployment | Get the app running and accessible | Built app | Live URL |

#### Step 3.2 — Research Tasks

```
RESEARCH: GitHub API for PR status

Question: What GitHub API endpoints do we need to fetch PR status, and do we need a GitHub App or is a personal token sufficient?
Why it matters: Determines auth complexity and rate limiting for GitHub integration.
How to investigate:
  - [ ] Read GitHub REST API docs for pull requests
  - [ ] Check rate limits for personal tokens vs. GitHub Apps
  - [ ] Test fetching PR status with a sample token
Expected output: Decision on auth method + list of needed API endpoints
Time estimate: 1 hour
```

#### Step 3.3 — Task Breakdown

(Tasks shown in abbreviated form; full task cards use the template from [plan-template.md](plan-template.md).)

**Auth System**: Setup auth middleware, login/signup endpoints, JWT handling
**Task Engine**: DB schema for tasks, CRUD API endpoints, assignment logic, status transitions
**Board UI**: Kanban board component, drag-and-drop, task detail modal
**GitHub Integration**: PR linking UI, GitHub API service, PR status polling
**Database Layer**: Schema migration scripts, seed data
**Deployment**: Docker setup, basic CI

---

### Phase 4: PLAN

**Agent assembles and presents:**

> # Implementation Plan: Team Task Manager
>
> ## Overview
> Build a Kanban-style task management web app using React + Node.js + PostgreSQL. The MVP replaces the team's spreadsheets with a clean, simple interface for creating, assigning, and tracking tasks. GitHub PR linking is included.
>
> ## Research Phase
>
> ### RESEARCH: GitHub API for PR status
> **Question**: Which API endpoints and auth method for fetching PR status?
> **How to investigate**:
>   - [ ] Read GitHub REST API docs for pull requests
>   - [ ] Compare personal token vs. GitHub App rate limits
> **Expected output**: Auth method decision + endpoint list
> **Time estimate**: 1 hour
>
> ## Implementation Phases
>
> ### Phase 1: Foundation (Week 1)
> **Goal**: Database, auth, and project skeleton
>
> #### Task 1.1: Project Setup
> **Deliverable**: Monorepo with React frontend + Node.js backend scaffolded
> **Complexity**: Small
> **Depends on**: None
> **Acceptance criteria**:
>   - [ ] `npm run dev` starts both frontend and backend
>   - [ ] Basic health check endpoint responds
>
> #### Task 1.2: Database Schema
> **Deliverable**: PostgreSQL schema with users, tasks, and assignments tables
> **Complexity**: Medium
> **Depends on**: Task 1.1
> **Acceptance criteria**:
>   - [ ] Migration scripts run cleanly
>   - [ ] Schema supports task CRUD and user assignment
>
> #### Task 1.3: Auth System
> **Deliverable**: Login/signup endpoints with JWT-based session
> **Complexity**: Medium
> **Depends on**: Task 1.2
> **Acceptance criteria**:
>   - [ ] User can sign up with email and password
>   - [ ] User can log in and receive a JWT
>   - [ ] Protected routes reject unauthenticated requests
>
> ### Phase 2: Core Features (Week 2-3)
> **Goal**: Task CRUD and Kanban board
>
> #### Task 2.1: Task API
> **Deliverable**: REST endpoints for task CRUD + assignment
> **Complexity**: Medium
> **Depends on**: Task 1.2, Task 1.3
> **Acceptance criteria**:
>   - [ ] Create, read, update, delete tasks via API
>   - [ ] Assign tasks to users
>   - [ ] Filter tasks by status and assignee
>
> #### Task 2.2: Kanban Board UI
> **Deliverable**: React board with columns for To Do, In Progress, Done
> **Complexity**: Large
> **Depends on**: Task 2.1
> **Acceptance criteria**:
>   - [ ] Tasks displayed in correct columns
>   - [ ] Drag-and-drop moves tasks between columns
>   - [ ] Task detail modal shows full info
>
> #### Task 2.3: Team Management
> **Deliverable**: User list page + task assignment dropdown
> **Complexity**: Small
> **Depends on**: Task 2.1
> **Acceptance criteria**:
>   - [ ] See all team members
>   - [ ] Assign/reassign tasks from the board
>
> ### Phase 3: Integration & Ship (Week 4)
> **Goal**: GitHub integration, polish, deploy
>
> #### Task 3.1: GitHub PR Linking
> **Deliverable**: PR link field on tasks + status badge showing PR state
> **Complexity**: Medium
> **Depends on**: Task 2.1, Research
> **Acceptance criteria**:
>   - [ ] User can paste a PR URL on a task
>   - [ ] PR status (open/merged/closed) displays on the task card
>
> #### Task 3.2: UX Polish
> **Deliverable**: UI improvements based on Linear's simplicity
> **Complexity**: Medium
> **Depends on**: Task 2.2
> **Acceptance criteria**:
>   - [ ] Keyboard shortcuts for common actions
>   - [ ] Clean, minimal design
>   - [ ] Loading states and error handling
>
> #### Task 3.3: Deployment
> **Deliverable**: App deployed and accessible via URL
> **Complexity**: Medium
> **Depends on**: All previous tasks
> **Acceptance criteria**:
>   - [ ] Docker Compose setup for local and production
>   - [ ] App accessible at a team-shared URL
>   - [ ] Basic CI runs tests on push
>
> ## Risk Register
> | Risk | Impact | Likelihood | Mitigation |
> |------|--------|------------|------------|
> | GitHub API rate limits | Medium | Low | Use caching; poll status every 5 min instead of real-time |
> | Low team adoption | High | Medium | Keep UX simple; get 2-3 team members to beta test in Week 3 |
> | 4-week deadline too tight | Medium | Medium | Task 3.2 (polish) is deferrable; ship functional MVP first |
>
> ## Summary
> - **Total tasks**: 9
> - **Research tasks**: 1
> - **Estimated phases**: 3 (4 weeks)
> - **Key decision points**: GitHub auth method (token vs. App)
>
> **Does this plan look reasonable? Any tasks missing or priorities to adjust?**

**User confirms.** Mission complete.

---

## Why This Example Works

1. **Questions were batched** (3 per batch, not 10 at once) — reduces cognitive load on the user.
2. **Gaps were caught** (auth, database, GitHub scope) — Phase 2 prevented building the wrong thing.
3. **Summary was confirmed** before any planning — alignment checkpoint.
4. **Research was separated** from implementation — uncertainty handled explicitly.
5. **Every task has a deliverable and acceptance criteria** — nothing vague.
6. **Risks were named** with mitigation — the plan is honest about what could go wrong.
7. **The plan is phase-sequenced** with dependencies — execution order is clear.
