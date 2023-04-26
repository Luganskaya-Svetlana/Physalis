from django.urls import path

from . import views

app_name = 'tags'
urlpatterns = [
    path('', views.TagsView.as_view(), name='list'),
    path('<slug:slug>', views.ProblemsView.as_view(),
         name='problems')
]
