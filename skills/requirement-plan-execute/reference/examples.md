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

#### Batch 1 — Background & Goal + Constraints

**Agent asks (using AskQuestion tool or conversational options):**

> A few quick questions to scope this:
>
> 1. What type of project?
>    (A) ⭐ Web app (accessible to whole team instantly)
>    (B) Mobile app (needs app store distribution)
>    (C) CLI tool (developer-only usage)
>    (D) Other — specify
>
> 2. What's the core problem?
>    (A) Replacing a clunky existing tool (migration needed)
>    (B) No tool exists yet (greenfield)
>    (C) Scaling/improving current solution
>    (D) Other
>
> 3. Team size?
>    (A) 1-5  (B) 5-20  (C) 20-100  (D) 100+
>
> 4. Tech stack preference?
>    (A) ⭐ React + Node.js (most common, huge ecosystem)
>    (B) Vue + Python
>    (C) Next.js (SSR built-in)
>    (D) Other — specify
>
> 5. Timeline?
>    (A) 1-2 weeks (tight, MVP only)
>    (B) ⭐ 3-4 weeks (solid MVP with core features)
>    (C) 1-3 months (full-featured v1)
>    (D) No deadline

**User responds:**

> A, A (spreadsheets are a mess — tasks get lost), B (about 15 devs), A, B

#### Batch 2 — Scope & Integrations

**Agent asks:**

> 6. Which of these are IN scope? (pick all that apply)
>    (A) Task CRUD + assignment (core)
>    (B) Status tracking / kanban board (visual workflow)
>    (C) Time tracking (effort logging)
>    (D) Calendar integration (deadline sync)
>    (E) File attachments (docs on tasks)
>    (F) GitHub integration (link PRs to tasks)
>
> 7. What matters most?
>    (A) ⭐ Ship fast — polish later (get team using it ASAP)
>    (B) Polished UX from day one (higher adoption, slower delivery)
>    (C) Performance/scale (optimize for large data)
>    (D) Maintainability (clean code, easy to extend)

**User responds:**

> A, B, F are in scope. C/D/E out. And A — ship fast, but I like Linear's simplicity. Concerned about team adoption if it's clunky.

**Agent auto-decides (not asked):**
- Project structure: monorepo with `/frontend` and `/backend`
- Linting: ESLint + Prettier defaults
- Git workflow: feature branches + PRs

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
> ### Auto-decided (defaults chosen, override if needed)
> - Project structure: monorepo (`/frontend` + `/backend`) — standard for React+Node
> - Linting: ESLint + Prettier — team convention
> - Git workflow: feature branches + PRs — industry default
>
> **Does this look right? Check the auto-decided items too — override any you disagree with.**

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

**User confirms.** Agent then offers:

> "Would you like me to output an **agent-executable version** of this plan? That version is optimized for pasting into a coding agent for direct implementation."

**User responds**: "Yes, give me the agent version."

**Agent outputs:**

