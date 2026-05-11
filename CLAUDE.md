# CLAUDE.md
ansh soni the great

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Spendly** — a personal expense tracker web app. This is an educational project with a partially-built Flask backend; routes and the database layer are progressively implemented as features are added.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (http://localhost:5001, debug=True)
python app.py

# Run tests
pytest
pytest -v
pytest -k <test_name>
```

No linting tools are configured.

## Architecture

**Stack**: Python 3 / Flask, SQLite, Jinja2 templates, vanilla CSS + JS.

**Entry point**: `app.py` — defines all Flask routes. Routes are split into implemented ones (`/`, `/register`, `/login`, `/terms`, `/privacy`) and placeholder stubs (`/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`) that students fill in progressively.

**Database layer**: `database/db.py` — stub module with three functions to implement:
- `get_db()` — returns an SQLite connection (row_factory + foreign keys enabled)
- `init_db()` — creates tables via `CREATE TABLE IF NOT EXISTS`
- `seed_db()` — populates sample data

The database file `expense_tracker.db` is gitignored and created at runtime. The inferred schema from the UI: `users` (id, name, email, password_hash) and `expenses` (id, user_id, amount, category, date, description).

**Templates**: Jinja2 with base inheritance. `base.html` provides the navbar and footer; all other pages extend it.


**Currency**: The app targets Indian users — use ₹ (not $) in UI text and mock data.
