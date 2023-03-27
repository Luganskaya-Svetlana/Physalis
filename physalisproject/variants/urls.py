from django.urls import path, re_path

from . import views

app_name = 'variants'
urlpatterns = [
    path('', views.VariantsView.as_view(), name='list'),
    re_path(r'^(?P<pk>[1-9]\d*)/$', views.VariantView.as_view(),
            name='detail'),
]
