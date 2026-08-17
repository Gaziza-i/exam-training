from django.contrib import admin

from .models import Attempt, EssayAttempt, ExamVariant, Subject, Task, Topic


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "slug")


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "task_number", "title")
    list_filter = ("subject",)
    ordering = ("subject", "task_number")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "topic", "task_type", "difficulty", "source")
    list_filter = ("topic__subject", "task_type", "difficulty", "source")
    search_fields = ("text", "fipi_id")


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "mode", "is_correct", "created_at")
    list_filter = ("mode", "is_correct")


@admin.register(ExamVariant)
class ExamVariantAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "status", "started_at", "finished_at", "score")
    list_filter = ("subject", "status")


@admin.register(EssayAttempt)
class EssayAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "essay_type", "created_at", "updated_at")
    list_filter = ("essay_type",)
