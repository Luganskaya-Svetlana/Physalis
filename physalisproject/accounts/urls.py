from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import (
    admin_users_view,
    admin_user_edit_view,
    CustomLoginView,
    GroupInviteView,
    PublicStudentStatsView,
    SignUpView,
    profile_edit_view,
    student_stats_view,
    profile_view,
    teacher_student_edit_view,
    teacher_student_stats_view,
    teacher_groups_view,
    teacher_students_view,
    unread_messages_view,
)


app_name = 'accounts'


urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path(
        'logout/',
        LogoutView.as_view(),
        name='logout',
    ),
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', profile_edit_view, name='profile-edit'),
    path('users/', admin_users_view, name='users'),
    path('users/<int:user_id>/edit/', admin_user_edit_view, name='user-edit'),
    path('stats/', student_stats_view, name='stats'),
    path('students/<int:student_id>/stats/', teacher_student_stats_view, name='student-stats'),
    path('students/', teacher_students_view, name='students'),
    path('students/<int:student_id>/edit/', teacher_student_edit_view, name='student-edit'),
    path('groups/', teacher_groups_view, name='groups'),
    path('messages/', unread_messages_view, name='messages'),
    path('group-invite/<uuid:token>/', GroupInviteView.as_view(), name='group-invite'),
    path('stats/<uuid:token>/', PublicStudentStatsView.as_view(), name='public-stats'),
]
