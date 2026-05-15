# Spec: Delete Expense

## Overview

This feature implements the `/expenses/<id>/delete` route so logged-in users can permanently remove an expense record from the profile page. The route stub currently returns a placeholder string; after this step it performs an ownership check, deletes the row from the `expenses` table, and redirects back to `/profile`. Each transaction row in the profile page gains a "Delete" button next to the existing "Edit" link in the Actions column. The delete action uses a small inline form with a POST request so it cannot be triggered by a stray GET (e.g. prefetch, link preview).

## Depends on

- Step 1: Database setup (`expenses` table must exist)
- Step 3: Login (`session["user_id"]` must be set)
- Step 5: Profile backend routes (`/profile` must work as redirect destination)
- Step 8: Edit Expense (Actions column and `tx.id` already present in `profile.html`)

## Routes

- `POST /expenses/<int:id>/delete` — verify ownership, delete the expense row, redirect to `/profile` — logged-in only

## Database changes

No database changes. The existing `expenses` table schema is sufficient.

## Templates

- **Create:** none
- **Modify:** `templates/profile.html` — add a "Delete" button inside the existing `<td>` Actions cell for each transaction row; the button must be inside a `<form method="POST">` that posts to `url_for('delete_expense', id=tx.id)`

## Files to change

- `app.py`
  - Replace the GET stub `delete_expense` view with a POST-only handler accepting `methods=["POST"]`:
    - Guard for login → redirect to `/login`
    - Fetch the expense by id: `SELECT id, user_id FROM expenses WHERE id = ?`
    - If not found → return 404
    - If `expense["user_id"] != session["user_id"]` → return 403
    - Execute `DELETE FROM expenses WHERE id = ? AND user_id = ?`
    - Commit and close the connection
    - Redirect to `/profile`

- `templates/profile.html`
  - Inside the `<td>` for the Actions column, add a `<form>` that posts to `url_for('delete_expense', id=tx.id)` with a submit button labelled "Delete"
  - The Edit link and Delete form should sit side-by-side in the same `<td>`

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- The route must only accept POST — change `methods` from the implicit GET to `["POST"]`
- Ownership must be verified before deletion: fetch the row first, check `user_id`, then delete with `WHERE id = ? AND user_id = ?` as a double-fence
- The `DELETE` query must include `WHERE id = ? AND user_id = ?` — never delete by id alone
- `user_id` for the ownership check must come from `session["user_id"]`, never from the form
- The delete form in the template must use `method="POST"` — no JavaScript required
- Style the Delete button consistently with the existing Edit link (similar size, use `btn-ghost` or a danger variant using CSS variables)

## Definition of done

- [ ] Sending a POST to `/expenses/<id>/delete` without being logged in redirects to `/login`
- [ ] Sending a POST to `/expenses/<id>/delete` for a non-existent id returns 404
- [ ] Sending a POST to `/expenses/<id>/delete` for an expense owned by another user returns 403 and does not delete the row
- [ ] Sending a valid POST deletes the expense row from the database
- [ ] After a successful delete the user is redirected to `/profile`
- [ ] The deleted expense no longer appears in the transaction list on the profile page
- [ ] Each transaction row in the profile page has a "Delete" button that posts to the correct expense id
- [ ] The stats (total spent, transaction count, top category) update correctly after deletion
- [ ] A GET request to `/expenses/<id>/delete` returns 405 Method Not Allowed
