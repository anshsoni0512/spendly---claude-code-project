# Spec Document

## 1. Overview

Replace the stub in `database/db.py` with a working SQLite implementation.

This step establishes the **data layer foundation** for the Spendly application.

All future features (authentication, profile, expense tracking) depend on this being correctly implemented.

---

## 2. Depends on

Nothing — this is the first step.

---

## 3. Routes

- No new routes
- Existing placeholder routes in `app.py` remain unchanged

---

## 4. Database Schema

---

### A. users

| Column        | Type    | Constraints                |
| ------------- | ------- | -------------------------- |
| id            | INTEGER | Primary key, autoincrement |
| name          | TEXT    | Not null                   |
| email         | TEXT    | Unique, not null           |
| password_hash | TEXT    | Not null                   |
| created_at    | TEXT    | Default datetime('now')    |

---

### B. expenses

| Column      | Type    | Constraints                      |
| ----------- | ------- | -------------------------------- |
| id          | INTEGER | Primary key, autoincrement       |
| user_id     | INTEGER | Foreign key → users.id, not null |
| amount      | REAL    | Not null                         |
| category    | TEXT    | Not null                         |
| date        | TEXT    | Not null (YYYY-MM-DD format)     |
| description | TEXT    | Nullable                         |
| created_at  | TEXT    | Default datetime('now')          |

---

## 5. Functions to Implement (`database/db.py`)

---

### A. `get_db()`

- Opens connection to `spendly.db` (or `expense_tracker.db`) in project root
- Sets:
  - `row_factory = sqlite3.Row`
  - `PRAGMA foreign_keys = ON`
- Returns the connection

---

### B. `init_db()`

- Creates both tables using `CREATE TABLE IF NOT EXISTS`
- Safe to call multiple times
- Ensures schema is ready before app usage

---

### C. `seed_db()`

- Checks if `users` table already contains data
  - If yes → return early (no duplication)
- Inserts one demo user:
  - name: Demo User
  - email: [demo@spendly.com](mailto:demo@spendly.com)
  - password: demo123 (hashed using `werkzeug`)
- Inserts **8 sample expenses**:
  - All linked to demo user
  - Cover multiple categories
  - Dates spread across current month
  - At least one expense per category

---

## 6. Changes to `app.py`

- Import:
  - `get_db`
  - `init_db`
  - `seed_db`
- Call `init_db()` and `seed_db()` inside `app.app_context()` on startup
- Ensure DB is ready before routes are used

---

## 7. Files to Change

- `database/db.py` → implement all functions
- `app.py` → add imports and startup calls

---

## 8. Files to Create

- None

---

## 9. Dependencies

- No new pip packages
- Use:
  - `sqlite3` (standard library)
  - `werkzeug.security` (already installed)

---

## 10. Categories (Fixed List)

Use exactly these values:

- Food
- Transport
- Bills
- Health
- Entertainment
- Shopping
- Other

---

## 11. Rules for Implementation

- No ORMs (no SQLAlchemy)
- Use **parameterized queries only**
- Never use string formatting in SQL
- Enable `PRAGMA foreign_keys = ON` on every connection
- Store `amount` as REAL (float), not INTEGER
- Hash passwords using:
  ```
  fromwerkzeug.securityimportgenerate_password_hash
  ```
- `seed_db()` must prevent duplicate inserts
- Dates must follow **YYYY-MM-DD format consistently**

---

## 12. Expected Behavior

- `get_db()` returns a working connection with:
  - dictionary-like row access
  - foreign key enforcement enabled
- `init_db()`:
  - creates tables safely
  - does not fail on repeated runs
- `seed_db()`:
  - inserts demo data only once
  - does not duplicate records on multiple runs
- Database enforces:
  - unique email constraint
  - valid foreign key relationships

---

## 13. Error Handling Expectations

- Inserting duplicate email → should fail (UNIQUE constraint)
- Inserting expense with invalid `user_id` → should fail (foreign key constraint)
- Invalid queries → should raise clear errors for debugging

---

## 14. Definition of Done

