"""Пошук найближчого за смаками учасника. Без вебу, щоб логіку можна було тестувати."""

from __future__ import annotations

import numpy as np


def cosine_matrix(ratings: np.ndarray) -> np.ndarray:
    """Косинусна подібність кожного рядка з кожним. Рядки не можуть бути нульовими."""
    unit = ratings / np.linalg.norm(ratings, axis=1, keepdims=True)
    return unit @ unit.T


def nearest(ratings: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Для кожного рядка повертає індекс найближчого сусіда і його подібність.

    За однакової подібності перемагає менша евклідова відстань, потім менший індекс.
    Потрібно щонайменше два рядки.
    """
    sim = cosine_matrix(ratings)
    np.fill_diagonal(sim, -np.inf)
    dist = np.linalg.norm(ratings[:, None, :] - ratings[None, :, :], axis=2)

    n = len(ratings)
    twins = np.empty(n, dtype=int)
    for i in range(n):
        best = np.flatnonzero(np.isclose(sim[i], sim[i].max()))
        twins[i] = best[np.argmin(dist[i, best])]
    return twins, sim[np.arange(n), twins]


def shared_topics(a: np.ndarray, b: np.ndarray, topics: list[str], limit: int = 2) -> list[str]:
    """Теми, які обом подобаються найбільше (оцінка 3 і вище в обох)."""
    both = np.minimum(a, b)
    order = np.argsort(-both, kind="stable")
    return [topics[i] for i in order[:limit] if both[i] >= 3]


def map_points(ratings: np.ndarray) -> np.ndarray:
    """Проєкція на площину методом головних компонент, координати в межах [-1, 1]."""
    n = len(ratings)
    if n < 2:
        return np.zeros((n, 2))
    centered = ratings - ratings.mean(axis=0)
    u, s, _ = np.linalg.svd(centered, full_matrices=False)
    points = np.zeros((n, 2))
    k = min(2, len(s))
    points[:, :k] = u[:, :k] * s[:k]
    scale = np.abs(points).max()
    return points / scale if scale > 1e-9 else np.zeros((n, 2))
