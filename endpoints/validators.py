import socket
import ipaddress

from urllib.parse import urlparse
from django.core.exceptions import ValidationError


def is_safe_ip(ip: str) -> bool:
    address = ipaddress.ip_address(ip)

    return (
        address.is_global
        and not address.is_loopback
        and not address.is_private
        and not address.is_link_local
        and not address.is_multicast
        and not address.is_reserved
        and not address.is_unspecified
    )


def validate_endpoint_url(url: str):
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValidationError("Only HTTP and HTTPS are allowed.")

    if not parsed.hostname:
        raise ValidationError("URL must contain a hostname.")

    if parsed.username or parsed.password:
        raise ValidationError("Credentials in URL are not allowed.")

    hostname = parsed.hostname.lower().rstrip(".")

    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValidationError("Localhost is not allowed.")

    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if not is_safe_ip(hostname):
            raise ValidationError("Unsafe IP address.")
        return

    try:
        resolved_ips = socket.getaddrinfo(
            hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror:
        raise ValidationError("Hostname could not be resolved.")

    if not resolved_ips:
        raise ValidationError("Hostname has no resolved addresses.")

    for result in resolved_ips:
        ip = result[4][0]

        if not is_safe_ip(ip):
            raise ValidationError(
                "Hostname resolves to an unsafe IP address."
            )
