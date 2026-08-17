from django.db import models


class Subject(models.Model):
    """Учебный предмет: русский язык, математика (база) и т.д."""

    RUSSIAN = "rus"
    MATH_BASE = "math_base"

    CODE_CHOICES = [
        (RUSSIAN, "Русский язык"),
        (MATH_BASE, "Математика (база)"),
    ]

    code = models.CharField(max_length=20, choices=CODE_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Topic(models.Model):
    """Тема/номер задания ЕГЭ внутри предмета (например, №1 «Средства связи предложений»)."""

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="topics")
    task_number = models.PositiveSmallIntegerField(help_text="Номер задания в КИМ ЕГЭ")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["subject_id", "task_number"]
        unique_together = ("subject", "task_number")

    def __str__(self):
        return f"{self.subject.code} №{self.task_number} — {self.title}"


class Task(models.Model):
    """Конкретное задание. Источник — открытый банк ФИПИ (см. exam/services/fipi_import.py)."""

    TYPE_SHORT_ANSWER = "short_answer"
    TYPE_CHOICE = "choice"
    TYPE_ESSAY = "essay"

    TYPE_CHOICES = [
        (TYPE_SHORT_ANSWER, "Краткий ответ"),
        (TYPE_CHOICE, "Выбор варианта"),
        (TYPE_ESSAY, "Сочинение"),
    ]

    DIFFICULTY_CHOICES = [
        ("base", "Базовый"),
        ("advanced", "Повышенный"),
        ("high", "Высокий"),
    ]

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="tasks")
    task_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_SHORT_ANSWER)
    text = models.TextField()
    options = models.JSONField(
        blank=True,
        null=True,
        help_text="Список вариантов ответа для заданий с выбором (JSON-массив строк)",
    )
    correct_answer = models.CharField(max_length=500)
    explanation = models.TextField(blank=True)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="base")

    # Происхождение задания: реальный банк ФИПИ (fipi) или служебные демо-данные (seed).
    source = models.CharField(max_length=20, default="seed")
    fipi_id = models.CharField(max_length=100, blank=True, help_text="Идентификатор задания в открытом банке ФИПИ")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["topic_id", "id"]

    def __str__(self):
        return f"{self.topic} — задание {self.id}"


class Attempt(models.Model):
    """Попытка решения одного задания (в тренировке или в режиме варианта)."""

    MODE_PRACTICE = "practice"
    MODE_EXAM = "exam"

    MODE_CHOICES = [
        (MODE_PRACTICE, "Тренировка"),
        (MODE_EXAM, "Вариант на время"),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attempts")
    exam_variant = models.ForeignKey(
        "ExamVariant", on_delete=models.CASCADE, related_name="attempts", blank=True, null=True
    )
    user_answer = models.CharField(max_length=1000, blank=True)
    is_correct = models.BooleanField(default=False)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default=MODE_PRACTICE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Attempt(task={self.task_id}, correct={self.is_correct})"


class ExamVariant(models.Model):
    """Сессия «вариант на время» — экзаменационная симуляция по одному предмету."""

    STATUS_IN_PROGRESS = "in_progress"
    STATUS_FINISHED = "finished"

    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, "Идёт"),
        (STATUS_FINISHED, "Завершён"),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="exam_variants")
    tasks = models.ManyToManyField(Task, related_name="exam_variants")
    time_limit_minutes = models.PositiveIntegerField(default=180)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    score = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"Вариант #{self.id} ({self.subject.code}, {self.status})"


# Сочинение-рассуждение по прочитанному тексту (задание 27 КИМ ЕГЭ по русскому языку).
ESSAY_CRITERIA_EGE = [
    {"code": "K1", "title": "Формулировка проблемы исходного текста"},
    {"code": "K2", "title": "Комментарий к проблеме"},
    {"code": "K3", "title": "Отражение позиции автора"},
    {"code": "K4", "title": "Отношение к позиции автора, аргументация"},
    {"code": "K5", "title": "Смысловая цельность, речевая связность и последовательность изложения"},
    {"code": "K6", "title": "Точность и выразительность речи"},
    {"code": "K7", "title": "Соблюдение орфографических норм"},
    {"code": "K8", "title": "Соблюдение пунктуационных норм"},
    {"code": "K9", "title": "Соблюдение языковых норм"},
    {"code": "K10", "title": "Соблюдение речевых норм"},
    {"code": "K11", "title": "Соблюдение этических норм"},
    {"code": "K12", "title": "Соблюдение фактологической точности"},
]

# Итоговое сочинение (допуск к ЕГЭ) — оценивается "зачёт/незачёт".
# Требование 1 и 2 обязательны; из критериев 1-5 «зачёт» нужен минимум по трём,
# в том числе обязательно по критериям 1 и 2.
ESSAY_CRITERIA_FINAL = [
    {"code": "T1", "title": "Требование 1. Объём — не менее 250 слов"},
    {"code": "T2", "title": "Требование 2. Самостоятельность написания"},
    {"code": "C1", "title": "Критерий 1. Соответствие теме"},
    {"code": "C2", "title": "Критерий 2. Аргументация. Привлечение литературного материала"},
    {"code": "C3", "title": "Критерий 3. Композиция и логика рассуждения"},
    {"code": "C4", "title": "Критерий 4. Качество письменной речи"},
    {"code": "C5", "title": "Критерий 5. Грамотность"},
]

# Сохраняем старое имя для обратной совместимости (использовалось до разделения на два вида).
ESSAY_CRITERIA = ESSAY_CRITERIA_EGE

ESSAY_CRITERIA_BY_TYPE = {
    "ege": ESSAY_CRITERIA_EGE,
    "final": ESSAY_CRITERIA_FINAL,
}


class EssayAttempt(models.Model):
    """Черновик сочинения + самопроверка по критериям."""

    TYPE_EGE = "ege"
    TYPE_FINAL = "final"

    TYPE_CHOICES = [
        (TYPE_EGE, "Сочинение ЕГЭ (задание 27)"),
        (TYPE_FINAL, "Итоговое сочинение"),
    ]

    essay_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_EGE)
    source_text = models.TextField(
        blank=True,
        help_text="Исходный текст для сочинения ЕГЭ или тема — для итогового сочинения (опционально)",
    )
    essay_text = models.TextField(blank=True)
    checklist = models.JSONField(
        default=dict,
        blank=True,
        help_text="Словарь {код критерия: bool} — самопроверка по чек-листу",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Сочинение #{self.id} ({self.get_essay_type_display()}, {self.created_at:%Y-%m-%d})"
