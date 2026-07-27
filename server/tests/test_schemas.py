"""Tests for the Marshmallow schema validations."""

from datetime import date, timedelta

import pytest
from marshmallow import ValidationError

from schemas import exercise_schema, workout_exercise_schema, workout_schema

YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


class TestExerciseSchema:
    def test_requires_name_and_category(self):
        with pytest.raises(ValidationError) as error:
            exercise_schema.load({})
        assert set(error.value.messages) == {"name", "category"}

    def test_rejects_short_name(self):
        with pytest.raises(ValidationError) as error:
            exercise_schema.load({"name": "A", "category": "strength"})
        assert "name" in error.value.messages

    def test_rejects_blank_name(self):
        with pytest.raises(ValidationError) as error:
            exercise_schema.load({"name": "     ", "category": "strength"})
        assert "name" in error.value.messages

    def test_rejects_unknown_category(self):
        with pytest.raises(ValidationError) as error:
            exercise_schema.load({"name": "Napping", "category": "sleeping"})
        assert "category" in error.value.messages

    def test_defaults_equipment_needed_to_false(self):
        exercise = exercise_schema.load({"name": "Push Up", "category": "strength"})
        assert exercise.equipment_needed is False


class TestWorkoutSchema:
    def test_requires_date_and_duration(self):
        with pytest.raises(ValidationError) as error:
            workout_schema.load({})
        assert set(error.value.messages) == {"date", "duration_minutes"}

    def test_rejects_future_date(self):
        future = (date.today() + timedelta(days=1)).isoformat()
        with pytest.raises(ValidationError) as error:
            workout_schema.load({"date": future, "duration_minutes": 60})
        assert "date" in error.value.messages

    def test_rejects_out_of_range_duration(self):
        with pytest.raises(ValidationError) as error:
            workout_schema.load({"date": YESTERDAY, "duration_minutes": 900})
        assert "duration_minutes" in error.value.messages

    def test_rejects_malformed_date(self):
        with pytest.raises(ValidationError) as error:
            workout_schema.load({"date": "not-a-date", "duration_minutes": 60})
        assert "date" in error.value.messages

    def test_accepts_valid_payload(self):
        workout = workout_schema.load(
            {"date": YESTERDAY, "duration_minutes": 45, "notes": "Good session."}
        )
        assert workout.duration_minutes == 45


class TestWorkoutExerciseSchema:
    def test_rejects_empty_body(self):
        with pytest.raises(ValidationError, match="Provide both reps and sets"):
            workout_exercise_schema.load({})

    def test_rejects_reps_without_sets(self):
        with pytest.raises(ValidationError, match="Provide both reps and sets"):
            workout_exercise_schema.load({"reps": 10})

    def test_rejects_zero_sets(self):
        with pytest.raises(ValidationError) as error:
            workout_exercise_schema.load({"reps": 10, "sets": 0})
        assert "sets" in error.value.messages

    def test_accepts_reps_and_sets(self):
        entry = workout_exercise_schema.load({"reps": 10, "sets": 3})
        assert (entry.reps, entry.sets) == (10, 3)

    def test_accepts_duration_only(self):
        entry = workout_exercise_schema.load({"duration_seconds": 90})
        assert entry.duration_seconds == 90
