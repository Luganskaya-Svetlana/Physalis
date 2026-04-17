from django.contrib import admin

from .models import PlatformSettings, StudyGroup, TeacherStudentLink, UserProfile


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'allow_student_self_signup',
                    'allow_teacher_self_signup',
                    'require_email_on_signup',
                )
            },
        ),
    )

    def has_add_permission(self, request):
        if PlatformSettings.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'role',
        'teacher_approval_status',
        'teacher_approved_by',
        'teacher_approved_at',
        'statistics_share_enabled',
    )
    list_filter = ('role', 'teacher_approval_status', 'statistics_share_enabled')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')
    raw_id_fields = ('user', 'teacher_approved_by')
    actions = ('approve_selected_teachers',)

    @admin.action(description='Одобрить выбранных учителей')
    def approve_selected_teachers(self, request, queryset):
        updated = 0
        for profile in queryset:
            if profile.role != UserProfile.Role.TEACHER:
                continue
            profile.approve_teacher(approved_by=request.user)
            profile.save()
            updated += 1
        self.message_user(request, f'Одобрено профилей: {updated}.')


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'teachers_count', 'students_count', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    filter_horizontal = ('teachers', 'students')

    def teachers_count(self, obj):
        return obj.teachers.count()

    teachers_count.short_description = 'учителей'

    def students_count(self, obj):
        return obj.students.count()

    students_count.short_description = 'учеников'


@admin.register(TeacherStudentLink)
class TeacherStudentLinkAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'student', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = (
        'teacher__username',
        'teacher__first_name',
        'teacher__last_name',
        'student__username',
        'student__first_name',
        'student__last_name',
    )
    raw_id_fields = ('teacher', 'student', 'created_by')
