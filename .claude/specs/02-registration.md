# Spec: Registration

## Overview

Implement the user registration flow so new visitors can create a Spendly account. The `/register` route currently only handles GET (renders the form). This step adds POST handling: validates the submitted fields, checks for duplicate emails, hashes the password, inserts the new user row, and redirects to `/login` on success. Error messages are surfaced back into the same form via the `error` variable already wired in `register.html`.

## Depends on

Step 01 — Database Setup (users table must exist; `get_db()` must be implemented).

## Routes

- `GET /register` — render the empty registration form — public (already exists, no change needed)
- `POST /register` — process form submission, create user, redirect to login — public

## Database changes

No new tables or columns. Uses the existing `users` table:
- `name TEXT NOT NULL`
- `email TEXT UNIQUE NOT NULL`
- `password_hash TEXT NOT NULL`

## Templates

- **Modify:** `templates/register.html` — add `value="{{ name }}"` and `value="{{ email }}"` attributes to the name and email inputs so values are preserved when validation fails and the form is re-rendered.

## Files to change

- `app.py` — add `POST` method to the `/register` route; add imports for `request`, `redirect`, `url_for`; add registration logic

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders, never f-strings in SQL)
- Passwords hashed with `werkzeug.security.generate_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Do not start a session or set any cookie — session management is Step 3
- Validation order: (1) all fields present, (2) password ≥ 8 characters, (3) email not already registered
- On duplicate email the error message must not reveal whether the account exists (use "An account with that email already exists.")
- On success redirect to `url_for('login')` — do not render a new template

## Definition of done

- [ ] Submitting the form with all valid fields creates a new row in `users` with a hashed password and redirects to `/login`
- [ ] Submitting with any field empty re-renders the form with an error message and preserves entered values
- [ ] Submitting with a password shorter than 8 characters shows a validation error
- [ ] Submitting with an already-registered email shows an error without crashing
- [ ] Password is stored as a hash, never plaintext (verifiable via SQLite browser or `sqlite3` CLI)
- [ ] App starts without errors after the change

---

## Implementation Plan

### Files to change

| File | What changes |
|---|---|
| `app.py` | Add POST handler to `/register`; add imports |
| `templates/register.html` | Add `value=` attributes to name + email inputs |

### Step 1 — Update imports in `app.py`

```python
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash
```

### Step 2 — Replace the `/register` route in `app.py`

```python
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return render_template("register.html",
                                   error="All fields are required.",
                                   name=name, email=email)

        if len(password) < 8:
            return render_template("register.html",
                                   error="Password must be at least 8 characters.",
                                   name=name, email=email)

        db = get_db()
        existing = db.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            db.close()
            return render_template("register.html",
                                   error="An account with that email already exists.",
                                   name=name, email=email)

        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        db.commit()
        db.close()
        return redirect(url_for("login"))

    return render_template("register.html")
```

Key decisions:
- `.strip()` / `.lower()` normalises input before DB write
- `get_db()` called only after basic validation passes
- Password never echoed back on error
- No session set — that is Step 3

### Step 3 — Update `templates/register.html`

Add `value` attributes with `| default('')` filter to preserve input on error:

```html
<input type="text" id="name" name="name"
       class="form-input" placeholder="Nitish Kumar"
       value="{{ name | default('') }}"
       required autofocus>

<input type="email" id="email" name="email"
       class="form-input" placeholder="nitish@example.com"
       value="{{ email | default('') }}"
       required>
```

### Verification

1. `python app.py` — app starts without errors.
2. Visit `http://localhost:5001/register`:
   - Empty submit → "All fields are required."
   - Password `abc` (7 chars) → "Password must be at least 8 characters.", name/email preserved.
   - Email `demo@spendly.com` → "An account with that email already exists."
   - Valid new user → redirected to `/login`.
3. Check DB: `sqlite3 expense_tracker.db "SELECT id, name, email, password_hash FROM users;"` — new row with `pbkdf2:sha256:...` hash.
