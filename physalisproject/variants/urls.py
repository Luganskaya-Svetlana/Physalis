from django.urls import path

from . import views

app_name = 'variants'
urlpatterns = [
    path('', views.VariantsView.as_view(), name='list'),
]
