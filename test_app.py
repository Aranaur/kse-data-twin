import numpy as np
import pytest

import app as server
from room import TOPICS, Room
from twin import map_points, nearest, shared_topics

N = len(TOPICS)


def test_nearest_picks_same_taste_and_breaks_ties_by_distance():
    ratings = np.array([[5, 0, 0], [1, 0, 0], [4, 0, 0], [0, 5, 5]], dtype=float)
    twins, sims = nearest(ratings)
    assert twins[0] == 2  # 1 і 2 мають однаковий косинус, але 2 ближче
    assert sims[0] == pytest.approx(1.0)
    assert twins[3] != 3


def test_shared_topics_needs_both_to_like_it():
    a, b = np.array([5, 5, 0]), np.array([4, 1, 5])
    assert shared_topics(a, b, ["x", "y", "z"]) == ["x"]


def test_map_points_handles_identical_people_and_stays_in_bounds():
    assert not map_points(np.ones((3, 4))).any()
    points = map_points(np.random.default_rng(1).integers(0, 6, (30, 8)).astype(float))
    assert np.abs(points).max() <= 1 and np.isfinite(points).all()


def test_twin_stays_hidden_until_reveal():
    room = Room()
    room.answer("a", "Аня", [5] + [0] * (N - 1))
    room.answer("b", "Богдан", [4] + [0] * (N - 1))
    assert room.me("a")["status"] == "waiting"
    room.revealed = True
    result = room.me("a")
    assert result["twin"] == "Богдан" and result["similarity"] == 100


def test_public_map_and_svg_never_contain_names():
    room = Room()
    room.answer("a", "Аня", [5] + [0] * (N - 1))
    room.answer("b", "Богдан", [0, 5] + [0] * (N - 2))
    room.revealed = True
    data = room.map()
    assert "Аня" not in str(data) and "Богдан" not in server.svg(data)
    assert server.svg(data).count("<circle") == 2 and server.svg(data).count("<line") == 2


@pytest.mark.parametrize("ratings", [[0] * N, [6] * N, [1] * (N - 1)])
def test_bad_ratings_are_rejected(ratings):
    room = Room()
    with pytest.raises(ValueError):
        room.answer("a", "Аня", ratings)
    assert not room.people


def test_blank_name_is_rejected_and_long_name_is_cut():
    room = Room()
    with pytest.raises(ValueError):
        room.answer("a", "   ", [1] * N)
    room.answer("a", "я" * 50, [1] * N)
    assert len(room.people["a"]["name"]) == 24


def test_same_person_can_change_answer():
    room = Room()
    room.answer("a", "Аня", [1] * N)
    room.answer("a", "Аня", [2] * N)
    assert len(room.people) == 1 and room.people["a"]["ratings"] == [2] * N


def test_reset_clears_everything():
    room = Room()
    room.answer("a", "Аня", [5] * N)
    room.revealed = True
    room.reset()
    assert room.map() == {"count": 0, "points": [], "links": []} and not room.revealed


def test_admin_key_checks_hash_only():
    assert not server.is_admin("")
    assert not server.is_admin("wrong")
