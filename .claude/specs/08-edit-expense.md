# Spec: Edit Expense

## Overview

This feature implements the `/expenses/<id>/edit` route so logged-in users can update an existing expense record directly from the profile page. The route stub currently returns a placeholder string; after this step it renders a pre-filled edit form (same fields as Add Expense) and processes the POST to update the `expenses` row. Each transaction row in the profile page gains an "Edit" action link that navigates to this route. The feature also enforces ownership — users may only edit their own expenses.

## Depends on

- Step 1: Database setup (`expenses` table with `id`, `user_id`, `amount`, `category`, `date`, `description`)
- Step 3: Login (`session["user_id"]` must be set)
- Step 5: Profile backend routes (`/profile` must work as redirect destination)
- Step 7: Add Expense (categories list and validation logic are the same)

## Routes

- `GET /expenses/<int:id>/edit` — render the pre-filled edit form for expense `id` — logged-in only
- `POST /expenses/<int:id>/edit` — validate submitted data, update the expense row, redirect to `/profile` — logged-in only

## Database changes

No database changes. The existing `expenses` table schema is sufficient.

## Templates

- **Create:** `templates/edit_expense.html` — edit form page extending `base.html`; identical fields to `add_expense.html` but pre-filled with existing values; form action posts to `POST /expenses/<id>/edit`
- **Modify:** `templates/profile.html` — add an "Edit" link in each transaction row; the transactions loop must also receive the expense `id` so the link can be generated with `url_for('edit_expense', id=tx.id)`

## Files to change

- `app.py`
  - Change the profile route SQL to also select `id` from `expenses`
  - Update `_get_transactions()` helper to include `id` in each returned dict
  - Replace the `GET`-only stub `edit_expense` view with a `GET`/`POST` view accepting `methods=["GET", "POST"]`:
    - Both methods: guard for login; fetch the expense by `id`; return 403 if it does not belong to `session["user_id"]`; return 404 if not found
    - `GET`: render `edit_expense.html` with the existing values pre-filled and the categories list
    - `POST`: read `amount`, `category`, `date`, `description` from `request.form`; apply the same validation rules as `add_expense`; on error re-render the form with the error and submitted values; on success run `UPDATE expenses SET ... WHERE id = ? AND user_id = ?` and redirect to `/profile`

- `templates/profile.html`
  - Add an "Actions" column header to the `<thead>` of the expense table
  - Add a table cell in each `{% for tx in transactions %}` row containing `<a href="{{ url_for('edit_expense', id=tx.id) }}" class="btn-ghost btn-sm">Edit</a>`

## Files to create

- `templates/edit_expense.html` — edit form page with:
  - Page title "Edit Expense"
  - Inline error message block (only shown when `error` is set)
  - Amount input: `type="number"`, `step="0.01"`, `min="0.01"`, `name="amount"`, pre-filled with `{{ amount }}`
  - Category select: `name="category"`, options: Food, Transport, Bills, Health, Entertainment, Shopping, Other; selected option matches `{{ category }}`
  - Date input: `type="date"`, `name="date"`, pre-filled with `{{ date }}`
  - Description input: `type="text"`, `name="description"`, pre-filled with `{{ description }}`
  - Submit button labelled "Save Changes"
  - Cancel link back to `/profile`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Ownership must be verified on both GET and POST: fetch the expense with `WHERE id = ? AND user_id = ?`; abort with 403 if no row is returned
- Allowed categories are the same list as in `add_expense`; validate server-side on POST
- Amount must be cast to `float` inside a `try/except`; reject non-numeric or non-positive values
- Date must be validated with `datetime.strptime(value, "%Y-%m-%d")` inside a `try/except`
- On validation failure, re-render `edit_expense.html` with the error and the user's submitted values
- The `UPDATE` query must include `WHERE id = ? AND user_id = ?` — never update by id alone
- `user_id` for the ownership check must come from `session["user_id"]`, never from the form

## Definition of done

- [ ] Visiting `/expenses/<id>/edit` without being logged in redirects to `/login`
- [ ] Visiting `GET /expenses/<id>/edit` for an expense owned by another user returns 403
- [ ] Visiting `GET /expenses/<id>/edit` for a non-existent id returns 404
- [ ] Visiting `GET /expenses/<id>/edit` while logged in and owning the expense returns HTTP 200 with all fields pre-filled
- [ ] Submitting a valid POST updates the expense row in the database
- [ ] After a successful update the user is redirected to `/profile`
- [ ] The updated values are visible in the transaction list on the profile page immediately
- [ ] Submitting with a missing or non-numeric amount shows an inline error and does not update
- [ ] Submitting with an invalid category shows an inline error and does not update
- [ ] Submitting with a malformed date shows an inline error and does not update
- [ ] On a validation error the form retains the user's submitted values
- [ ] A POST to `/expenses/<id>/edit` with another user's expense id returns 403 and does not update
- [ ] Each row in the profile transaction table has an "Edit" link pointing to the correct expense id

---

## Implementation Plan

### 1. `app.py` — three targeted changes

**A. `_get_transactions()` helper** — add `"id"` to the returned dict:
```python
{"id": row["id"], "date": ..., "description": ..., "category": ..., "amount": ...}
```

**B. Profile route SQL** — add `id` to all four SELECT variants:
```sql
SELECT id, amount, category, date, description FROM expenses WHERE user_id = ? ...
```

**C. `edit_expense` view** — replace stub with GET/POST handler:
- Guard login → redirect to `/login`
- Fetch by id only first → `abort(404)` if missing
- Check `expense["user_id"] == session["user_id"]` → `abort(403)` if not owner
- GET: render `edit_expense.html` with existing values pre-filled
- POST: same validation as `add_expense` (amount float > 0, category in list, date strptime); on error re-render with submitted values; on success `UPDATE ... WHERE id=? AND user_id=?` → redirect to `/profile`

### 2. `templates/profile.html` — two targeted changes

- Add `<th>Actions</th>` to the `<thead>` row
- Add `<td><a href="{{ url_for('edit_expense', id=tx.id) }}" class="btn-ghost" style="padding:0.35rem 0.85rem;font-size:0.82rem;">Edit</a></td>` inside each `{% for tx %}` row

### 3. `templates/edit_expense.html` — new file

Copy structure of `add_expense.html` with:
- Title: "Edit Expense" / subtitle: "Update your transaction"
- Form action: `/expenses/{{ expense_id }}/edit`
- All inputs pre-filled from template variables
- Submit label: "Save Changes"

### Key decisions

| Decision | Reason |
|---|---|
| Two-step ownership check (404 then 403) | Satisfies both DoD checklist items separately |
| `WHERE id=? AND user_id=?` on UPDATE | Double-fence so even a bypass of the GET check can't update another user's row |
| Inline style for small Edit button | `.btn-sm` doesn't exist in the stylesheet; avoids adding new CSS |
