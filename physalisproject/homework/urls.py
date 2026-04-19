from django.urls import path

from . import views


app_name = 'homework'


urlpatterns = [
    path('', views.HomeworkSubmissionListView.as_view(), name='list'),
    path('attachment/<int:pk>/', views.HomeworkAttachmentDetailView.as_view(), name='attachment-detail'),
    path('<int:pk>/', views.HomeworkAssignmentDetailView.as_view(), name='detail'),
    path('<int:pk>/practice/start/', views.HomeworkPracticeAttemptStartView.as_view(), name='practice-start'),
    path('<int:pk>/practice/<int:attempt_id>/', views.HomeworkPracticeAttemptDetailView.as_view(), name='practice-detail'),
    path('<int:pk>/edit/', views.HomeworkAssignmentUpdateView.as_view(), name='edit'),
    path('<int:pk>/autosave/', views.HomeworkSubmissionAutosaveView.as_view(), name='autosave'),
    path('create/from-variant/<int:variant_id>/', views.HomeworkAssignmentCreateView.as_view(), name='create'),
]
