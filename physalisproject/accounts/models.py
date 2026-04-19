import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


User = get_user_model()


class PlatformSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    allow_student_self_signup = models.BooleanField(
        'разрешить саморегистрацию учеников',
        default=True,
    )
    allow_teacher_self_signup = models.BooleanField(
        'разрешить саморегистрацию учителей',
        default=True,
    )
    require_email_on_signup = models.BooleanField(
        'требовать почту при регистрации',
        default=True,
    )

    class Meta:
        verbose_name = 'настройки платформы'
        verbose_name_plural = 'настройки платформы'

    def __str__(self):
        return 'настройки платформы'

    @classmethod
    def load(cls):
        settings_obj, _ = cls.objects.get_or_create(pk=1)
        return settings_obj


class UserProfile(models.Model):
    class Role(models.TextChoices):
        STUDENT = 'student', 'ученик'
        TEACHER = 'teacher', 'учитель'

    class TeacherApprovalStatus(models.TextChoices):
        NOT_REQUIRED = 'not_required', 'не требуется'
        PENDING = 'pending', 'ожидает одобрения'
        APPROVED = 'approved', 'одобрен'
        REJECTED = 'rejected', 'отклонен'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='пользователь',
    )
    role = models.CharField(
        'роль',
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    teacher_approval_status = models.CharField(
        'статус одобрения учителя',
        max_length=20,
        choices=TeacherApprovalStatus.choices,
        default=TeacherApprovalStatus.NOT_REQUIRED,
    )
    teacher_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_teacher_profiles',
        verbose_name='кто одобрил',
    )
    teacher_approved_at = models.DateTimeField(
        'когда одобрен',
        null=True,
        blank=True,
    )
    statistics_share_token = models.UUIDField(
        'токен публичной статистики',
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    statistics_share_enabled = models.BooleanField(
        'разрешить внешнюю ссылку на статистику',
        default=False,
    )
    telegram_login = models.CharField(
        'логин в Telegram',
        max_length=64,
        blank=True,
    )
    admin_users_seen_at = models.DateTimeField(
        'когда админ смотрел список пользователей',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField('создан', auto_now_add=True)
    updated_at = models.DateTimeField('обновлен', auto_now=True)

    class Meta:
        verbose_name = 'профиль пользователя'
        verbose_name_plural = 'профили пользователей'

    def __str__(self):
        return f'профиль {self.user}'

    def clean(self):
        super().clean()
        if self.role == self.Role.STUDENT:
            self.teacher_approval_status = self.TeacherApprovalStatus.NOT_REQUIRED
            self.teacher_approved_by = None
            self.teacher_approved_at = None
        elif self.teacher_approval_status == self.TeacherApprovalStatus.NOT_REQUIRED:
            self.teacher_approval_status = self.TeacherApprovalStatus.PENDING

    def approve_teacher(self, approved_by=None):
        self.role = self.Role.TEACHER
        self.teacher_approval_status = self.TeacherApprovalStatus.APPROVED
        self.teacher_approved_by = approved_by
        self.teacher_approved_at = timezone.now()

    @property
    def is_teacher_approved(self):
        return (
            self.role == self.Role.TEACHER
            and self.teacher_approval_status == self.TeacherApprovalStatus.APPROVED
        )

    @property
    def can_assign_homework(self):
        return self.user.is_staff or self.is_teacher_approved


class StudyGroup(models.Model):
    name = models.CharField('название', max_length=255, unique=True)
    description = models.TextField('описание', blank=True)
    invite_token = models.UUIDField(
        'токен приглашения',
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='managed_study_groups',
        verbose_name='учителя',
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='student_study_groups',
        verbose_name='ученики',
    )
    is_active = models.BooleanField('активна', default=True)
    created_at = models.DateTimeField('создана', auto_now_add=True)
    updated_at = models.DateTimeField('обновлена', auto_now=True)

    class Meta:
        verbose_name = 'учебная группа'
        verbose_name_plural = 'учебные группы'
        ordering = ['name']

    def __str__(self):
        return self.name


class TeacherStudentLink(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_links',
        verbose_name='учитель',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_links',
        verbose_name='ученик',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_teacher_student_links',
        verbose_name='кем создана связь',
    )
    notes = models.TextField('заметки', blank=True)
    is_active = models.BooleanField('активна', default=True)
    created_at = models.DateTimeField('создана', auto_now_add=True)
    updated_at = models.DateTimeField('обновлена', auto_now=True)

    class Meta:
        verbose_name = 'связь учителя и ученика'
        verbose_name_plural = 'связи учителей и учеников'
        constraints = [
            models.UniqueConstraint(
                fields=['teacher', 'student'],
                name='unique_teacher_student_link',
            ),
        ]

    def __str__(self):
        return f'{self.teacher} -> {self.student}'

    def clean(self):
        super().clean()
        if self.teacher_id == self.student_id:
            raise ValidationError('Учитель и ученик должны быть разными пользователями.')

        teacher_profile = getattr(self.teacher, 'profile', None)
        student_profile = getattr(self.student, 'profile', None)

        if not (self.teacher.is_staff or (teacher_profile and teacher_profile.is_teacher_approved)):
            raise ValidationError('Указанный пользователь не может быть учителем.')
        if not (student_profile and student_profile.role == UserProfile.Role.STUDENT):
            raise ValidationError('Указанный пользователь не является учеником.')
