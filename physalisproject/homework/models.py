from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import StudyGroup
from variants.models import Variant


class HomeworkAssignment(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'черновик'
        PUBLISHED = 'published', 'назначено'
        ARCHIVED = 'archived', 'в архиве'

    class MaxScoreStrategy(models.TextChoices):
        AUTO = 'auto', 'автоматически по задачам'
        MANUAL = 'manual', 'вручную'

    class SecondPartMode(models.TextChoices):
        SINGLE_FILE = 'single_file', 'одним общим файлом'
        PER_PROBLEM = 'per_problem', 'обязательно отдельно файл по каждому заданию'
        FLEXIBLE = 'flexible', 'можно и отдельно, и все одним файлом'

    variant = models.ForeignKey(
        Variant,
        on_delete=models.CASCADE,
        related_name='homework_assignments',
        verbose_name='вариант',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_homework_assignments',
        verbose_name='кто назначил',
    )
    title = models.CharField('название', max_length=255, blank=True)
    instructions = models.TextField('инструкции', blank=True)
    due_at = models.DateTimeField('дедлайн', null=True, blank=True)
    allow_late_submissions = models.BooleanField(
        'разрешить сдачу после дедлайна',
        default=True,
    )
    status = models.CharField(
        'статус',
        max_length=20,
        choices=Status.choices,
        default=Status.PUBLISHED,
    )
    max_score_strategy = models.CharField(
        'как считать максимум',
        max_length=20,
        choices=MaxScoreStrategy.choices,
        default=MaxScoreStrategy.AUTO,
    )
    manual_max_score = models.DecimalField(
        'максимум баллов вручную',
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    second_part_mode = models.CharField(
        'как сдавать вторую часть',
        max_length=20,
        choices=SecondPartMode.choices,
        default=SecondPartMode.SINGLE_FILE,
    )
    allow_second_part_text = models.BooleanField(
        'разрешить печатать вторую часть текстом',
        default=False,
    )
    target_students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='direct_homework_assignments',
        verbose_name='назначенные ученики',
    )
    target_groups = models.ManyToManyField(
        StudyGroup,
        blank=True,
        related_name='homework_assignments',
        verbose_name='назначенные группы',
    )
    created_at = models.DateTimeField('создано', auto_now_add=True)
    updated_at = models.DateTimeField('обновлено', auto_now=True)

    class Meta:
        verbose_name = 'назначение ДЗ'
        verbose_name_plural = 'назначения ДЗ'
        ordering = ['-created_at']

    def __str__(self):
        return self.title or f'ДЗ #{self.pk} по варианту #{self.variant_id}'

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse('homework:detail', kwargs={'pk': self.pk})

    def clean(self):
        super().clean()
        if self.max_score_strategy == self.MaxScoreStrategy.MANUAL and self.manual_max_score is None:
            raise ValidationError('При ручном максимуме нужно указать количество баллов.')

        if self.max_score_strategy == self.MaxScoreStrategy.AUTO and self.calculate_auto_max_score() is None:
            raise ValidationError(
                'Не удалось автоматически посчитать максимум баллов: '
                'у части задач отсутствует максимальный балл. '
                'Выберите ручной режим и задайте максимум явно.'
            )

    def calculate_auto_max_score(self):
        total = Decimal('0')
        for problem in self.variant.problems.select_related('type_ege').all():
            max_score = getattr(problem.type_ege, 'max_score', None)
            if max_score is None:
                return None
            total += Decimal(str(max_score))
        return total

    def get_resolved_max_score(self):
        if self.max_score_strategy == self.MaxScoreStrategy.MANUAL:
            return self.manual_max_score
        return self.calculate_auto_max_score()

    def get_effective_students(self):
        group_students = self.target_groups.values_list('students__id', flat=True)
        student_ids = set(self.target_students.values_list('id', flat=True))
        student_ids.update(student_id for student_id in group_students if student_id)
        if not student_ids:
            return self.target_students.model.objects.none()
        return self.target_students.model.objects.filter(id__in=student_ids).distinct()

    def ensure_submissions(self):
        resolved_max_score = self.get_resolved_max_score()
        for student in self.get_effective_students():
            HomeworkSubmission.objects.get_or_create(
                assignment=self,
                student=student,
                defaults={'max_score_snapshot': resolved_max_score},
            )

    @property
    def allows_shared_second_part_uploads(self):
        return self.second_part_mode in {
            self.SecondPartMode.SINGLE_FILE,
            self.SecondPartMode.FLEXIBLE,
        }

    @property
    def allows_per_problem_second_part_uploads(self):
        return self.second_part_mode in {
            self.SecondPartMode.PER_PROBLEM,
            self.SecondPartMode.FLEXIBLE,
        }


class HomeworkSubmission(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = 'assigned', 'назначено'
        DRAFT = 'draft', 'черновик'
        SUBMITTED = 'submitted', 'сдано'
        UNDER_REVIEW = 'under_review', 'на проверке'
        REVIEWED = 'reviewed', 'проверено'
        RETURNED = 'returned', 'возвращено на доработку'
        DELETED = 'deleted', 'удалено учеником'

    assignment = models.ForeignKey(
        HomeworkAssignment,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name='назначение',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='homework_submissions',
        verbose_name='ученик',
    )
    status = models.CharField(
        'статус',
        max_length=20,
        choices=Status.choices,
        default=Status.ASSIGNED,
    )
    submitted_at = models.DateTimeField('когда сдано', null=True, blank=True)
    reviewed_at = models.DateTimeField('когда проверено', null=True, blank=True)
    student_review_seen_at = models.DateTimeField(
        'когда ученик увидел проверку',
        null=True,
        blank=True,
    )
    deleted_at = models.DateTimeField('когда удалено', null=True, blank=True)
    restored_at = models.DateTimeField('когда восстановлено', null=True, blank=True)
    last_student_activity_at = models.DateTimeField(
        'последняя активность ученика',
        null=True,
        blank=True,
    )
    last_teacher_activity_at = models.DateTimeField(
        'последняя активность учителя',
        null=True,
        blank=True,
    )
    auto_score = models.DecimalField(
        'автоматический балл',
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    manual_score = models.DecimalField(
        'ручной балл',
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    total_score = models.DecimalField(
        'итоговый балл',
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    max_score_snapshot = models.DecimalField(
        'максимум баллов на момент назначения',
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField('создано', auto_now_add=True)
    updated_at = models.DateTimeField('обновлено', auto_now=True)

    class Meta:
        verbose_name = 'сдача ДЗ'
        verbose_name_plural = 'сдачи ДЗ'
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'student'],
                name='unique_homework_submission_per_student',
            ),
        ]
        ordering = ['-updated_at']

    def __str__(self):
        return f'сдача #{self.pk} для {self.student}'

    @property
    def can_student_edit(self):
        return self.status != self.Status.REVIEWED

    @property
    def teacher_needs_review(self):
        return self.status in {self.Status.SUBMITTED, self.Status.UNDER_REVIEW}


class HomeworkSubmissionAnswer(models.Model):
    submission = models.ForeignKey(
        HomeworkSubmission,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name='сдача',
    )
    problem = models.ForeignKey(
        'problems.Problem',
        on_delete=models.CASCADE,
        related_name='submission_answers',
        verbose_name='задача',
    )
    answer_text = models.TextField('ответ ученика', blank=True)
    normalized_answer = models.TextField('нормализованный ответ', blank=True)
    is_correct = models.BooleanField('верно', default=False)
    score_awarded = models.DecimalField(
        'начислено баллов',
        max_digits=7,
        decimal_places=2,
        default=0,
    )
    max_score_snapshot = models.DecimalField(
        'максимум баллов',
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    evaluation_payload = models.JSONField('детали проверки', default=dict, blank=True)
    created_at = models.DateTimeField('создано', auto_now_add=True)
    updated_at = models.DateTimeField('обновлено', auto_now=True)

    class Meta:
        verbose_name = 'ответ в сдаче'
        verbose_name_plural = 'ответы в сдаче'
        constraints = [
            models.UniqueConstraint(
                fields=['submission', 'problem'],
                name='unique_submission_answer_per_problem',
            ),
        ]
        ordering = ['problem_id']

    def __str__(self):
        return f'ответ по задаче #{self.problem_id} в сдаче #{self.submission_id}'


class HomeworkPracticeAttempt(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'черновик'
        SUBMITTED = 'submitted', 'проверено для себя'

    assignment = models.ForeignKey(
        HomeworkAssignment,
        on_delete=models.CASCADE,
        related_name='practice_attempts',
        verbose_name='назначение',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='homework_practice_attempts',
        verbose_name='ученик',
    )
    status = models.CharField(
        'статус',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    submitted_at = models.DateTimeField('когда проверено', null=True, blank=True)
    auto_score = models.DecimalField(
        'автоматический балл',
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    max_score_snapshot = models.DecimalField(
        'максимум баллов',
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField('создано', auto_now_add=True)
    updated_at = models.DateTimeField('обновлено', auto_now=True)

    class Meta:
        verbose_name = 'личная попытка'
        verbose_name_plural = 'личные попытки'
        ordering = ['-created_at']

    def __str__(self):
        return f'личная попытка #{self.pk} для {self.student}'

    @property
    def can_student_edit(self):
        return self.status != self.Status.SUBMITTED


class HomeworkPracticeAttemptAnswer(models.Model):
    attempt = models.ForeignKey(
        HomeworkPracticeAttempt,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name='попытка',
    )
    problem = models.ForeignKey(
        'problems.Problem',
        on_delete=models.CASCADE,
        related_name='practice_attempt_answers',
        verbose_name='задача',
    )
    answer_text = models.TextField('ответ ученика', blank=True)
    normalized_answer = models.TextField('нормализованный ответ', blank=True)
    is_correct = models.BooleanField('верно', default=False)
    score_awarded = models.DecimalField(
        'начислено баллов',
        max_digits=7,
        decimal_places=2,
        default=0,
    )
    max_score_snapshot = models.DecimalField(
        'максимум баллов',
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    evaluation_payload = models.JSONField('детали проверки', default=dict, blank=True)
    created_at = models.DateTimeField('создано', auto_now_add=True)
    updated_at = models.DateTimeField('обновлено', auto_now=True)

    class Meta:
        verbose_name = 'ответ в личной попытке'
        verbose_name_plural = 'ответы в личных попытках'
        constraints = [
            models.UniqueConstraint(
                fields=['attempt', 'problem'],
                name='unique_practice_attempt_answer_per_problem',
            ),
        ]
        ordering = ['problem_id']

    def __str__(self):
        return f'ответ по задаче #{self.problem_id} в попытке #{self.attempt_id}'


class HomeworkSubmissionSecondPartResponse(models.Model):
    submission = models.ForeignKey(
        HomeworkSubmission,
        on_delete=models.CASCADE,
        related_name='second_part_responses',
        verbose_name='сдача',
    )
    problem = models.ForeignKey(
        'problems.Problem',
        on_delete=models.CASCADE,
        related_name='second_part_responses',
        verbose_name='задача',
    )
    text_answer = models.TextField('текст ответа', blank=True)
    created_at = models.DateTimeField('создано', auto_now_add=True)
    updated_at = models.DateTimeField('обновлено', auto_now=True)

    class Meta:
        verbose_name = 'ответ второй части'
        verbose_name_plural = 'ответы второй части'
        constraints = [
            models.UniqueConstraint(
                fields=['submission', 'problem'],
                name='unique_second_part_response_per_problem',
            ),
        ]
        ordering = ['problem_id']

    def __str__(self):
        return f'вторая часть #{self.problem_id} в сдаче #{self.submission_id}'


class HomeworkSubmissionSecondPartScore(models.Model):
    submission = models.ForeignKey(
        HomeworkSubmission,
        on_delete=models.CASCADE,
        related_name='second_part_scores',
        verbose_name='сдача',
    )
    problem = models.ForeignKey(
        'problems.Problem',
        on_delete=models.CASCADE,
        related_name='second_part_scores',
        verbose_name='задача',
    )
    score_awarded = models.DecimalField(
        'балл',
        max_digits=7,
        decimal_places=2,
        default=0,
    )
    created_at = models.DateTimeField('создано', auto_now_add=True)
    updated_at = models.DateTimeField('обновлено', auto_now=True)

    class Meta:
        verbose_name = 'балл второй части'
        verbose_name_plural = 'баллы второй части'
        constraints = [
            models.UniqueConstraint(
                fields=['submission', 'problem'],
                name='unique_second_part_score_per_problem',
            ),
        ]
        ordering = ['problem_id']

    def __str__(self):
        return f'балл второй части #{self.problem_id} в сдаче #{self.submission_id}'


class SubmissionAttachment(models.Model):
    submission = models.ForeignKey(
        HomeworkSubmission,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='сдача',
    )
    problem = models.ForeignKey(
        'problems.Problem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='submission_attachments',
        verbose_name='задача',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_submission_attachments',
        verbose_name='кто загрузил',
    )
    file = models.FileField(
        'файл',
        upload_to='homework/submissions/%Y/%m/%d/',
    )
    rotation_degrees = models.PositiveSmallIntegerField(
        'поворот',
        default=0,
    )
    sort_order = models.PositiveSmallIntegerField('порядок', default=0)
    created_at = models.DateTimeField('создано', auto_now_add=True)

    class Meta:
        verbose_name = 'вложение к сдаче'
        verbose_name_plural = 'вложения к сдаче'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'вложение #{self.pk} к сдаче #{self.submission_id}'

    def clean(self):
        super().clean()
        if self.rotation_degrees not in {0, 90, 180, 270}:
            raise ValidationError('Допустимы повороты только на 0, 90, 180 или 270 градусов.')

    @property
    def is_image(self):
        suffix = Path(self.file.name or '').suffix.lower()
        return suffix in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}


class SubmissionComment(models.Model):
    submission = models.ForeignKey(
        HomeworkSubmission,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='сдача',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submission_comments',
        verbose_name='автор',
    )
    body = models.TextField('текст')
    image = models.FileField(
        'картинка',
        upload_to='homework/comments/%Y/%m/%d/',
        blank=True,
    )
    created_at = models.DateTimeField('создано', auto_now_add=True)
    updated_at = models.DateTimeField('обновлено', auto_now=True)

    class Meta:
        verbose_name = 'комментарий к сдаче'
        verbose_name_plural = 'комментарии к сдаче'
        ordering = ['created_at']

    def __str__(self):
        return f'комментарий #{self.pk}'


class SubmissionCommentRead(models.Model):
    comment = models.ForeignKey(
        SubmissionComment,
        on_delete=models.CASCADE,
        related_name='read_receipts',
        verbose_name='комментарий',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comment_read_receipts',
        verbose_name='пользователь',
    )
    read_at = models.DateTimeField('когда прочитано', auto_now_add=True)

    class Meta:
        verbose_name = 'прочтение комментария'
        verbose_name_plural = 'прочтения комментариев'
        constraints = [
            models.UniqueConstraint(
                fields=['comment', 'user'],
                name='unique_submission_comment_read_receipt',
            ),
        ]

    def __str__(self):
        return f'{self.user} прочитал комментарий #{self.comment_id}'


class SubmissionEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = 'created', 'создано'
        DRAFT_SAVED = 'draft_saved', 'черновик сохранен'
        SUBMITTED = 'submitted', 'сдано'
        EDITED = 'edited', 'отредактировано'
        DELETED = 'deleted', 'удалено'
        RESTORED = 'restored', 'восстановлено'
        REVIEW_STARTED = 'review_started', 'проверка начата'
        REVIEWED = 'reviewed', 'проверено'
        COMMENT_ADDED = 'comment_added', 'добавлен комментарий'
        STATUS_CHANGED = 'status_changed', 'смена статуса'

    submission = models.ForeignKey(
        HomeworkSubmission,
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name='сдача',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submission_events',
        verbose_name='кто сделал',
    )
    event_type = models.CharField(
        'тип события',
        max_length=30,
        choices=EventType.choices,
    )
    payload = models.JSONField('данные события', default=dict, blank=True)
    created_at = models.DateTimeField('создано', auto_now_add=True)

    class Meta:
        verbose_name = 'событие сдачи'
        verbose_name_plural = 'события сдач'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.event_type} для сдачи #{self.submission_id}'
