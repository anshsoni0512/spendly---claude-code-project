# Spec: Profile Page Backend Routes

## Overview

This feature replaces the hardcoded data in the `/profile` route with real database queries. The profile page UI was built in Step 4 with static dicts; Step 5 wires it to the actual `users` and `expenses` tables so the logged-in user sees their own name, email, join date, real transactions, computed stats (total spent, transaction count, top category), and a live category breakdown — all derived from the DB at request time.

## Depends on

- Step 1: Database setup (users and expenses tables must exist)
- Step 2: Registration (real user rows must be creatable)
- Step 3: Login + Logout (session["user_id"] must be set correctly)
- Step 4: Profile page UI (profile.html template must exist and accept the same context variables)

## Routes

- `GET /profile` — fetch real user and expense data from DB, render profile.html — logged-in only (redirect to /login if not authenticated)

No new routes. Only the existing `/profile` view function is updated.

## Database changes

No database changes. The existing `users` and `expenses` tables are sufficient.

## Templates

- **Modify:** `templates/profile.html` — update the member-since display to use `user.member_since` formatted from `created_at`; ensure all template variables match the new context shape described below.

No new templates.

## Context variables passed to profile.html

Replace all hardcoded dicts with DB-derived values:

- `user` — dict with keys: `name`, `email`, `member_since` (formatted as "Month YYYY" from `created_at`)
- `stats` — dict with keys:
  - `total_spent` — formatted as `₹X,XXX` (sum of all expense amounts for the user)
  - `transactions` — integer count of all expenses for the user
  - `top_category` — name of the category with the highest total spend
- `transactions` — list of dicts ordered by date DESC, each with: `date`, `description`, `category`, `amount` (formatted as `₹X,XXX.XX`)
- `categories` — list of dicts ordered by total DESC, each with: `name`, `amount` (formatted as `₹X,XXX`), `percent` (integer, relative to top category = 100), `fill` (CSS class string `fill-1` through `fill-6`, assigned by rank)

## Files to change

- `app.py` — rewrite the `/profile` view function body to:
  1. Guard: redirect to `/login` if `session.get("user_id")` is falsy
  2. Open DB connection via `get_db()`
  3. Query `users` for the logged-in user's `name`, `email`, `created_at`
  4. Query `expenses` for all rows belonging to `user_id`, ordered by `date DESC`
  5. Compute stats in Python from the query results (no extra SQL aggregation queries needed)
  6. Build `categories` list with percent and fill class
  7. Close DB connection
  8. Render `profile.html` with the assembled context

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Close the DB connection before returning from the view (use `db.close()`)
- Format currency in Python before passing to the template — do not format in Jinja
- Limit category fill classes to `fill-1` through `fill-6`; if there are more than 6 categories, reuse `fill-6` for the remainder
- `member_since` must be derived from the `created_at` column of the `users` table, not hardcoded
- Do not add any new columns or tables to support this feature

## Definition of done

- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in returns HTTP 200
- [ ] The displayed name and email match the logged-in user's actual DB record
- [ ] The member-since date is derived from `created_at`, not hardcoded
- [ ] Total spent reflects the real sum of that user's expenses
- [ ] Transaction count reflects the real number of that user's expense rows
- [ ] Top category reflects the category with the highest total spend in the DB
- [ ] The transaction history table shows the user's actual expense rows (not hardcoded)
- [ ] The category breakdown reflects real per-category totals from the DB
- [ ] A second registered user sees only their own data on `/profile`
