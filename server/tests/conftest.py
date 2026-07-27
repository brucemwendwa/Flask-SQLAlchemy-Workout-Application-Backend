"""Shared pytest fixtures.

Each test runs against a throwaway SQLite file created before ``app`` is
imported, so the development ``app.db`` is never touched.
"""

import os
import sys
import tempfile

import pytest

# Make the modules in server/ importable when pytest is run from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URI"] = f"sqlite:///{_TEST_DB_PATH}"

from app import app as flask_app  # noqa: E402  (import must follow the env var)
from models import db  # noqa: E402


@pytest.fixture
def app():
    """A Flask app with empty tables, rebuilt for every test."""
    flask_app.config["TESTING"] = True
    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client bound to the fresh-database app."""
    return app.test_client()
