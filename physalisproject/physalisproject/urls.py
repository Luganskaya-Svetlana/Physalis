from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('problems/', include('problems.urls', namespace='problems')),
    path('types/', include('typesinege.urls', namespace='typesinege')),
    path('variants/', include('variants.urls', namespace='variants')),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
