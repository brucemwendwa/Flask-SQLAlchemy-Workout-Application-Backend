"""Flask application entry point for the Workout Tracker API.

Wiring only: configuration, extensions, error handlers and blueprints. The
resource logic lives in ``routes/``, the models in ``models.py`` and the
serialization in ``schemas.py``.
"""

import os

from flask import Flask
from flask_migrate import Migrate

from errors import register_error_handlers
from models import *
from routes import register_blueprints

app = Flask(__name__)
# Defaults to the local SQLite file; the test suite points DATABASE_URI at a
# throwaway database so it never touches development data.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URI', 'sqlite:///app.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Keep JSON keys in the order the schemas declare them rather than alphabetical.
app.json.sort_keys = False

migrate = Migrate(app, db)

db.init_app(app)


@app.get('/')
def index():
    """Tiny landing route listing the available endpoints."""
    return {
        'message': 'Workout Tracker API',
        'endpoints': [
            'GET /workouts',
            'GET /workouts/<id>',
            'POST /workouts',
            'DELETE /workouts/<id>',
            'GET /exercises',
            'GET /exercises/<id>',
            'POST /exercises',
            'DELETE /exercises/<id>',
            'POST /workouts/<workout_id>/exercises/<exercise_id>/workout_exercises',
        ],
    }, 200


register_blueprints(app)
register_error_handlers(app)


if __name__ == '__main__':
    app.run(port=5555, debug=True)
