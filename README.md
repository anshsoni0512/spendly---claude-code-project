# Spendly (Sonico) — Personal Expense Tracker

> A full-stack web app built entirely using **Claude Code** (AI-powered CLI by Anthropic)
> 
> ---

## Live Demo

### [https://spendly-production-d15b.up.railway.app](https://spendly-production-d15b.up.railway.app)

---


## What is Spendly?

Spendly is a personal finance tracker built with Python and Flask. It gives users a clean dashboard to manage their day-to-day spending, from adding expenses to viewing category-wise breakdowns and monthly trends.

**Key features:**
- Secure user registration and login (password hashing with Werkzeug)
- Add, edit, and delete expenses with category tagging
- Profile dashboard with total spending stats and top category
- Filter expenses by month or custom date range
- Category breakdown with percentage bars
- Analytics page with spending insights
- Fully responsive UI built with vanilla CSS

---

## How I Built This with Claude Code

This project was built **step by step using Claude Code** - Anthropic's AI coding assistant that runs directly in your terminal. Instead of writing all the code manually, I described what I wanted and Claude Code wrote the routes, templates, database queries, and tests - while I reviewed and guided the direction.

### 1. Spec-Driven Development
Every feature started as a **spec file** (a plain text description of what the feature should do). Claude Code read the spec and implemented it - keeping things predictable and reviewable at each step.

| Step | Feature |
|------|---------|
| 01 | Database setup - SQLite schema for users and expenses |
| 02 | User registration with validation |
| 03 | Login & session-based authentication |
| 04 | Profile page UI with expense table |
| 05 | Backend profile routes and stats helpers |
| 06 | Date filter on profile (month picker, custom range) |
| 07 | Add expense form with server-side validation |
| 08 | Edit expense with ownership checks |
| 09 | Delete expense with confirmation |

After each step, Claude Code also wrote **pytest tests** based on the spec - not the implementation - so tests verified behavior, not just code.

### 2. Custom Slash Commands
To avoid repeating the same instructions every session, I created reusable slash commands stored in `.claude/commands/`. These are markdown files that Claude Code executes when called:

| Command | What it does |
|---------|-------------|
| `/acp` | Runs `git add .` → `git commit` → `git push` in one shot |
| `/createspec` | Scaffolds a spec file and feature branch for the next step |
| `/seeduser` | Inserts a dummy user into the local database for testing |
| `/seedexpense` | Seeds sample expense data into the database |
| `/code-review` | Launches parallel security + quality review agents on changed code |
| `/test-feature` | Runs pytest for a specific feature |
| `/ship` | Pushes the latest changes to GitHub |

### 3. Custom AI Sub-Agents
Beyond slash commands, I set up specialized AI agents inside `.claude/agents/`. Each agent has its own role and only activates when needed:

- **spendly-test-writer** - reads a feature spec and writes pytest test cases from scratch, spec-first not implementation-first
- **pytest-test-runner** - takes the completed test suite and runs it, reporting pass/fail with context
- **Quality Reviewer (qr)** - reviews changed code for readability, duplication, and Flask best practices
- **Security Reviewer (sr)** - scans the same diff for security issues like SQL injection, missing auth checks, or session misuse

The quality and security agents ran **in parallel** on every feature using `/code-review`, giving two independent opinions at once.

### 4. CLAUDE.md - Project Memory
A `CLAUDE.md` file at the root of the project told Claude Code everything it needed to know about the codebase - architecture, commands to run the app, the database schema, and conventions like currency format. This meant every new conversation started with full context, no re-explaining needed.

### 5. Marketplace Plugins
I extended Claude Code's capabilities by installing a plugin from the marketplace:

```bash
/plugin marketplace add railwayapp/railway-skills
/reload-plugins
```

This gave Claude Code the `railway:use-railway` skill — it could now create Railway projects, deploy the app, generate domains, and read deployment logs, all from within the conversation without leaving the terminal.

---

## Project Structure

```
spendly/
├── app.py                  # All Flask routes
├── wsgi.py                 # Gunicorn entry point
├── Procfile                # Railway start command
├── requirements.txt        # Python dependencies
├── database/
│   └── db.py               # get_db, init_db, seed_db
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS and JS
├── tests/                  # pytest test suite
└── .claude/
    ├── commands/           # Custom slash commands
    ├── agents/             # Custom AI sub-agents
    ├── specs/              # Feature spec files (01–09)
    └── settings.json       # Claude Code permissions
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3 / Flask |
| Database | SQLite |
| Templates | Jinja2 |
| Frontend | Vanilla CSS + JS |
| Testing | pytest + pytest-flask |
| Production Server | Gunicorn |
| Hosting | Railway |
| Version Control | GitHub |

---

## Deployment

The app is deployed on **Railway** with GitHub connected for automatic deploys:

```
Write code → /acp → GitHub (push) → Railway detects push → Auto-builds & deploys → Live
```

**How it was set up:**
1. Installed Railway CLI via npm: `npm install -g @railway/cli`
2. Authenticated: `railway login --browserless`
3. Created project: `railway init --name spendly`
4. Added `gunicorn` to `requirements.txt` and created a `Procfile`
5. First deploy: `railway up --ci -m "initial deploy"`
6. Generated public domain: `railway domain`
7. Connected GitHub repo in Railway dashboard for auto-deploys

Every `git push origin main` now triggers a full rebuild and redeploy automatically.

---

## Running Locally

```bash
# Clone the repo
git clone https://github.com/anshsoni0512/spendly---claude-code-project.git
cd spendly---claude-code-project

# Install dependencies
pip install -r requirements.txt

# Run the development server
python app.py
# Visit http://localhost:5001
```

Demo account (auto-seeded on first run):
- **Email:** `demo@spendly.com`
- **Password:** `demo123`



*Built by **Ansh Soni** using [Claude Code](https://claude.ai/code) by Anthropic*
