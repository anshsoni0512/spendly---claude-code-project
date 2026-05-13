from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db
from collections import defaultdict
from datetime import datetime, date
import calendar

app = Flask(__name__)
app.secret_key = "spendly-dev-secret"


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


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

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
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": f"₹{row['amount']:,.2f}"
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
        "total_spent": f"₹{total:,.0f}",
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
        result.append({
            "name": name,
            "amount": f"₹{cat_total:,.0f}",
            "percent": int(cat_total / max_total * 100),
            "fill": f"fill-{min(rank, 6)}",
        })
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
    year  = today.year
    while month <= 0:
        month += 12
        year  -= 1
    day = min(today.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).strftime("%Y-%m-%d")


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    date_from = _parse_date(request.args.get("from", "").strip())
    date_to   = _parse_date(request.args.get("to", "").strip())

    db = get_db()

    user_row = db.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()

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
    db.close()

    member_since = datetime.strptime(user_row["created_at"][:10], "%Y-%m-%d").strftime("%B %Y")
    user = {"name": user_row["name"], "email": user_row["email"], "member_since": member_since}
    transactions = _get_transactions(raw_rows)
    stats        = _get_stats(raw_rows)
    categories   = _get_categories(raw_rows)

    today_str = date.today().strftime("%Y-%m-%d")
    quick_filters = {
        "1m": _months_ago(1),
        "3m": _months_ago(3),
        "6m": _months_ago(6),
        "today": today_str,
    }

    return render_template("profile.html",
                           user=user, stats=stats,
                           transactions=transactions, categories=categories,
                           date_from=date_from, date_to=date_to,
                           quick_filters=quick_filters)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
