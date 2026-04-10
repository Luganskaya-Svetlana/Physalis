from django.urls import path, re_path

from . import views

app_name = 'variants'
urlpatterns = [
    path('current/', views.CurrentVariantSelectionView.as_view(), name='current'),
    path('current/data/', views.CurrentVariantSelectionDataView.as_view(), name='current-data'),
    path('current/problem/', views.CurrentVariantSelectionProblemView.as_view(), name='current-problem'),
    path('current/clear/', views.CurrentVariantSelectionClearView.as_view(), name='current-clear'),
    path('', views.VariantsView.as_view(), name='list'),
    re_path(r'^(?P<pk>[1-9]\d*)-(?P<slug>[a-z]{4})/$',
            views.VariantAnswerView.as_view(), name='answers'),
    re_path(r'^(?P<pk>[1-9]\d*)/$', views.VariantView.as_view(),
            name='detail'),
]
