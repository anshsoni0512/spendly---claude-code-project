"""
Tests for Step 06 — Date Filter for Profile Page
=================================================
Feature: The GET /profile route accepts optional `from` and `to` query
parameters (YYYY-MM-DD) and filters the displayed expenses, summary stats,
and category breakdown to only the matching rows. When neither parameter is
supplied the route returns all expenses, preserving previous behaviour.

All monetary assertions use $ (USD). No seed data is used; every test
inserts its own rows so the expected values are always deterministic.
"""

import pytest
from database.db import get_db


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _insert_expenses(db, user_id, expenses):
    """
    Insert a list of expense tuples (amount, category, date, description)
    for the given user_id and commit.
    """
    db.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (?, ?, ?, ?, ?)",
        [(user_id, amt, cat, dt, desc) for amt, cat, dt, desc in expenses],
    )
    db.commit()


def _get_profile(auth_client, query_string=""):
    """GET /profile with an optional raw query string, return response."""
    url = "/profile" + (f"?{query_string}" if query_string else "")
    return auth_client.get(url)


# ------------------------------------------------------------------ #
# Class: unauthenticated access                                       #
# ------------------------------------------------------------------ #

class TestProfileAuthGuard:
    def test_unauthenticated_request_redirects_to_login(self, client):
        """Visiting /profile without a session must redirect to /login."""
        response = client.get("/profile")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_with_filter_params_redirects_to_login(self, client):
        """Filter params do not bypass the authentication guard."""
        response = client.get("/profile?from=2026-05-01&to=2026-05-10")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ------------------------------------------------------------------ #
# Class: no filter — unchanged baseline behaviour                     #
# ------------------------------------------------------------------ #

