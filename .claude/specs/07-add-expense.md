# Spec: Add Expense

## Overview

This feature implements the `/expenses/add` route so logged-in users can record new expenses. The route currently returns a stub string; after this step it renders a form with fields for amount, category, date, and description. On a valid POST the expense is inserted into the `expenses` table and the user is redirected to `/profile`. A prominent "Add Expense" button is added to the profile page header so users can reach the form without manually typing the URL.

## Depends on

- Step 1: Database setup (`expenses` table must exist with `user_id`, `amount`, `category`, `date`, `description` columns)
- Step 3: Login (session["user_id"] must be set)
- Step 5: Profile backend routes (redirect destination `/profile` must work)

## Routes

- `GET /expenses/add` — render the add-expense form — logged-in only (redirect to /login if not authenticated)
- `POST /expenses/add` — validate form data, insert into `expenses`, redirect to `/profile` — logged-in only

## Database changes

No database changes. The existing `expenses` table schema is sufficient:

```
expenses(id, user_id, amount, category, date, description, created_at)
```

## Templates

- **Create:** `templates/add_expense.html` — standalone form page extending `base.html`; fields: amount (number), category (select), date (date), description (text); shows validation error inline on bad input
- **Modify:** `templates/profile.html` — add an "Add Expense" button/link in the profile header next to the existing Analytics button

## Files to change

- `app.py`
  - Replace the `GET`-only stub `add_expense` view with a `GET`/`POST` view:
    - `GET`: guard for login, render `add_expense.html` with today's date pre-filled and the categories list
    - `POST`: read `amount`, `category`, `date`, `description` from `request.form`; validate (amount must be a positive number, category must be from the allowed list, date must be a valid `YYYY-MM-DD`); on error re-render the form with the error and the user's input; on success insert the row and redirect to `/profile`
- `templates/profile.html`
  - Add `<a href="{{ url_for('add_expense') }}" class="btn-primary">+ Add Expense</a>` in the `.profile-header` div, alongside the existing Analytics button

## Files to create

- `templates/add_expense.html` — form page with:
  - Page title "Add Expense"
  - Inline error message block (only shown when `error` is set)
  - Amount input: `type="number"`, `step="0.01"`, `min="0.01"`, `name="amount"`
  - Category select: `name="category"`, options: Food, Transport, Bills, Health, Entertainment, Shopping, Other
  - Date input: `type="date"`, `name="date"`, pre-filled with today's date
  - Description input: `type="text"`, `name="description"` (optional)
  - Submit button labelled "Save Expense"
  - Cancel link back to `/profile`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Allowed categories are defined as a Python list in the route; validate the submitted category against this list server-side
- Amount must be cast to `float` inside a `try/except`; reject non-numeric or non-positive values
- Date must be validated with `datetime.strptime(value, "%Y-%m-%d")` inside a `try/except`
- On validation failure, re-render `add_expense.html` with the error message and the submitted values so the user does not have to retype everything
- Redirect to `/profile` (not `/`) on successful insert
- The `user_id` for the insert must come from `session["user_id"]`, never from the form

## Definition of done

- [ ] Visiting `/expenses/add` without being logged in redirects to `/login`
- [ ] Visiting `GET /expenses/add` while logged in returns HTTP 200 and shows the form
- [ ] The date field is pre-filled with today's date on the initial `GET`
- [ ] Submitting a valid form inserts one row into `expenses` for the logged-in user
- [ ] After a successful insert the user is redirected to `/profile`
- [ ] The new expense appears in the transaction list on the profile page immediately
- [ ] Submitting with a missing or non-numeric amount shows an inline error and does not insert
- [ ] Submitting with an invalid category (e.g. via URL tampering) shows an inline error and does not insert
- [ ] Submitting with a malformed date shows an inline error and does not insert
- [ ] On a validation error the form retains the user's previously entered values
- [ ] The profile page header has an "Add Expense" button that navigates to `/expenses/add`
- [ ] A second logged-in user's expense is never attributed to another user
