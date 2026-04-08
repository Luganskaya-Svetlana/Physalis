from django.conf import settings
from django.contrib.flatpages.middleware import FlatpageFallbackMiddleware
from django.contrib.flatpages.views import flatpage
from django.core.cache import cache
from django.http import Http404, HttpResponse
import time

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

            cached_data = cache.get(key)
            if cached_data is not None:
                cached_response = HttpResponse(
                    content=cached_data['content'],
                    status=cached_data['status_code'],
                    content_type=cached_data['content_type'],
                )
                if cached_data.get('charset'):
                    cached_response.charset = cached_data['charset']

                cached_response['X-Flatpage-Cache'] = 'HIT'
                cached_response['X-Flatpage-Cache-Key'] = key
                cached_response['X-Flatpage-Generated-At'] = cached_data['generated_at']
                return cached_response

            page_response = flatpage(request, request.path_info)

            # На всякий случай убеждаемся, что контент уже отрендерен
            content = page_response.content

            cache_data = {
                'content': content,
                'status_code': page_response.status_code,
                'content_type': page_response.get('Content-Type', 'text/html; charset=utf-8'),
                'charset': getattr(page_response, 'charset', None),
                'generated_at': f'{time.time():.6f}',
            }
            cache.set(key, cache_data, self.cache_timeout)

            fresh_response = HttpResponse(
                content=cache_data['content'],
                status=cache_data['status_code'],
                content_type=cache_data['content_type'],
            )
            if cache_data.get('charset'):
                fresh_response.charset = cache_data['charset']

            fresh_response['X-Flatpage-Cache'] = 'MISS'
            fresh_response['X-Flatpage-Cache-Key'] = key
            fresh_response['X-Flatpage-Generated-At'] = cache_data['generated_at']
            return fresh_response

        except Http404:
            return response
        except Exception:
            if settings.DEBUG:
                raise
            return response
