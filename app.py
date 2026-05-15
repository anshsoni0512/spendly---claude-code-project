from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db
from collections import defaultdict
from datetime import datetime, date
import calendar
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sonico-dev-secret")


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


with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return render_template(
                "register.html",
                error="All fields are required.",
                name=name,
                email=email,
            )

        if len(password) < 8:
            return render_template(
                "register.html",
                error="Password must be at least 8 characters.",
                name=name,
                email=email,
            )

        db = get_db()
        existing = db.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            db.close()
            return render_template(
                "register.html",
                error="An account with that email already exists.",
                name=name,
                email=email,
            )

        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        db.commit()
        db.close()
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template(
                "login.html", error="Invalid email or password.", email=email
            )

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        db.close()

        if not user or not check_password_hash(user["password_hash"], password):
            return render_template(
                "login.html", error="Invalid email or password.", email=email
            )

        session["user_id"] = user["id"]
        return redirect(url_for("profile"))

    return render_template("login.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


# ------------------------------------------------------------------ #
# Profile helpers                                                      #
# ------------------------------------------------------------------ #


def _get_transactions(raw_rows):
    return [
        {
            "id": row["id"],
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": f"${row['amount']:,.2f}",
        }
        for row in raw_rows
    ]


def _get_stats(raw_rows):
    total = sum(row["amount"] for row in raw_rows)
    cat_totals = defaultdict(float)
    for row in raw_rows:
        cat_totals[row["category"]] += row["amount"]
    top = max(cat_totals, key=cat_totals.get) if cat_totals else "N/A"
    return {
        "total_spent": f"${total:,.0f}",
        "transactions": len(raw_rows),
        "top_category": top,
    }


def _get_categories(raw_rows):
    totals = defaultdict(float)
    for row in raw_rows:
        totals[row["category"]] += row["amount"]

    if not totals:
        return []

    sorted_cats = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    max_total = sorted_cats[0][1]

    result = []
    for rank, (name, cat_total) in enumerate(sorted_cats, start=1):
        result.append(
            {
                "name": name,
                "amount": f"${cat_total:,.0f}",
                "percent": int(cat_total / max_total * 100),
                "fill": f"fill-{min(rank, 6)}",
            }
        )
    return result


def _parse_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        return ""


def _months_ago(n):
    today = date.today()
    month = today.month - n
    year = today.year
    while month <= 0:
        month += 12
        year -= 1
    day = min(today.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).strftime("%Y-%m-%d")


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    month_str = request.args.get("month", "").strip()
    active_month = ""

    if month_str and len(month_str) == 7:
        try:
            year_m, month_m = int(month_str[:4]), int(month_str[5:7])
            _, last_day = calendar.monthrange(year_m, month_m)
            date_from = f"{year_m}-{month_m:02d}-01"
            date_to = f"{year_m}-{month_m:02d}-{last_day:02d}"
            active_month = month_str
        except (ValueError, IndexError):
            date_from = _parse_date(request.args.get("from", "").strip())
            date_to = _parse_date(request.args.get("to", "").strip())
    else:
        date_from = _parse_date(request.args.get("from", "").strip())
        date_to = _parse_date(request.args.get("to", "").strip())

    db = get_db()

    user_row = db.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if date_from and date_to:
        sql = "SELECT id, amount, category, date, description FROM expenses WHERE user_id = ? AND date BETWEEN ? AND ? ORDER BY date DESC"
        params = (user_id, date_from, date_to)
    elif date_from:
        sql = "SELECT id, amount, category, date, description FROM expenses WHERE user_id = ? AND date >= ? ORDER BY date DESC"
        params = (user_id, date_from)
    elif date_to:
        sql = "SELECT id, amount, category, date, description FROM expenses WHERE user_id = ? AND date <= ? ORDER BY date DESC"
        params = (user_id, date_to)
    else:
        sql = "SELECT id, amount, category, date, description FROM expenses WHERE user_id = ? ORDER BY date DESC"
        params = (user_id,)

    raw_rows = db.execute(sql, params).fetchall()

    # ── Month management ──────────────────────────────────────────────
    # Auto-sync: ensure every month that has expenses exists in the months table
    expense_months = db.execute(
        "SELECT DISTINCT substr(date, 1, 7) AS ym FROM expenses WHERE user_id = ? ORDER BY ym",
        (user_id,),
    ).fetchall()
    for row in expense_months:
        db.execute(
            "INSERT OR IGNORE INTO months (user_id, year_month) VALUES (?, ?)",
            (user_id, row["ym"]),
        )
    db.commit()

    month_rows = db.execute(
        "SELECT year_month FROM months WHERE user_id = ? ORDER BY year_month ASC",
        (user_id,),
    ).fetchall()
    db.close()

    today_d = date.today()
    available_months = []
    for row in month_rows:
        ym = row["year_month"]
        y, m = int(ym[:4]), int(ym[5:7])
        label = (
            calendar.month_abbr[m]
            if y == today_d.year
            else f"{calendar.month_abbr[m]} '{str(y)[2:]}"
        )
        available_months.append({"key": ym, "label": label})

    # Figure out what the next addable month is
    if month_rows:
        latest = month_rows[-1]["year_month"]
        ly, lm = int(latest[:4]), int(latest[5:7])
        nm, ny = (lm % 12) + 1, ly + (1 if lm == 12 else 0)
    else:
        nm, ny = today_d.month, today_d.year
    next_month_key = f"{ny}-{nm:02d}"
    next_month_label = (
        calendar.month_abbr[nm]
        if ny == today_d.year
        else f"{calendar.month_abbr[nm]} '{str(ny)[2:]}"
    )

    member_since = datetime.strptime(user_row["created_at"][:10], "%Y-%m-%d").strftime(
        "%B %Y"
    )
    user = {
        "name": user_row["name"],
        "email": user_row["email"],
        "member_since": member_since,
    }
    transactions = _get_transactions(raw_rows)
    stats = _get_stats(raw_rows)
    categories = _get_categories(raw_rows)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        date_from=date_from,
        date_to=date_to,
        active_month=active_month,
        available_months=available_months,
        next_month_key=next_month_key,
        next_month_label=next_month_label,
    )


