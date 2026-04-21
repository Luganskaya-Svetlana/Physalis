from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils import timezone

from .models import PlatformSettings, StudyGroup, TeacherStudentLink, UserProfile


User = get_user_model()


class SignUpForm(UserCreationForm):
    username = forms.CharField(
        label='Логин',
        max_length=20,
        error_messages={'max_length': 'Логин не должен быть длиннее 20 символов.'},
    )
    first_name = forms.CharField(label='Имя', required=True, max_length=150)
    last_name = forms.CharField(label='Фамилия', required=True, max_length=150)
    role = forms.ChoiceField(
        label='Кто вы',
        choices=UserProfile.Role.choices,
    )
    email = forms.EmailField(
        label='Почта',
        required=True,
    )
    telegram_login = forms.CharField(
        label='Логин в Telegram',
        required=False,
        max_length=64,
    )
    teacher_login = forms.CharField(
        label='Укажите логин учителя, чтобы он мог задавать вам ДЗ (необязательно)',
        required=False,
        max_length=150,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'telegram_login', 'role', 'teacher_login')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        platform_settings = PlatformSettings.load()
        self.platform_settings = platform_settings
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Подтверждение пароля'
        self.fields['password1'].widget.attrs.update({
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget.attrs.update({
            'autocomplete': 'new-password',
            'onpaste': 'return false;',
        })
        self.fields['email'].help_text = 'Обязательное поле.'

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            return ''
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Этот адрес электронной почты уже используется.')
        return email

    def clean_teacher_login(self):
        teacher_login = (self.cleaned_data.get('teacher_login') or '').strip()
        if not teacher_login:
            return ''
        try:
            teacher = User.objects.get(username=teacher_login)
        except User.DoesNotExist:
            raise forms.ValidationError('Учитель с таким логином не найден.')
        teacher_profile = getattr(teacher, 'profile', None)
        if not (teacher.is_staff or (teacher_profile and teacher_profile.is_teacher_approved)):
            raise forms.ValidationError('Указанный пользователь пока не может быть выбран как учитель.')
        return teacher_login

    def clean_role(self):
        role = self.cleaned_data['role']
        if role == UserProfile.Role.STUDENT and not self.platform_settings.allow_student_self_signup:
            raise forms.ValidationError('Саморегистрация учеников временно отключена.')
        if role == UserProfile.Role.TEACHER and not self.platform_settings.allow_teacher_self_signup:
            raise forms.ValidationError('Саморегистрация учителей временно отключена.')
        return role

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get('email', '')
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
            profile = user.profile
            profile.role = self.cleaned_data['role']
            profile.telegram_login = (self.cleaned_data.get('telegram_login') or '').strip()
            if profile.role == UserProfile.Role.TEACHER:
                profile.teacher_approval_status = UserProfile.TeacherApprovalStatus.PENDING
                profile.teacher_approved_by = None
                profile.teacher_approved_at = None
            else:
                profile.teacher_approval_status = UserProfile.TeacherApprovalStatus.NOT_REQUIRED
                profile.teacher_approved_by = None
                profile.teacher_approved_at = None
            profile.save()
            teacher_login = self.cleaned_data.get('teacher_login')
            if teacher_login and profile.role == UserProfile.Role.STUDENT:
                teacher = User.objects.get(username=teacher_login)
                TeacherStudentLink.objects.get_or_create(
                    teacher=teacher,
                    student=user,
                    defaults={'created_by': user},
                )
        return user


class ProfileForm(forms.ModelForm):
    email = forms.EmailField(label='Почта', required=True)
    first_name = forms.CharField(label='Имя', required=True, max_length=150)
    last_name = forms.CharField(label='Фамилия', required=True, max_length=150)
    telegram_login = forms.CharField(label='Логин в Telegram', required=False, max_length=64)
    teacher_login = forms.CharField(
        label='Укажите логин учителя, чтобы он мог задавать вам ДЗ (необязательно)',
        required=False,
        max_length=150,
    )

    class Meta:
        model = UserProfile
        fields = ('statistics_share_enabled',)
        labels = {
            'statistics_share_enabled': 'Внешняя ссылка со статистикой',
        }
        help_texts = {
            'statistics_share_enabled': (
                'Ссылка позволяет показать обезличенную таблицу с домашними работами и баллами.'
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user
        self.fields['email'].initial = user.email
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        self.fields['telegram_login'].initial = self.instance.telegram_login
        if self.instance.role != UserProfile.Role.STUDENT:
            self.fields.pop('statistics_share_enabled')
        if self.instance.role != UserProfile.Role.STUDENT:
            self.fields.pop('teacher_login')

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            return ''
        queryset = User.objects.filter(email__iexact=email).exclude(pk=self.instance.user_id)
        if queryset.exists():
            raise forms.ValidationError('Этот адрес электронной почты уже используется.')
        return email

    def clean_teacher_login(self):
        teacher_login = (self.cleaned_data.get('teacher_login') or '').strip()
        if not teacher_login:
            return ''
        try:
            teacher = User.objects.get(username=teacher_login)
        except User.DoesNotExist:
            raise forms.ValidationError('Учитель с таким логином не найден.')
        teacher_profile = getattr(teacher, 'profile', None)
        if not (teacher.is_staff or (teacher_profile and teacher_profile.is_teacher_approved)):
            raise forms.ValidationError('Указанный пользователь пока не может быть выбран как учитель.')
        return teacher_login

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        profile.telegram_login = (self.cleaned_data.get('telegram_login') or '').strip()
        if commit:
            user.save(update_fields=['email', 'first_name', 'last_name'])
            profile.save()
            teacher_login = self.cleaned_data.get('teacher_login')
            if teacher_login and profile.role == UserProfile.Role.STUDENT:
                teacher = User.objects.get(username=teacher_login)
                TeacherStudentLink.objects.get_or_create(
                    teacher=teacher,
                    student=user,
                    defaults={'created_by': user},
                )
        return profile


class TeacherGroupCreateForm(forms.ModelForm):
    students = forms.ModelMultipleChoiceField(
        label='Ученики',
        queryset=User.objects.none(),
        required=False,
    )

    class Meta:
        model = StudyGroup
        fields = ('name', 'description', 'students')
        labels = {
            'name': 'Новая группа',
            'description': 'Описание группы',
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher is not None:
            if teacher.is_staff:
                queryset = User.objects.filter(profile__role=UserProfile.Role.STUDENT).distinct()
            else:
                direct_student_ids = TeacherStudentLink.objects.filter(
                    teacher=teacher,
                    is_active=True,
                ).values_list('student_id', flat=True)
                group_student_ids = StudyGroup.objects.filter(
                    teachers=teacher,
                    is_active=True,
                ).values_list('students__id', flat=True)
                student_ids = {student_id for student_id in direct_student_ids if student_id}
                student_ids.update(student_id for student_id in group_student_ids if student_id)
                queryset = User.objects.filter(
                    id__in=student_ids,
                    profile__role=UserProfile.Role.STUDENT,
                ).distinct()
            self.fields['students'].queryset = queryset.order_by('username')

    def save(self, teacher, commit=True):
        group = super().save(commit=commit)
        if commit:
            group.teachers.add(teacher)
            group.students.set(self.cleaned_data['students'])
        return group


class TeacherGroupUpdateForm(TeacherGroupCreateForm):
    class Meta(TeacherGroupCreateForm.Meta):
        labels = {
            'name': 'Название группы',
            'description': 'Описание группы',
            'students': 'Ученики',
        }


class TeacherStudentEditForm(forms.ModelForm):
    username = forms.CharField(
        label='Логин',
        max_length=20,
        error_messages={'max_length': 'Логин не должен быть длиннее 20 символов.'},
    )
    first_name = forms.CharField(label='Имя', required=True, max_length=150)
    last_name = forms.CharField(label='Фамилия', required=True, max_length=150)
    email = forms.EmailField(label='Почта', required=True)
    study_group = forms.ModelChoiceField(
        label='Группа',
        queryset=StudyGroup.objects.none(),
        required=False,
        empty_label='Без группы',
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'study_group')
        labels = {
            'username': 'Логин',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'email': 'Почта',
            'study_group': 'Группа',
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if actor is not None:
            if actor.is_staff:
                manageable_groups = StudyGroup.objects.filter(is_active=True).order_by('name')
            else:
                manageable_groups = StudyGroup.objects.filter(is_active=True, teachers=actor).order_by('name')
            self.fields['study_group'].queryset = manageable_groups
            self.fields['study_group'].initial = (
                self.instance.student_study_groups.filter(id__in=manageable_groups.values('id')).order_by('name').first()
            )

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            return ''
        queryset = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError('Этот адрес электронной почты уже используется.')
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        study_group = self.cleaned_data.get('study_group')
        manageable_groups = self.fields['study_group'].queryset
        user.student_study_groups.remove(*manageable_groups)
        if study_group is not None:
            study_group.students.add(user)
        return user


class AdminUserEditForm(forms.ModelForm):
    username = forms.CharField(
        label='Логин',
        max_length=20,
        error_messages={'max_length': 'Логин не должен быть длиннее 20 символов.'},
    )
    first_name = forms.CharField(label='Имя', required=True, max_length=150)
    last_name = forms.CharField(label='Фамилия', required=True, max_length=150)
    email = forms.EmailField(label='Почта', required=True)
    telegram_login = forms.CharField(label='Логин в Telegram', required=False, max_length=64)
    role = forms.ChoiceField(label='Роль', choices=UserProfile.Role.choices)
    teacher_approval_status = forms.ChoiceField(
        label='Статус учителя',
        choices=UserProfile.TeacherApprovalStatus.choices,
        required=False,
    )
    is_staff = forms.BooleanField(label='Админ', required=False)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_staff')
        labels = {
            'username': 'Логин',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'email': 'Почта',
            'is_staff': 'Админ',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = self.instance.profile
        self.fields['role'].initial = profile.role
        self.fields['teacher_approval_status'].initial = profile.teacher_approval_status
        self.fields['telegram_login'].initial = profile.telegram_login

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            return ''
        queryset = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError('Этот адрес электронной почты уже используется.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        approval_status = cleaned_data.get('teacher_approval_status')
        if role == UserProfile.Role.STUDENT:
            cleaned_data['teacher_approval_status'] = UserProfile.TeacherApprovalStatus.NOT_REQUIRED
        elif approval_status == UserProfile.TeacherApprovalStatus.NOT_REQUIRED:
            self.add_error('teacher_approval_status', 'Для учителя выберите осмысленный статус.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        profile = user.profile
        profile.role = self.cleaned_data['role']
        profile.teacher_approval_status = self.cleaned_data['teacher_approval_status']
        profile.telegram_login = (self.cleaned_data.get('telegram_login') or '').strip()
        if profile.role == UserProfile.Role.STUDENT:
            profile.teacher_approved_by = None
            profile.teacher_approved_at = None
        elif profile.teacher_approval_status == UserProfile.TeacherApprovalStatus.APPROVED and not profile.teacher_approved_at:
            profile.teacher_approved_at = timezone.now()
        elif profile.teacher_approval_status != UserProfile.TeacherApprovalStatus.APPROVED:
            profile.teacher_approved_by = None
            profile.teacher_approved_at = None
        if commit:
            user.save()
            profile.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Пожалуйста, введите правильные имя пользователя и пароль. Оба поля чувствительны к регистру.',
        'inactive': 'Этот аккаунт отключен.',
    }

    username = forms.CharField(label='Логин')
    password = forms.CharField(label='Пароль', strip=False, widget=forms.PasswordInput)
