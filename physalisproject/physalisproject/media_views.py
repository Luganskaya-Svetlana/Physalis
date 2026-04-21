from pathlib import Path
from urllib.parse import urljoin

from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.views.static import serve


def serve_media_or_redirect(request, path):
    media_root = Path(settings.MEDIA_ROOT).resolve()
    media_path = (media_root / path).resolve()

    try:
        media_path.relative_to(media_root)
    except ValueError as exc:
        raise Http404("Invalid media path") from exc

    if media_path.is_file():
        return serve(request, path, document_root=media_root)

    remote_media_url = getattr(settings, 'REMOTE_MEDIA_URL', '').strip()
    if remote_media_url:
        return HttpResponseRedirect(urljoin(remote_media_url.rstrip('/') + '/', path))

    raise Http404("Media file not found")
