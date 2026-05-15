"""
Tests for Step 09 — Delete Expense
===================================
Feature: POST /expenses/<int:id>/delete deletes the authenticated user's expense
and redirects to /profile. The route enforces authentication and ownership so
that unauthenticated callers are redirected to /login, requests for non-existent
expenses return 404, and attempts to delete another user's expense return 403
without touching the database row.

All monetary assertions use $ (USD). No seed data is used; every test inserts
its own rows so the expected values are always deterministic.
"""

import pytest
from database.db import get_db
from werkzeug.security import generate_password_hash

# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #


def _insert_expense(db, user_id, amount, category, date, description):
    """Insert a single expense row and return its auto-assigned id."""
    cursor = db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    db.commit()
    return cursor.lastrowid


def _delete_post(client, expense_id):
    """POST to /expenses/<expense_id>/delete without following redirects."""
    return client.post(
        f"/expenses/{expense_id}/delete",
        follow_redirects=False,
    )


def _row_exists(db, expense_id):
    """Return True if a row with the given id still exists in expenses."""
    row = db.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    return row is not None


# ------------------------------------------------------------------ #
# Class: authentication guard                                         #
# ------------------------------------------------------------------ #


class TestDeleteExpenseAuthGuard:
    def test_unauthenticated_post_redirects_to_login(self, client, test_user, db):
        """POST without a session must redirect to /login."""
        expense_id = _insert_expense(
            db, test_user["id"], 500.00, "Food", "2026-05-01", "Lunch"
        )
        response = _delete_post(client, expense_id)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_post_does_not_delete_row(self, client, test_user, db):
        """An unauthenticated request must not remove the expense from the database."""
        expense_id = _insert_expense(
            db, test_user["id"], 500.00, "Food", "2026-05-01", "Lunch"
        )
        _delete_post(client, expense_id)
        assert _row_exists(db, expense_id)

    def test_unauthenticated_get_returns_405(self, client, test_user, db):
        """GET to the delete URL must return 405 Method Not Allowed."""
        expense_id = _insert_expense(
            db, test_user["id"], 300.00, "Transport", "2026-05-02", "Cab"
        )
        response = client.get(f"/expenses/{expense_id}/delete", follow_redirects=False)
        assert response.status_code == 405


# ------------------------------------------------------------------ #
# Class: HTTP method guard                                            #
# ------------------------------------------------------------------ #


class TestDeleteExpenseMethodGuard:
    def test_get_request_returns_405(self, auth_client, test_user, db):
        """GET to /expenses/<id>/delete from an authenticated session must return 405."""
        expense_id = _insert_expense(
            db, test_user["id"], 200.00, "Bills", "2026-05-03", "Electric"
        )
        response = auth_client.get(
            f"/expenses/{expense_id}/delete", follow_redirects=False
        )
        assert response.status_code == 405

    def test_get_request_does_not_delete_row(self, auth_client, test_user, db):
        """A GET request must not delete the expense row even when authenticated."""
        expense_id = _insert_expense(
            db, test_user["id"], 200.00, "Bills", "2026-05-03", "Electric"
        )
        auth_client.get(f"/expenses/{expense_id}/delete", follow_redirects=False)
        assert _row_exists(db, expense_id)


# ------------------------------------------------------------------ #
# Class: non-existent expense                                         #
# ------------------------------------------------------------------ #


class TestDeleteExpenseNotFound:
    def test_post_for_nonexistent_id_returns_404(self, auth_client):
        """POST for an id that has no matching row must return 404."""
        response = _delete_post(auth_client, 99999)
        assert response.status_code == 404

    def test_post_for_nonexistent_id_returns_not_found_text(self, auth_client):
        """The 404 response body must contain 'Not found'."""
        response = _delete_post(auth_client, 99999)
        assert b"Not found" in response.data


# ------------------------------------------------------------------ #
# Class: ownership enforcement                                        #
# ------------------------------------------------------------------ #


