from django.utils.encoding import iri_to_uri


def normalize_cache_path(path: str) -> str:
    if not path.startswith('/'):
        path = f'/{path}'
    return iri_to_uri(path)


def flatpage_cache_key(path: str, is_staff: bool) -> str:
    normalized = normalize_cache_path(path)
    role = 'staff' if is_staff else 'anon'
    return f'flatpage:{role}:{normalized}'
