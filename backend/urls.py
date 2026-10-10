"""Validate operator-configured URLs without DNS lookups or network access."""
from ipaddress import ip_address
from urllib.parse import urlsplit

LOCAL_HOSTS = {'localhost', 'n8n', 'app', 'host.docker.internal', 'gateway.docker.internal'}


def service_url(value: str, name: str = 'Service') -> str:
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        raise ValueError(f'{name} URL has an invalid hostname or port') from None
    if not hostname or parsed.scheme not in ('http', 'https') or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f'{name} needs an HTTP(S) base URL without credentials, query, or fragment')
    local = hostname in LOCAL_HOSTS or hostname.endswith('.localhost')
    try:
        address = ip_address(hostname)
        local = address.is_loopback or (address.is_private and not address.is_unspecified and not address.is_reserved)
    except ValueError:
        pass
    if parsed.scheme == 'http' and not local:
        raise ValueError(f'{name} HTTP is limited to localhost or a private Docker/LAN address; use HTTPS for public hosts')
    if port == 0:
        raise ValueError(f'{name} URL needs a valid port')
    return value.rstrip('/')
