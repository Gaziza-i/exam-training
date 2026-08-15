"""
Импорт заданий из открытого банка ФИПИ.

ФИПИ не предоставляет официальный REST API, поэтому задания нужно получить
парсером и передать сюда в виде JSON. Формат — список объектов:

    [
      {
        "topic_number": 4,                 # номер задания в КИМ (обязательно)
        "topic_title": "Орфоэпические нормы",  # название темы (обязательно при первом импорте темы)
        "task_type": "short_answer",        # short_answer | choice | essay
        "text": "Текст задания...",
        "options": ["вариант 1", "вариант 2"],   # только для task_type == "choice"
        "correct_answer": "жалюзи",          # можно "вариант1|вариант2" при нескольких формах ответа
        "explanation": "Пояснение (опционально)",
        "difficulty": "base",                # base | advanced | high
        "fipi_id": "1A2B3C"                  # идентификатор задания в банке ФИПИ, если известен
      },
      ...
    ]

Такой JSON можно получить любым сторонним парсером открытого банка ФИПИ
(например, проектом OpenFIPI: https://openfipi.devinf.ru/ — на момент
написания сайт покрывает не все предметы, поэтому для русского языка и
математики может понадобиться собственный скрипт на базе requests/bs4
поверх https://ege.fipi.ru или https://oge.fipi.ru).

Использование:
    python manage.py import_fipi path/to/tasks.json --subject rus

Если готового парсера под рукой нет — приложение прекрасно работает и на
демо-данных (см. `python manage.py seed_demo`), а реальные задания из ФИПИ
можно подключить позже, не меняя ни модели, ни фронтенд — только наполнив
JSON в этом формате.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from exam.models import Subject, Task, Topic


class FipiImportError(Exception):
    pass


@dataclass
class ImportStats:
    topics_created: int = 0
    tasks_created: int = 0
    tasks_updated: int = 0
    tasks_skipped: int = 0


def load_tasks_json(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        raise FipiImportError(f"Файл не найден: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise FipiImportError("Ожидался JSON-массив заданий")
    return data


def import_tasks(subject_code: str, items: list[dict]) -> ImportStats:
    try:
        subject = Subject.objects.get(code=subject_code)
    except Subject.DoesNotExist as exc:
        raise FipiImportError(
            f"Предмет '{subject_code}' не найден. Сначала выполните seed_demo, "
            "чтобы создать справочник предметов."
        ) from exc

    stats = ImportStats()

    for item in items:
        try:
            topic_number = int(item["topic_number"])
        except (KeyError, TypeError, ValueError) as exc:
            raise FipiImportError(f"Некорректный topic_number в задании: {item}") from exc

        topic, created = Topic.objects.get_or_create(
            subject=subject,
            task_number=topic_number,
            defaults={"title": item.get("topic_title") or f"Задание {topic_number}"},
        )
        if created:
            stats.topics_created += 1

        fipi_id = item.get("fipi_id", "")
        correct_answer = item.get("correct_answer")
        text = item.get("text")
        if not correct_answer or not text:
            stats.tasks_skipped += 1
            continue

        defaults = {
            "topic": topic,
            "task_type": item.get("task_type", Task.TYPE_SHORT_ANSWER),
            "text": text,
            "options": item.get("options"),
            "correct_answer": correct_answer,
            "explanation": item.get("explanation", ""),
            "difficulty": item.get("difficulty", "base"),
            "source": "fipi",
        }

        if fipi_id:
            _, was_created = Task.objects.update_or_create(
                fipi_id=fipi_id, defaults=defaults
            )
        else:
            Task.objects.create(fipi_id="", **defaults)
            was_created = True

        if was_created:
            stats.tasks_created += 1
        else:
            stats.tasks_updated += 1

    return stats