@app.route("/months/add", methods=["POST"])
def add_month():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    year_month = request.form.get("year_month", "").strip()
    try:
        y, m = int(year_month[:4]), int(year_month[5:7])
        if not (len(year_month) == 7 and year_month[4] == "-" and 1 <= m <= 12):
            raise ValueError
    except (ValueError, IndexError):
        return redirect(url_for("profile"))

    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO months (user_id, year_month) VALUES (?, ?)",
        (session["user_id"], year_month),
    )
    db.commit()
    db.close()
    return redirect(url_for("profile") + f"?month={year_month}")


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    categories = [
        "Dining",
        "Grocery",
        "Transport",
        "Bills",
        "Health",
        "Entertainment",
        "Shopping",
        "Other",
    ]

    if request.method == "POST":
        amount_raw = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        date_val = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError
        except ValueError:
            return render_template(
                "add_expense.html",
                categories=categories,
                error="Amount must be a positive number.",
                amount=amount_raw,
                category=category,
                date=date_val,
                description=description,
            )

        if category not in categories:
            return render_template(
                "add_expense.html",
                categories=categories,
                error="Please select a valid category.",
                amount=amount_raw,
                category=category,
                date=date_val,
                description=description,
            )

        if not _parse_date(date_val):
            return render_template(
                "add_expense.html",
                categories=categories,
                error="Please enter a valid date.",
                amount=amount_raw,
                category=category,
                date=date_val,
                description=description,
            )

        db = get_db()
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], amount, category, date_val, description),
        )
        db.commit()
        db.close()
        return redirect(url_for("profile"))

    prefill_date = _parse_date(request.args.get("date", ""))
    if not prefill_date:
        prefill_date = date.today().strftime("%Y-%m-%d")
    return render_template(
        "add_expense.html",
        categories=categories,
        date=prefill_date,
    )


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    categories = [
        "Dining",
        "Grocery",
        "Transport",
        "Bills",
        "Health",
        "Entertainment",
        "Shopping",
        "Other",
    ]
    db = get_db()

    expense = db.execute("SELECT * FROM expenses WHERE id = ?", (id,)).fetchone()
    if expense is None:
        db.close()
        return "Not found", 404
    if expense["user_id"] != session["user_id"]:
        db.close()
        return "Forbidden", 403

    if request.method == "POST":
        amount_raw = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        date_val = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError
        except ValueError:
            db.close()
            return render_template(
                "edit_expense.html",
                categories=categories,
                expense_id=id,
                error="Amount must be a positive number.",
                amount=amount_raw,
                category=category,
                date=date_val,
                description=description,
            )

        if category not in categories:
            db.close()
            return render_template(
                "edit_expense.html",
                categories=categories,
                expense_id=id,
                error="Please select a valid category.",
                amount=amount_raw,
                category=category,
                date=date_val,
                description=description,
            )

        if not _parse_date(date_val):
            db.close()
            return render_template(
                "edit_expense.html",
                categories=categories,
                expense_id=id,
                error="Please enter a valid date.",
                amount=amount_raw,
                category=category,
                date=date_val,
                description=description,
            )

        db.execute(
            "UPDATE expenses SET amount=?, category=?, date=?, description=? WHERE id=? AND user_id=?",
            (amount, category, date_val, description, id, session["user_id"]),
        )
        db.commit()
        db.close()
        return redirect(url_for("profile"))

    db.close()
    return render_template(
        "edit_expense.html",
        categories=categories,
        expense_id=id,
        amount=expense["amount"],
        category=expense["category"],
        date=expense["date"],
        description=expense["description"] or "",
    )


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    expense = db.execute(
        "SELECT id, user_id FROM expenses WHERE id = ?", (id,)
    ).fetchone()

    if expense is None:
        db.close()
        return "Not found", 404
    if expense["user_id"] != session["user_id"]:
        db.close()
        return "Forbidden", 403

    db.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    )
    db.commit()
    db.close()
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
