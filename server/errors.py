"""Centralised JSON error handling.

Registering these once means route handlers can simply let a validation error
propagate instead of wrapping every call in try/except, and clients always get a
consistent ``{"errors": ...}`` body instead of Flask's HTML error pages.
"""

from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from models import db


def register_error_handlers(app):
    """Attach JSON error handlers to the given Flask app."""

    @app.errorhandler(ValidationError)
    def handle_schema_validation_error(error):
        """Marshmallow schema validation failed -> 400 with per-field messages."""
        return {"errors": error.messages}, 400

    @app.errorhandler(ValueError)
    def handle_model_validation_error(error):
        """A model ``@validates`` hook rejected a value -> 400."""
        db.session.rollback()
        return {"errors": [str(error)]}, 400

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        """A database constraint rejected the row -> 400."""
        db.session.rollback()
        return {"errors": ["Database constraint violated.", str(error.orig)]}, 400

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Render Flask's own 404/405/etc. as JSON rather than HTML."""
        return {"errors": [error.description]}, error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Last resort so an unhandled bug still returns JSON, not an HTML page."""
        db.session.rollback()
        return {"errors": ["An unexpected server error occurred."]}, 500
