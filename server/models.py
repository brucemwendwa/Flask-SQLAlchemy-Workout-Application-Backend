"""SQLAlchemy models for the workout tracking API.

Three tables are defined here:

* ``exercises``          - reusable exercises a trainer can drop into any workout
* ``workouts``           - a single training session
* ``workout_exercises``  - the join table carrying the sets/reps/duration that
  describe *how* an exercise was performed inside one specific workout

Data integrity is enforced at two levels:

1. **Table constraints** (``CheckConstraint`` / ``UniqueConstraint`` / ``nullable``)
   live in each model's ``__table_args__`` and are written into the SQLite schema
   by the migration, so bad rows are rejected even by raw SQL.
2. **Model validations** (``@validates``) run in Python on attribute assignment,
   so they fail fast with a readable message before a flush is ever attempted.
"""

import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import validates

db = SQLAlchemy()

# Allowed values for Exercise.category. Kept here so the model validation, the
# table constraint and the Marshmallow schema all share a single source of truth.
EXERCISE_CATEGORIES = (
    "strength",
    "cardio",
    "mobility",
    "balance",
    "core",
)


class Exercise(db.Model):
    """A reusable movement (e.g. "Back Squat") that can appear in many workouts."""

    __tablename__ = "exercises"

    # --- Table constraints -------------------------------------------------
    __table_args__ = (
        # 1. An exercise name must be unique so trainers don't create duplicates.
        UniqueConstraint("name", name="uq_exercises_name"),
        # 2. Names must be a sensible length (blank/whitespace names are rejected).
        CheckConstraint(
            "length(trim(name)) BETWEEN 2 AND 50", name="ck_exercises_name_length"
        ),
        # 3. Category must be one of the supported values.
        CheckConstraint(
            "category IN ('strength', 'cardio', 'mobility', 'balance', 'core')",
            name="ck_exercises_category_valid",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    equipment_needed = db.Column(db.Boolean, nullable=False, default=False)

    # --- Relationships -----------------------------------------------------
    # An Exercise has many WorkoutExercises. Deleting the exercise removes its
    # join rows so no workout is left pointing at a missing exercise.
    workout_exercises = db.relationship(
        "WorkoutExercise",
        back_populates="exercise",
        cascade="all, delete-orphan",
    )
    # An Exercise has many Workouts *through* WorkoutExercises.
    workouts = association_proxy("workout_exercises", "workout")

    # --- Model validations -------------------------------------------------
    @validates("name")
    def validate_name(self, key, value):
        """Require a non-blank name of 2-50 characters."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Exercise name is required.")
        cleaned = value.strip()
        if not 2 <= len(cleaned) <= 50:
            raise ValueError("Exercise name must be between 2 and 50 characters.")
        return cleaned

    @validates("category")
    def validate_category(self, key, value):
        """Restrict categories to the supported vocabulary."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Exercise category is required.")
        cleaned = value.strip().lower()
        if cleaned not in EXERCISE_CATEGORIES:
            raise ValueError(
                f"Category must be one of: {', '.join(EXERCISE_CATEGORIES)}."
            )
        return cleaned

    @validates("equipment_needed")
    def validate_equipment_needed(self, key, value):
        """``equipment_needed`` is a required boolean flag, not a truthy string."""
        if not isinstance(value, bool):
            raise ValueError("equipment_needed must be true or false.")
        return value

    def __repr__(self):
        return f"<Exercise {self.id}: {self.name} ({self.category})>"


class Workout(db.Model):
    """A single training session on a given date."""

    __tablename__ = "workouts"

    # --- Table constraints -------------------------------------------------
    __table_args__ = (
        # 1. A session has to have taken some time, and 8 hours is a sane ceiling.
        CheckConstraint(
            "duration_minutes > 0 AND duration_minutes <= 480",
            name="ck_workouts_duration_range",
        ),
        # 2. Notes are optional, but if present they must not be blank padding.
        CheckConstraint(
            "notes IS NULL OR length(trim(notes)) > 0", name="ck_workouts_notes_present"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)

    # --- Relationships -----------------------------------------------------
    # A Workout has many WorkoutExercises; deleting it deletes those join rows.
    workout_exercises = db.relationship(
        "WorkoutExercise",
        back_populates="workout",
        cascade="all, delete-orphan",
    )
    # A Workout has many Exercises *through* WorkoutExercises.
    exercises = association_proxy("workout_exercises", "exercise")

    # --- Model validations -------------------------------------------------
    @validates("date")
    def validate_date(self, key, value):
        """A workout must have a real date and cannot be logged in the future.

        ``datetime`` is imported as a module because the ``date`` column below
        would otherwise shadow a bare ``date`` import inside the class body.
        """
        if not isinstance(value, datetime.date):
            raise ValueError("Workout date is required and must be a date.")
        if value > datetime.date.today():
            raise ValueError("Workout date cannot be in the future.")
        return value

    @validates("duration_minutes")
    def validate_duration_minutes(self, key, value):
        """Duration must be a positive whole number of minutes (max 8 hours)."""
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("duration_minutes must be an integer.")
        if not 1 <= value <= 480:
            raise ValueError("duration_minutes must be between 1 and 480.")
        return value

    @validates("notes")
    def validate_notes(self, key, value):
        """Notes are optional, but a supplied value must contain real text."""
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Notes cannot be blank; omit the field instead.")
        return value.strip()

    def __repr__(self):
        return f"<Workout {self.id}: {self.date} ({self.duration_minutes} min)>"


class WorkoutExercise(db.Model):
    """Join record: one exercise as performed inside one workout.

    Carries the performance metrics, which are either strength-style
    (``reps`` + ``sets``) or time-based (``duration_seconds``).
    """

    __tablename__ = "workout_exercises"

    # --- Table constraints -------------------------------------------------
    __table_args__ = (
        # 1. The same exercise may only be attached to a workout once; the
        #    reps/sets/duration columns already describe the whole prescription.
        UniqueConstraint(
            "workout_id", "exercise_id", name="uq_workout_exercises_workout_exercise"
        ),
        # 2. Metrics, when supplied, must be positive.
        CheckConstraint("reps IS NULL OR reps > 0", name="ck_workout_exercises_reps"),
        CheckConstraint("sets IS NULL OR sets > 0", name="ck_workout_exercises_sets"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0",
            name="ck_workout_exercises_duration",
        ),
        # 3. Every row must describe the work done *somehow*: either reps and
        #    sets together, or a duration.
        CheckConstraint(
            "(reps IS NOT NULL AND sets IS NOT NULL) OR duration_seconds IS NOT NULL",
            name="ck_workout_exercises_metrics_present",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(
        db.Integer, db.ForeignKey("workouts.id"), nullable=False
    )
    exercise_id = db.Column(
        db.Integer, db.ForeignKey("exercises.id"), nullable=False
    )
    reps = db.Column(db.Integer)
    sets = db.Column(db.Integer)
    duration_seconds = db.Column(db.Integer)

    # --- Relationships -----------------------------------------------------
    # A WorkoutExercise belongs to a Workout and belongs to an Exercise.
    workout = db.relationship("Workout", back_populates="workout_exercises")
    exercise = db.relationship("Exercise", back_populates="workout_exercises")

    # --- Model validations -------------------------------------------------
    @validates("reps", "sets", "duration_seconds")
    def validate_positive_metric(self, key, value):
        """Each metric is optional, but a supplied value must be a positive int."""
        if value is None:
            return None
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{key} must be an integer.")
        if value < 1:
            raise ValueError(f"{key} must be greater than 0.")
        return value

    def validate_metrics_present(self):
        """Require either a reps/sets pair or a duration.

        This spans several columns, so it cannot live in a single-attribute
        ``@validates`` hook - the route layer calls it before committing, and the
        matching ``CHECK`` constraint backstops it at the database level.
        """
        has_strength_metrics = self.reps is not None and self.sets is not None
        has_time_metric = self.duration_seconds is not None
        if not (has_strength_metrics or has_time_metric):
            raise ValueError(
                "Provide both reps and sets, or duration_seconds, for this exercise."
            )

    def __repr__(self):
        return (
            f"<WorkoutExercise {self.id}: workout {self.workout_id} / "
            f"exercise {self.exercise_id}>"
        )
