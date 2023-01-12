from django.urls import re_path

from . import views

app_name = 'problems'
urlpatterns = [
    re_path(r'^(?P<pk>[1-9]\d*)/$', views.ProblemView.as_view(),
            name='detail'),
]
