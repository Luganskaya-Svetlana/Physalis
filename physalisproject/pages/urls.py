from django.urls import path
from .views import clear_flatpage_cache

app_name = 'pages'

urlpatterns = [
    path('clear-flatpage-cache/', clear_flatpage_cache, name='clear_flatpage_cache'),
]
