from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from physalisproject.cache_utils import flatpage_cache_key


@staff_member_required
@require_POST
def clear_flatpage_cache(request):
    path = request.POST.get('path', '').strip()
    if path:
        cache.delete(flatpage_cache_key(path, is_staff=False))
        cache.delete(flatpage_cache_key(path, is_staff=True))

    next_url = request.POST.get('next') or path or '/'
    return redirect(next_url)