class TestDeleteExpenseOwnership:
    def test_post_for_other_users_expense_returns_403(self, app, test_user, db):
        """Attempting to delete another user's expense must return 403."""
        other_cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (
                "Other User",
                "other@spendly.com",
                generate_password_hash("other1234"),
            ),
        )
        db.commit()
        other_id = other_cursor.lastrowid

        expense_id = _insert_expense(
            db, other_id, 800.00, "Health", "2026-05-04", "Doctor"
        )

        with app.test_client() as attacker_client:
            attacker_client.post(
                "/login",
                data={"email": test_user["email"], "password": test_user["password"]},
                follow_redirects=False,
            )
            response = _delete_post(attacker_client, expense_id)

        assert response.status_code == 403

    def test_post_for_other_users_expense_row_still_exists(self, app, test_user, db):
        """The target row must still exist in the database after a forbidden delete attempt."""
        other_cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (
                "Other User",
                "other2@spendly.com",
                generate_password_hash("other5678"),
            ),
        )
        db.commit()
        other_id = other_cursor.lastrowid

        expense_id = _insert_expense(
            db, other_id, 600.00, "Shopping", "2026-05-05", "Shoes"
        )

        with app.test_client() as attacker_client:
            attacker_client.post(
                "/login",
                data={"email": test_user["email"], "password": test_user["password"]},
                follow_redirects=False,
            )
            _delete_post(attacker_client, expense_id)

        assert _row_exists(db, expense_id)

    def test_post_for_other_users_expense_returns_forbidden_text(
        self, app, test_user, db
    ):
        """The 403 response body must contain 'Forbidden'."""
        other_cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (
                "Third User",
                "third@spendly.com",
                generate_password_hash("third9999"),
            ),
        )
        db.commit()
        other_id = other_cursor.lastrowid

        expense_id = _insert_expense(
            db, other_id, 250.00, "Food", "2026-05-06", "Dinner"
        )

        with app.test_client() as attacker_client:
            attacker_client.post(
                "/login",
                data={"email": test_user["email"], "password": test_user["password"]},
                follow_redirects=False,
            )
            response = _delete_post(attacker_client, expense_id)

        assert b"Forbidden" in response.data

    def test_user_id_in_form_body_cannot_bypass_ownership(self, app, test_user, db):
        """Sending a user_id form field must not override the session-based ownership check."""
        # Insert an expense belonging to a second user
        other_cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (
                "Fourth User",
                "fourth@spendly.com",
                generate_password_hash("fourth0000"),
            ),
        )
        db.commit()
        other_id = other_cursor.lastrowid

        expense_id = _insert_expense(
            db, other_id, 400.00, "Bills", "2026-05-07", "Water"
        )

        # Log in as test_user and post with a spoofed user_id body param
        with app.test_client() as attacker_client:
            attacker_client.post(
                "/login",
                data={"email": test_user["email"], "password": test_user["password"]},
                follow_redirects=False,
            )
            response = attacker_client.post(
                f"/expenses/{expense_id}/delete",
                data={"user_id": other_id},
                follow_redirects=False,
            )

        assert response.status_code == 403
        assert _row_exists(db, expense_id)


# ------------------------------------------------------------------ #
# Class: successful deletion — database state                         #
# ------------------------------------------------------------------ #


class TestDeleteExpenseSuccess:
    def test_valid_post_removes_row_from_database(self, auth_client, test_user, db):
        """A valid POST must delete the expense row from the database."""
        expense_id = _insert_expense(
            db, test_user["id"], 1000.00, "Food", "2026-05-08", "Groceries"
        )
        _delete_post(auth_client, expense_id)
        assert not _row_exists(db, expense_id)

    def test_valid_post_redirects_to_profile(self, auth_client, test_user, db):
        """A successful delete must respond with a 302 redirect."""
        expense_id = _insert_expense(
            db, test_user["id"], 300.00, "Transport", "2026-05-09", "Metro"
        )
        response = _delete_post(auth_client, expense_id)
        assert response.status_code == 302

    def test_valid_post_redirect_location_is_profile(self, auth_client, test_user, db):
        """The redirect after a successful delete must point to /profile."""
        expense_id = _insert_expense(
            db, test_user["id"], 300.00, "Transport", "2026-05-09", "Metro"
        )
        response = _delete_post(auth_client, expense_id)
        assert "/profile" in response.headers["Location"]

    def test_deleted_expense_absent_from_profile_page(self, auth_client, test_user, db):
        """After deletion the expense description must not appear in the /profile response."""
        expense_id = _insert_expense(
            db, test_user["id"], 750.00, "Entertainment", "2026-05-10", "Cinema tickets"
        )
        _delete_post(auth_client, expense_id)
        response = auth_client.get("/profile")
        assert b"Cinema tickets" not in response.data

    def test_deleting_one_expense_leaves_others_intact(
        self, auth_client, test_user, db
    ):
        """Deleting one expense must not remove any other expense rows."""
        keep_id = _insert_expense(
            db, test_user["id"], 200.00, "Food", "2026-05-11", "Breakfast"
        )
        delete_id = _insert_expense(
            db, test_user["id"], 500.00, "Bills", "2026-05-12", "Internet bill"
        )
        _delete_post(auth_client, delete_id)
        assert _row_exists(db, keep_id)
        assert not _row_exists(db, delete_id)

    def test_remaining_expense_still_appears_on_profile(
        self, auth_client, test_user, db
    ):
        """After deleting one expense the remaining expense still appears on /profile."""
        _insert_expense(
            db, test_user["id"], 200.00, "Food", "2026-05-11", "Breakfast kept"
        )
        delete_id = _insert_expense(
            db, test_user["id"], 500.00, "Bills", "2026-05-12", "Bill removed"
        )
        _delete_post(auth_client, delete_id)
        response = auth_client.get("/profile")
        assert b"Breakfast kept" in response.data
        assert b"Bill removed" not in response.data


