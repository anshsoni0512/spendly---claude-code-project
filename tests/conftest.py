"""
Shared pytest fixtures for Spendly tests.

DB isolation strategy: monkeypatch database.db.DB_PATH to a temporary file
before each test so every test gets a clean, empty SQLite database.
get_db() reads DB_PATH at call time, so patching the module-level variable
is sufficient — no mocking of the connection itself is needed.
"""

import os
import pytest
import database.db as db_module
from database.db import init_db, get_db
from app import app as flask_app
from werkzeug.security import generate_password_hash


@pytest.fixture()
def app(tmp_path, monkeypatch):
    """
    Yield the Flask app configured for testing with an isolated temp DB.
    A fresh schema is created; no seed data is inserted so each test
    controls exactly what rows exist.
    """
    db_file = str(tmp_path / "test_spendly.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"

    with flask_app.app_context():
        init_db()

    yield flask_app


@pytest.fixture()
def client(app):
    """Plain (unauthenticated) test client."""
    return app.test_client()


@pytest.fixture()
def db(app):
    """
    Return an open DB connection scoped to the test's temp database.
    Caller must NOT close it — the fixture tears it down automatically.
    """
    conn = get_db()
    yield conn
    conn.close()


@pytest.fixture()
def test_user(db):
    """
    Insert a single test user and return a dict with id, email, password.
    """
    password = "password123"
    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Test User", "testuser@spendly.com", generate_password_hash(password)),
    )
    db.commit()
    return {"id": cursor.lastrowid, "email": "testuser@spendly.com", "password": password}


@pytest.fixture()
def auth_client(client, test_user):
    """
    Test client that is already logged in as test_user.
    Uses a real POST to /login so the session cookie is set correctly.
    """
    client.post(
        "/login",
        data={"email": test_user["email"], "password": test_user["password"]},
        follow_redirects=False,
    )
    return client