class TestProfileNoFilter:
    def test_no_params_returns_200(self, auth_client):
        """/profile with no query params must return HTTP 200."""
        response = _get_profile(auth_client)
        assert response.status_code == 200

    def test_no_params_shows_all_expenses(self, auth_client, test_user, db):
        """All inserted expenses appear when no filter is applied."""
        _insert_expenses(db, test_user["id"], [
            (500.00, "Food",      "2026-04-01", "April lunch"),
            (800.00, "Bills",     "2026-05-03", "Electricity"),
            (200.00, "Transport", "2026-05-10", "Cab"),
        ])
        response = _get_profile(auth_client)
        assert b"April lunch" in response.data
        assert b"Electricity" in response.data
        assert b"Cab" in response.data

    def test_no_params_total_spent_reflects_all_rows(self, auth_client, test_user, db):
        """total_spent stat equals the sum of all expenses when no filter set."""
        _insert_expenses(db, test_user["id"], [
            (1000.00, "Food",  "2026-05-01", "Groceries"),
            (500.00,  "Bills", "2026-05-05", "Internet"),
        ])
        response = _get_profile(auth_client)
        # 1000 + 500 = 1,500  → rendered as $1,500
        assert "$1,500".encode() in response.data

    def test_no_params_transaction_count_reflects_all_rows(self, auth_client, test_user, db):
        """Transaction count stat matches the total number of expense rows."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food",      "2026-05-01", "Coffee"),
            (200.00, "Transport", "2026-05-02", "Metro"),
            (300.00, "Bills",     "2026-05-03", "Phone"),
        ])
        response = _get_profile(auth_client)
        # The stat value "3" must appear in the page
        assert b">3<" in response.data

    def test_no_params_no_active_filter_label(self, auth_client, test_user, db):
        """The active filter label must NOT be visible when no params are given."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-01", "Snack"),
        ])
        response = _get_profile(auth_client)
        assert b"filter-active-label" not in response.data

    def test_no_params_no_clear_link(self, auth_client, test_user, db):
        """The Clear link must NOT appear when no filter is active."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-01", "Snack"),
        ])
        response = _get_profile(auth_client)
        assert b"btn-filter-clear" not in response.data


# ------------------------------------------------------------------ #
# Class: from-only filter                                             #
# ------------------------------------------------------------------ #

class TestProfileFromFilter:
    def test_from_filter_excludes_earlier_expenses(self, auth_client, test_user, db):
        """Expenses before the `from` date must not appear in the response."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food",  "2026-04-10", "Old lunch"),
            (200.00, "Bills", "2026-05-05", "New bill"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01")
        assert b"Old lunch" not in response.data
        assert b"New bill" in response.data

    def test_from_filter_includes_boundary_date(self, auth_client, test_user, db):
        """An expense on exactly the `from` date must be included."""
        _insert_expenses(db, test_user["id"], [
            (300.00, "Health", "2026-05-01", "Boundary day expense"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01")
        assert b"Boundary day expense" in response.data

    def test_from_filter_stats_reflect_only_filtered_rows(self, auth_client, test_user, db):
        """total_spent must sum only rows on/after `from`, not excluded rows."""
        _insert_expenses(db, test_user["id"], [
            (1000.00, "Food",  "2026-04-01", "April spend"),   # excluded
            (400.00,  "Bills", "2026-05-10", "May bill"),       # included
        ])
        response = _get_profile(auth_client, "from=2026-05-01")
        assert "$400".encode() in response.data
        # The excluded amount must not appear as total_spent
        assert "$1,400".encode() not in response.data

    def test_from_filter_transaction_count_reflects_filtered_rows(self, auth_client, test_user, db):
        """Transaction count stat must only count rows on/after `from`."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food",  "2026-04-01", "Excluded"),
            (200.00, "Bills", "2026-05-02", "Included A"),
            (300.00, "Bills", "2026-05-03", "Included B"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01")
        assert b">2<" in response.data

    def test_from_filter_category_breakdown_reflects_filtered_rows(self, auth_client, test_user, db):
        """Category breakdown must omit categories that only exist before `from`."""
        _insert_expenses(db, test_user["id"], [
            (500.00, "Entertainment", "2026-04-15", "Old Netflix"),  # excluded
            (300.00, "Food",          "2026-05-10", "Groceries"),    # included
        ])
        response = _get_profile(auth_client, "from=2026-05-01")
        assert b"Food" in response.data
        assert b"Entertainment" not in response.data


# ------------------------------------------------------------------ #
# Class: to-only filter                                               #
# ------------------------------------------------------------------ #

class TestProfileToFilter:
    def test_to_filter_excludes_later_expenses(self, auth_client, test_user, db):
        """Expenses after the `to` date must not appear in the response."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food",      "2026-05-01", "Early lunch"),
            (200.00, "Transport", "2026-05-20", "Late cab"),
        ])
        response = _get_profile(auth_client, "to=2026-05-10")
        assert b"Early lunch" in response.data
        assert b"Late cab" not in response.data

    def test_to_filter_includes_boundary_date(self, auth_client, test_user, db):
        """An expense on exactly the `to` date must be included."""
        _insert_expenses(db, test_user["id"], [
            (250.00, "Health", "2026-05-10", "Boundary day expense"),
        ])
        response = _get_profile(auth_client, "to=2026-05-10")
        assert b"Boundary day expense" in response.data

    def test_to_filter_stats_reflect_only_filtered_rows(self, auth_client, test_user, db):
        """total_spent must sum only rows on/before `to`."""
        _insert_expenses(db, test_user["id"], [
            (600.00, "Bills",    "2026-05-05", "Included bill"),  # included
            (900.00, "Shopping", "2026-05-25", "Late purchase"),  # excluded
        ])
        response = _get_profile(auth_client, "to=2026-05-10")
        assert "$600".encode() in response.data
        assert "$1,500".encode() not in response.data

    def test_to_filter_transaction_count_reflects_filtered_rows(self, auth_client, test_user, db):
        """Transaction count stat must only count rows on/before `to`."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-01", "Row A"),
            (200.00, "Food", "2026-05-05", "Row B"),
            (300.00, "Food", "2026-05-25", "Row C — excluded"),
        ])
        response = _get_profile(auth_client, "to=2026-05-10")
        assert b">2<" in response.data

    def test_to_filter_category_breakdown_reflects_filtered_rows(self, auth_client, test_user, db):
        """Category breakdown must omit categories that only exist after `to`."""
        _insert_expenses(db, test_user["id"], [
            (400.00, "Food",          "2026-05-02", "Early food"),   # included
            (700.00, "Entertainment", "2026-05-30", "Late concert"),  # excluded
        ])
        response = _get_profile(auth_client, "to=2026-05-15")
        assert b"Food" in response.data
        assert b"Entertainment" not in response.data


# ------------------------------------------------------------------ #
# Class: both from and to filter                                      #
# ------------------------------------------------------------------ #

class TestProfileDateRangeFilter:
    def test_range_filter_includes_only_expenses_within_range(self, auth_client, test_user, db):
        """Only expenses within [from, to] inclusive appear on the page."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food",      "2026-04-28", "Before range"),
            (200.00, "Bills",     "2026-05-03", "In range A"),
            (300.00, "Transport", "2026-05-07", "In range B"),
            (400.00, "Shopping",  "2026-05-20", "After range"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-10")
        assert b"Before range" not in response.data
        assert b"In range A" in response.data
        assert b"In range B" in response.data
        assert b"After range" not in response.data

    def test_range_filter_includes_start_boundary(self, auth_client, test_user, db):
        """An expense on the `from` date is included in a range filter."""
        _insert_expenses(db, test_user["id"], [
            (150.00, "Food", "2026-05-01", "Start boundary"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-10")
        assert b"Start boundary" in response.data

    def test_range_filter_includes_end_boundary(self, auth_client, test_user, db):
        """An expense on the `to` date is included in a range filter."""
        _insert_expenses(db, test_user["id"], [
            (150.00, "Food", "2026-05-10", "End boundary"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-10")
        assert b"End boundary" in response.data

    def test_range_filter_total_spent_reflects_range(self, auth_client, test_user, db):
        """total_spent must equal sum of only in-range expenses."""
        _insert_expenses(db, test_user["id"], [
            (1000.00, "Bills",    "2026-04-01", "Out"),          # excluded
            (200.00,  "Food",     "2026-05-03", "In A"),          # included
            (300.00,  "Food",     "2026-05-08", "In B"),          # included
            (999.00,  "Shopping", "2026-06-01", "Out future"),   # excluded
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-10")
        # 200 + 300 = 500
        assert "$500".encode() in response.data

    def test_range_filter_transaction_count_reflects_range(self, auth_client, test_user, db):
        """Transaction count stat must equal the number of in-range expenses."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food",      "2026-04-10", "Out A"),
            (200.00, "Bills",     "2026-05-03", "In A"),
            (300.00, "Transport", "2026-05-07", "In B"),
            (400.00, "Shopping",  "2026-06-01", "Out B"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-10")
        assert b">2<" in response.data

    def test_range_filter_top_category_reflects_range(self, auth_client, test_user, db):
        """top_category must reflect only in-range expenses."""
        _insert_expenses(db, test_user["id"], [
            (5000.00, "Shopping", "2026-04-01", "Big purchase out"),  # excluded
            (100.00,  "Food",     "2026-05-02", "Small food in"),     # included
            (200.00,  "Food",     "2026-05-04", "More food in"),      # included
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-10")
        assert b"Food" in response.data

    def test_range_filter_category_breakdown_omits_out_of_range_categories(
        self, auth_client, test_user, db
    ):
        """Category breakdown must not list categories whose expenses are all outside the range."""
        _insert_expenses(db, test_user["id"], [
            (800.00, "Entertainment", "2026-04-01", "Old concert"),   # excluded
            (250.00, "Food",          "2026-05-05", "In-range meal"),  # included
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-10")
        assert b"Food" in response.data
        assert b"Entertainment" not in response.data

    def test_range_with_no_matching_expenses_shows_zero_stats(self, auth_client, test_user, db):
        """When a filter range matches no expenses, stats show zero/N/A and no transactions."""
        _insert_expenses(db, test_user["id"], [
            (500.00, "Food", "2026-03-01", "March expense"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-31")
        assert response.status_code == 200
        # total_spent: $0
        assert "$0".encode() in response.data
        # transaction count: 0
        assert b">0<" in response.data


# ------------------------------------------------------------------ #
# Class: template — form pre-fill and filter UI elements              #
# ------------------------------------------------------------------ #

class TestProfileFilterFormUI:
    def test_from_input_prefilled_when_from_param_set(self, auth_client, test_user, db):
        """The `from` date input value attribute must reflect the query parameter."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01")
        assert b'value="2026-05-01"' in response.data

    def test_to_input_prefilled_when_to_param_set(self, auth_client, test_user, db):
        """The `to` date input value attribute must reflect the query parameter."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client, "to=2026-05-10")
        assert b'value="2026-05-10"' in response.data

    def test_both_inputs_prefilled_when_both_params_set(self, auth_client, test_user, db):
        """Both date inputs are prefilled when both query params are present."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-10")
        assert b'value="2026-05-01"' in response.data
        assert b'value="2026-05-10"' in response.data

    def test_inputs_empty_when_no_filter_active(self, auth_client, test_user, db):
        """Both date inputs must have empty value attributes when no filter is active."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client)
        # Both inputs rendered with value=""
        assert b'value=""' in response.data

    def test_filter_form_uses_get_method(self, auth_client, test_user, db):
        """The filter form must submit via GET so the filter state lives in the URL."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client)
        assert b'method="get"' in response.data

    def test_filter_form_action_points_to_profile(self, auth_client, test_user, db):
        """The filter form action must point to /profile."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client)
        assert b'action="/profile"' in response.data

    def test_active_label_visible_when_from_param_set(self, auth_client, test_user, db):
        """The active range label must be visible when `from` param is supplied."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01")
        assert b"filter-active-label" in response.data

    def test_active_label_visible_when_to_param_set(self, auth_client, test_user, db):
        """The active range label must be visible when `to` param is supplied."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client, "to=2026-05-10")
        assert b"filter-active-label" in response.data

    def test_active_label_visible_when_both_params_set(self, auth_client, test_user, db):
        """The active range label must be visible when both params are supplied."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-10")
        assert b"filter-active-label" in response.data

    def test_active_label_hidden_when_no_params(self, auth_client, test_user, db):
        """The active range label must NOT appear when no filter params are present."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client)
        assert b"filter-active-label" not in response.data

    def test_active_label_contains_from_date(self, auth_client, test_user, db):
        """The active range label must include the `from` date value."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-10")
        assert b"2026-05-01" in response.data

    def test_active_label_contains_to_date(self, auth_client, test_user, db):
        """The active range label must include the `to` date value."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-10")
        assert b"2026-05-10" in response.data

    def test_clear_link_present_when_from_param_active(self, auth_client, test_user, db):
        """The Clear link must appear when a `from` filter is active."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01")
        assert b"btn-filter-clear" in response.data

    def test_clear_link_present_when_to_param_active(self, auth_client, test_user, db):
        """The Clear link must appear when a `to` filter is active."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client, "to=2026-05-10")
        assert b"btn-filter-clear" in response.data

    def test_clear_link_href_points_to_profile_no_params(self, auth_client, test_user, db):
        """The Clear link's href must be exactly /profile (no query params)."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-10")
        assert b'href="/profile"' in response.data

    def test_clear_link_absent_when_no_filter_active(self, auth_client, test_user, db):
        """The Clear link must NOT appear when no filter params are active."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client)
        assert b"btn-filter-clear" not in response.data

    def test_quick_filter_links_present_on_page(self, auth_client, test_user, db):
        """Quick filter anchor links (Last 1 Month, 3 Months, 6 Months) must be rendered."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client)
        assert b"Last 1 Month" in response.data
        assert b"Last 3 Months" in response.data
        assert b"Last 6 Months" in response.data


# ------------------------------------------------------------------ #
# Class: malformed / invalid date inputs                              #
# ------------------------------------------------------------------ #

class TestProfileMalformedDateParams:
    def test_malformed_from_silently_ignored_shows_all_expenses(self, auth_client, test_user, db):
        """A non-date `from` value must be silently discarded; all expenses shown."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food",  "2026-04-01", "April row"),
            (200.00, "Bills", "2026-05-10", "May row"),
        ])
        response = _get_profile(auth_client, "from=notadate")
        assert response.status_code == 200
        assert b"April row" in response.data
        assert b"May row" in response.data

    def test_malformed_to_silently_ignored_shows_all_expenses(self, auth_client, test_user, db):
        """A non-date `to` value must be silently discarded; all expenses shown."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food",  "2026-04-01", "April row"),
            (200.00, "Bills", "2026-05-10", "May row"),
        ])
        response = _get_profile(auth_client, "to=also-bad")
        assert response.status_code == 200
        assert b"April row" in response.data
        assert b"May row" in response.data

    def test_malformed_both_params_silently_ignored_shows_all_expenses(
        self, auth_client, test_user, db
    ):
        """Both malformed params must be silently discarded; all expenses shown."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food",  "2026-04-01", "April row"),
            (200.00, "Bills", "2026-05-10", "May row"),
        ])
        response = _get_profile(auth_client, "from=notadate&to=also-bad")
        assert response.status_code == 200
        assert b"April row" in response.data
        assert b"May row" in response.data

    def test_malformed_params_no_active_label_shown(self, auth_client, test_user, db):
        """When malformed params are discarded the active filter label must not appear."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client, "from=notadate&to=also-bad")
        assert b"filter-active-label" not in response.data

    def test_malformed_params_no_clear_link_shown(self, auth_client, test_user, db):
        """When malformed params are discarded the Clear link must not appear."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food", "2026-05-05", "Snack"),
        ])
        response = _get_profile(auth_client, "from=notadate&to=also-bad")
        assert b"btn-filter-clear" not in response.data

    def test_wrong_format_date_silently_ignored(self, auth_client, test_user, db):
        """Dates in DD-MM-YYYY format (wrong separator order) must be treated as malformed."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food",  "2026-04-01", "April row"),
            (200.00, "Bills", "2026-05-10", "May row"),
        ])
        response = _get_profile(auth_client, "from=01-05-2026")
        assert response.status_code == 200
        assert b"April row" in response.data
        assert b"May row" in response.data

    def test_empty_string_params_show_all_expenses(self, auth_client, test_user, db):
        """Explicitly empty `from` and `to` params behave the same as no params."""
        _insert_expenses(db, test_user["id"], [
            (100.00, "Food",  "2026-04-01", "April row"),
            (200.00, "Bills", "2026-05-10", "May row"),
        ])
        response = _get_profile(auth_client, "from=&to=")
        assert response.status_code == 200
        assert b"April row" in response.data
        assert b"May row" in response.data


