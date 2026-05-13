# Spec: Date Filter for Profile Page

## Overview

This feature adds a date range filter to the profile page so users can narrow the transaction history and summary stats to a specific period. The `/profile` route currently returns all expenses for the logged-in user; after this step it will also accept optional `from` and `to` query parameters and apply a `WHERE date BETWEEN ? AND ?` clause before computing stats, transactions, and the category breakdown. The filter form lives at the top of the profile page and persists the user's chosen dates as pre-filled values on reload.

## Depends on

- Step 1: Database setup (expenses table with a `date` column must exist)
- Step 3: Login + Logout (session["user_id"] must be set)
- Step 5: Profile backend routes (the `/profile` view with real DB queries must be in place)

## Routes

No new routes. The existing `GET /profile` route is extended to read optional query parameters:

- `from` — ISO date string (`YYYY-MM-DD`); lower bound (inclusive)
- `to` — ISO date string (`YYYY-MM-DD`); upper bound (inclusive)

When neither parameter is provided, the route behaves exactly as before (all expenses returned).

## Database changes

No database changes. The existing `expenses.date` column (TEXT, stored as `YYYY-MM-DD`) supports `BETWEEN` comparisons.

## Templates

- **Modify:** `templates/profile.html`
  - Add a filter form above the summary stats section with two `<input type="date">` fields (`name="from"` and `name="to"`) and a "Filter" button that submits via `GET` to `/profile`
  - Pre-fill both date inputs from the current query parameters so the selected range is visible after filtering
  - Add a "Clear" link that navigates to `/profile` (no query params) to reset the filter
  - Show the active date range as a human-readable label (e.g. "Showing: 01 May 2026 – 13 May 2026") when a filter is active; hide the label when no filter is set

## Files to change

- `app.py`
  - In the `/profile` view: read `request.args.get("from")` and `request.args.get("to")`
  - Validate that both values are valid `YYYY-MM-DD` dates if provided; if either is malformed, ignore both and fall back to unfiltered results
  - Build the SQL query for expenses conditionally:
    - No filter: `WHERE user_id = ? ORDER BY date DESC`
    - Both bounds: `WHERE user_id = ? AND date BETWEEN ? AND ? ORDER BY date DESC`
    - Only `from`: `WHERE user_id = ? AND date >= ? ORDER BY date DESC`
    - Only `to`: `WHERE user_id = ? AND date <= ? ORDER BY date DESC`
  - Pass `date_from` and `date_to` (raw string values, or empty string when absent) into the `render_template` call so the template can pre-fill the form inputs
  - All stats (`_get_stats`, `_get_transactions`, `_get_categories`) are recomputed from the filtered rows — no changes to those helper functions needed

- `templates/profile.html` — see Templates section above

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
- Date validation in Python: use `datetime.strptime(value, "%Y-%m-%d")` inside a try/except; silently discard malformed input
- The filter form must use `method="get"` and `action="/profile"` so the filter state lives in the URL
- Do not use JavaScript to apply the filter — it must work with a plain form submit
- Do not add any new columns, tables, or indexes to the database

## Definition of done

- [ ] Visiting `/profile` with no query params still shows all expenses (unchanged behaviour)
- [ ] Submitting the filter form with a `from` date limits transactions to that date and later
- [ ] Submitting the filter form with a `to` date limits transactions to that date and earlier
- [ ] Submitting with both `from` and `to` shows only transactions within that range
- [ ] Summary stats (total spent, transaction count, top category) reflect only the filtered expenses
- [ ] Category breakdown reflects only the filtered expenses
- [ ] The date inputs are pre-filled with the currently active filter values after submit
- [ ] The active range label is visible when a filter is applied and hidden when it is not
- [ ] The "Clear" link resets the page to show all expenses
- [ ] Malformed date values in the URL are silently ignored and the full expense list is shown
- [ ] SQL is parameterised — no string interpolation in queries

---

## Technical Implementation Plan

### Step 1 — `app.py`: Extend the `/profile` route

After `user_id = session["user_id"]`, read and validate query params using a local helper:

```python
date_from_raw = request.args.get("from", "").strip()
date_to_raw   = request.args.get("to", "").strip()

def _parse_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        return ""

date_from = _parse_date(date_from_raw)
date_to   = _parse_date(date_to_raw)
```

Replace the static SQL query with a conditional one (all four branches):

