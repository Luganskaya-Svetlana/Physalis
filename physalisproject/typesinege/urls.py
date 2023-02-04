from django.urls import path, re_path

from . import views

app_name = 'typesinege'
urlpatterns = [
    path('', views.TypesView.as_view(), name='list'),
    re_path(r'^(?P<number>[1-9]\d*)/$', views.ProblemsView.as_view(),
            name='problems')
]
