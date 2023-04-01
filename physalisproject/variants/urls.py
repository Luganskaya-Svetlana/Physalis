from django.urls import path, re_path

from . import views

app_name = 'variants'
urlpatterns = [
    path('', views.VariantsView.as_view(), name='list'),
    re_path(r'^(?P<pk>[1-9]\d*)-(?P<slug>[a-z]{4})/$',
            views.VariantAnswerView.as_view(),
            name='answers'),
    re_path(r'^(?P<pk>[1-9]\d*)/$', views.VariantView.as_view(),
            name='detail'),
]
