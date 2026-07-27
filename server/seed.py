#!/usr/bin/env python3
"""Reset the database and populate it with realistic example data.

Safe to re-run at any time: every table is cleared first, so running the seed
twice will not duplicate rows.

Usage (from the ``server/`` directory)::

    python seed.py
"""

from datetime import date, timedelta

from app import app
from models import Exercise, Workout, WorkoutExercise, db


def clear_tables():
    """Delete existing rows, children first so no foreign keys dangle."""
    WorkoutExercise.query.delete()
    Workout.query.delete()
    Exercise.query.delete()
    db.session.commit()


def create_exercises():
    """Create the reusable exercise library and return it keyed by name."""
    exercises = [
        Exercise(name="Back Squat", category="strength", equipment_needed=True),
        Exercise(name="Deadlift", category="strength", equipment_needed=True),
        Exercise(name="Bench Press", category="strength", equipment_needed=True),
        Exercise(name="Pull Up", category="strength", equipment_needed=True),
        Exercise(name="Push Up", category="strength", equipment_needed=False),
        Exercise(name="Treadmill Run", category="cardio", equipment_needed=True),
        Exercise(name="Jump Rope", category="cardio", equipment_needed=True),
        Exercise(name="Rowing Machine", category="cardio", equipment_needed=True),
        Exercise(name="Plank", category="core", equipment_needed=False),
        Exercise(name="Russian Twist", category="core", equipment_needed=False),
        Exercise(name="Hip Flexor Stretch", category="mobility", equipment_needed=False),
        Exercise(name="Single Leg Stand", category="balance", equipment_needed=False),
    ]
    db.session.add_all(exercises)
    db.session.commit()
    return {exercise.name: exercise for exercise in exercises}


def create_workouts():
    """Create a week of training sessions and return them in order."""
    today = date.today()
    workouts = [
        Workout(
            date=today - timedelta(days=6),
            duration_minutes=60,
            notes="Lower body strength day. Felt strong on squats.",
        ),
        Workout(
            date=today - timedelta(days=4),
            duration_minutes=45,
            notes="Conditioning circuit, kept rest under 60 seconds.",
        ),
        Workout(
            date=today - timedelta(days=2),
            duration_minutes=75,
            notes="Upper body push/pull with core finisher.",
        ),
        Workout(
            date=today,
            duration_minutes=30,
            notes="Light mobility and balance recovery session.",
        ),
    ]
    db.session.add_all(workouts)
    db.session.commit()
    return workouts


def create_workout_exercises(exercises, workouts):
    """Attach exercises to workouts with reps/sets or a duration."""
    lower_body, conditioning, upper_body, recovery = workouts

    entries = [
        # Lower body strength day
        WorkoutExercise(workout=lower_body, exercise=exercises["Back Squat"], reps=5, sets=5),
        WorkoutExercise(workout=lower_body, exercise=exercises["Deadlift"], reps=3, sets=4),
        WorkoutExercise(workout=lower_body, exercise=exercises["Plank"], duration_seconds=60),
        # Conditioning circuit
        WorkoutExercise(
            workout=conditioning, exercise=exercises["Treadmill Run"], duration_seconds=900
        ),
        WorkoutExercise(
            workout=conditioning, exercise=exercises["Jump Rope"], duration_seconds=300
        ),
        WorkoutExercise(
            workout=conditioning, exercise=exercises["Rowing Machine"], duration_seconds=600
        ),
        WorkoutExercise(workout=conditioning, exercise=exercises["Push Up"], reps=20, sets=3),
        # Upper body push/pull
        WorkoutExercise(workout=upper_body, exercise=exercises["Bench Press"], reps=8, sets=4),
        WorkoutExercise(workout=upper_body, exercise=exercises["Pull Up"], reps=6, sets=4),
        WorkoutExercise(workout=upper_body, exercise=exercises["Push Up"], reps=15, sets=3),
        # A row can carry reps, sets *and* a timed component.
        WorkoutExercise(
            workout=upper_body,
            exercise=exercises["Russian Twist"],
            reps=30,
            sets=3,
            duration_seconds=45,
        ),
        # Recovery session
        WorkoutExercise(
            workout=recovery, exercise=exercises["Hip Flexor Stretch"], duration_seconds=120
        ),
        WorkoutExercise(
            workout=recovery, exercise=exercises["Single Leg Stand"], duration_seconds=90
        ),
        WorkoutExercise(workout=recovery, exercise=exercises["Plank"], duration_seconds=45),
    ]
    db.session.add_all(entries)
    db.session.commit()
    return entries


if __name__ == "__main__":
    with app.app_context():
        print("Clearing existing data...")
        clear_tables()

        print("Seeding exercises...")
        exercises = create_exercises()

        print("Seeding workouts...")
        workouts = create_workouts()

        print("Seeding workout exercises...")
        entries = create_workout_exercises(exercises, workouts)

        print(
            f"Done. Seeded {len(exercises)} exercises, {len(workouts)} workouts "
            f"and {len(entries)} workout exercise entries."
        )
