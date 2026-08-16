import random

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ESSAY_CRITERIA, Attempt, EssayAttempt, ExamVariant, Subject, Task, Topic
from .serializers import (
    AttemptSerializer,
    EssayAttemptSerializer,
    ExamVariantSerializer,
    SubjectSerializer,
    TaskPublicSerializer,
    TaskSerializer,
    TopicSerializer,
)

# Экзаменационные лимиты по умолчанию (реальные ориентиры ЕГЭ).
DEFAULT_TIME_LIMIT = {
    Subject.RUSSIAN: 210,
    Subject.MATH_BASE: 180,
}


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


class TopicViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        subject = self.request.query_params.get("subject")
        if subject:
            qs = qs.filter(subject__slug=subject)
        return qs


class TaskViewSet(viewsets.ReadOnlyModelViewSet):
    """Список заданий для тренировки. Ответ отдаётся без correct_answer."""

    queryset = Task.objects.all()
    serializer_class = TaskPublicSerializer
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        topic = self.request.query_params.get("topic")
        subject = self.request.query_params.get("subject")
        random_pick = self.request.query_params.get("random")
        if topic:
            qs = qs.filter(topic_id=topic)
        if subject:
            qs = qs.filter(topic__subject__slug=subject)
        if random_pick:
            ids = list(qs.values_list("id", flat=True))
            random.shuffle(ids)
            ids = ids[: int(random_pick)]
            qs = qs.filter(id__in=ids)
        return qs

    @action(detail=True, methods=["get"])
    def with_answer(self, request, pk=None):
        """Отдаёт задание вместе с верным ответом и объяснением (после попытки/для проверки)."""
        task = self.get_object()
        return Response(TaskSerializer(task).data)


class AttemptViewSet(viewsets.ModelViewSet):
    queryset = Attempt.objects.all()
    serializer_class = AttemptSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        attempt = Attempt.objects.get(pk=response.data["id"])
        task = attempt.task
        response.data["correct_answer"] = task.correct_answer
        response.data["explanation"] = task.explanation
        return response


class ExamVariantViewSet(viewsets.ModelViewSet):
    """Режим «вариант на время»: собирает случайный набор заданий по всем темам предмета."""

    queryset = ExamVariant.objects.all()
    serializer_class = ExamVariantSerializer

    def create(self, request, *args, **kwargs):
        subject_id = request.data.get("subject")
        try:
            subject = Subject.objects.get(pk=subject_id)
        except Subject.DoesNotExist:
            return Response({"detail": "Предмет не найден"}, status=status.HTTP_404_NOT_FOUND)

        tasks = []
        for topic in subject.topics.all():
            topic_tasks = list(topic.tasks.all())
            if topic_tasks:
                tasks.append(random.choice(topic_tasks))

        if not tasks:
            return Response(
                {"detail": "Для этого предмета пока нет заданий. Загрузите или сгенерируйте демо-данные."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        variant = ExamVariant.objects.create(
            subject=subject,
            time_limit_minutes=request.data.get("time_limit_minutes") or DEFAULT_TIME_LIMIT.get(subject.code, 180),
        )
        variant.tasks.set(tasks)
        return Response(ExamVariantSerializer(variant).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        variant = self.get_object()
        # Берём последнюю попытку по каждому заданию — на случай повторной отправки.
        attempts_by_task = {}
        for attempt in variant.attempts.order_by("created_at"):
            attempts_by_task[attempt.task_id] = attempt

        correct = sum(1 for a in attempts_by_task.values() if a.is_correct)
        variant.status = ExamVariant.STATUS_FINISHED
        variant.finished_at = timezone.now()
        variant.score = correct
        variant.save()

        review = []
        for task in variant.tasks.all():
            attempt = attempts_by_task.get(task.id)
            review.append(
                {
                    "task_id": task.id,
                    "text": task.text,
                    "task_type": task.task_type,
                    "options": task.options,
                    "user_answer": attempt.user_answer if attempt else "",
                    "is_correct": attempt.is_correct if attempt else False,
                    "correct_answer": task.correct_answer,
                    "explanation": task.explanation,
                }
            )

        data = ExamVariantSerializer(variant).data
        data["review"] = review
        return Response(data)


class EssayAttemptViewSet(viewsets.ModelViewSet):
    queryset = EssayAttempt.objects.all()
    serializer_class = EssayAttemptSerializer


class EssayCriteriaView(APIView):
    def get(self, request):
        return Response(ESSAY_CRITERIA)


class StatsView(APIView):
    """Статистика прогресса: точность по темам, слабые/сильные стороны."""

    def get(self, request):
        subject_slug = request.query_params.get("subject")
        topics = Topic.objects.all()
        if subject_slug:
            topics = topics.filter(subject__slug=subject_slug)

        result = []
        for topic in topics.select_related("subject"):
            attempts = Attempt.objects.filter(task__topic=topic)
            total = attempts.count()
            correct = attempts.filter(is_correct=True).count()
            accuracy = round(correct / total * 100, 1) if total else None
            result.append(
                {
                    "topic_id": topic.id,
                    "subject": topic.subject.code,
                    "task_number": topic.task_number,
                    "title": topic.title,
                    "attempts": total,
                    "correct": correct,
                    "accuracy": accuracy,
                }
            )

        attempted = [r for r in result if r["attempts"] > 0]
        weak = sorted(attempted, key=lambda r: r["accuracy"])[:5]
        strong = sorted(attempted, key=lambda r: -r["accuracy"])[:5]

        total_attempts = Attempt.objects.count()
        total_correct = Attempt.objects.filter(is_correct=True).count()

        return Response(
            {
                "topics": result,
                "weak_topics": weak,
                "strong_topics": strong,
                "overall": {
                    "attempts": total_attempts,
                    "correct": total_correct,
                    "accuracy": round(total_correct / total_attempts * 100, 1) if total_attempts else None,
                },
                "exam_variants_completed": ExamVariant.objects.filter(status=ExamVariant.STATUS_FINISHED).count(),
            }
        )
