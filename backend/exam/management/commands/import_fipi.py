from django.core.management.base import BaseCommand, CommandError

from exam.services.fipi_import import FipiImportError, import_tasks, load_tasks_json


class Command(BaseCommand):
    help = "Импортирует задания из JSON-файла (см. exam/services/fipi_import.py за форматом)"

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Путь к JSON-файлу с заданиями")
        parser.add_argument(
            "--subject",
            type=str,
            required=True,
            choices=["rus", "math_base"],
            help="Код предмета, к которому относятся задания",
        )

    def handle(self, *args, **options):
        try:
            items = load_tasks_json(options["json_path"])
            stats = import_tasks(options["subject"], items)
        except FipiImportError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: тем создано {stats.topics_created}, заданий добавлено "
                f"{stats.tasks_created}, обновлено {stats.tasks_updated}, пропущено {stats.tasks_skipped}"
            )
        )
