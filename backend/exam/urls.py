from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AttemptViewSet,
    EssayAttemptViewSet,
    EssayCriteriaView,
    ExamVariantViewSet,
    StatsView,
    SubjectViewSet,
    TaskViewSet,
    TopicViewSet,
)

router = DefaultRouter()
router.register("subjects", SubjectViewSet)
router.register("topics", TopicViewSet)
router.register("tasks", TaskViewSet)
router.register("attempts", AttemptViewSet)
router.register("exam-variants", ExamVariantViewSet)
router.register("essays", EssayAttemptViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("essay-criteria/", EssayCriteriaView.as_view(), name="essay-criteria"),
    path("stats/", StatsView.as_view(), name="stats"),
]
