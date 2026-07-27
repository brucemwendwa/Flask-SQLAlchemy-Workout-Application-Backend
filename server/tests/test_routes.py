"""Tests for the API endpoints: status codes and response bodies."""

from datetime import date, timedelta

import pytest

from models import Exercise, Workout, WorkoutExercise, db

YESTERDAY = date.today() - timedelta(days=1)


@pytest.fixture
def seeded(app):
    """One workout, two exercises, one existing join row."""
    workout = Workout(date=YESTERDAY, duration_minutes=60, notes="Leg day.")
    squat = Exercise(name="Back Squat", category="strength", equipment_needed=True)
    plank = Exercise(name="Plank", category="core", equipment_needed=False)
    db.session.add_all([workout, squat, plank])
    db.session.commit()
    db.session.add(WorkoutExercise(workout=workout, exercise=squat, reps=5, sets=5))
    db.session.commit()
    return {"workout_id": workout.id, "squat_id": squat.id, "plank_id": plank.id}


class TestWorkoutEndpoints:
    def test_index(self, client, seeded):
        response = client.get("/workouts")
        assert response.status_code == 200
        assert len(response.json) == 1
        assert response.json[0]["duration_minutes"] == 60

    def test_show_includes_exercises_and_metrics(self, client, seeded):
        response = client.get(f"/workouts/{seeded['workout_id']}")
        assert response.status_code == 200
        entries = response.json["workout_exercises"]
        assert len(entries) == 1
        assert entries[0]["reps"] == 5
        assert entries[0]["sets"] == 5
        assert entries[0]["exercise"]["name"] == "Back Squat"

    def test_show_missing_returns_404(self, client, app):
        assert client.get("/workouts/999").status_code == 404

    def test_create(self, client, app):
        response = client.post(
            "/workouts",
            json={"date": YESTERDAY.isoformat(), "duration_minutes": 30, "notes": "Easy."},
        )
        assert response.status_code == 201
        assert response.json["id"] is not None
        assert Workout.query.count() == 1

    def test_create_with_invalid_data_returns_400(self, client, app):
        response = client.post("/workouts", json={"duration_minutes": -5})
        assert response.status_code == 400
        assert "date" in response.json["errors"]
        assert Workout.query.count() == 0

    def test_delete_removes_join_rows_but_keeps_exercises(self, client, seeded):
        response = client.delete(f"/workouts/{seeded['workout_id']}")
        assert response.status_code == 200
        assert Workout.query.count() == 0
        assert WorkoutExercise.query.count() == 0
        assert Exercise.query.count() == 2

    def test_delete_missing_returns_404(self, client, app):
        assert client.delete("/workouts/999").status_code == 404


class TestExerciseEndpoints:
    def test_index(self, client, seeded):
        response = client.get("/exercises")
        assert response.status_code == 200
        assert [e["name"] for e in response.json] == ["Back Squat", "Plank"]

    def test_show_includes_workouts(self, client, seeded):
        response = client.get(f"/exercises/{seeded['squat_id']}")
        assert response.status_code == 200
        assert len(response.json["workouts"]) == 1
        assert response.json["workout_exercises"][0]["workout"]["duration_minutes"] == 60

    def test_show_missing_returns_404(self, client, app):
        assert client.get("/exercises/999").status_code == 404

    def test_create(self, client, app):
        response = client.post(
            "/exercises",
            json={"name": "Deadlift", "category": "strength", "equipment_needed": True},
        )
        assert response.status_code == 201
        assert response.json["name"] == "Deadlift"

    def test_create_with_invalid_category_returns_400(self, client, app):
        response = client.post("/exercises", json={"name": "Napping", "category": "sleeping"})
        assert response.status_code == 400
        assert "category" in response.json["errors"]

    def test_create_duplicate_name_returns_400(self, client, seeded):
        response = client.post("/exercises", json={"name": "Plank", "category": "core"})
        assert response.status_code == 400

    def test_delete_removes_join_rows_but_keeps_workouts(self, client, seeded):
        response = client.delete(f"/exercises/{seeded['squat_id']}")
        assert response.status_code == 200
        assert Exercise.query.count() == 1
        assert WorkoutExercise.query.count() == 0
        assert Workout.query.count() == 1

    def test_delete_missing_returns_404(self, client, app):
        assert client.delete("/exercises/999").status_code == 404


class TestAddExerciseToWorkout:
    def _url(self, seeded, exercise_key="plank_id"):
        return (
            f"/workouts/{seeded['workout_id']}/exercises/"
            f"{seeded[exercise_key]}/workout_exercises"
        )

    def test_adds_with_duration(self, client, seeded):
        response = client.post(self._url(seeded), json={"duration_seconds": 60})
        assert response.status_code == 201
        assert response.json["duration_seconds"] == 60
        assert response.json["exercise"]["name"] == "Plank"
        assert WorkoutExercise.query.count() == 2

    def test_adds_with_reps_and_sets(self, client, seeded):
        response = client.post(self._url(seeded), json={"reps": 12, "sets": 4})
        assert response.status_code == 201
        assert (response.json["reps"], response.json["sets"]) == (12, 4)

    def test_missing_metrics_returns_400(self, client, seeded):
        response = client.post(self._url(seeded), json={})
        assert response.status_code == 400
        assert WorkoutExercise.query.count() == 1

    def test_reps_without_sets_returns_400(self, client, seeded):
        response = client.post(self._url(seeded), json={"reps": 10})
        assert response.status_code == 400

    def test_duplicate_pairing_returns_400(self, client, seeded):
        response = client.post(
            self._url(seeded, "squat_id"), json={"reps": 10, "sets": 3}
        )
        assert response.status_code == 400

    def test_unknown_workout_returns_404(self, client, seeded):
        response = client.post(
            f"/workouts/999/exercises/{seeded['plank_id']}/workout_exercises",
            json={"duration_seconds": 60},
        )
        assert response.status_code == 404

    def test_unknown_exercise_returns_404(self, client, seeded):
        response = client.post(
            f"/workouts/{seeded['workout_id']}/exercises/999/workout_exercises",
            json={"duration_seconds": 60},
        )
        assert response.status_code == 404
