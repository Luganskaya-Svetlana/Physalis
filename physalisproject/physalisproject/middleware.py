from django.conf import settings
from django.contrib.flatpages.middleware import FlatpageFallbackMiddleware
from django.contrib.flatpages.views import flatpage
from django.core.cache import cache
from django.http import Http404

from .cache_utils import flatpage_cache_key


class CachedFlatpageFallbackMiddleware(FlatpageFallbackMiddleware):
    cache_timeout = 7 * 24 * 60 * 60

    def process_response(self, request, response):
        if response.status_code != 404:
            return response

        try:
            key = flatpage_cache_key(
                request.path_info,
                is_staff=bool(getattr(request.user, 'is_staff', False)),
            )

            cached_response = cache.get(key)
            if cached_response is not None:
                return cached_response

            page_response = flatpage(request, request.path_info)
            cache.set(key, page_response, self.cache_timeout)
            return page_response

        except Http404:
            return response
        except Exception:
            if settings.DEBUG:
                raise
            return response
