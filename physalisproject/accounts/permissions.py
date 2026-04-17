from django.contrib.auth import get_user_model

from .models import StudyGroup, TeacherStudentLink, UserProfile


User = get_user_model()


def can_manage_homework(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    if user.is_staff:
        return True
    profile = getattr(user, 'profile', None)
    return bool(profile and profile.is_teacher_approved)


def get_manageable_groups(user):
    if not getattr(user, 'is_authenticated', False):
        return StudyGroup.objects.none()
    if user.is_staff:
        return StudyGroup.objects.filter(is_active=True)
    if not can_manage_homework(user):
        return StudyGroup.objects.none()
    return StudyGroup.objects.filter(is_active=True, teachers=user)


def get_manageable_students(user):
    if not getattr(user, 'is_authenticated', False):
        return User.objects.none()
    if user.is_staff:
        return User.objects.filter(profile__role=UserProfile.Role.STUDENT).distinct()
    if not can_manage_homework(user):
        return User.objects.none()

    direct_student_ids = TeacherStudentLink.objects.filter(
        teacher=user,
        is_active=True,
    ).values_list('student_id', flat=True)
    group_student_ids = StudyGroup.objects.filter(
        teachers=user,
        is_active=True,
    ).values_list('students__id', flat=True)
    student_ids = {student_id for student_id in direct_student_ids if student_id}
    student_ids.update(student_id for student_id in group_student_ids if student_id)
    return User.objects.filter(
        id__in=student_ids,
        profile__role=UserProfile.Role.STUDENT,
    ).distinct()