# ------------------------------------------------------------------ #
# Class: USD currency rendering                                       #
# ------------------------------------------------------------------ #

class TestProfileCurrencyRendering:
    def test_transaction_amounts_use_inr_symbol(self, auth_client, test_user, db):
        """Every displayed monetary amount must use the $ symbol, never $."""
        _insert_expenses(db, test_user["id"], [
            (1500.00, "Food", "2026-05-05", "Expensive lunch"),
        ])
        response = _get_profile(auth_client)
        assert "$".encode() in response.data
        assert b"$" not in response.data

    def test_total_spent_uses_inr_symbol(self, auth_client, test_user, db):
        """The total_spent stat must be prefixed with $."""
        _insert_expenses(db, test_user["id"], [
            (2000.00, "Bills", "2026-05-03", "Water bill"),
        ])
        response = _get_profile(auth_client)
        assert "$2,000".encode() in response.data

    def test_category_breakdown_amounts_use_inr_symbol(self, auth_client, test_user, db):
        """Category breakdown amounts must use $ prefix."""
        _insert_expenses(db, test_user["id"], [
            (750.00, "Health", "2026-05-04", "Doctor visit"),
        ])
        response = _get_profile(auth_client)
        assert "$750".encode() in response.data

    def test_filtered_transaction_amount_uses_inr_symbol(self, auth_client, test_user, db):
        """Amounts shown under a date filter must also use $, not $."""
        _insert_expenses(db, test_user["id"], [
            (850.00, "Shopping", "2026-05-06", "Filtered purchase"),
        ])
        response = _get_profile(auth_client, "from=2026-05-01&to=2026-05-10")
        assert "$".encode() in response.data
        assert b"$" not in response.data


# ------------------------------------------------------------------ #
# Class: data isolation between users                                 #
# ------------------------------------------------------------------ #

class TestProfileUserIsolation:
    def test_filter_returns_only_current_users_expenses(self, app, test_user, db):
        """Expenses belonging to another user must never appear, even if in-range."""
        from werkzeug.security import generate_password_hash

        # Create a second user
        other_cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Other User", "other@spendly.com", generate_password_hash("other1234")),
        )
        db.commit()
        other_id = other_cursor.lastrowid

        # Insert one expense for each user in the same date range
        _insert_expenses(db, test_user["id"], [
            (200.00, "Food", "2026-05-05", "My expense"),
        ])
        _insert_expenses(db, other_id, [
            (999.00, "Bills", "2026-05-05", "Other user expense"),
        ])

        with app.test_client() as other_client:
            other_client.post(
                "/login",
                data={"email": test_user["email"], "password": test_user["password"]},
                follow_redirects=False,
            )
            response = other_client.get("/profile?from=2026-05-01&to=2026-05-31")

        assert b"My expense" in response.data
        assert b"Other user expense" not in response.data
