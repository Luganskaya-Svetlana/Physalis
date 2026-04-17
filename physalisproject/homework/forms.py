from django import forms

from accounts.permissions import get_manageable_groups, get_manageable_students

from .models import HomeworkAssignment, HomeworkSubmission


class HomeworkAssignmentCreateForm(forms.ModelForm):
    class Meta:
        model = HomeworkAssignment
        fields = (
            'title',
            'instructions',
            'due_at',
            'allow_late_submissions',
            'max_score_strategy',
            'manual_max_score',
            'second_part_mode',
            'allow_second_part_text',
            'target_students',
            'target_groups',
        )
        widgets = {
            'instructions': forms.Textarea(attrs={'rows': 5}),
            'due_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        labels = {
            'title': 'Название ДЗ',
            'instructions': 'Комментарий для учеников',
            'due_at': 'Дедлайн',
            'allow_late_submissions': 'Разрешить сдачу после дедлайна',
            'max_score_strategy': 'Как считать максимум баллов',
            'manual_max_score': 'Максимум баллов вручную',
            'second_part_mode': 'Как сдавать вторую часть',
            'allow_second_part_text': 'Разрешить печатать вторую часть текстом',
            'target_students': 'Конкретные ученики',
            'target_groups': 'Группы',
        }
        help_texts = {
            'due_at': 'Необязательно. Если оставить поле пустым, срок сдачи не ограничен.',
            'manual_max_score': 'Поле активно только при выборе ручного режима.',
            'second_part_mode': 'Можно требовать отдельные материалы по задачам или разрешить оба способа сразу.',
        }

    def __init__(self, *args, request=None, variant=None, allow_retarget=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.variant = variant
        self.allow_retarget = allow_retarget
        if variant is not None:
            self.instance.variant = variant
        if request is not None and getattr(request.user, 'is_authenticated', False):
            self.instance.created_by = request.user
        self.fields['target_students'].queryset = get_manageable_students(request.user)
        self.fields['target_groups'].queryset = get_manageable_groups(request.user)
        self.fields['target_students'].widget = forms.CheckboxSelectMultiple(
            choices=self.fields['target_students'].choices,
        )
        self.fields['target_groups'].widget = forms.CheckboxSelectMultiple(
            choices=self.fields['target_groups'].choices,
        )
        self.fields['target_students'].required = False
        self.fields['target_groups'].required = False
        self.fields['title'].required = False
        self.fields['manual_max_score'].required = False
        self.fields['second_part_mode'].required = False
        second_part_choices = [
            (
                HomeworkAssignment.SecondPartMode.PER_PROBLEM,
                'обязательно отдельно файл по каждому заданию',
            ),
            (
                HomeworkAssignment.SecondPartMode.FLEXIBLE,
                'можно и отдельно, и все одним файлом',
            ),
        ]
        current_second_part_mode = getattr(self.instance, 'second_part_mode', '')
        if current_second_part_mode == HomeworkAssignment.SecondPartMode.SINGLE_FILE:
            second_part_choices.insert(
                0,
                (
                    HomeworkAssignment.SecondPartMode.SINGLE_FILE,
                    'одним общим файлом',
                ),
            )
        self.fields['second_part_mode'].choices = second_part_choices
        self.fields['second_part_mode'].initial = HomeworkAssignment.SecondPartMode.FLEXIBLE
        self.fields['manual_max_score'].widget.attrs['step'] = '1'
        self.fields['manual_max_score'].widget.attrs['inputmode'] = 'numeric'
        if variant is not None and not self.is_bound:
            self.fields['title'].initial = f'ДЗ по варианту #{variant.id}'
        if not allow_retarget:
            self.fields['target_students'].disabled = True
            self.fields['target_groups'].disabled = True
            self.fields['target_students'].help_text = 'После того как ученики начали работу, состав адресатов менять нельзя.'
            self.fields['target_groups'].help_text = 'После того как ученики начали работу, состав адресатов менять нельзя.'
        strategy = self.data.get('max_score_strategy') if self.is_bound else self.initial.get(
            'max_score_strategy',
            HomeworkAssignment.MaxScoreStrategy.AUTO,
        )
        if strategy != HomeworkAssignment.MaxScoreStrategy.MANUAL:
            self.fields['manual_max_score'].widget.attrs['disabled'] = 'disabled'

    def clean(self):
        cleaned_data = super().clean()
        students = cleaned_data.get('target_students')
        groups = cleaned_data.get('target_groups')
        if not students and not groups:
            raise forms.ValidationError('Нужно выбрать хотя бы одного ученика или одну группу.')
        return cleaned_data

    def save(self, commit=True):
        assignment = super().save(commit=False)
        if self.variant is not None:
            assignment.variant = self.variant
        if self.request is not None and not assignment.created_by_id:
            assignment.created_by = self.request.user
        if commit:
            assignment.save()
            if self.allow_retarget:
                self.save_m2m()
            assignment.ensure_submissions()
        return assignment


class SubmissionCommentForm(forms.Form):
    body = forms.CharField(
        label='Комментарий',
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    image = forms.FileField(
        label='Картинка',
        required=False,
        widget=forms.ClearableFileInput(attrs={'accept': 'image/*', 'class': 'comment-image-input'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        body = (cleaned_data.get('body') or '').strip()
        image = cleaned_data.get('image')
        if not body and not image:
            raise forms.ValidationError('Нужно написать комментарий или приложить картинку.')
        return cleaned_data


class SubmissionReviewForm(forms.ModelForm):
    class Meta:
        model = HomeworkSubmission
        fields = ('manual_score',)
        labels = {
            'manual_score': 'Суммарный балл',
        }
        widgets = {
            'manual_score': forms.NumberInput(attrs={'step': '1', 'min': '0', 'inputmode': 'numeric'}),
        }
