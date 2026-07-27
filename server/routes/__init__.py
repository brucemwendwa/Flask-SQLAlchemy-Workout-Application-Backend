"""Blueprints for the API, grouped by resource.

``register_blueprints`` is the single place ``app.py`` has to touch when a new
resource is added.
"""

from routes.exercises import exercises_bp
from routes.workout_exercises import workout_exercises_bp
from routes.workouts import workouts_bp


def register_blueprints(app):
    """Attach every resource blueprint to the given Flask app."""
    app.register_blueprint(workouts_bp)
    app.register_blueprint(exercises_bp)
    app.register_blueprint(workout_exercises_bp)
