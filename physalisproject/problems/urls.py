from django.urls import path, re_path

from . import views

app_name = 'problems'


urlpatterns = [
    path('', views.problems_view, name='list'),
    re_path(r'^(?P<pk>[1-9]\d*)/$', views.ProblemView.as_view(), name='detail'),
]