# ------------------------------------------------------------------ #
# Class: stats update after deletion                                  #
# ------------------------------------------------------------------ #


class TestDeleteExpenseStatsUpdate:
    def test_total_spent_decreases_after_deletion(self, auth_client, test_user, db):
        """total_spent on /profile must reflect the reduced total after a delete."""
        _insert_expense(db, test_user["id"], 1000.00, "Food", "2026-05-01", "Big order")
        delete_id = _insert_expense(
            db, test_user["id"], 500.00, "Bills", "2026-05-02", "Cable"
        )
        # Before delete: total = $1,500
        _delete_post(auth_client, delete_id)
        response = auth_client.get("/profile")
        # After delete: total = $1,000; $1,500 must no longer appear
        assert "$1,000".encode() in response.data
        assert "$1,500".encode() not in response.data

    def test_transaction_count_decreases_by_one_after_deletion(
        self, auth_client, test_user, db
    ):
        """The Transactions stat must drop by exactly one after a single delete."""
        _insert_expense(db, test_user["id"], 100.00, "Food", "2026-05-01", "Coffee")
        _insert_expense(db, test_user["id"], 200.00, "Transport", "2026-05-02", "Bus")
        delete_id = _insert_expense(
            db, test_user["id"], 300.00, "Health", "2026-05-03", "Pharmacy"
        )
        _delete_post(auth_client, delete_id)
        response = auth_client.get("/profile")
        # 3 rows inserted, 1 deleted → 2 remaining
        assert b">2<" in response.data

    def test_total_spent_is_zero_when_last_expense_deleted(
        self, auth_client, test_user, db
    ):
        """Deleting the only expense must make total_spent show $0."""
        expense_id = _insert_expense(
            db, test_user["id"], 800.00, "Shopping", "2026-05-04", "Clothes"
        )
        _delete_post(auth_client, expense_id)
        response = auth_client.get("/profile")
        assert "$0".encode() in response.data

    def test_transaction_count_is_zero_when_last_expense_deleted(
        self, auth_client, test_user, db
    ):
        """Deleting the only expense must make the Transactions stat show 0."""
        expense_id = _insert_expense(
            db, test_user["id"], 800.00, "Shopping", "2026-05-04", "Clothes"
        )
        _delete_post(auth_client, expense_id)
        response = auth_client.get("/profile")
        assert b">0<" in response.data


# ------------------------------------------------------------------ #
# Class: profile template — delete form rendering                     #
# ------------------------------------------------------------------ #


class TestDeleteExpenseProfileTemplate:
    def test_profile_renders_delete_form_with_correct_action(
        self, auth_client, test_user, db
    ):
        """Each expense row must contain a delete form posting to /expenses/<id>/delete."""
        expense_id = _insert_expense(
            db, test_user["id"], 350.00, "Food", "2026-05-05", "Lunch out"
        )
        response = auth_client.get("/profile")
        expected_action = f"/expenses/{expense_id}/delete".encode()
        assert expected_action in response.data

    def test_profile_delete_form_uses_post_method(self, auth_client, test_user, db):
        """The delete form in the transactions table must use method='POST'."""
        _insert_expense(db, test_user["id"], 350.00, "Food", "2026-05-05", "Lunch out")
        response = auth_client.get("/profile")
        assert b'method="POST"' in response.data

    def test_profile_renders_delete_button(self, auth_client, test_user, db):
        """Each expense row must contain a Delete submit button."""
        _insert_expense(db, test_user["id"], 350.00, "Food", "2026-05-05", "Lunch out")
        response = auth_client.get("/profile")
        assert b"btn-danger" in response.data
        assert b"Delete" in response.data

    def test_profile_renders_correct_delete_action_for_multiple_expenses(
        self, auth_client, test_user, db
    ):
        """When multiple expenses exist each must have its own correctly-addressed delete form."""
        id_a = _insert_expense(
            db, test_user["id"], 100.00, "Food", "2026-05-01", "Snack A"
        )
        id_b = _insert_expense(
            db, test_user["id"], 200.00, "Transport", "2026-05-02", "Cab B"
        )
        response = auth_client.get("/profile")
        assert f"/expenses/{id_a}/delete".encode() in response.data
        assert f"/expenses/{id_b}/delete".encode() in response.data

    def test_profile_expense_amount_uses_inr_symbol(self, auth_client, test_user, db):
        """Expense amounts displayed in the transactions table must use $, not $."""
        _insert_expense(
            db, test_user["id"], 1200.00, "Bills", "2026-05-06", "Phone plan"
        )
        response = auth_client.get("/profile")
        assert "$".encode() in response.data
        assert b"$" not in response.data