- [ ] Database file is created on app startup
- [ ] Both tables exist with correct schema and constraints
- [ ] Demo user exists with hashed password
- [ ] 8 sample expenses exist across categories
- [ ] No duplicate seed data on repeated runs
- [ ] App starts without errors
- [ ] Foreign key enforcement works
- [ ] All queries use parameterized SQL

---

## 15. Technical Implementation Plan

### Context

The Spendly app currently has no data layer. `database/db.py` is a stub with comments only, and `app.py` makes no database calls. All future features (auth, profile, expense tracking) depend on this foundation being in place. This plan implements the SQLite layer and wires it into the Flask startup sequence.

---

### Files Modified

| File | Change |
|---|---|
| `database/db.py` | Implement `get_db()`, `init_db()`, `seed_db()` |
| `app.py` | Import the three functions; call `init_db()` + `seed_db()` in app context |

---

### `database/db.py`

#### `get_db()`
- Open connection to `expense_tracker.db` in project root
- Set `conn.row_factory = sqlite3.Row`
- Execute `PRAGMA foreign_keys = ON`
- Return the connection

#### `init_db()`
- Call `get_db()` to get a connection
- Execute `CREATE TABLE IF NOT EXISTS users` with columns:
  - `id INTEGER PRIMARY KEY AUTOINCREMENT`
  - `name TEXT NOT NULL`
  - `email TEXT UNIQUE NOT NULL`
  - `password_hash TEXT NOT NULL`
  - `created_at TEXT DEFAULT (datetime('now'))`
- Execute `CREATE TABLE IF NOT EXISTS expenses` with columns:
  - `id INTEGER PRIMARY KEY AUTOINCREMENT`
  - `user_id INTEGER NOT NULL REFERENCES users(id)`
  - `amount REAL NOT NULL`
  - `category TEXT NOT NULL`
  - `date TEXT NOT NULL`
  - `description TEXT`
  - `created_at TEXT DEFAULT (datetime('now'))`
- Commit and close connection
- Safe to call multiple times (`IF NOT EXISTS` guards prevent failure)

#### `seed_db()`
- Call `get_db()`, check `SELECT COUNT(*) FROM users`
- If count > 0 → return early (prevents duplicate seeding)
- Insert demo user using parameterized query:
  - name: `Demo User`
  - email: `demo@spendly.com`
  - password: `demo123` hashed via `generate_password_hash` from `werkzeug.security`
- Fetch the new user's `lastrowid` as `user_id`
- Insert 8 sample expenses (all linked to demo user, amounts in ₹, dates in YYYY-MM-DD format):

| # | Category | Amount (₹) | Description |
|---|---|---|---|
| 1 | Food | 450.00 | Lunch at café |
| 2 | Transport | 180.00 | Ola cab to office |
| 3 | Bills | 1200.00 | Electricity bill |
| 4 | Health | 850.00 | Pharmacy - vitamins |
| 5 | Entertainment | 599.00 | Netflix subscription |
| 6 | Shopping | 2300.00 | New headphones |
| 7 | Other | 200.00 | Miscellaneous |
| 8 | Food | 320.00 | Grocery run |

- Commit and close connection

---

### `app.py` Changes

```python
from database.db import get_db, init_db, seed_db

app = Flask(__name__)

with app.app_context():
    init_db()
    seed_db()
```

---

### Key Constraints

- No ORMs — raw `sqlite3` only
- All SQL uses parameterized queries (`?` placeholders), never f-strings or `%` formatting
- `PRAGMA foreign_keys = ON` on every connection (inside `get_db()`)
- `amount` stored as `REAL` (float), not `INTEGER`
- Dates in `YYYY-MM-DD` format
- `seed_db()` is idempotent — checks row count before inserting

---

### Verification

1. Run `python app.py` — app should start without errors
2. Verify `expense_tracker.db` is created in the project root
3. Confirm in SQLite:
   - Both tables exist with correct columns and constraints
   - Demo user row exists with a hashed (non-plaintext) password
   - 8 expense rows exist, all with `user_id = 1`
4. Run `python app.py` a second time — no duplicate rows should appear