> # Team Task Manager — Agent Execution Plan
>
> ## Context
> - Tech stack: React, Node.js, PostgreSQL
> - Monorepo: `/frontend` (React), `/backend` (Node.js)
> - Timeline: 4 weeks MVP. UX reference: Linear
>
> ## Tasks
>
> ### Phase 1: Foundation (Week 1)
>
> #### Task 1.1: Project Setup
> - **Do**: Scaffold monorepo with React frontend (`/frontend`) and Node.js+Express backend (`/backend`). Add shared config for ESLint + Prettier.
> - **Files**: `package.json`, `frontend/`, `backend/`, `.eslintrc`, `.prettierrc`
> - **Depends on**: None
> - **Done when**:
>   - [ ] `npm run dev` starts both frontend and backend
>   - [ ] Health-check endpoint at `GET /api/health` returns 200
>
> #### Task 1.2: Database Schema
> - **Do**: Create PostgreSQL schema with `users`, `tasks`, `task_assignments` tables. Write migration scripts.
> - **Files**: `backend/migrations/`, `backend/src/db/`
> - **Depends on**: 1.1
> - **Done when**:
>   - [ ] Migrations run without errors
>   - [ ] Schema supports CRUD + assignment
>
> #### Task 1.3: Auth System
> - **Do**: Implement email+password signup/login endpoints. Use bcrypt for hashing, JWT for sessions. Add auth middleware.
> - **Files**: `backend/src/routes/auth.ts`, `backend/src/middleware/auth.ts`
> - **Depends on**: 1.2
> - **Done when**:
>   - [ ] POST `/api/auth/signup` creates user
>   - [ ] POST `/api/auth/login` returns JWT
>   - [ ] Protected routes reject requests without valid JWT
>
> ### Phase 2: Core Features (Week 2-3)
>
> #### Task 2.1: Task API
> - **Do**: CRUD endpoints for tasks. Support assignment, status transitions (todo/in-progress/done), filtering by status and assignee.
> - **Files**: `backend/src/routes/tasks.ts`, `backend/src/models/task.ts`
> - **Depends on**: 1.2, 1.3
> - **Done when**:
>   - [ ] All CRUD operations work via API
>   - [ ] Filter by `?status=` and `?assignee=` works
>
> #### Task 2.2: Kanban Board UI
> - **Do**: Build kanban board with 3 columns (To Do, In Progress, Done). Add drag-and-drop (use `@dnd-kit`). Task detail modal on click.
> - **Files**: `frontend/src/components/Board/`, `frontend/src/components/TaskModal/`
> - **Depends on**: 2.1
> - **Done when**:
>   - [ ] Tasks render in correct columns
>   - [ ] Drag-and-drop updates status
>   - [ ] Click opens detail modal
>
> #### Task 2.3: Team & Assignment
> - **Do**: User list page. Assignment dropdown on task cards.
> - **Files**: `frontend/src/components/TeamList/`, `frontend/src/components/AssignDropdown/`
> - **Depends on**: 2.1
> - **Done when**:
>   - [ ] All team members visible
>   - [ ] Can assign/reassign from board
>
> ### Phase 3: Integration & Ship (Week 4)
>
> #### Task 3.1: GitHub PR Linking
> - **Do**: Add PR URL field to tasks. Fetch PR status via GitHub REST API (personal token auth). Display status badge on task card.
> - **Files**: `backend/src/services/github.ts`, `frontend/src/components/PRBadge/`
> - **Depends on**: 2.1
> - **Done when**:
>   - [ ] User can paste PR URL on a task
>   - [ ] PR status (open/merged/closed) shows on card
>
> #### Task 3.2: UX Polish
> - **Do**: Add keyboard shortcuts (N=new task, Esc=close modal). Loading states, error toasts, empty states. Clean minimal styling (Linear reference).
> - **Files**: `frontend/src/hooks/useKeyboard.ts`, `frontend/src/components/`
> - **Depends on**: 2.2
> - **Done when**:
>   - [ ] Keyboard shortcuts work
>   - [ ] Loading/error states present
>
> #### Task 3.3: Deployment
> - **Do**: Docker Compose setup for local + production. Basic CI with GitHub Actions (lint + test on push).
> - **Files**: `docker-compose.yml`, `Dockerfile`, `.github/workflows/ci.yml`
> - **Depends on**: All above
> - **Done when**:
>   - [ ] `docker compose up` runs full stack
>   - [ ] CI passes on push
>
> ## Notes for Agent
> - Use TypeScript throughout
> - Follow existing ESLint + Prettier config
> - Keep components small and composable — Linear-style simplicity
> - Do not implement time tracking, calendar, or file attachments

Mission complete.

---

## Why This Example Works

1. **Questions used selectable options** — user picked A/B/C instead of typing paragraphs, making interaction fast.
2. **Trivial items were auto-decided** (project structure, linting, git workflow) — listed in summary for transparency.
3. **Gaps were caught** (auth, database, GitHub scope) — Phase 2 prevented building the wrong thing.
4. **Summary was confirmed** before any planning — alignment checkpoint.
5. **Research was separated** from implementation — uncertainty handled explicitly.
6. **Every task has a deliverable and acceptance criteria** — nothing vague.
7. **Risks were named** with mitigation — the plan is honest about what could go wrong.
8. **The plan is phase-sequenced** with dependencies — execution order is clear.
9. **Agent-executable version was offered and delivered** — ready to paste into a coding agent for implementation.
