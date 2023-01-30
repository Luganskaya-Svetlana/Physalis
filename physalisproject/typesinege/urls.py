from django.urls import path

from . import views

app_name = 'typesinege'
urlpatterns = [
    path('', views.TypesView.as_view(), name='list')
]
