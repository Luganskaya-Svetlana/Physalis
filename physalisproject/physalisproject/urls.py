from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from problems.views import GameStartView, ProblemGameView
from .sitemap import FlatPageSitemap, ProblemSitemap, StaticViewSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'problem': ProblemSitemap,
    'flatpages': FlatPageSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),

    path('game/', GameStartView.as_view(), name='game-start'),
    path('game/<int:pk>/', ProblemGameView.as_view(), name='game-detail'),

    path('problems/', include('problems.urls', namespace='problems')),
    path('types/', include('typesinege.urls', namespace='typesinege')),
    path('variants/', include('variants.urls', namespace='variants')),
    path('tags/', include('tags.urls', namespace='tags')),
    path('pages/', include('pages.urls', namespace='pages')),

    path(
        'sitemap.xml',
        sitemap,
        {'sitemaps': sitemaps},
        name='django.contrib.sitemaps.views.sitemap'
    ),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
