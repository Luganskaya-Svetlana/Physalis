from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.contrib.sitemaps.views import sitemap
from .sitemap import StaticViewSitemap, ProblemSitemap, FlatPageSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'problem': ProblemSitemap,
    'flatpages': FlatPageSitemap,
}


urlpatterns = [
    path('admin/', admin.site.urls),
    path('problems/', include('problems.urls', namespace='problems')),
    path('types/', include('typesinege.urls', namespace='typesinege')),
    path('variants/', include('variants.urls', namespace='variants')),
    path('tags/', include('tags.urls', namespace='tags')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