```python
if date_from and date_to:
    sql    = "SELECT amount, category, date, description FROM expenses WHERE user_id = ? AND date BETWEEN ? AND ? ORDER BY date DESC"
    params = (user_id, date_from, date_to)
elif date_from:
    sql    = "SELECT amount, category, date, description FROM expenses WHERE user_id = ? AND date >= ? ORDER BY date DESC"
    params = (user_id, date_from)
elif date_to:
    sql    = "SELECT amount, category, date, description FROM expenses WHERE user_id = ? AND date <= ? ORDER BY date DESC"
    params = (user_id, date_to)
else:
    sql    = "SELECT amount, category, date, description FROM expenses WHERE user_id = ? ORDER BY date DESC"
    params = (user_id,)

raw_rows = db.execute(sql, params).fetchall()
```

Add `date_from` and `date_to` to the `render_template` call:

```python
return render_template("profile.html",
                       user=user, stats=stats,
                       transactions=transactions, categories=categories,
                       date_from=date_from, date_to=date_to)
```

No changes needed to `_get_transactions`, `_get_stats`, or `_get_categories`.

---

### Step 2 — `templates/profile.html`: Add filter form

Insert a new `.profile-card.filter-card` block **between** the profile header (`</div>` at line 20) and the summary stats (`<div class="profile-stats">` at line 23):

```html
<!-- Date filter -->
<div class="profile-card filter-card">
    <form class="filter-form" method="get" action="/profile">
        <div class="filter-fields">
            <div class="form-group">
                <label for="from">From</label>
                <input class="form-input" type="date" id="from" name="from"
                       value="{{ date_from }}">
            </div>
            <div class="form-group">
                <label for="to">To</label>
                <input class="form-input" type="date" id="to" name="to"
                       value="{{ date_to }}">
            </div>
        </div>
        <div class="filter-actions">
            <button type="submit" class="btn-filter">Filter</button>
            {% if date_from or date_to %}
            <a href="/profile" class="btn-ghost btn-filter-clear">Clear</a>
            {% endif %}
        </div>
    </form>
    {% if date_from or date_to %}
    <p class="filter-active-label">
        <i data-lucide="filter"></i>
        Showing:
        {% if date_from %}{{ date_from }}{% else %}start{% endif %}
        –
        {% if date_to %}{{ date_to }}{% else %}today{% endif %}
    </p>
    {% endif %}
</div>
```

Reuses existing `.form-group`, `.form-input`, and `.btn-ghost` classes. New classes are defined in Step 3.

---

### Step 3 — `static/css/style.css`: Filter form styles

Append at the bottom of the stylesheet. All values use existing CSS variables — no hex codes:

```css
/* ── Date filter ─────────────────────────────── */
.filter-card {
    padding: 1.25rem 2rem;
}

.filter-form {
    display: flex;
    align-items: flex-end;
    gap: 1rem;
    flex-wrap: wrap;
}

.filter-fields {
    display: flex;
    gap: 1rem;
    flex: 1;
    flex-wrap: wrap;
}

.filter-fields .form-group {
    margin-bottom: 0;
    min-width: 140px;
}

.filter-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}

.btn-filter {
    padding: 0.6rem 1.25rem;
    background: var(--ink);
    color: var(--paper);
    border: none;
    border-radius: var(--radius-sm);
    font-family: var(--font-body);
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
}

.btn-filter:hover {
    background: var(--accent);
}

.btn-filter-clear {
    padding: 0.55rem 1rem;
    font-size: 0.9rem;
    text-decoration: none;
}

.filter-active-label {
    margin-top: 0.75rem;
    margin-bottom: 0;
    font-size: 0.85rem;
    color: var(--ink-muted);
    display: flex;
    align-items: center;
    gap: 0.35rem;
}

.filter-active-label svg {
    width: 14px;
    height: 14px;
}
```

---

### Verification

Test these scenarios at `http://localhost:5001/profile`:

1. No params → all expenses shown, no filter label, no Clear link
2. `?from=2026-05-05` → only expenses on/after May 5; stats update
3. `?to=2026-05-05` → only expenses on/before May 5; stats update
4. `?from=2026-05-03&to=2026-05-09` → only expenses in that range; stats update
5. `?from=notadate&to=also-bad` → falls back to all expenses (malformed input ignored)
6. Click "Clear" → returns to unfiltered profile
7. Date inputs are pre-filled with the active filter values after each submit
