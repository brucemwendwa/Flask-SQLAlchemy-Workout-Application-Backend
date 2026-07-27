"""Tests for model validations, relationships and table constraints."""

from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from models import Exercise, Workout, WorkoutExercise, db

YESTERDAY = date.today() - timedelta(days=1)


def make_exercise(**overrides):
    defaults = {"name": "Back Squat", "category": "strength", "equipment_needed": True}
    return Exercise(**{**defaults, **overrides})


def make_workout(**overrides):
    defaults = {"date": YESTERDAY, "duration_minutes": 60, "notes": "Leg day."}
    return Workout(**{**defaults, **overrides})


# --------------------------------------------------------------------------
# Model validations
# --------------------------------------------------------------------------


class TestExerciseValidations:
    def test_rejects_blank_name(self, app):
        with pytest.raises(ValueError, match="name is required"):
            make_exercise(name="   ")

    def test_rejects_short_name(self, app):
        with pytest.raises(ValueError, match="between 2 and 50"):
            make_exercise(name="A")

    def test_rejects_unknown_category(self, app):
        with pytest.raises(ValueError, match="Category must be one of"):
            make_exercise(category="interpretive dance")

    def test_rejects_non_boolean_equipment_flag(self, app):
        with pytest.raises(ValueError, match="true or false"):
            make_exercise(equipment_needed="yes")

    def test_normalises_valid_input(self, app):
        exercise = make_exercise(name="  Front Squat  ", category="STRENGTH")
        assert exercise.name == "Front Squat"
        assert exercise.category == "strength"


class TestWorkoutValidations:
    def test_rejects_future_date(self, app):
        with pytest.raises(ValueError, match="cannot be in the future"):
            make_workout(date=date.today() + timedelta(days=1))

    def test_rejects_non_date(self, app):
        with pytest.raises(ValueError, match="must be a date"):
            make_workout(date="2026-01-01")

    def test_rejects_zero_duration(self, app):
        with pytest.raises(ValueError, match="between 1 and 480"):
            make_workout(duration_minutes=0)

    def test_rejects_blank_notes(self, app):
        with pytest.raises(ValueError, match="cannot be blank"):
            make_workout(notes="   ")

    def test_allows_omitted_notes(self, app):
        assert make_workout(notes=None).notes is None


class TestWorkoutExerciseValidations:
    def test_rejects_zero_reps(self, app):
        with pytest.raises(ValueError, match="greater than 0"):
            WorkoutExercise(reps=0, sets=3)

    def test_rejects_non_integer_duration(self, app):
        with pytest.raises(ValueError, match="must be an integer"):
            WorkoutExercise(duration_seconds="sixty")

    def test_requires_reps_and_sets_or_duration(self, app):
        entry = WorkoutExercise(reps=10)
        with pytest.raises(ValueError, match="Provide both reps and sets"):
            entry.validate_metrics_present()

    def test_accepts_duration_only(self, app):
        entry = WorkoutExercise(duration_seconds=60)
        entry.validate_metrics_present()  # does not raise


# --------------------------------------------------------------------------
# Table constraints (exercised with raw SQL so they are not shadowed by the
# Python-level model validations)
# --------------------------------------------------------------------------


class TestTableConstraints:
    def test_exercise_name_is_unique(self, app):
        db.session.add(make_exercise())
        db.session.commit()
        db.session.add(make_exercise(category="cardio"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_exercise_name_length_check(self, app):
        with pytest.raises(IntegrityError):
            db.session.execute(
                text(
                    "INSERT INTO exercises (name, category, equipment_needed) "
                    "VALUES ('A', 'strength', 0)"
                )
            )
        db.session.rollback()

    def test_exercise_category_check(self, app):
        with pytest.raises(IntegrityError):
            db.session.execute(
                text(
                    "INSERT INTO exercises (name, category, equipment_needed) "
                    "VALUES ('Nap', 'sleeping', 0)"
                )
            )
        db.session.rollback()

    def test_workout_duration_check(self, app):
        with pytest.raises(IntegrityError):
            db.session.execute(
                text(
                    "INSERT INTO workouts (date, duration_minutes) "
                    "VALUES ('2026-01-01', 0)"
                )
            )
        db.session.rollback()

    def test_workout_exercise_requires_metrics(self, app):
        workout = make_workout()
        exercise = make_exercise()
        db.session.add_all([workout, exercise])
        db.session.commit()

        with pytest.raises(IntegrityError):
            db.session.execute(
                text(
                    "INSERT INTO workout_exercises (workout_id, exercise_id) "
                    "VALUES (:w, :e)"
                ),
                {"w": workout.id, "e": exercise.id},
            )
        db.session.rollback()

    def test_exercise_cannot_repeat_within_a_workout(self, app):
        workout = make_workout()
        exercise = make_exercise()
        db.session.add_all([workout, exercise])
        db.session.commit()

        db.session.add(
            WorkoutExercise(workout=workout, exercise=exercise, reps=10, sets=3)
        )
        db.session.commit()
        db.session.add(
            WorkoutExercise(workout=workout, exercise=exercise, reps=8, sets=4)
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


# --------------------------------------------------------------------------
# Relationships
# --------------------------------------------------------------------------


class TestRelationships:
    @pytest.fixture
    def seeded(self, app):
        workout = make_workout()
        squat = make_exercise(name="Back Squat")
        plank = make_exercise(name="Plank", category="core", equipment_needed=False)
        db.session.add_all([workout, squat, plank])
        db.session.commit()
        db.session.add_all(
            [
                WorkoutExercise(workout=workout, exercise=squat, reps=5, sets=5),
                WorkoutExercise(workout=workout, exercise=plank, duration_seconds=60),
            ]
        )
        db.session.commit()
        return workout, squat, plank

    def test_workout_has_many_workout_exercises(self, seeded):
        workout, _, _ = seeded
        assert len(workout.workout_exercises) == 2

    def test_workout_has_many_exercises_through_join(self, seeded):
        workout, squat, plank = seeded
        assert {exercise.name for exercise in workout.exercises} == {
            squat.name,
            plank.name,
        }

    def test_exercise_has_many_workouts_through_join(self, seeded):
        workout, squat, _ = seeded
        assert [w.id for w in squat.workouts] == [workout.id]

    def test_workout_exercise_belongs_to_both_sides(self, seeded):
        workout, squat, _ = seeded
        entry = workout.workout_exercises[0]
        assert entry.workout is workout
        assert entry.exercise in (squat, workout.workout_exercises[1].exercise)

    def test_deleting_workout_cascades_to_join_rows_only(self, seeded):
        workout, _, _ = seeded
        db.session.delete(workout)
        db.session.commit()
        assert WorkoutExercise.query.count() == 0
        assert Exercise.query.count() == 2

    def test_deleting_exercise_cascades_to_join_rows_only(self, seeded):
        _, squat, _ = seeded
        db.session.delete(squat)
        db.session.commit()
        assert WorkoutExercise.query.count() == 1
        assert Workout.query.count() == 1
