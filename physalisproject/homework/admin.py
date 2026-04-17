from django.contrib import admin

from .models import (
    HomeworkAssignment,
    HomeworkSubmission,
    HomeworkSubmissionAnswer,
    SubmissionAttachment,
    SubmissionComment,
    SubmissionCommentRead,
    SubmissionEvent,
)


class SubmissionAttachmentInline(admin.TabularInline):
    model = SubmissionAttachment
    extra = 0


class SubmissionCommentInline(admin.TabularInline):
    model = SubmissionComment
    extra = 0


class HomeworkSubmissionAnswerInline(admin.TabularInline):
    model = HomeworkSubmissionAnswer
    extra = 0
    readonly_fields = ('problem', 'normalized_answer', 'is_correct', 'score_awarded')


class HomeworkSubmissionInline(admin.TabularInline):
    model = HomeworkSubmission
    extra = 0
    raw_id_fields = ('student',)
    fields = ('student', 'status', 'submitted_at', 'reviewed_at', 'total_score')
    readonly_fields = ('submitted_at', 'reviewed_at')
    show_change_link = True


@admin.register(HomeworkAssignment)
class HomeworkAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'variant',
        'created_by',
        'status',
        'due_at',
        'allow_late_submissions',
        'created_at',
    )
    list_filter = ('status', 'allow_late_submissions', 'max_score_strategy')
    search_fields = ('id', 'title', 'variant__text', 'created_by__username')
    raw_id_fields = ('variant', 'created_by', 'target_students')
    filter_horizontal = ('target_groups',)
    inlines = (HomeworkSubmissionInline,)

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.ensure_submissions()


@admin.register(HomeworkSubmission)
class HomeworkSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'assignment',
        'student',
        'status',
        'submitted_at',
        'reviewed_at',
        'total_score',
        'updated_at',
    )
    list_filter = ('status',)
    search_fields = ('id', 'student__username', 'student__first_name', 'student__last_name')
    raw_id_fields = ('assignment', 'student')
    inlines = (HomeworkSubmissionAnswerInline, SubmissionAttachmentInline, SubmissionCommentInline)


@admin.register(HomeworkSubmissionAnswer)
class HomeworkSubmissionAnswerAdmin(admin.ModelAdmin):
    list_display = ('submission', 'problem', 'is_correct', 'score_awarded', 'updated_at')
    raw_id_fields = ('submission', 'problem')


@admin.register(SubmissionAttachment)
class SubmissionAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission', 'uploaded_by', 'rotation_degrees', 'sort_order', 'created_at')
    raw_id_fields = ('submission', 'uploaded_by')


@admin.register(SubmissionComment)
class SubmissionCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission', 'author', 'created_at', 'updated_at')
    raw_id_fields = ('submission', 'author')
    search_fields = ('body', 'author__username')


@admin.register(SubmissionCommentRead)
class SubmissionCommentReadAdmin(admin.ModelAdmin):
    list_display = ('comment', 'user', 'read_at')
    raw_id_fields = ('comment', 'user')


@admin.register(SubmissionEvent)
class SubmissionEventAdmin(admin.ModelAdmin):
    list_display = ('submission', 'event_type', 'actor', 'created_at')
    list_filter = ('event_type',)
    raw_id_fields = ('submission', 'actor')
