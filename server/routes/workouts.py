"""Endpoints for the /workouts resource."""

from flask import Blueprint, request

from models import Workout, db
from schemas import workout_detail_schema, workout_schema, workouts_schema

workouts_bp = Blueprint("workouts", __name__, url_prefix="/workouts")


@workouts_bp.get("")
def list_workouts():
    """GET /workouts - list every workout, newest session first."""
    workouts = Workout.query.order_by(Workout.date.desc(), Workout.id.desc()).all()
    return workouts_schema.dump(workouts), 200


@workouts_bp.get("/<int:id>")
def get_workout(id):
    """GET /workouts/<id> - one workout with its exercises and their reps/sets/duration."""
    workout = db.session.get(Workout, id)
    if workout is None:
        return {"errors": ["Workout not found."]}, 404
    return workout_detail_schema.dump(workout), 200


@workouts_bp.post("")
def create_workout():
    """POST /workouts - create a workout from a JSON body."""
    # ``load`` runs the schema validations and returns an unsaved Workout, whose
    # own ``@validates`` hooks run as the attributes are set.
    workout = workout_schema.load(request.get_json() or {})
    db.session.add(workout)
    db.session.commit()
    return workout_schema.dump(workout), 201


@workouts_bp.delete("/<int:id>")
def delete_workout(id):
    """DELETE /workouts/<id> - delete a workout and its WorkoutExercise rows.

    The cascade on ``Workout.workout_exercises`` removes the join rows, leaving
    the exercises themselves untouched so they stay reusable.
    """
    workout = db.session.get(Workout, id)
    if workout is None:
        return {"errors": ["Workout not found."]}, 404
    db.session.delete(workout)
    db.session.commit()
    return {"message": f"Workout {id} and its exercise entries were deleted."}, 200
