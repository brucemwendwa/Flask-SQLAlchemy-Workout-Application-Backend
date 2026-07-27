"""Endpoints for the /exercises resource."""

from flask import Blueprint, request

from models import Exercise, db
from schemas import exercise_detail_schema, exercise_schema, exercises_schema

exercises_bp = Blueprint("exercises", __name__, url_prefix="/exercises")


@exercises_bp.get("")
def list_exercises():
    """GET /exercises - list every exercise alphabetically."""
    exercises = Exercise.query.order_by(Exercise.name).all()
    return exercises_schema.dump(exercises), 200


@exercises_bp.get("/<int:id>")
def get_exercise(id):
    """GET /exercises/<id> - one exercise plus every workout it appears in."""
    exercise = db.session.get(Exercise, id)
    if exercise is None:
        return {"errors": ["Exercise not found."]}, 404
    return exercise_detail_schema.dump(exercise), 200


@exercises_bp.post("")
def create_exercise():
    """POST /exercises - create a reusable exercise from a JSON body."""
    exercise = exercise_schema.load(request.get_json() or {})
    db.session.add(exercise)
    db.session.commit()
    return exercise_schema.dump(exercise), 201


@exercises_bp.delete("/<int:id>")
def delete_exercise(id):
    """DELETE /exercises/<id> - delete an exercise and its WorkoutExercise rows.

    The cascade on ``Exercise.workout_exercises`` removes the join rows so no
    workout is left referencing a deleted exercise.
    """
    exercise = db.session.get(Exercise, id)
    if exercise is None:
        return {"errors": ["Exercise not found."]}, 404
    db.session.delete(exercise)
    db.session.commit()
    return {"message": f"Exercise {id} and its workout entries were deleted."}, 200
