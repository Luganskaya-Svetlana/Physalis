import time

from django.conf import settings
from django.contrib.flatpages.middleware import FlatpageFallbackMiddleware
from django.contrib.flatpages.views import flatpage
from django.http import Http404
from django.views.decorators.cache import cache_page


def flatpage_with_debug_header(request, url):
    response = flatpage(request, url)
    response['X-Flatpage-Generated-At'] = f'{time.time():.6f}'
    return response


cached_flatpage_view = cache_page(60 * 60)(flatpage_with_debug_header)


class CachedFlatpageFallbackMiddleware(FlatpageFallbackMiddleware):
    def process_response(self, request, response):
        if response.status_code != 404:
            return response

        try:
            if request.user.is_authenticated:
                return flatpage_with_debug_header(request, request.path_info)
            return cached_flatpage_view(request, request.path_info)
        except Http404:
            return response
        except Exception:
            if settings.DEBUG:
                raise
            return response
