# Workout Tracker API

A Flask + SQLAlchemy + Marshmallow backend for a workout tracking application used by
personal trainers.

## Description

Trainers build a library of reusable **exercises** (Back Squat, Jump Rope, Plank, …) and
log **workouts** (a dated training session). Exercises are attached to workouts through a
**workout_exercises** join table, which records *how* the exercise was performed in that
particular session — either `reps` and `sets`, or a `duration_seconds`, or both.

Because the metrics live on the join row, the same exercise can be reused across any
number of workouts without duplicating it.

Data integrity is enforced at three levels:

| Level | Where | Examples |
| --- | --- | --- |
| Table constraints | `__table_args__` in [server/models.py](server/models.py) | unique exercise names, `duration_minutes BETWEEN 1 AND 480`, a join row must have reps+sets or a duration |
| Model validations | `@validates` hooks in [server/models.py](server/models.py) | category must be a known value, a workout cannot be dated in the future, metrics must be positive integers |
| Schema validations | [server/schemas.py](server/schemas.py) | required fields, `Length`/`Range`/`OneOf` rules, a cross-field `@validates_schema` check on the metrics |

## Project structure

```
.
├── Pipfile                 # dependencies
├── README.md
└── server/
    ├── app.py              # app configuration, extensions, blueprint registration
    ├── models.py           # SQLAlchemy models, table constraints, model validations
    ├── schemas.py          # Marshmallow schemas for (de)serialization + validation
    ├── errors.py           # centralised JSON error handlers
    ├── seed.py             # resets and repopulates the database
    ├── migrations/         # Alembic migration history
    ├── routes/
    │   ├── __init__.py     # blueprint registration helper
    │   ├── workouts.py     # /workouts endpoints
    │   ├── exercises.py    # /exercises endpoints
    │   └── workout_exercises.py  # adding an exercise to a workout
    └── tests/              # pytest suite (models, schemas, endpoints)
```

## Installation

Requires Python 3.8.13+ and [pipenv](https://pipenv.pypa.io/).

```bash
# 1. Install dependencies and enter the virtual environment
pipenv install
pipenv shell

# 2. Move into the application directory
cd server

# 3. Create the database from the migration history
flask db upgrade head

# 4. Populate it with example data
python seed.py
```

If you would rather build the migration history from scratch, delete `server/migrations/`
and run:

```bash
flask db init
flask db migrate -m "create exercises, workouts and workout_exercises tables"
flask db upgrade head
```

## Running the app

From the `server/` directory:

```bash
flask run --port=5555
```

or

```bash
python app.py
```

The API is then available at `http://localhost:5555`.

### Running the tests

From the repository root:

```bash
pipenv run pytest
```

## Endpoints

All responses are JSON. Errors come back as `{"errors": ...}` with an appropriate status
code (`400` for validation failures, `404` for missing records).

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Landing route listing the available endpoints |
| `GET` | `/workouts` | List all workouts, most recent first |
| `GET` | `/workouts/<id>` | Show one workout with its exercises **and** the reps/sets/duration for each |
| `POST` | `/workouts` | Create a workout |
| `DELETE` | `/workouts/<id>` | Delete a workout and its `workout_exercises` rows (exercises are kept) |
| `GET` | `/exercises` | List all exercises, alphabetically |
| `GET` | `/exercises/<id>` | Show one exercise with every workout it has been used in |
| `POST` | `/exercises` | Create an exercise |
| `DELETE` | `/exercises/<id>` | Delete an exercise and its `workout_exercises` rows (workouts are kept) |
| `POST` | `/workouts/<workout_id>/exercises/<exercise_id>/workout_exercises` | Add an exercise to a workout with its reps/sets/duration |

### `GET /workouts`

```json
[
  {
    "id": 4,
    "date": "2026-07-27",
    "duration_minutes": 30,
    "notes": "Light mobility and balance recovery session."
  }
]
```

### `GET /workouts/<id>`

Includes the join-table metrics alongside each exercise.

```json
{
  "id": 1,
  "date": "2026-07-21",
  "duration_minutes": 60,
  "notes": "Lower body strength day. Felt strong on squats.",
  "workout_exercises": [
    {
      "id": 1,
      "reps": 5,
      "sets": 5,
      "duration_seconds": null,
      "exercise": {
        "id": 1,
        "name": "Back Squat",
        "category": "strength",
        "equipment_needed": true
      }
    }
  ],
  "exercises": [
    { "id": 1, "name": "Back Squat", "category": "strength", "equipment_needed": true }
  ]
}
```

### `POST /workouts`

Request body:

```json
{
  "date": "2026-07-25",
  "duration_minutes": 45,
  "notes": "Tempo intervals."
}
```

* `date` — **required**, `YYYY-MM-DD`, cannot be in the future.
* `duration_minutes` — **required**, integer between 1 and 480.
* `notes` — optional, up to 500 characters, cannot be blank if provided.

Returns `201` with the created workout, or `400` with per-field messages.

### `GET /exercises/<id>`

```json
{
  "id": 1,
  "name": "Back Squat",
  "category": "strength",
  "equipment_needed": true,
  "workout_exercises": [
    {
      "id": 1,
      "reps": 5,
      "sets": 5,
      "duration_seconds": null,
      "workout": {
        "id": 1,
        "date": "2026-07-21",
        "duration_minutes": 60,
        "notes": "Lower body strength day. Felt strong on squats."
      }
    }
  ],
  "workouts": [
    {
      "id": 1,
      "date": "2026-07-21",
      "duration_minutes": 60,
      "notes": "Lower body strength day. Felt strong on squats."
    }
  ]
}
```

### `POST /exercises`

Request body:

```json
{
  "name": "Deadlift",
  "category": "strength",
  "equipment_needed": true
}
```

* `name` — **required**, 2–50 characters, must be unique.
* `category` — **required**, one of `strength`, `cardio`, `mobility`, `balance`, `core`.
* `equipment_needed` — optional boolean, defaults to `false`.

Returns `201` with the created exercise, or `400` with per-field messages.

### `POST /workouts/<workout_id>/exercises/<exercise_id>/workout_exercises`

The workout and exercise ids come from the URL; the body carries only the metrics.

```json
{ "reps": 10, "sets": 3 }
```

or

```json
{ "duration_seconds": 300 }
```

* Requires **either** `reps` and `sets` together, **or** `duration_seconds` (or all three).
* Every supplied metric must be a positive integer.
* An exercise may only be attached to a given workout once.

Returns `201` with the created entry and its exercise inlined, `400` if the metrics are
missing/invalid or the pairing already exists, or `404` if the workout or exercise does
not exist.

### `DELETE /workouts/<id>` and `DELETE /exercises/<id>`

```json
{ "message": "Workout 1 and its exercise entries were deleted." }
```

Deleting either side removes the associated `workout_exercises` rows via an ORM cascade,
but never deletes records on the other side of the relationship.

## Data model

```
Exercise                 WorkoutExercise                 Workout
--------                 ---------------                 -------
id                       id                              id
name (unique)            workout_id  -> workouts.id      date
category                 exercise_id -> exercises.id     duration_minutes
equipment_needed         reps                            notes
                         sets
                         duration_seconds
```

* A `WorkoutExercise` belongs to a `Workout` and belongs to an `Exercise`.
* A `Workout` has many `WorkoutExercises`; an `Exercise` has many `WorkoutExercises`.
* A `Workout` has many `Exercises` through `WorkoutExercises`, and vice versa — exposed as
  `workout.exercises` and `exercise.workouts` via SQLAlchemy association proxies.
