"""Endpoint for attaching an exercise to a workout."""

from flask import Blueprint, request

from models import Exercise, Workout, db
from schemas import workout_exercise_schema
from schemas import WorkoutExerciseDetailSchema

workout_exercises_bp = Blueprint("workout_exercises", __name__)

# The created join row is echoed back with its exercise inlined so the client
# does not need a follow-up request to see what was added.
_created_schema = WorkoutExerciseDetailSchema()


@workout_exercises_bp.post(
    "/workouts/<int:workout_id>/exercises/<int:exercise_id>/workout_exercises"
)
def add_exercise_to_workout(workout_id, exercise_id):
    """POST - add an exercise to a workout with its reps/sets/duration.

    The two ids come from the URL; the JSON body carries only the performance
    metrics, e.g. ``{"reps": 10, "sets": 3}`` or ``{"duration_seconds": 300}``.
    """
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        return {"errors": ["Workout not found."]}, 404

    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None:
        return {"errors": ["Exercise not found."]}, 404

    workout_exercise = workout_exercise_schema.load(request.get_json() or {})
    workout_exercise.workout = workout
    workout_exercise.exercise = exercise
    # Cross-column model validation; the matching CHECK constraint backs it up.
    workout_exercise.validate_metrics_present()

    db.session.add(workout_exercise)
    db.session.commit()
    return _created_schema.dump(workout_exercise), 201
