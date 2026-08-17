from rest_framework import serializers

from .models import (
    ESSAY_CRITERIA_BY_TYPE,
    ESSAY_CRITERIA_EGE,
    Attempt,
    EssayAttempt,
    ExamVariant,
    Subject,
    Task,
    Topic,
)


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "code", "name", "slug"]


class TopicSerializer(serializers.ModelSerializer):
    task_count = serializers.IntegerField(source="tasks.count", read_only=True)

    class Meta:
        model = Topic
        fields = ["id", "subject", "task_number", "title", "description", "task_count"]


class TaskSerializer(serializers.ModelSerializer):
    """Полное представление задания (используется в тренировке / варианте, содержит верный ответ)."""

    class Meta:
        model = Task
        fields = [
            "id",
            "topic",
            "task_type",
            "text",
            "options",
            "correct_answer",
            "explanation",
            "difficulty",
            "source",
            "fipi_id",
        ]


class TaskPublicSerializer(serializers.ModelSerializer):
    """Задание без верного ответа — то, что отправляется клиенту до попытки."""

    class Meta:
        model = Task
        fields = ["id", "topic", "task_type", "text", "options", "difficulty", "source"]


class AttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attempt
        fields = ["id", "task", "exam_variant", "user_answer", "is_correct", "mode", "created_at"]
        read_only_fields = ["is_correct", "created_at"]

    def create(self, validated_data):
        task = validated_data["task"]
        user_answer = validated_data.get("user_answer", "").strip()
        is_correct = _answers_match(user_answer, task.correct_answer)
        validated_data["is_correct"] = is_correct
        return super().create(validated_data)


def _answers_match(user_answer: str, correct_answer: str) -> bool:
    """Сравнение ответов: регистронезависимо, без лишних пробелов.

    Для заданий с несколькими верными формами ответа correct_answer может
    содержать варианты через "|" (например, "красный|алый").
    """
    normalize = lambda s: " ".join(s.strip().lower().replace("ё", "е").split())
    candidates = [normalize(c) for c in correct_answer.split("|")]
    return normalize(user_answer) in candidates


class ExamVariantSerializer(serializers.ModelSerializer):
    tasks = TaskPublicSerializer(many=True, read_only=True)

    class Meta:
        model = ExamVariant
        fields = [
            "id",
            "subject",
            "tasks",
            "time_limit_minutes",
            "status",
            "started_at",
            "finished_at",
            "score",
        ]
        read_only_fields = ["status", "started_at", "finished_at", "score"]


class EssayAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = EssayAttempt
        fields = ["id", "essay_type", "source_text", "essay_text", "checklist", "created_at", "updated_at"]


class EssayCriterionSerializer(serializers.Serializer):
    code = serializers.CharField()
    title = serializers.CharField()


def get_essay_criteria(essay_type="ege"):
    return ESSAY_CRITERIA_BY_TYPE.get(essay_type, ESSAY_CRITERIA_EGE)
