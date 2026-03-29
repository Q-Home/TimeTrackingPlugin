import hmac
import ipaddress

from flask import current_app, request


def _trusted_networks():
    raw_value = current_app.config.get("INTERNAL_TRUSTED_SUBNETS", "")
    networks = []

    for item in raw_value.split(","):
        candidate = item.strip()
        if not candidate:
            continue
        try:
            networks.append(ipaddress.ip_network(candidate, strict=False))
        except ValueError:
            continue

    return networks


def has_valid_internal_api_key():
    internal_api_key = current_app.config.get("INTERNAL_API_KEY", "")
    provided_api_key = request.headers.get("X-Internal-API-Key", "")

    if not internal_api_key or not provided_api_key:
        return False

    return hmac.compare_digest(provided_api_key, internal_api_key)


def is_trusted_internal_request():
    if has_valid_internal_api_key():
        return True

    remote_addr = request.remote_addr
    if not remote_addr:
        return False

    try:
        remote_ip = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False

    return any(remote_ip in network for network in _trusted_networks())
