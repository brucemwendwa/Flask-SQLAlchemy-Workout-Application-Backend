"""Marshmallow schemas for serialization, deserialization and request validation.

Each model gets a "summary" schema used when it appears nested inside another
payload, and a fuller schema used for its own endpoints. Splitting them this way
keeps the nested relationships one level deep, which avoids the infinite
recursion you would otherwise get from Workout -> Exercise -> Workout.
"""

import datetime

from marshmallow import (
    Schema,
    ValidationError,
    fields,
    post_load,
    validate,
    validates,
    validates_schema,
)

from models import EXERCISE_CATEGORIES, Exercise, Workout, WorkoutExercise


class ExerciseSchema(Schema):
    """Load/dump schema for a standalone Exercise."""

    id = fields.Integer(dump_only=True)
    name = fields.String(
        required=True,
        validate=validate.Length(
            min=2, max=50, error="Name must be between 2 and 50 characters."
        ),
    )
    category = fields.String(
        required=True,
        validate=validate.OneOf(
            EXERCISE_CATEGORIES,
            error="Category must be one of: {choices}.",
        ),
    )
    equipment_needed = fields.Boolean(load_default=False)

    @validates("name")
    def validate_name_not_blank(self, value):
        """Reject names made only of whitespace, which pass a raw Length check."""
        if not value.strip():
            raise ValidationError("Name cannot be blank.")

    @post_load
    def make_exercise(self, data, **kwargs):
        """Turn validated input into an unsaved ``Exercise`` instance."""
        return Exercise(**data)


class ExerciseSummarySchema(Schema):
    """Trimmed Exercise used when nested inside a workout payload."""

    id = fields.Integer()
    name = fields.String()
    category = fields.String()
    equipment_needed = fields.Boolean()


class WorkoutSchema(Schema):
    """Load/dump schema for a standalone Workout."""

    id = fields.Integer(dump_only=True)
    date = fields.Date(required=True)
    duration_minutes = fields.Integer(
        required=True,
        validate=validate.Range(
            min=1, max=480, error="Duration must be between 1 and 480 minutes."
        ),
    )
    notes = fields.String(
        allow_none=True,
        load_default=None,
        validate=validate.Length(max=500, error="Notes cannot exceed 500 characters."),
    )

    @validates("date")
    def validate_date_not_future(self, value):
        """A workout can only be logged once it has happened."""
        if value > datetime.date.today():
            raise ValidationError("Workout date cannot be in the future.")

    @validates("notes")
    def validate_notes_not_blank(self, value):
        """Catch whitespace-only notes here so the error is reported per-field."""
        if value is not None and not value.strip():
            raise ValidationError("Notes cannot be blank; omit the field instead.")

    @post_load
    def make_workout(self, data, **kwargs):
        """Turn validated input into an unsaved ``Workout`` instance."""
        return Workout(**data)


class WorkoutSummarySchema(Schema):
    """Trimmed Workout used when nested inside an exercise payload."""

    id = fields.Integer()
    date = fields.Date()
    duration_minutes = fields.Integer()
    notes = fields.String()


class WorkoutExerciseSchema(Schema):
    """Load/dump schema for the join record's performance metrics.

    ``workout_id`` and ``exercise_id`` come from the URL rather than the body,
    so they are dump-only here.
    """

    id = fields.Integer(dump_only=True)
    workout_id = fields.Integer(dump_only=True)
    exercise_id = fields.Integer(dump_only=True)
    reps = fields.Integer(
        allow_none=True,
        load_default=None,
        validate=validate.Range(min=1, max=1000, error="Reps must be 1 or greater."),
    )
    sets = fields.Integer(
        allow_none=True,
        load_default=None,
        validate=validate.Range(min=1, max=100, error="Sets must be 1 or greater."),
    )
    duration_seconds = fields.Integer(
        allow_none=True,
        load_default=None,
        validate=validate.Range(
            min=1, max=36000, error="Duration must be 1 second or greater."
        ),
    )

    @validates_schema
    def validate_metrics_present(self, data, **kwargs):
        """Require a reps/sets pair or a duration - a row with neither is meaningless."""
        has_strength_metrics = data.get("reps") is not None and data.get("sets") is not None
        has_time_metric = data.get("duration_seconds") is not None
        if not (has_strength_metrics or has_time_metric):
            raise ValidationError(
                "Provide both reps and sets, or duration_seconds.",
                field_name="_schema",
            )

    @post_load
    def make_workout_exercise(self, data, **kwargs):
        """Turn validated input into an unsaved ``WorkoutExercise`` instance."""
        return WorkoutExercise(**data)


class WorkoutExerciseDetailSchema(Schema):
    """A join row rendered with its exercise inlined (used on GET /workouts/<id>)."""

    id = fields.Integer()
    reps = fields.Integer()
    sets = fields.Integer()
    duration_seconds = fields.Integer()
    exercise = fields.Nested(ExerciseSummarySchema)


class WorkoutExerciseWithWorkoutSchema(Schema):
    """A join row rendered with its workout inlined (used on GET /exercises/<id>)."""

    id = fields.Integer()
    reps = fields.Integer()
    sets = fields.Integer()
    duration_seconds = fields.Integer()
    workout = fields.Nested(WorkoutSummarySchema)


class WorkoutDetailSchema(WorkoutSchema):
    """A workout plus its exercises and the reps/sets/duration for each."""

    workout_exercises = fields.List(
        fields.Nested(WorkoutExerciseDetailSchema), dump_only=True
    )
    exercises = fields.List(fields.Nested(ExerciseSummarySchema), dump_only=True)


class ExerciseDetailSchema(ExerciseSchema):
    """An exercise plus every workout it has been used in."""

    workout_exercises = fields.List(
        fields.Nested(WorkoutExerciseWithWorkoutSchema), dump_only=True
    )
    workouts = fields.List(fields.Nested(WorkoutSummarySchema), dump_only=True)


# Reusable schema instances. Marshmallow schemas are stateless once configured,
# so building them once at import time keeps the route handlers tidy.
exercise_schema = ExerciseSchema()
exercises_schema = ExerciseSchema(many=True)
exercise_detail_schema = ExerciseDetailSchema()

workout_schema = WorkoutSchema()
workouts_schema = WorkoutSchema(many=True)
workout_detail_schema = WorkoutDetailSchema()

workout_exercise_schema = WorkoutExerciseSchema()
