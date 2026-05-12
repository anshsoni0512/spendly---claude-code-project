# Spec: Login

## Overview

Implement the login and logout flow so registered users can authenticate into Spendly. The `/login` route currently only handles GET. This step adds POST handling: validates credentials, verifies the password hash, stores the user id in a Flask session, and redirects to the landing page on success. The `/logout` stub is also implemented here — it clears the session and redirects to landing. The navbar in `base.html` is updated to show context-aware links (Sign in / Get started when logged out; user name + Logout when logged in).

## Depends on

- Step 01 — Database Setup (`users` table, `get_db()`)
- Step 02 — Registration (users exist in the database with hashed passwords)

## Routes

- `GET /login` — render the login form — public (already exists, no change needed)
- `POST /login` — verify credentials, set session, redirect to landing — public
- `GET /logout` — clear session, redirect to landing — any (safe to call even if not logged in)

## Database changes

No database changes. Reads from the existing `users` table only.

## Templates

- **Modify:** `templates/login.html` — add `value="{{ email | default('') }}"` to the email input to preserve it on failed login
- **Modify:** `templates/base.html` — update the `nav-links` block to show different links based on whether `session.user_id` is set:
  - Logged out: "Sign in" link + "Get started" CTA (current behaviour)
  - Logged in: user's name (non-clickable or links to `/profile`) + "Logout" link

## Files to change

- `app.py` — set `app.secret_key`; add `session`, `check_password_hash` to imports; add POST handler to `/login`; implement `/logout`
- `templates/login.html` — add `value` attribute to email input
- `templates/base.html` — conditional navbar links

## Files to create

None.

## New dependencies

No new dependencies. Flask session and `werkzeug.security.check_password_hash` are already available.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders, never f-strings in SQL)
- Passwords verified with `werkzeug.security.check_password_hash` — never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `app.secret_key` must be set before any session use — use a fixed dev string (e.g. `"spendly-dev-secret"`) for now; note it must be changed for production
- Login error message must be generic: `"Invalid email or password."` — never reveal which field is wrong
- Validation order: (1) both fields present, (2) user exists, (3) password matches
- Steps 2 and 3 must share the same generic error to prevent user enumeration
- `session['user_id']` stores the integer user id; no other user data goes in the session
- Logout uses `session.clear()`, not `session.pop()`
- After login: redirect to `url_for('landing')` (dashboard comes in a later step)
- After logout: redirect to `url_for('landing')`

## Definition of done

- [ ] Submitting valid credentials sets a session and redirects to the landing page
- [ ] Submitting with any field empty shows "Invalid email or password." and preserves the email value
- [ ] Submitting an unregistered email shows the same generic error
- [ ] Submitting the correct email but wrong password shows the same generic error
- [ ] After login, the navbar shows the user's name and a "Logout" link instead of "Sign in" / "Get started"
- [ ] Visiting `/logout` clears the session and redirects to landing; navbar reverts to logged-out state
- [ ] App starts without errors after the change

---

## Implementation Plan

### Files to change

| File | What changes |
|---|---|
| `app.py` | Imports, secret key, context processor, `/login` POST handler, `/logout` implementation |
| `templates/login.html` | Add `value` attribute to email input |
| `templates/base.html` | Conditional navbar based on `current_user` |

---

### Step 1 — Update imports in `app.py`

```python
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
```

---

### Step 2 — Set secret key in `app.py`

Add immediately after `app = Flask(__name__)`:

```python
app.secret_key = "spendly-dev-secret"
```

Flask requires this to sign session cookies. Without it, any `session` write raises a `RuntimeError`.

---

### Step 3 — Add context processor in `app.py`

Add after `app.secret_key`, before the routes. Makes `current_user` available in every template automatically — no route needs to pass it manually:

```python
@app.context_processor
def inject_user():
    user = None
    if session.get("user_id"):
        db = get_db()
        user = db.execute(
            "SELECT id, name FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
        db.close()
    return {"current_user": user}
```

Why a context processor over `before_request` + `g`: context processors only run when a template is rendered, not on redirects — correct for a template-only app.

---

### Step 4 — Replace `/login` route in `app.py`

```python
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("login.html",
                                   error="Invalid email or password.",
                                   email=email)

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        db.close()

        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("login.html",
                                   error="Invalid email or password.",
                                   email=email)

        session["user_id"] = user["id"]
        return redirect(url_for("landing"))

    return render_template("login.html")
```

Key decisions:
- Same error for missing fields, wrong email, and wrong password — prevents user enumeration
- `db.close()` called before the password check so the connection is not held open during hashing
- Email preserved on error; password never echoed back

---

### Step 5 — Replace `/logout` stub in `app.py`

```python
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))
```

---

### Step 6 — Update `templates/login.html`

Add `value="{{ email | default('') }}"` to the email input:

```html
<input type="email" id="email" name="email"
       class="form-input" placeholder="nitish@example.com"
       value="{{ email | default('') }}"
       required autofocus>
```

---

### Step 7 — Update `templates/base.html`

Replace the static `nav-links` div with a conditional block:

```html
<div class="nav-links">
    {% if current_user %}
        <span class="nav-user">{{ current_user["name"] }}</span>
        <a href="{{ url_for('logout') }}" class="nav-cta">Logout</a>
    {% else %}
        <a href="{{ url_for('login') }}">Sign in</a>
        <a href="{{ url_for('register') }}" class="nav-cta">Get started</a>
    {% endif %}
</div>
```

`current_user` is `None` when not logged in (injected by context processor), so the existing nav renders unchanged for logged-out users.

---

### Verification

1. `python app.py` — starts without errors.
2. Visit `http://localhost:5001/login`:
   - Empty submit → "Invalid email or password.", email field stays empty.
   - Unknown email → same generic error.
   - Correct email + wrong password → same generic error.
   - `demo@spendly.com` / `demo123` → redirected to landing, navbar shows "Demo User" + Logout.
3. Click Logout → session cleared, navbar reverts to "Sign in / Get started".
4. Register a new account → redirected to `/login` → log in with new credentials → works.
