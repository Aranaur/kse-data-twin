"""Стан залу в пам'яті процесу. Без вебу, щоб логіку можна було тестувати."""

from __future__ import annotations

import numpy as np

from twin import map_points, nearest, shared_topics

TOPICS = ["Ігри", "Музика", "Спорт", "Наука", "Кіно і серіали", "Аніме", "Подорожі", "Книжки"]
MAX_PEOPLE = 300
MAX_NAME = 24


class Room:
    def __init__(self) -> None:
        self.people: dict[str, dict] = {}
        self.revealed = False

    def _matrix(self) -> tuple[list[str], np.ndarray]:
        ids = list(self.people)
        return ids, np.array([self.people[i]["ratings"] for i in ids], dtype=float)

    def answer(self, person: str, name: str, ratings: list[int]) -> None:
        """Зберігає відповідь або кидає ValueError з текстом для учасника."""
        name = name.strip()[:MAX_NAME]
        if not name:
            raise ValueError("Вкажи ім'я або псевдонім")
        if len(ratings) != len(TOPICS) or any(not 0 <= r <= 5 for r in ratings):
            raise ValueError("Оцінки мають бути від 0 до 5")
        if not any(ratings):
            raise ValueError("Постав хоча б одну оцінку вище нуля")
        if person not in self.people and len(self.people) >= MAX_PEOPLE:
            raise ValueError("Забагато учасників")
        self.people[person] = {"name": name, "ratings": list(ratings)}

    def me(self, person: str) -> dict:
        if person not in self.people:
            return {"status": "unknown"}
        if not self.revealed or len(self.people) < 2:
            return {"status": "waiting", "count": len(self.people)}
        ids, ratings = self._matrix()
        twins, sims = nearest(ratings)
        i = ids.index(person)
        j = int(twins[i])
        return {
            "status": "ready",
            "twin": self.people[ids[j]]["name"],
            "similarity": round(float(sims[i]) * 100),
            "shared": shared_topics(ratings[i], ratings[j], TOPICS),
        }

    def map(self) -> dict:
        """Тільки безіменні точки: це бачить увесь зал."""
        if not self.people:
            return {"count": 0, "points": [], "links": []}
        ids, ratings = self._matrix()
        links = nearest(ratings)[0].tolist() if len(ids) >= 2 and self.revealed else []
        return {"count": len(ids), "points": map_points(ratings).round(4).tolist(), "links": links}

    def pairs(self) -> list[str]:
        """Список імен для ведучого: запасний варіант з паперовими анкетами."""
        if len(self.people) < 2:
            return []
        ids, ratings = self._matrix()
        twins, sims = nearest(ratings)
        return [
            f"{self.people[i]['name']} → {self.people[ids[int(t)]]['name']} ({round(float(s) * 100)}%)"
            for i, t, s in zip(ids, twins, sims)
        ]

    def reset(self) -> None:
        self.people.clear()
        self.revealed = False
