from django.contrib.auth import get_user_model

from .models import StudyGroup


User = get_user_model()


def attach_student_to_group(student, group):
    if not hasattr(student, 'profile') or student.profile.role != student.profile.Role.STUDENT:
        return False
    group.students.add(student)
    return True
