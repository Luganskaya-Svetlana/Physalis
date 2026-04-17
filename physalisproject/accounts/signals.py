from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


User = get_user_model()


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        default_role = UserProfile.Role.TEACHER if instance.is_staff else UserProfile.Role.STUDENT
        approval_status = (
            UserProfile.TeacherApprovalStatus.APPROVED
            if instance.is_staff
            else UserProfile.TeacherApprovalStatus.NOT_REQUIRED
        )
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                'role': default_role,
                'teacher_approval_status': approval_status,
            },
        )
        return

    UserProfile.objects.get_or_create(user=instance)
